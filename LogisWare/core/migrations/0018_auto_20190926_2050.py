# Generated by Django 2.2.3 on 2019-09-26 19:50

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_auto_20190921_1107'),
    ]

    operations = [
        migrations.AddField(
            model_name='quote',
            name='new_eta',
            field=models.DateField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='quote',
            name='new_eta_set',
            field=models.BooleanField(default=False),
        ),
    ]
