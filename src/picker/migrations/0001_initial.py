# -*- coding: utf-8 -*-
from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Alias",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(unique=True, max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name="Conference",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                ("abbr", models.CharField(max_length=8)),
            ],
        ),
        migrations.CreateModel(
            name="Division",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                (
                    "conference",
                    models.ForeignKey(on_delete=models.CASCADE, to="picker.Conference"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Game",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("kickoff", models.DateTimeField()),
                ("tv", models.CharField(max_length=8, verbose_name=b"TV", blank=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "category",
                    models.CharField(
                        default="REG",
                        max_length=4,
                        choices=[("REG", b"Regular Season"), ("POST", b"Post Season")],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        default="U",
                        max_length=1,
                        choices=[
                            ("U", b"Unplayed"),
                            ("T", b"Tie"),
                            ("H", b"Home Win"),
                            ("A", b"Away Win"),
                        ],
                    ),
                ),
                ("location", models.CharField(max_length=50, blank=True)),
            ],
            options={
                "ordering": ("kickoff", "away"),
            },
        ),
        migrations.CreateModel(
            name="GamePick",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "game",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="gamepicks",
                        to="picker.Game",
                    ),
                ),
            ],
            options={
                "ordering": ("game__kickoff", "game__away"),
            },
        ),
        migrations.CreateModel(
            name="GameSet",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("season", models.PositiveSmallIntegerField()),
                ("week", models.PositiveSmallIntegerField()),
                ("points", models.PositiveSmallIntegerField(default=0)),
                ("opens", models.DateTimeField()),
                ("closes", models.DateTimeField()),
            ],
            options={
                "ordering": ("season", "week"),
            },
        ),
        migrations.CreateModel(
            name="League",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(unique=True, max_length=50)),
                ("abbr", models.CharField(max_length=8)),
                (
                    "logo",
                    models.ImageField(null=True, upload_to=b"picker/logos", blank=True),
                ),
                ("is_pickable", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="PickSet",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("points", models.PositiveSmallIntegerField(default=0)),
                ("correct", models.PositiveSmallIntegerField(default=0)),
                ("wrong", models.PositiveSmallIntegerField(default=0)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "strategy",
                    models.CharField(
                        default="USER",
                        max_length=4,
                        choices=[
                            ("USER", b"User"),
                            ("RAND", b"Random"),
                            ("HOME", b"Home Team"),
                            ("BEST", b"Best Record"),
                        ],
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="picksets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "week",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="picksets",
                        to="picker.GameSet",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Playoff",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("season", models.PositiveSmallIntegerField()),
                ("kickoff", models.DateTimeField()),
                (
                    "league",
                    models.ForeignKey(on_delete=models.CASCADE, to="picker.League"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PlayoffPicks",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("picks", models.TextField(blank=True)),
                (
                    "playoff",
                    models.ForeignKey(on_delete=models.CASCADE, to="picker.Playoff"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.SET_NULL,
                        blank=True,
                        to=settings.AUTH_USER_MODEL,
                        null=True,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PlayoffTeam",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("seed", models.PositiveSmallIntegerField()),
                (
                    "playoff",
                    models.ForeignKey(on_delete=models.CASCADE, to="picker.Playoff"),
                ),
            ],
            options={
                "ordering": ("seed",),
            },
        ),
        migrations.CreateModel(
            name="Preference",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        default="ACTV",
                        max_length=4,
                        choices=[
                            ("ACTV", b"Active"),
                            ("IDLE", b"Inactive"),
                            ("SUSP", b"Suspended"),
                        ],
                    ),
                ),
                (
                    "autopick",
                    models.CharField(
                        default="RAND",
                        max_length=4,
                        choices=[("NONE", b"None"), ("RAND", b"Random")],
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Team",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                ("abbr", models.CharField(max_length=8, blank=True)),
                ("nickname", models.CharField(max_length=50)),
                ("location", models.CharField(max_length=100, blank=True)),
                ("image", models.CharField(max_length=50, blank=True)),
                ("colors", models.CharField(max_length=40, blank=True)),
                (
                    "logo",
                    models.ImageField(null=True, upload_to=b"picker/logos", blank=True),
                ),
                (
                    "conference",
                    models.ForeignKey(on_delete=models.CASCADE, to="picker.Conference"),
                ),
                (
                    "division",
                    models.ForeignKey(
                        on_delete=models.SET_NULL,
                        blank=True,
                        to="picker.Division",
                        null=True,
                    ),
                ),
                (
                    "league",
                    models.ForeignKey(on_delete=models.CASCADE, to="picker.League"),
                ),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.AddField(
            model_name="preference",
            name="favorite_team",
            field=models.ForeignKey(
                on_delete=models.SET_NULL, blank=True, to="picker.Team", null=True
            ),
        ),
        migrations.AddField(
            model_name="preference",
            name="league",
            field=models.ForeignKey(on_delete=models.CASCADE, to="picker.League"),
        ),
        migrations.AddField(
            model_name="preference",
            name="user",
            field=models.OneToOneField(
                on_delete=models.CASCADE,
                related_name="picker_preferences",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="playoffteam",
            name="team",
            field=models.ForeignKey(on_delete=models.CASCADE, to="picker.Team"),
        ),
        migrations.AddField(
            model_name="gameset",
            name="byes",
            field=models.ManyToManyField(
                related_name="bye_set", verbose_name=b"Bye Teams", to="picker.Team"
            ),
        ),
        migrations.AddField(
            model_name="gameset",
            name="league",
            field=models.ForeignKey(
                on_delete=models.CASCADE, related_name="game_set", to="picker.League"
            ),
        ),
        migrations.AddField(
            model_name="gamepick",
            name="pick",
            field=models.ForeignKey(on_delete=models.CASCADE, to="picker.PickSet"),
        ),
        migrations.AddField(
            model_name="gamepick",
            name="winner",
            field=models.ForeignKey(
                on_delete=models.SET_NULL, blank=True, to="picker.Team", null=True
            ),
        ),
        migrations.AddField(
            model_name="game",
            name="away",
            field=models.ForeignKey(
                on_delete=models.CASCADE, related_name="away_games", to="picker.Team"
            ),
        ),
        migrations.AddField(
            model_name="game",
            name="home",
            field=models.ForeignKey(
                on_delete=models.CASCADE, related_name="home_games", to="picker.Team"
            ),
        ),
        migrations.AddField(
            model_name="game",
            name="week",
            field=models.ForeignKey(
                on_delete=models.CASCADE, related_name="games", to="picker.GameSet"
            ),
        ),
        migrations.AddField(
            model_name="conference",
            name="league",
            field=models.ForeignKey(on_delete=models.CASCADE, to="picker.League"),
        ),
        migrations.AddField(
            model_name="alias",
            name="team",
            field=models.ForeignKey(on_delete=models.CASCADE, to="picker.Team"),
        ),
        migrations.AlterUniqueTogether(
            name="pickset",
            unique_together=set([("user", "week")]),
        ),
    ]
