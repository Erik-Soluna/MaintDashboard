"""
Create PDU equipment under an MDC location, following the naming schema
"PDU {building}-{n}" (e.g. PDU 10-1 = building 10, PDU 1) — SSDEV-26 #2.

Idempotent (skips PDUs that already exist by name) and dry-run by default.

Examples:
  # building 10, PDUs 1..6 under the MDC location named "MDC 1" (dry-run)
  python manage.py create_pdus --map "10:6" --location-name "MDC 1"

  # multiple buildings, then actually write
  python manage.py create_pdus --map "10:6,11:6" --location-name "MDC 1" --apply

  # target an exact location id (skips name lookup)
  python manage.py create_pdus --building 10 --count 6 --location-id 42 --apply
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from core.models import EquipmentCategory, Location
from equipment.models import Equipment


class Command(BaseCommand):
    help = ('Create PDU equipment ("PDU {building}-{n}") under an MDC location. '
            'Dry-run unless --apply.')

    def add_arguments(self, parser):
        parser.add_argument('--map', dest='map',
                            help='Comma-separated building:count pairs, e.g. "10:6,11:6".')
        parser.add_argument('--building', type=int, help='Single building number (with --count).')
        parser.add_argument('--count', type=int, help='PDUs per building (1..count), with --building.')
        parser.add_argument('--location-id', type=int, help='Target location id (the MDC).')
        parser.add_argument('--location-name', help='Target location name, e.g. "MDC 1".')
        parser.add_argument('--site', help='Site name to disambiguate --location-name.')
        parser.add_argument('--category', default='PDU', help='Equipment category name (default: PDU).')
        parser.add_argument('--apply', action='store_true', help='Persist changes (otherwise report only).')

    # ----- helpers -----
    def _parse_buildings(self, options):
        """Return an ordered list of (building, count) from --map or --building/--count."""
        pairs = []
        if options.get('map'):
            for chunk in options['map'].split(','):
                chunk = chunk.strip()
                if not chunk:
                    continue
                try:
                    b, c = chunk.split(':')
                    pairs.append((int(b), int(c)))
                except ValueError:
                    raise CommandError(f'Bad --map entry "{chunk}"; expected building:count.')
        if options.get('building') is not None:
            if options.get('count') is None:
                raise CommandError('--building requires --count.')
            pairs.append((options['building'], options['count']))
        if not pairs:
            raise CommandError('Provide --map "10:6,11:6" or --building N --count M.')
        for _, c in pairs:
            if c < 1:
                raise CommandError('count must be >= 1.')
        return pairs

    def _resolve_location(self, options):
        if options.get('location_id'):
            try:
                return Location.objects.get(id=options['location_id'])
            except Location.DoesNotExist:
                raise CommandError(f"No location with id {options['location_id']}.")
        name = options.get('location_name')
        if not name:
            raise CommandError('Provide --location-id or --location-name (the MDC).')
        qs = Location.objects.filter(name=name)
        matches = list(qs)
        if options.get('site'):
            matches = [m for m in matches if (m.get_site_location() and m.get_site_location().name == options['site'])]
        if not matches:
            raise CommandError(f'No location named "{name}"' + (f' under site "{options["site"]}".' if options.get('site') else '.'))
        if len(matches) > 1:
            paths = "\n  ".join(f'id={m.id}: {m.get_hierarchical_display()}' for m in matches)
            raise CommandError(f'Multiple locations named "{name}". Use --site or --location-id:\n  {paths}')
        return matches[0]

    # ----- main -----
    def handle(self, *args, **options):
        apply_changes = options['apply']
        buildings = self._parse_buildings(options)
        location = self._resolve_location(options)
        system_user = User.objects.filter(is_superuser=True).order_by('id').first()

        mode = 'APPLY' if apply_changes else 'DRY-RUN'
        self.stdout.write(f"Create PDUs [{mode}]")
        self.stdout.write(f"  Location : {location.get_hierarchical_display()} (id={location.id})")
        self.stdout.write(f"  Category : {options['category']}")

        category = None
        if apply_changes:
            category, cat_created = EquipmentCategory.objects.get_or_create(
                name=options['category'], defaults={'is_active': True})
            if cat_created:
                self.stdout.write(self.style.SUCCESS(f"  + created category '{options['category']}'"))
        else:
            existing_cat = EquipmentCategory.objects.filter(name=options['category']).first()
            if not existing_cat:
                self.stdout.write(f"  (would create category '{options['category']}')")

        created = skipped = 0
        for building, count in buildings:
            for i in range(1, count + 1):
                name = f"PDU {building}-{i}"
                tag = f"PDU-{building}-{i}"
                if Equipment.objects.filter(name=name).exists():
                    self.stdout.write(f"  = exists: {name}")
                    skipped += 1
                    continue
                self.stdout.write(self.style.SUCCESS(f"  + {name}  (asset_tag={tag})"))
                created += 1
                if apply_changes:
                    Equipment.objects.create(
                        name=name,
                        category=category,
                        location=location,
                        manufacturer_serial=tag,
                        asset_tag=tag,
                        status='active',
                        is_active=True,
                        created_by=system_user,
                        updated_by=system_user,
                    )

        summary = f"{created} PDU(s) to create, {skipped} already present."
        if apply_changes:
            summary = f"Created {created} PDU(s); {skipped} already present."
        elif created:
            summary += " Re-run with --apply to persist."
        self.stdout.write(self.style.SUCCESS(summary))
