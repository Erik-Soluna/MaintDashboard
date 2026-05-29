"""
Backfill Equipment.next_maintenance_date and dga_due_date from current schedules
and completed activities.

These fields used to only be set manually / via CSV. After the scheduling fixes
(#84/#86) they are kept up to date on activity completion, but existing rows need
a one-time recompute. Dry-run by default; pass --apply to persist.
"""

from django.core.management.base import BaseCommand

from equipment.models import Equipment
from maintenance.models import MaintenanceActivity, MaintenanceSchedule
from maintenance.scheduling import add_one_period
from maintenance.signals import _is_dga_activity


class Command(BaseCommand):
    help = "Recompute Equipment next_maintenance_date and dga_due_date. Dry-run unless --apply."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Persist changes (otherwise report only).')

    def handle(self, *args, **options):
        apply_changes = options['apply']
        self.stdout.write(f"Recompute equipment due dates [{'APPLY' if apply_changes else 'DRY-RUN'}]")

        changed = 0
        for eq in Equipment.objects.all().iterator():
            update_fields = []

            dues = [s.get_next_due_date()
                    for s in MaintenanceSchedule.objects.filter(equipment=eq, is_active=True)]
            dues = [d for d in dues if d]
            if dues:
                soonest = min(dues)
                if eq.next_maintenance_date != soonest:
                    eq.next_maintenance_date = soonest
                    update_fields.append('next_maintenance_date')

            completed = (MaintenanceActivity.objects
                         .filter(equipment=eq, status='completed', actual_end__isnull=False)
                         .order_by('-actual_end'))
            last_dga = next((a for a in completed if _is_dga_activity(a)), None)
            if last_dga:
                sch = MaintenanceSchedule.objects.filter(
                    equipment=eq, activity_type=last_dga.activity_type, is_active=True
                ).first()
                base = last_dga.actual_end.date()
                new_dga = (add_one_period(base, sch.frequency, sch.frequency_days)
                           if sch else add_one_period(base, 'annual', None))
                if eq.dga_due_date != new_dga:
                    eq.dga_due_date = new_dga
                    update_fields.append('dga_due_date')

            if update_fields:
                changed += 1
                self.stdout.write(
                    f"  {eq.name}: " + ", ".join(
                        f"{f}={getattr(eq, f)}" for f in update_fields)
                )
                if apply_changes:
                    eq.save(update_fields=update_fields)

        summary = f"{changed} equipment record(s) need(ed) updates."
        if not apply_changes and changed:
            summary += " Re-run with --apply to persist."
        self.stdout.write(self.style.SUCCESS(summary))
