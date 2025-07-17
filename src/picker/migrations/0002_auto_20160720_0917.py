# -*- coding: utf-8 -*-
from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("picker", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="preference",
            name="user",
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name="picker_preferences",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="preference",
            unique_together=set([("league", "user")]),
        ),
    ]
