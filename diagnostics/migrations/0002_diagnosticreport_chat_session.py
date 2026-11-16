from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("chatbot", "0005_chatsession_vehicle"),
        ("diagnostics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="diagnosticreport",
            name="chat_session",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="diagnostic_reports", to="chatbot.chatsession"),
        ),
    ]
