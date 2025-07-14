"""
Management command to generate PODs for existing sites.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Location


class Command(BaseCommand):
    help = 'Generate PODs for existing sites'

    def add_arguments(self, parser):
        parser.add_argument(
            '--site-id',
            type=int,
            help='Generate PODs for a specific site ID'
        )
        parser.add_argument(
            '--site-name',
            type=str,
            help='Generate PODs for a specific site name'
        )
        parser.add_argument(
            '--pod-count',
            type=int,
            default=11,
            help='Number of PODs to generate per site (default: 11, max: 100)'
        )
        parser.add_argument(
            '--mdcs-per-pod',
            type=int,
            default=2,
            help='Number of MDCs to generate per POD (default: 2)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of existing PODs'
        )

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

        # Determine which sites to process
        if options['site_id']:
            sites = Location.objects.filter(
                id=options['site_id'],
                is_site=True,
                is_active=True
            )
        elif options['site_name']:
            sites = Location.objects.filter(
                name__icontains=options['site_name'],
                is_site=True,
                is_active=True
            )
        else:
            sites = Location.objects.filter(is_site=True, is_active=True)

        if not sites.exists():
            self.stdout.write(
                self.style.ERROR('No sites found matching the criteria.')
            )
            return

        pod_count = options['pod_count']
        mdcs_per_pod = options['mdcs_per_pod']
        force = options['force']
        
        # Validate pod count
        if pod_count > 100:
            self.stdout.write(
                self.style.ERROR('Pod count cannot exceed 100')
            )
            return
        
        if pod_count < 1:
            self.stdout.write(
                self.style.ERROR('Pod count must be at least 1')
            )
            return

        total_pods_created = 0
        total_mdcs_created = 0

        for site in sites:
            self.stdout.write(f'Processing site: {site.name}')
            
            # Generate PODs for this site
            for pod_num in range(1, pod_count + 1):
                pod_name = f'POD {pod_num}'
                
                # Check if POD already exists
                existing_pod = Location.objects.filter(
                    name=pod_name,
                    parent_location=site,
                    is_site=False
                ).first()
                
                if existing_pod and not force:
                    self.stdout.write(
                        self.style.WARNING(f'POD already exists: {site.name} > {pod_name}')
                    )
                    continue
                
                # Create or update POD
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
                        self.style.SUCCESS(f'Created POD: {site.name} > {pod_name}')
                    )
                    total_pods_created += 1
                elif force:
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated existing POD: {site.name} > {pod_name}')
                    )

                # Generate MDCs for this POD
                mdc_start = (pod_num - 1) * mdcs_per_pod + 1
                mdc_end = pod_num * mdcs_per_pod
                
                for mdc_num in range(mdc_start, mdc_end + 1):
                    mdc_name = f'MDC {mdc_num}'
                    
                    # Check if MDC already exists
                    existing_mdc = Location.objects.filter(
                        name=mdc_name,
                        parent_location=pod,
                        is_site=False
                    ).first()
                    
                    if existing_mdc and not force:
                        self.stdout.write(
                            self.style.WARNING(f'MDC already exists: {site.name} > {pod_name} > {mdc_name}')
                        )
                        continue
                    
                    # Create or update MDC
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
                            self.style.SUCCESS(f'Created MDC: {site.name} > {pod_name} > {mdc_name}')
                        )
                        total_mdcs_created += 1
                    elif force:
                        self.stdout.write(
                            self.style.SUCCESS(f'Updated existing MDC: {site.name} > {pod_name} > {mdc_name}')
                        )

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated {total_pods_created} PODs and {total_mdcs_created} MDCs!'
            )
        )
        
        # Print final statistics
        total_sites = Location.objects.filter(is_site=True).count()
        total_pods = Location.objects.filter(is_site=False, parent_location__is_site=True).count()
        total_mdcs = Location.objects.filter(is_site=False, parent_location__is_site=False).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Final summary: {total_sites} sites, {total_pods} PODs, {total_mdcs} MDCs'
            )
        ) 