# Generated by Django 2.2.3 on 2019-07-14 11:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_auto_20190707_1304'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='quote',
            name='quote_items',
        ),
        migrations.RemoveField(
            model_name='quote',
            name='quote_rejected',
        ),
        migrations.RemoveField(
            model_name='quote',
            name='quote_rejected_reason_type',
        ),
        migrations.RemoveField(
            model_name='quote',
            name='reason_for_rejection',
        ),
        migrations.RemoveField(
            model_name='quote',
            name='reference',
        ),
        migrations.DeleteModel(
            name='QuoteItem',
        ),
    ]
