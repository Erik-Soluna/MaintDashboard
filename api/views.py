"""Dynamic, read-only API. Reflects live models + diagnostics for an AI agent."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination

from .registry import exposed_models, get_model, model_key, field_metadata, safe_field_names
from .serializers import build_serializer
from .permissions import HasApiReadAccess, HasApiDeployAccess


class ApiPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


def _resolve_model(kwargs):
    model = get_model(kwargs.get('app_label'), kwargs.get('model_name'))
    if not model:
        raise NotFound('Unknown or non-exposed model.')
    return model


class ApiRoot(APIView):
    """Self-describing index — lists every exposed model (live, never stale)."""
    permission_classes = [HasApiReadAccess]

    def get(self, request):
        models = []
        for m in exposed_models():
            models.append({
                'key': model_key(m),
                'app': m._meta.app_label,
                'model': m._meta.model_name,
                'verbose_name_plural': str(m._meta.verbose_name_plural),
                'count': m.objects.count(),
                'fields': field_metadata(m),
                'list_url': request.build_absolute_uri(f'/api/v1/data/{model_key(m)}/'),
            })
        return Response({
            'models': models,
            'diagnostics': {
                'health': request.build_absolute_uri('/api/v1/diagnostics/health/'),
                'summary': request.build_absolute_uri('/api/v1/diagnostics/summary/'),
            },
            'usage': 'List: /api/v1/data/<app>/<model>/?<field>=<value>&ordering=<field>&page_size=N',
        })


class ModelListView(ListAPIView):
    permission_classes = [HasApiReadAccess]
    pagination_class = ApiPagination

    def get_serializer_class(self):
        return build_serializer(_resolve_model(self.kwargs))

    def get_queryset(self):
        model = _resolve_model(self.kwargs)
        qs = model.objects.all()
        valid = set(safe_field_names(model))
        params = self.request.query_params
        for key in params:
            if key in ('page', 'page_size', 'ordering', 'format'):
                continue
            base = key.split('__')[0]
            if base in valid:
                try:
                    qs = qs.filter(**{key: params.get(key)})
                except Exception:
                    pass  # ignore bad filters rather than 500
        ordering = params.get('ordering')
        if ordering and ordering.lstrip('-') in valid:
            qs = qs.order_by(ordering)
        return qs


class ModelDetailView(RetrieveAPIView):
    permission_classes = [HasApiReadAccess]

    def get_serializer_class(self):
        return build_serializer(_resolve_model(self.kwargs))

    def get_queryset(self):
        return _resolve_model(self.kwargs).objects.all()


class DiagnosticsHealth(APIView):
    permission_classes = [HasApiReadAccess]

    def get(self, request):
        from core.views.helpers import get_comprehensive_system_health
        return Response(get_comprehensive_system_health())


class DiagnosticsSummary(APIView):
    """At-a-glance state for diagnosis: open/critical issues, overdue work, fleet status."""
    permission_classes = [HasApiReadAccess]

    def get(self, request):
        from django.utils import timezone
        from django.db.models import Count
        from equipment.models import Equipment, EquipmentIssue
        from maintenance.models import MaintenanceActivity

        now = timezone.now()
        open_issues = EquipmentIssue.objects.filter(status__in=['open', 'in_progress']).select_related('equipment')
        critical = open_issues.filter(severity='critical')
        overdue = (MaintenanceActivity.objects
                   .filter(scheduled_end__lt=now, status__in=['scheduled', 'pending', 'overdue'])
                   .select_related('equipment').order_by('scheduled_end'))

        eq_status = {row['status']: row['c'] for row in
                     Equipment.objects.values('status').annotate(c=Count('id'))}

        return Response({
            'generated_at': now.isoformat(),
            'equipment_total': Equipment.objects.count(),
            'equipment_by_status': eq_status,
            'open_issues': open_issues.count(),
            'critical_open_issues': critical.count(),
            'critical_issues_sample': [{
                'id': i.id, 'title': i.title, 'severity': i.severity, 'status': i.status,
                'equipment': i.equipment.name if i.equipment else None,
                'created_at': i.created_at.isoformat() if i.created_at else None,
            } for i in critical[:25]],
            'overdue_maintenance': overdue.count(),
            'overdue_sample': [{
                'id': a.id, 'title': a.title, 'status': a.status,
                'equipment': a.equipment.name if a.equipment else None,
                'scheduled_end': a.scheduled_end.isoformat() if a.scheduled_end else None,
            } for a in overdue[:25]],
        })


class RedeployView(APIView):
    """Trigger a Portainer GitOps stack redeploy. Reuses the existing webhook
    configured on the Webhook Settings page (PortainerConfig) — the same path as
    the 'Update Stack' button. Privileged: requires diagnostics.deploy /
    administration.write / staff. Every call is logged."""
    permission_classes = [HasApiDeployAccess]

    def get(self, request):
        from core.models import PortainerConfig
        cfg = PortainerConfig.get_config()
        return Response({'configured': bool(cfg.portainer_url),
                         'stack_name': cfg.stack_name or None,
                         'usage': 'POST here to trigger a Portainer stack redeploy.'})

    def post(self, request):
        import logging
        from core.views.helpers import trigger_portainer_stack_update
        logging.getLogger(__name__).warning(
            "Stack redeploy triggered via API by user=%s", getattr(request.user, 'username', '?'))
        result = trigger_portainer_stack_update()
        ok = 'successfully' in result.lower() or 'triggered' in result.lower()
        return Response({'success': ok, 'message': result}, status=200 if ok else 502)
