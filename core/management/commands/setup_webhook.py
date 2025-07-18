from django.core.management.base import BaseCommand
from django.conf import settings
from django.urls import reverse
import requests
import secrets
import string


class Command(BaseCommand):
    help = 'Setup and test webhook configuration for Portainer integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--generate-secret',
            action='store_true',
            help='Generate a new webhook secret',
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test connection to Portainer',
        )
        parser.add_argument(
            '--show-config',
            action='store_true',
            help='Show current webhook configuration',
        )

    def handle(self, *args, **options):
        if options['generate_secret']:
            self.generate_secret()
        elif options['test_connection']:
            self.test_connection()
        elif options['show_config']:
            self.show_config()
        else:
            self.show_help()

    def generate_secret(self):
        """Generate a secure webhook secret."""
        alphabet = string.ascii_letters + string.digits + string.punctuation
        secret = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        self.stdout.write(
            self.style.SUCCESS(f'Generated webhook secret: {secret}')
        )
        self.stdout.write(
            self.style.WARNING(
                'Add this to your environment variables as PORTAINER_WEBHOOK_SECRET'
            )
        )

    def test_connection(self):
        """Test connection to Portainer API."""
        portainer_url = getattr(settings, 'PORTAINER_URL', '')
        portainer_user = getattr(settings, 'PORTAINER_USER', '')
        portainer_pass = getattr(settings, 'PORTAINER_PASSWORD', '')
        
        if not all([portainer_url, portainer_user, portainer_pass]):
            self.stdout.write(
                self.style.ERROR(
                    'Portainer configuration incomplete. Set PORTAINER_URL, '
                    'PORTAINER_USER, and PORTAINER_PASSWORD environment variables.'
                )
            )
            return
        
        try:
            # Test authentication
            auth_response = requests.post(
                f"{portainer_url}/api/auth",
                json={'Username': portainer_user, 'Password': portainer_pass},
                timeout=10
            )
            
            if auth_response.status_code == 200:
                self.stdout.write(
                    self.style.SUCCESS('✓ Portainer authentication successful')
                )
                
                # Test getting stacks
                token = auth_response.json().get('jwt')
                headers = {'Authorization': f'Bearer {token}'}
                stacks_response = requests.get(
                    f"{portainer_url}/api/stacks",
                    headers=headers,
                    timeout=10
                )
                
                if stacks_response.status_code == 200:
                    stacks = stacks_response.json()
                    stack_name = getattr(settings, 'PORTAINER_STACK_NAME', '')
                    
                    if stack_name:
                        stack_found = any(stack.get('Name') == stack_name for stack in stacks)
                        if stack_found:
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Stack "{stack_name}" found')
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'⚠ Stack "{stack_name}" not found')
                            )
                            self.stdout.write('Available stacks:')
                            for stack in stacks:
                                self.stdout.write(f'  - {stack.get("Name")}')
                    else:
                        self.stdout.write(
                            self.style.WARNING('⚠ PORTAINER_STACK_NAME not configured')
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Failed to get stacks: {stacks_response.status_code}')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Authentication failed: {auth_response.status_code}')
                )
                
        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Network error: {str(e)}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error: {str(e)}')
            )

    def show_config(self):
        """Show current webhook configuration."""
        self.stdout.write(self.style.SUCCESS('Webhook Configuration:'))
        self.stdout.write('=' * 50)
        
        # Show webhook URL
        webhook_url = f"http://localhost:8000{reverse('core:webhook_handler')}"
        self.stdout.write(f'Webhook URL: {webhook_url}')
        
        # Show environment variables
        env_vars = [
            ('PORTAINER_URL', getattr(settings, 'PORTAINER_URL', 'Not set')),
            ('PORTAINER_USER', getattr(settings, 'PORTAINER_USER', 'Not set')),
            ('PORTAINER_PASSWORD', '***' if getattr(settings, 'PORTAINER_PASSWORD', '') else 'Not set'),
            ('PORTAINER_STACK_NAME', getattr(settings, 'PORTAINER_STACK_NAME', 'Not set')),
            ('PORTAINER_WEBHOOK_SECRET', '***' if getattr(settings, 'PORTAINER_WEBHOOK_SECRET', '') else 'Not set'),
        ]
        
        for var, value in env_vars:
            self.stdout.write(f'{var}: {value}')
        
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Setup Instructions:'))
        self.stdout.write('1. Set the environment variables above')
        self.stdout.write('2. Configure the webhook URL in Portainer')
        self.stdout.write('3. Test the connection with: python manage.py setup_webhook --test-connection')

    def show_help(self):
        """Show help information."""
        self.stdout.write(self.style.SUCCESS('Webhook Setup Commands:'))
        self.stdout.write('=' * 50)
        self.stdout.write('python manage.py setup_webhook --generate-secret')
        self.stdout.write('  Generate a secure webhook secret')
        self.stdout.write('')
        self.stdout.write('python manage.py setup_webhook --test-connection')
        self.stdout.write('  Test connection to Portainer API')
        self.stdout.write('')
        self.stdout.write('python manage.py setup_webhook --show-config')
        self.stdout.write('  Show current webhook configuration') 