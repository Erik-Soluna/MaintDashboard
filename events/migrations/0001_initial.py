# Generated by Django 5.2.4 on 2025-07-09 17:58

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('equipment', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CalendarEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(help_text='Event title', max_length=200)),
                ('description', models.TextField(blank=True, help_text='Event description')),
                ('event_type', models.CharField(choices=[('maintenance', 'Maintenance Activity'), ('inspection', 'Inspection'), ('calibration', 'Calibration'), ('outage', 'Equipment Outage'), ('upgrade', 'Equipment Upgrade'), ('commissioning', 'Commissioning'), ('decommissioning', 'Decommissioning'), ('testing', 'Testing'), ('other', 'Other')], default='other', help_text='Type of event', max_length=20)),
                ('event_date', models.DateField(help_text='Event date')),
                ('start_time', models.TimeField(blank=True, help_text='Event start time', null=True)),
                ('end_time', models.TimeField(blank=True, help_text='Event end time', null=True)),
                ('all_day', models.BooleanField(default=False, help_text='All day event')),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium', max_length=10)),
                ('is_recurring', models.BooleanField(default=False)),
                ('recurrence_pattern', models.CharField(blank=True, help_text="Recurrence pattern (e.g., 'weekly', 'monthly')", max_length=100)),
                ('notify_assigned', models.BooleanField(default=True, help_text='Send notification to assigned user')),
                ('notification_sent', models.BooleanField(default=False)),
                ('is_completed', models.BooleanField(default=False)),
                ('completion_notes', models.TextField(blank=True)),
                ('assigned_to', models.ForeignKey(blank=True, help_text='User assigned to this event', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_events', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('equipment', models.ForeignKey(help_text='Equipment this event relates to', on_delete=django.db.models.deletion.CASCADE, related_name='calendar_events', to='equipment.equipment')),

                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Calendar Event',
                'verbose_name_plural': 'Calendar Events',
                'ordering': ['event_date', 'start_time'],
            },
        ),
        migrations.CreateModel(
            name='EventAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(help_text='Attachment title', max_length=200)),
                ('file', models.FileField(help_text='Attached file', upload_to='events/attachments/')),
                ('description', models.TextField(blank=True, help_text='Attachment description')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='events.calendarevent')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Event Attachment',
                'verbose_name_plural': 'Event Attachments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='EventComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('comment', models.TextField(help_text='Comment text')),
                ('is_internal', models.BooleanField(default=True, help_text='Internal comment (not visible to external users)')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='events.calendarevent')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Event Comment',
                'verbose_name_plural': 'Event Comments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='EventReminder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reminder_type', models.CharField(choices=[('email', 'Email Notification'), ('sms', 'SMS Notification'), ('dashboard', 'Dashboard Notification')], max_length=20)),
                ('reminder_time', models.DateTimeField(help_text='When to send the reminder')),
                ('message', models.TextField(help_text='Reminder message')),
                ('is_sent', models.BooleanField(default=False)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reminders', to='events.calendarevent')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='event_reminders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Event Reminder',
                'verbose_name_plural': 'Event Reminders',
                'ordering': ['reminder_time'],
            },
        ),
        migrations.AddIndex(
            model_name='calendarevent',
            index=models.Index(fields=['event_date'], name='events_cale_event_d_eb93f5_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarevent',
            index=models.Index(fields=['equipment', 'event_date'], name='events_cale_equipme_4ccb89_idx'),
        ),
        migrations.AddIndex(
            model_name='calendarevent',
            index=models.Index(fields=['event_type', 'priority'], name='events_cale_event_t_143f18_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='eventreminder',
            unique_together={('event', 'user', 'reminder_type')},
        ),
    ]
