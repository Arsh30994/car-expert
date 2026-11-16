from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("garage", "0003_vehicle_identity_and_history"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DiagnosticReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("summary", models.TextField()),
                ("urgency", models.CharField(choices=[("unknown", "Unknown"), ("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="unknown", max_length=12)),
                ("report_data", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="diagnostic_reports", to=settings.AUTH_USER_MODEL)),
                ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="diagnostic_reports", to="garage.vehicle")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
