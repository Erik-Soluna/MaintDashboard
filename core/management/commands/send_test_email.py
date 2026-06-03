"""Send a test email to verify the SMTP configuration / relay is working."""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email to confirm email delivery is working."

    def add_arguments(self, parser):
        parser.add_argument('to', help='Recipient email address.')
        parser.add_argument('--subject', default='Maintenance Dashboard — test email')
        parser.add_argument('--message', default='This is a test email from the Maintenance Dashboard. '
                                                 'If you received it, SMTP delivery is working.')

    def handle(self, *args, **options):
        to = options['to']
        self.stdout.write(f"Backend : {settings.EMAIL_BACKEND}")
        self.stdout.write(f"Host    : {settings.EMAIL_HOST}:{settings.EMAIL_PORT} (TLS={settings.EMAIL_USE_TLS})")
        self.stdout.write(f"From    : {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"To      : {to}")
        try:
            sent = send_mail(
                subject=options['subject'],
                message=options['message'],
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to],
                fail_silently=False,
            )
        except Exception as e:
            raise CommandError(f"Failed to send: {e}")
        if sent:
            self.stdout.write(self.style.SUCCESS(f"Sent {sent} message(s) to {to}."))
        else:
            self.stdout.write(self.style.WARNING("send_mail returned 0 — nothing sent."))
