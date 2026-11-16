from .models import DiagnosticReport
from .schema import validate_diagnostic_payload


def persist_diagnostic_report(*, user, vehicle, title, payload):
    """Validate report structure and enforce vehicle ownership before persistence."""
    if vehicle.user_id != user.pk:
        raise PermissionError("You can only save diagnostic reports to your own vehicle.")
    validated = validate_diagnostic_payload(payload)
    return DiagnosticReport.objects.create(
        vehicle=vehicle,
        created_by=user,
        title=(title or "Vehicle diagnostic")[:160],
        summary=validated["summary"],
        urgency=validated["urgency"],
        report_data=validated,
    )
