# Generated by Django 2.1 on 2018-08-27 13:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashapp', '0005_auto_20180827_1200'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='company',
            options={'permissions': (('manager_access', 'Access to manager features'),)},
        ),
    ]
