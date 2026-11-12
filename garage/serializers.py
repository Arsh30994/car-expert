from datetime import date

from rest_framework import serializers
from .models import Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Vehicle
        fields = ["id", "make", "model", "year", "variant", "fuel_type", "transmission",
                  "mileage_km", "vin", "display_name", "created_at", "updated_at"]
        read_only_fields = ["id", "display_name", "created_at", "updated_at"]

    def validate_year(self, value):
        if value < 1886 or value > date.today().year + 2:
            raise serializers.ValidationError("Enter a plausible vehicle year.")
        return value

    def validate_make(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Vehicle make is required.")
        return value

    def validate_model(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Vehicle model is required.")
        return value
