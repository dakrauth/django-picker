# Generated by Django 2.1.1 on 2018-12-04 23:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('picker', '0010_auto_20181202_1240'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]