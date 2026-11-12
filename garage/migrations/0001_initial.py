from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Vehicle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("make", models.CharField(max_length=80)),
                ("model", models.CharField(max_length=80)),
                ("year", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1886), django.core.validators.MaxValueValidator(2200)])),
                ("variant", models.CharField(blank=True, max_length=100)),
                ("fuel_type", models.CharField(blank=True, max_length=40)),
                ("transmission", models.CharField(blank=True, max_length=40)),
                ("mileage_km", models.PositiveIntegerField(default=0)),
                ("vin", models.CharField(blank=True, max_length=17)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="garage_vehicles", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
