# Generated by Django 2.1.1 on 2018-09-02 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('picker', '0007_auto_20180828_1855'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='playoff',
            name='league',
        ),
        migrations.RemoveField(
            model_name='playoffpicks',
            name='playoff',
        ),
        migrations.RemoveField(
            model_name='playoffpicks',
            name='user',
        ),
        migrations.RemoveField(
            model_name='playoffteam',
            name='playoff',
        ),
        migrations.RemoveField(
            model_name='playoffteam',
            name='team',
        ),
        migrations.AlterModelOptions(
            name='league',
            options={'permissions': (('can_update_score', 'Can update scores'),)},
        ),
        migrations.AlterField(
            model_name='league',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='picker/logos/nfl'),
        ),
        migrations.AlterField(
            model_name='team',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to='picker/logos/nfl'),
        ),
        migrations.DeleteModel(
            name='Playoff',
        ),
        migrations.DeleteModel(
            name='PlayoffPicks',
        ),
        migrations.DeleteModel(
            name='PlayoffTeam',
        ),
    ]
