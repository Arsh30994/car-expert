from .models import DiagnosticReport
from .schema import validate_diagnostic_payload


def persist_diagnostic_report(*, user, vehicle, title, payload, chat_session=None):
    """Validate report structure and enforce vehicle ownership before persistence."""
    if vehicle.user_id != user.pk:
        raise PermissionError("You can only save diagnostic reports to your own vehicle.")
    if chat_session is not None:
        if chat_session.user_id != user.pk:
            raise PermissionError("You can only attach reports to your own chat sessions.")
        if chat_session.garage_vehicle_id not in (None, vehicle.pk):
            raise ValueError("The chat session is associated with a different vehicle.")
    validated = validate_diagnostic_payload(payload)
    return DiagnosticReport.objects.create(
        vehicle=vehicle,
        chat_session=chat_session,
        created_by=user,
        title=(title or "Vehicle diagnostic")[:160],
        summary=validated["summary"],
        urgency=validated["urgency"],
        report_data=validated,
    )
