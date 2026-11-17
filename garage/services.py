"""Small, deterministic ownership insights derived from stored garage records."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone


def dashboard_insights(user):
    """Return account-scoped dashboard metrics; never query another user's data."""
    from diagnostics.models import DiagnosticReport
    from .models import MaintenanceTask, ServiceRecord, Vehicle

    today = timezone.localdate()
    vehicles = Vehicle.objects.filter(user=user)
    open_tasks = MaintenanceTask.objects.filter(
        vehicle__user=user, status__in=["pending", "scheduled"]
    )
    attention_vehicle_ids = set(open_tasks.filter(priority__in=["high", "critical"]).values_list("vehicle_id", flat=True))
    attention_vehicle_ids.update(
        DiagnosticReport.objects.filter(vehicle__user=user, urgency__in=["high", "critical"])
        .values_list("vehicle_id", flat=True)
    )
    upcoming = open_tasks.filter(due_date__gte=today, due_date__lte=today + timedelta(days=30)).select_related("vehicle")[:5]
    recent_services = ServiceRecord.objects.filter(vehicle__user=user).select_related("vehicle")[:5]
    estimated_cost = open_tasks.aggregate(total=Sum("estimated_cost"))["total"] or Decimal("0.00")
    return {
        "vehicles_requiring_attention": len(attention_vehicle_ids),
        "open_maintenance_cost": estimated_cost,
        "upcoming_maintenance": upcoming,
        "recent_services": recent_services,
        "vehicle_health": {
            "attention": len(attention_vehicle_ids),
            "healthy": max(vehicles.count() - len(attention_vehicle_ids), 0),
        },
    }
