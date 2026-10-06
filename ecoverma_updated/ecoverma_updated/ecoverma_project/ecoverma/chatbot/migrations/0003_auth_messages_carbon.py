import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chatbot", "0002_alter_conversation_budget_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="conversations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="conversation",
            name="extra_entities",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="conversation",
            name="pending_action",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterModelOptions(
            name="conversation",
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sender",
                    models.CharField(
                        choices=[("user", "User"), ("bot", "Bot")],
                        max_length=10,
                    ),
                ),
                ("text", models.TextField(blank=True)),
                ("links", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="chatbot.conversation",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="CarbonCalculation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("total_emission_kg", models.FloatField(default=0)),
                ("best_mode", models.CharField(blank=True, max_length=50, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="carbon_calculations",
                        to="chatbot.conversation",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="carbon_calculations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="VehicleLeg",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "vehicle_type",
                    models.CharField(
                        choices=[
                            ("walk", "Walking"),
                            ("cycle", "Cycling"),
                            ("train", "Train"),
                            ("coach", "Coach / long-distance bus"),
                            ("electric_car", "Electric car"),
                            ("car_petrol", "Petrol car"),
                            ("ferry", "Ferry"),
                            ("flight_short", "Short-haul flight"),
                            ("flight_long", "Long-haul flight"),
                        ],
                        max_length=20,
                    ),
                ),
                ("distance_km", models.FloatField()),
                ("emission_kg", models.FloatField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "calculation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vehicles",
                        to="chatbot.carboncalculation",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
