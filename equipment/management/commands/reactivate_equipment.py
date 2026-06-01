"""
Recover equipment wrongly deactivated by the edit form bug.

Until fixed, editing an equipment posted no is_active value (the edit template
didn't render the checkbox), so saving set is_active=False and the equipment
disappeared from the maintenance pickers. This reactivates equipment that is
is_active=False but whose operational status is 'active' or 'maintenance'
(i.e. clearly still in service) — it does NOT touch 'retired'/'inactive' status
equipment, which may be deactivated on purpose.

Dry-run by default; pass --apply to persist.
"""

from django.core.management.base import BaseCommand

from equipment.models import Equipment


class Command(BaseCommand):
    help = ("Reactivate equipment wrongly set is_active=False whose status is "
            "active/maintenance. Dry-run unless --apply.")

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Persist changes (otherwise report only).')

    def handle(self, *args, **options):
        apply_changes = options['apply']
        self.stdout.write(f"Reactivate wrongly-deactivated equipment [{'APPLY' if apply_changes else 'DRY-RUN'}]")

        qs = Equipment.objects.filter(is_active=False, status__in=['active', 'maintenance']) \
            .select_related('location')
        total = qs.count()
        for eq in qs.iterator():
            loc = eq.location.name if eq.location else 'no location'
            self.stdout.write(f"  {eq.name}  (status={eq.status}, {loc})")
            if apply_changes:
                eq.is_active = True
                eq.save(update_fields=['is_active'])

        summary = f"{total} equipment record(s) would be reactivated."
        if apply_changes:
            summary = f"Reactivated {total} equipment record(s)."
        elif total:
            summary += " Re-run with --apply to persist."
        self.stdout.write(self.style.SUCCESS(summary))
