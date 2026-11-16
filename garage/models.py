from datetime import date

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Vehicle(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="garage_vehicles")
    make = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    year = models.PositiveIntegerField(validators=[MinValueValidator(1886), MaxValueValidator(2200)])
    variant = models.CharField(max_length=100, blank=True)
    nickname = models.CharField(max_length=80, blank=True)
    registration_number = models.CharField(max_length=20, blank=True)
    fuel_type = models.CharField(max_length=40, blank=True)
    transmission = models.CharField(max_length=40, blank=True)
    mileage_km = models.PositiveIntegerField(default=0)
    vin = models.CharField(max_length=17, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @property
    def current_odometer_km(self):
        """Compatibility alias: mileage_km is the persisted current odometer."""
        return self.mileage_km

    @property
    def display_name(self):
        return f"{self.year} {self.make} {self.model}"

    def as_context(self):
        parts = [self.display_name]
        if self.nickname:
            parts.append(f"({self.nickname})")
        if self.variant:
            parts.append(self.variant)
        if self.fuel_type:
            parts.append(self.fuel_type)
        if self.transmission:
            parts.append(self.transmission)
        if self.mileage_km:
            parts.append(f"{self.mileage_km} km")
        return ", ".join(parts)

    def __str__(self):
        return self.display_name


class GarageSelection(models.Model):
    """The single account-wide vehicle context shared by all platform modules."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="garage_selection")
    selected_vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selected_by_users",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id}: {self.selected_vehicle_id or 'no vehicle selected'}"


class ServiceRecord(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="service_records")
    service_date = models.DateField()
    odometer_km = models.PositiveIntegerField()
    service_type = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    provider = models.CharField(max_length=160, blank=True)
    cost = models.DecimalField(max_digits=11, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-service_date", "-id"]

    def __str__(self):
        return f"{self.service_type} — {self.vehicle.display_name}"


class MaintenanceTask(models.Model):
    PRIORITY_CHOICES = [
        ("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"), ("scheduled", "Scheduled"),
        ("completed", "Completed"), ("dismissed", "Dismissed"),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="maintenance_tasks")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=12, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    due_date = models.DateField(null=True, blank=True)
    due_odometer_km = models.PositiveIntegerField(null=True, blank=True)
    source = models.CharField(max_length=160, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "-priority", "-created_at"]

    def __str__(self):
        return f"{self.title} — {self.vehicle.display_name}"
