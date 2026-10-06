from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0003_auth_messages_carbon"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExchangeRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("currency_code", models.CharField(max_length=10, unique=True)),
                ("rate_per_eur", models.DecimalField(decimal_places=8, max_digits=20)),
                ("rate_date", models.DateField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["currency_code"],
            },
        ),
    ]
