"""
Convert legacy standalone CalendarEvents (not linked to a MaintenanceActivity)
into MaintenanceActivities and link them.

Background: the app now treats the calendar as a view of maintenance activities.
Standalone CalendarEvents created by the old calendar popup have no working edit
path (edit_event just redirects). Converting them to MaintenanceActivities — and
linking the original event to the new activity — makes them editable through the
maintenance flow and keeps them showing exactly once on the calendar.

Dry-run by default; pass --apply to persist.
"""

from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand

from events.models import CalendarEvent
from maintenance.models import MaintenanceActivity, MaintenanceActivityType
from maintenance.utils import parse_wallclock_to_utc, DEFAULT_ACTIVITY_TIMEZONE


class Command(BaseCommand):
    help = ("Convert unlinked CalendarEvents into MaintenanceActivities and link "
            "them so they become editable. Dry-run unless --apply.")

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Persist changes (otherwise report only).')
        parser.add_argument('--default-activity-type-id', type=int, default=None,
                            help='MaintenanceActivityType id to use when an event '
                                 'has no resolvable activity type.')

    def _resolve_activity_type(self, event, default_type):
        """event_type may be 'activity_<id>' or a type name; fall back to default."""
        et = (event.event_type or '').strip()
        if et.startswith('activity_'):
            try:
                return MaintenanceActivityType.objects.get(id=int(et.split('_', 1)[1]))
            except (ValueError, MaintenanceActivityType.DoesNotExist):
                pass
        match = MaintenanceActivityType.objects.filter(name__iexact=et).first()
        return match or default_type

    def handle(self, *args, **options):
        apply_changes = options['apply']
        self.stdout.write(
            f"Convert unlinked CalendarEvents -> MaintenanceActivities "
            f"[{'APPLY' if apply_changes else 'DRY-RUN'}]"
        )

        default_type = None
        if options['default_activity_type_id']:
            default_type = MaintenanceActivityType.objects.filter(
                id=options['default_activity_type_id']).first()
        if not default_type:
            default_type = MaintenanceActivityType.objects.filter(
                is_active=True).order_by('id').first()
        if not default_type:
            self.stdout.write(self.style.ERROR(
                "No MaintenanceActivityType exists to use as a fallback type. Aborting."))
            return
        self.stdout.write(f"Fallback activity type: {default_type.name} (id={default_type.id})")

        events = (CalendarEvent.objects
                  .filter(maintenance_activity__isnull=True)
                  .select_related('equipment', 'assigned_to', 'created_by'))
        total = events.count()
        converted = skipped = 0

        for event in events.iterator():
            if not event.equipment_id:
                skipped += 1
                self.stdout.write(f"  SKIP event #{event.id} '{event.title}': no equipment")
                continue

            atype = self._resolve_activity_type(event, default_type)
            start_t = event.start_time or time(8, 0)
            start_utc = parse_wallclock_to_utc(
                datetime.combine(event.event_date, start_t), DEFAULT_ACTIVITY_TIMEZONE)
            if event.end_time:
                end_utc = parse_wallclock_to_utc(
                    datetime.combine(event.event_date, event.end_time), DEFAULT_ACTIVITY_TIMEZONE)
                if end_utc <= start_utc:
                    end_utc = start_utc + timedelta(hours=1)
            else:
                end_utc = start_utc + timedelta(hours=1)

            self.stdout.write(
                f"  CONVERT event #{event.id} '{event.title}' -> activity "
                f"(type={atype.name}, start={start_utc.date()})")

            if apply_changes:
                activity = MaintenanceActivity.objects.create(
                    equipment=event.equipment,
                    activity_type=atype,
                    title=event.title,
                    description=event.description or '',
                    status='completed' if event.is_completed else 'scheduled',
                    priority=event.priority or 'medium',
                    scheduled_start=start_utc,
                    scheduled_end=end_utc,
                    timezone=DEFAULT_ACTIVITY_TIMEZONE,
                    assigned_to=event.assigned_to,
                    created_by=event.created_by,
                )
                event.maintenance_activity = activity
                event.save(update_fields=['maintenance_activity'])
            converted += 1

        summary = f"{total} unlinked events; {converted} convertible, {skipped} skipped."
        if not apply_changes and converted:
            summary += " Re-run with --apply to persist."
        self.stdout.write(self.style.SUCCESS(summary))
