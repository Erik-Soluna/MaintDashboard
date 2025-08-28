# Generated manually for Logo model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Logo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Site Logo', max_length=100)),
                ('image', models.ImageField(help_text='Upload your site logo (recommended: 200x60px)', upload_to='logos/')),
                ('is_active', models.BooleanField(default=True, help_text='Only one logo can be active at a time')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Logo',
                'verbose_name_plural': 'Logos',
                'ordering': ['-is_active', '-created_at'],
            },
        ),
    ]
