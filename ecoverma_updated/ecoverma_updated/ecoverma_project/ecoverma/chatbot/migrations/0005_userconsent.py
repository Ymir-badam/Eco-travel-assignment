from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chatbot", "0004_exchangerate"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserConsent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("policy_version", models.CharField(max_length=20)),
                ("accepted_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-accepted_at"],
                "unique_together": {("user", "policy_version")},
            },
        ),
    ]
