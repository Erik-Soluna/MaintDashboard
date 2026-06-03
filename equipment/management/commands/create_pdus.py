"""
Create PDU equipment under MDC locations, named "PDU {building}-{n}"
(e.g. PDU 10-1 = building 10, PDU 1) — SSDEV-26 #2.

An MDC *is* a building: the building number is taken from the MDC's name
(the integer in "MDC 10"). You choose a whole site (every MDC under it) or a
single MDC, and how many PDUs per MDC.

Idempotent: PDUs that already exist (by name) are skipped — re-running never
duplicates or recreates them. Dry-run by default; pass --apply to write.

Examples:
  # every MDC under a site, 36 PDUs each (preview)
  python manage.py create_pdus --site-id 3 --count 36
  # just one MDC, 36 PDUs, write for real
  python manage.py create_pdus --location-id 42 --count 36 --apply
"""

import re

from django.core.management.base import BaseCommand, CommandError

from core.models import EquipmentCategory, Location
from core.utils import get_all_descendant_location_ids
from equipment.models import Equipment


class Command(BaseCommand):
    help = ('Create "PDU {building}-{n}" equipment under MDC locations '
            '(building number derived from the MDC name). Dry-run unless --apply.')

    def add_arguments(self, parser):
        parser.add_argument('--site-id', type=int, help='Generate for every MDC under this site.')
        parser.add_argument('--site', help='Site name (alternative to --site-id).')
        parser.add_argument('--location-id', type=int, help='Generate for a single MDC location id.')
        parser.add_argument('--count', type=int, required=True, help='PDUs per MDC/building (1..count).')
        parser.add_argument('--building', type=int,
                            help='Override the building number (only valid with a single --location-id).')
        parser.add_argument('--category', default='PDU', help='Equipment category name (default: PDU).')
        parser.add_argument('--apply', action='store_true', help='Persist changes (otherwise report only).')

    def _resolve_mdcs(self, options):
        """Return the list of target MDC locations."""
        if options.get('location_id'):
            try:
                return [Location.objects.get(id=options['location_id'])]
            except Location.DoesNotExist:
                raise CommandError(f"No location with id {options['location_id']}.")

        site = None
        if options.get('site_id'):
            try:
                site = Location.objects.get(id=options['site_id'], is_site=True)
            except Location.DoesNotExist:
                raise CommandError(f"No site with id {options['site_id']}.")
        elif options.get('site'):
            matches = list(Location.objects.filter(name=options['site'], is_site=True))
            if not matches:
                raise CommandError(f'No site named "{options["site"]}".')
            if len(matches) > 1:
                raise CommandError(f'Multiple sites named "{options["site"]}"; use --site-id.')
            site = matches[0]
        else:
            raise CommandError('Provide --site-id / --site (whole site) or --location-id (single MDC).')

        # MDCs = locations under the site whose parent is a POD (i.e. not the site itself).
        descendant_ids = get_all_descendant_location_ids(site, include_inactive=True)
        mdcs = list(Location.objects.filter(
            id__in=descendant_ids, is_site=False, parent_location__is_site=False, is_active=True))
        if not mdcs:
            raise CommandError(f'No MDC-level locations found under site "{site.name}".')
        return mdcs

    def _building_for(self, mdc, override, single):
        if override is not None and single:
            return override
        m = re.search(r'\d+', mdc.name or '')
        return int(m.group()) if m else None

    def handle(self, *args, **options):
        apply_changes = options['apply']
        count = options['count']
        if count < 1:
            raise CommandError('--count must be >= 1.')

        mdcs = self._resolve_mdcs(options)
        single = bool(options.get('location_id'))
        if options.get('building') is not None and not single:
            raise CommandError('--building is only valid with a single --location-id.')

        mode = 'APPLY' if apply_changes else 'DRY-RUN'
        self.stdout.write(f"Create PDUs [{mode}] — {len(mdcs)} MDC(s), {count} per MDC, category '{options['category']}'")

        category = None
        if apply_changes:
            category, _ = EquipmentCategory.objects.get_or_create(
                name=options['category'], defaults={'is_active': True})

        created = skipped = 0
        for mdc in sorted(mdcs, key=lambda m: m.name):
            building = self._building_for(mdc, options.get('building'), single)
            if building is None:
                self.stdout.write(self.style.WARNING(
                    f"  ! skipping {mdc.get_hierarchical_display()} — no building number in name"))
                continue
            self.stdout.write(f"  {mdc.get_hierarchical_display()} -> building {building}")
            for i in range(1, count + 1):
                name = f"PDU {building}-{i}"
                tag = f"PDU-{building}-{i}"
                if Equipment.objects.filter(name=name).exists():
                    skipped += 1
                    continue
                created += 1
                self.stdout.write(self.style.SUCCESS(f"    + {name}"))
                if apply_changes:
                    Equipment.objects.create(
                        name=name, category=category, location=mdc,
                        manufacturer_serial=tag, asset_tag=tag,
                        status='active', is_active=True,
                    )

        summary = f"{created} PDU(s) to create, {skipped} already present (skipped)."
        if apply_changes:
            summary = f"Created {created} PDU(s); {skipped} already present (skipped)."
        elif created:
            summary += " Re-run with --apply to persist."
        self.stdout.write(self.style.SUCCESS(summary))
