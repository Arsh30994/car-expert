from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("garage", "0003_vehicle_identity_and_history")]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="engine",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
