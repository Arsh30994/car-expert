from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0002_vehicleprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="title",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="chatsession",
            name="browser_key",
            field=models.CharField(blank=True, db_index=True, max_length=40),
        ),
        migrations.AddField(
            model_name="message",
            name="finding",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="vehicleprofile",
            name="vin",
            field=models.CharField(blank=True, max_length=17),
        ),
    ]
