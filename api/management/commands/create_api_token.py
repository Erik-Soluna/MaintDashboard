"""
Provision (or rotate) the read-only AI service account + API token.

Creates a least-privilege user assigned the `ai_diagnostics` role and prints a
DRF auth token. Put the token in the Portainer/MCP environment — never commit it.

    python manage.py create_api_token                 # create/show token for default user
    python manage.py create_api_token --username bot   # custom username
    python manage.py create_api_token --rotate         # revoke + reissue the token
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from rest_framework.authtoken.models import Token

from core.models import Role, UserProfile
from core.rbac import initialize_default_permissions

DEFAULT_USERNAME = 'ai-agent'
ROLE_NAME = 'ai_diagnostics'


class Command(BaseCommand):
    help = 'Create/show the read-only AI service account and its API token.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default=DEFAULT_USERNAME,
                            help=f'Service account username (default: {DEFAULT_USERNAME})')
        parser.add_argument('--email', default='', help='Optional email for the service account')
        parser.add_argument('--rotate', action='store_true',
                            help='Revoke the existing token and issue a fresh one')

    @transaction.atomic
    def handle(self, *args, **options):
        username = options['username']
        # Ensure RBAC catalog (incl. ai_diagnostics role) exists.
        initialize_default_permissions()

        try:
            role = Role.objects.get(name=ROLE_NAME)
        except Role.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f"Role '{ROLE_NAME}' missing even after init — aborting."))
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': options['email'], 'is_active': True, 'is_staff': False},
        )
        if created:
            user.set_unusable_password()  # API/token-only; cannot log in via password
            user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile.role_id != role.id:
            profile.role = role
            profile.is_active = True
            profile.save()

        if options['rotate']:
            Token.objects.filter(user=user).delete()
        token, _ = Token.objects.get_or_create(user=user)

        self.stdout.write(self.style.SUCCESS('AI service account ready.'))
        self.stdout.write(f'  username : {user.username}')
        self.stdout.write(f'  role     : {role.display_name} ({role.name})')
        self.stdout.write(f'  created  : {"new user" if created else "existing user"}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('API token (store in env, do NOT commit):'))
        self.stdout.write(f'  {token.key}')
        self.stdout.write('')
        self.stdout.write('Usage:  curl -H "Authorization: Token <key>" https://<host>/api/v1/')
