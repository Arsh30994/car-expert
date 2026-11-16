from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("chatbot", "0004_chatsession_user"),
        ("garage", "0003_vehicle_identity_and_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="vehicle",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chat_sessions", to="garage.vehicle"),
        ),
    ]
