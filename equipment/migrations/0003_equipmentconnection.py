# Generated migration for EquipmentConnection model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0002_alter_equipmentcategoryfield_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentConnection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('connection_type', models.CharField(
                    choices=[
                        ('power', 'Power Supply'),
                        ('data', 'Data Connection'),
                        ('cooling', 'Cooling System'),
                        ('control', 'Control System'),
                        ('mechanical', 'Mechanical'),
                        ('other', 'Other')
                    ],
                    default='power',
                    help_text='Type of connection between equipment',
                    max_length=20
                )),
                ('description', models.TextField(blank=True, help_text='Description of the connection')),
                ('is_critical', models.BooleanField(
                    default=True,
                    help_text='If True, downstream equipment goes offline when upstream is offline'
                )),
                ('is_active', models.BooleanField(default=True, help_text='Whether this connection is currently active')),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='%(class)s_created',
                    to='auth.user'
                )),
                ('downstream_equipment', models.ForeignKey(
                    help_text='Equipment that depends on the upstream equipment',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='upstream_connections',
                    to='equipment.equipment'
                )),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='%(class)s_updated',
                    to='auth.user'
                )),
                ('upstream_equipment', models.ForeignKey(
                    help_text='Equipment that supplies power/data/service to downstream equipment',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='downstream_connections',
                    to='equipment.equipment'
                )),
            ],
            options={
                'verbose_name': 'Equipment Connection',
                'verbose_name_plural': 'Equipment Connections',
                'ordering': ['upstream_equipment', 'downstream_equipment'],
                'unique_together': {('upstream_equipment', 'downstream_equipment')},
                'indexes': [
                    models.Index(fields=['upstream_equipment'], name='equipment_e_upstrea_idx'),
                    models.Index(fields=['downstream_equipment'], name='equipment_e_downstr_idx'),
                    models.Index(fields=['connection_type', 'is_active'], name='equipment_e_connect_idx'),
                ],
            },
        ),
    ]

