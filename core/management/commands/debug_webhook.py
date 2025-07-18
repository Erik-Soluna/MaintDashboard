from django.core.management.base import BaseCommand
from core.models import PortainerConfig

class Command(BaseCommand):
    help = 'Debug Portainer webhook configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            choices=['show', 'set', 'clear', 'test'],
            default='show',
            help='Action to perform'
        )
        parser.add_argument(
            '--url',
            type=str,
            help='Portainer URL to set'
        )
        parser.add_argument(
            '--stack',
            type=str,
            help='Stack name to set'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username to set'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password to set'
        )
        parser.add_argument(
            '--secret',
            type=str,
            help='Webhook secret to set'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'show':
            self.show_config()
        elif action == 'set':
            self.set_config(options)
        elif action == 'clear':
            self.clear_config()
        elif action == 'test':
            self.test_config()

    def show_config(self):
        """Show current configuration."""
        self.stdout.write("=== Portainer Webhook Configuration ===")
        
        config = PortainerConfig.get_config()
        
        self.stdout.write(f"ID: {config.id}")
        self.stdout.write(f"URL: '{config.portainer_url}'")
        self.stdout.write(f"Stack: '{config.stack_name}'")
        self.stdout.write(f"User: '{config.portainer_user}'")
        self.stdout.write(f"Password: '{'*' * len(config.portainer_password) if config.portainer_password else ''}'")
        self.stdout.write(f"Secret: '{config.webhook_secret[:4] + '*' * (len(config.webhook_secret) - 4) if config.webhook_secret else ''}'")
        self.stdout.write(f"Created: {config.created_at}")
        self.stdout.write(f"Updated: {config.updated_at}")
        
        # Check if configuration is complete
        if config.portainer_url and config.stack_name:
            self.stdout.write(self.style.SUCCESS("✅ Configuration is complete"))
        else:
            self.stdout.write(self.style.WARNING("⚠️ Configuration is incomplete"))

    def set_config(self, options):
        """Set configuration values."""
        self.stdout.write("=== Setting Portainer Configuration ===")
        
        config = PortainerConfig.get_config()
        
        if options['url']:
            config.portainer_url = options['url']
            self.stdout.write(f"Set URL: {options['url']}")
            
        if options['stack']:
            config.stack_name = options['stack']
            self.stdout.write(f"Set Stack: {options['stack']}")
            
        if options['user']:
            config.portainer_user = options['user']
            self.stdout.write(f"Set User: {options['user']}")
            
        if options['password']:
            config.portainer_password = options['password']
            self.stdout.write(f"Set Password: {'*' * len(options['password'])}")
            
        if options['secret']:
            config.webhook_secret = options['secret']
            self.stdout.write(f"Set Secret: {options['secret'][:4] + '*' * (len(options['secret']) - 4)}")
        
        try:
            config.save()
            self.stdout.write(self.style.SUCCESS("✅ Configuration saved successfully"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error saving configuration: {e}"))

    def clear_config(self):
        """Clear all configuration values."""
        self.stdout.write("=== Clearing Portainer Configuration ===")
        
        config = PortainerConfig.get_config()
        config.portainer_url = ''
        config.stack_name = ''
        config.portainer_user = ''
        config.portainer_password = ''
        config.webhook_secret = ''
        
        try:
            config.save()
            self.stdout.write(self.style.SUCCESS("✅ Configuration cleared successfully"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error clearing configuration: {e}"))

    def test_config(self):
        """Test the current configuration."""
        self.stdout.write("=== Testing Portainer Configuration ===")
        
        config = PortainerConfig.get_config()
        
        if not config.portainer_url:
            self.stdout.write(self.style.ERROR("❌ No Portainer URL configured"))
            return
            
        if not config.stack_name:
            self.stdout.write(self.style.ERROR("❌ No Stack name configured"))
            return
            
        self.stdout.write(f"Testing connection to: {config.portainer_url}")
        self.stdout.write(f"Stack name: {config.stack_name}")
        
        # Import the test function
        from core.views import test_portainer_connection
        result = test_portainer_connection()
        
        self.stdout.write(f"Test result: {result}")
        
        if 'successful' in result.lower():
            self.stdout.write(self.style.SUCCESS("✅ Connection test successful"))
        else:
            self.stdout.write(self.style.ERROR("❌ Connection test failed")) 