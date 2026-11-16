from django.conf import settings
from django.db import models

from garage.models import Vehicle


class DiagnosticReport(models.Model):
    URGENCY_CHOICES = [
        ("unknown", "Unknown"),
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="diagnostic_reports"
    )
    chat_session = models.ForeignKey(
        "chatbot.ChatSession", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="diagnostic_reports",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="diagnostic_reports"
    )
    title = models.CharField(max_length=160)
    summary = models.TextField()
    urgency = models.CharField(max_length=12, choices=URGENCY_CHOICES, default="unknown")
    report_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.title} — {self.vehicle.display_name}"
