# Generated by Django 2.1 on 2018-08-28 12:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashapp', '0006_auto_20180827_1349'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Cost',
            new_name='Expense',
        ),
    ]
