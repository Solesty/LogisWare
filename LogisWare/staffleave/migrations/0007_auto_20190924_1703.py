# Generated by Django 2.2.3 on 2019-09-24 16:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('staffleave', '0006_staff'),
    ]

    operations = [
        migrations.AlterField(
            model_name='request',
            name='staff',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='staffleave.Staff'),
        ),
    ]
