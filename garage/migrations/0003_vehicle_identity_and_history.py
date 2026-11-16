from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("garage", "0002_garageselection")]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="nickname",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="vehicle",
            name="registration_number",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.CreateModel(
            name="ServiceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("service_date", models.DateField()),
                ("odometer_km", models.PositiveIntegerField()),
                ("service_type", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("provider", models.CharField(blank=True, max_length=160)),
                ("cost", models.DecimalField(blank=True, decimal_places=2, max_digits=11, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_records", to="garage.vehicle")),
            ],
            options={"ordering": ["-service_date", "-id"]},
        ),
        migrations.CreateModel(
            name="MaintenanceTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                ("priority", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="medium", max_length=12)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("scheduled", "Scheduled"), ("completed", "Completed"), ("dismissed", "Dismissed")], default="pending", max_length=12)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("due_odometer_km", models.PositiveIntegerField(blank=True, null=True)),
                ("source", models.CharField(blank=True, max_length=160)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="maintenance_tasks", to="garage.vehicle")),
            ],
            options={"ordering": ["due_date", "-priority", "-created_at"]},
        ),
    ]
