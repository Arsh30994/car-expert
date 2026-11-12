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
    fuel_type = models.CharField(max_length=40, blank=True)
    transmission = models.CharField(max_length=40, blank=True)
    mileage_km = models.PositiveIntegerField(default=0)
    vin = models.CharField(max_length=17, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @property
    def display_name(self):
        return f"{self.year} {self.make} {self.model}"

    def as_context(self):
        parts = [self.display_name]
        if self.variant:
            parts.append(self.variant)
        if self.fuel_type:
            parts.append(self.fuel_type)
        if self.transmission:
            parts.append(self.transmission)
        if self.mileage_km:
            parts.append(f"{self.mileage_km} km")
        if self.vin:
            parts.append(f"VIN {self.vin}")
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
