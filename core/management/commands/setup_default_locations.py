"""
Management command to set up default sites and locations.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Location


class Command(BaseCommand):
    help = 'Set up default sites and locations (PODs and MDCs)'

    def handle(self, *args, **options):
        # Get or create a system user for creating locations
        try:
            system_user = User.objects.get(username='system')
        except User.DoesNotExist:
            system_user = User.objects.create_user(
                username='system',
                email='system@example.com',
                first_name='System',
                last_name='User',
                is_active=False
            )

        # Default sites
        sites = [
            'Sophie',
            'Dorothy 1A',
            'Dorothy 1B',
            'Dorothy 2'
        ]

        # Create sites
        for site_name in sites:
            site, created = Location.objects.get_or_create(
                name=site_name,
                defaults={
                    'is_site': True,
                    'parent_location': None,
                    'created_by': system_user,
                    'updated_by': system_user,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created site: {site_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Site already exists: {site_name}')
                )

            # Create PODs 1-11 for each site
            for pod_num in range(1, 12):
                pod_name = f'POD {pod_num}'
                pod, created = Location.objects.get_or_create(
                    name=pod_name,
                    parent_location=site,
                    defaults={
                        'is_site': False,
                        'created_by': system_user,
                        'updated_by': system_user,
                        'is_active': True
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created POD: {site_name} > {pod_name}')
                    )

                # Create MDCs for each POD
                # POD 1: MDC 1, 2
                # POD 2: MDC 3, 4
                # POD 3: MDC 5, 6
                # etc.
                mdc_start = (pod_num - 1) * 2 + 1
                mdc_end = pod_num * 2
                
                for mdc_num in range(mdc_start, mdc_end + 1):
                    mdc_name = f'MDC {mdc_num}'
                    mdc, created = Location.objects.get_or_create(
                        name=mdc_name,
                        parent_location=pod,
                        defaults={
                            'is_site': False,
                            'created_by': system_user,
                            'updated_by': system_user,
                            'is_active': True
                        }
                    )
                    
                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f'Created MDC: {site_name} > {pod_name} > {mdc_name}')
                        )

        self.stdout.write(
            self.style.SUCCESS('Successfully set up default locations!')
        )
        
        # Print summary
        total_sites = Location.objects.filter(is_site=True).count()
        total_pods = Location.objects.filter(is_site=False, parent_location__is_site=True).count()
        total_mdcs = Location.objects.filter(is_site=False, parent_location__is_site=False).count()
        
        self.stdout.write(
            self.style.SUCCESS(f'Summary: {total_sites} sites, {total_pods} PODs, {total_mdcs} MDCs')
        )