from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=80, blank=True)
    browser_key = models.CharField(max_length=40, blank=True, db_index=True)

    def __str__(self):
        return self.title or f"Session {self.pk}"


class Message(models.Model):
    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10)
    text = models.TextField(blank=True)
    file = models.FileField(upload_to="uploads/", blank=True, null=True)
    finding = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def attachment(self):
        return self.file

    @property
    def attachment_is_image(self):
        name = (self.file.name or "").lower()
        return name.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))

    @property
    def attachment_ext(self):
        name = self.file.name or ""
        if "." not in name:
            return "FILE"
        return name.rsplit(".", 1)[-1]


class VehicleProfile(models.Model):
    session = models.OneToOneField(
        ChatSession, on_delete=models.CASCADE, related_name="vehicle"
    )
    make = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    variant = models.CharField(max_length=50, blank=True)
    engine = models.CharField(max_length=50, blank=True)
    fuel_type = models.CharField(max_length=20, blank=True)
    transmission = models.CharField(max_length=20, blank=True)
    mileage_km = models.PositiveIntegerField(null=True, blank=True)
    vin = models.CharField(max_length=17, blank=True)

    def as_context(self):
        parts = []
        if self.year or self.make or self.model:
            parts.append(f"{self.year or ''} {self.make} {self.model}".strip())
        if self.variant:
            parts.append(self.variant)
        if self.engine:
            parts.append(self.engine)
        if self.fuel_type:
            parts.append(self.fuel_type)
        if self.transmission:
            parts.append(self.transmission)
        if self.mileage_km:
            parts.append(f"{self.mileage_km} km")
        if self.vin:
            parts.append(f"VIN {self.vin}")
        return ", ".join(p for p in parts if p)
