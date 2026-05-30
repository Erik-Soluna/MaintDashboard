"""
Rebuild CalendarEvent local time fields from their linked maintenance activities.

Earlier code stored CalendarEvent.event_date/start_time/end_time from the UTC
instant of the activity instead of the activity's local timezone, so events could
show on the wrong day/time. This command re-derives those split fields from each
linked activity via CalendarEvent.set_times_from_activity (idempotent).

Dry-run by default; pass --apply to write changes.
"""

from django.core.management.base import BaseCommand

from events.models import CalendarEvent


class Command(BaseCommand):
    help = "Rebuild CalendarEvent local time fields from linked maintenance activities."

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Persist changes. Without this flag the command only reports (dry-run).',
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        mode = 'APPLY' if apply_changes else 'DRY-RUN'
        self.stdout.write(f'Rebuilding CalendarEvent times from activities [{mode}]')

        events = (CalendarEvent.objects
                  .filter(maintenance_activity__isnull=False)
                  .select_related('maintenance_activity'))

        checked = 0
        changed = 0
        for event in events.iterator():
            checked += 1
            old = (event.event_date, event.start_time, event.end_time)
            event.set_times_from_activity(event.maintenance_activity)
            new = (event.event_date, event.start_time, event.end_time)
            if old != new:
                changed += 1
                self.stdout.write(
                    f'  #{event.id}: {old[0]} {old[1]}-{old[2]} -> {new[0]} {new[1]}-{new[2]}'
                )
                if apply_changes:
                    event.save(update_fields=['event_date', 'start_time', 'end_time'])

        summary = f'Checked {checked} linked events; {changed} need(ed) correction.'
        if not apply_changes and changed:
            summary += ' Re-run with --apply to persist.'
        self.stdout.write(self.style.SUCCESS(summary))
