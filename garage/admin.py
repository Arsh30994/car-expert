from django.contrib import admin

from .models import GarageSelection, MaintenanceTask, ServiceRecord, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("display_name", "nickname", "user", "mileage_km", "fuel_type")
    search_fields = ("make", "model", "nickname", "registration_number", "user__username")
    list_filter = ("fuel_type", "year")


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    list_display = ("service_type", "vehicle", "service_date", "odometer_km", "cost")
    list_filter = ("service_date", "service_type")


@admin.register(MaintenanceTask)
class MaintenanceTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "vehicle", "priority", "status", "due_date", "due_odometer_km")
    list_filter = ("priority", "status")


admin.site.register(GarageSelection)
