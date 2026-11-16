import os
import tempfile
import logging
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .gemini_client import get_response, is_car_related
from garage.models import GarageSelection, Vehicle
from garage.serializers import VehicleSerializer
from diagnostics.models import DiagnosticReport
from garage.models import MaintenanceTask, ServiceRecord

from .models import ChatSession, Message, VehicleProfile


logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


# These are conservative ownership reminders, not manufacturer service schedules.
# A specific vehicle manual and local driving conditions always take precedence.
MAINTENANCE_INTERVALS = (
    ("Engine oil & filter", ("oil", "filter"), 10_000, 365, "high"),
    ("Tyre rotation & pressure check", ("tyre", "tire", "rotation"), 10_000, 365, "medium"),
    ("Brake inspection", ("brake",), 15_000, 365, "high"),
)


def _maintenance_recommendations(vehicle):
    """Return explainable, read-only maintenance suggestions for one vehicle."""
    records = list(vehicle.service_records.all())
    is_electric = "electric" in (vehicle.fuel_type or "").lower() or "ev" in (vehicle.model or "").lower()
    intervals = list(MAINTENANCE_INTERVALS)
    if is_electric:
        intervals = [item for item in intervals if item[0] != "Engine oil & filter"]
        intervals.insert(0, ("Battery & charging system check", ("battery", "charging"), 15_000, 365, "high"))

    suggestions = []
    for title, keywords, distance_km, days, priority in intervals:
        matching = [
            record for record in records
            if any(word in record.service_type.lower() for word in keywords)
        ]
        latest = max(matching, key=lambda record: record.service_date) if matching else None
        if latest:
            due_odometer = latest.odometer_km + distance_km
            due_date = latest.service_date + timedelta(days=days)
            overdue = vehicle.mileage_km >= due_odometer or date.today() >= due_date
            detail = f"Last recorded at {latest.odometer_km:,} km on {latest.service_date:%d %b %Y}."
        else:
            due_odometer = vehicle.mileage_km
            overdue = False
            detail = "No matching service record found; add a baseline check to establish a schedule."
        suggestions.append({
            "title": title,
            "due_odometer_km": due_odometer,
            "priority": "high" if overdue else priority,
            "state": "Overdue" if overdue else ("Plan" if not latest else "Upcoming"),
            "detail": detail,
        })
    return suggestions


@require_GET
def health_check(request):
    try:
        connection.ensure_connection()
    except DatabaseError:
        logger.exception("Database health check failed.")
        return JsonResponse({"status": "unavailable", "database": "unavailable"}, status=503)

    return JsonResponse(
        {
            "status": "ok",
            "database": "connected",
            "ai_provider": "configured" if settings.OPENAI_API_KEY else "not_configured",
        }
    )


def _browser_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _sessions_for(request):
    return ChatSession.objects.filter(user=request.user).order_by("-created_at")


def _get_or_create_session(request, session_id=None):
    key = _browser_key(request)
    if session_id is not None:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        request.session["chat_session_id"] = session.id
        VehicleProfile.objects.get_or_create(session=session)
        return session

    stored_id = request.session.get("chat_session_id")
    if stored_id:
        session = ChatSession.objects.filter(id=stored_id, user=request.user).first()
        if session:
            VehicleProfile.objects.get_or_create(session=session)
            return session

    selection = GarageSelection.objects.filter(user=request.user).select_related("selected_vehicle").first()
    session = ChatSession.objects.create(
        user=request.user,
        browser_key=key,
        title="New session",
        garage_vehicle=selection.selected_vehicle if selection else None,
    )
    VehicleProfile.objects.get_or_create(session=session)
    request.session["chat_session_id"] = session.id
    return session


def _chat_context(request, session):
    vehicle, _ = VehicleProfile.objects.get_or_create(session=session)
    selection, _ = GarageSelection.objects.get_or_create(user=request.user)
    return {
        "messages": session.messages.order_by("created_at"),
        "vehicle": vehicle,
        "garage_vehicles": Vehicle.objects.filter(user=request.user),
        "selected_vehicle": session.garage_vehicle or selection.selected_vehicle,
        "sessions": _sessions_for(request),
        "current_session": session,
    }


def _parse_int(value):
    try:
        text = str(value).strip()
        if not text:
            return None
        return int(text)
    except (TypeError, ValueError):
        return None


def _apply_vehicle(vehicle, post):
    vehicle.make = post.get("make", "")
    vehicle.model = post.get("model", "")
    vehicle.year = _parse_int(post.get("year"))
    vehicle.variant = post.get("variant", "")
    vehicle.engine = post.get("engine", "")
    vehicle.fuel_type = post.get("fuel_type", "")
    vehicle.transmission = post.get("transmission", "")
    vehicle.mileage_km = _parse_int(post.get("mileage_km"))
    vehicle.vin = (post.get("vin") or "")[:17]
    vehicle.save()


def save_upload(uploaded_file):
    suffix = "_" + os.path.basename(uploaded_file.name)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    for chunk in uploaded_file.chunks():
        temp.write(chunk)
    temp.close()
    return temp.name


def _upload_error(uploaded_file):
    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        return "Only JPG, PNG, WebP, and GIF images are supported right now."
    if uploaded_file.size > settings.MAX_CHAT_UPLOAD_BYTES:
        max_mb = settings.MAX_CHAT_UPLOAD_BYTES // (1024 * 1024)
        return f"Images must be {max_mb} MB or smaller."
    return None


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")

    return render(request, "chatbot/register.html", {"form": form})


@login_required
def dashboard_view(request):
    vehicles = Vehicle.objects.filter(user=request.user)
    selection = GarageSelection.objects.filter(user=request.user).select_related("selected_vehicle").first()
    selected_vehicle = selection.selected_vehicle if selection else None
    reports = DiagnosticReport.objects.filter(vehicle__user=request.user)
    tasks = MaintenanceTask.objects.filter(
        vehicle__user=request.user, status__in=["pending", "scheduled"]
    )
    return render(request, "chatbot/dashboard.html", {
        "garage_vehicles": vehicles,
        "selected_vehicle": selected_vehicle,
        "diagnostic_reports": reports[:5],
        "pending_tasks": tasks[:5],
        "vehicle_count": vehicles.count(),
        "report_count": reports.count(),
        "task_count": tasks.count(),
    })


def _garage_context(user):
    selection, _ = GarageSelection.objects.get_or_create(user=user)
    vehicles = Vehicle.objects.filter(user=user)
    return {"garage_vehicles": vehicles, "selected_vehicle": selection.selected_vehicle}


@login_required
def garage_view(request):
    context = _garage_context(request.user)
    selected = context["selected_vehicle"]
    context.update({
        "service_records": ServiceRecord.objects.filter(vehicle__user=request.user)[:8],
        "selected_service_records": selected.service_records.all()[:5] if selected else [],
        "maintenance_recommendations": _maintenance_recommendations(selected) if selected else [],
    })
    return render(request, "chatbot/garage.html", context)


@login_required
def diagnostics_view(request):
    context = _garage_context(request.user)
    context["diagnostic_reports"] = DiagnosticReport.objects.filter(
        vehicle__user=request.user
    ).select_related("vehicle")
    return render(request, "chatbot/diagnostics.html", context)


@login_required
@require_POST
def create_task_from_report(request, report_id):
    """Create a user-approved maintenance follow-up from an owned diagnostic report."""
    report = get_object_or_404(DiagnosticReport, pk=report_id, vehicle__user=request.user)
    priority = report.urgency if report.urgency in {"low", "medium", "high", "critical"} else "medium"
    MaintenanceTask.objects.create(
        vehicle=report.vehicle,
        title=f"Follow up: {report.title}",
        description=report.summary,
        priority=priority,
        source=f"Diagnostic report #{report.id}",
    )
    return redirect("maintenance")


@login_required
@require_http_methods(["GET", "POST"])
def maintenance_view(request):
    context = _garage_context(request.user)
    if request.method == "POST":
        vehicle = context["selected_vehicle"]
        title = (request.POST.get("title") or "").strip()[:160]
        if not vehicle or not title:
            return JsonResponse({"error": "Choose an active vehicle and enter a task title."}, status=400)
        MaintenanceTask.objects.create(
            vehicle=vehicle,
            title=title,
            description=(request.POST.get("description") or "").strip(),
            priority=request.POST.get("priority") if request.POST.get("priority") in {"low", "medium", "high", "critical"} else "medium",
            due_odometer_km=_parse_int(request.POST.get("due_odometer_km")),
            source="Manual maintenance plan",
        )
        return redirect("maintenance")
    context["maintenance_tasks"] = MaintenanceTask.objects.filter(vehicle__user=request.user).select_related("vehicle")
    context["maintenance_recommendations"] = _maintenance_recommendations(context["selected_vehicle"]) if context["selected_vehicle"] else []
    return render(request, "chatbot/maintenance.html", context)


@login_required
@require_POST
def update_maintenance_task(request, task_id):
    task = get_object_or_404(MaintenanceTask, pk=task_id, vehicle__user=request.user)
    status = request.POST.get("status")
    if status not in {"completed", "dismissed", "pending", "scheduled"}:
        return JsonResponse({"error": "Choose a valid task status."}, status=400)
    task.status = status
    task.completed_at = timezone.now() if status == "completed" else None
    task.save(update_fields=["status", "completed_at", "updated_at"])
    return redirect("maintenance")


@login_required
def chat_view(request):
    session = _get_or_create_session(request)
    vehicle, _ = VehicleProfile.objects.get_or_create(session=session)

    if request.method == "POST" and "save_vehicle" in request.POST:
        _apply_vehicle(vehicle, request.POST)
        return redirect("session", session_id=session.id)

    return render(request, "chatbot/chat.html", _chat_context(request, session))


@login_required
def session_view(request, session_id):
    session = _get_or_create_session(request, session_id=session_id)
    return render(request, "chatbot/chat.html", _chat_context(request, session))


@login_required
@require_POST
def new_session(request):
    key = _browser_key(request)
    selection = GarageSelection.objects.filter(user=request.user).select_related("selected_vehicle").first()
    session = ChatSession.objects.create(
        user=request.user,
        browser_key=key,
        title="New session",
        garage_vehicle=selection.selected_vehicle if selection else None,
    )
    VehicleProfile.objects.create(session=session)
    request.session["chat_session_id"] = session.id
    return redirect("session", session_id=session.id)


@login_required
@require_http_methods(["GET", "POST"])
def edit_vehicle(request):
    session = _get_or_create_session(request)
    vehicle, _ = VehicleProfile.objects.get_or_create(session=session)

    if request.method == "POST":
        _apply_vehicle(vehicle, request.POST)
        return redirect("session", session_id=session.id)

    return render(
        request,
        "chatbot/edit_vehicle.html",
        {"vehicle": vehicle, "current_session": session},
    )


@login_required
@require_POST
def rename_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    title = (request.POST.get("title") or "").strip()[:80]
    session.title = title or "New session"
    session.save(update_fields=["title"])
    return redirect("session", session_id=session.id)


@login_required
@require_POST
def delete_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    was_current = request.session.get("chat_session_id") == session.id
    session.delete()

    if was_current:
        request.session.pop("chat_session_id", None)

    next_session = ChatSession.objects.filter(user=request.user).order_by(
        "-created_at"
    ).first()
    if next_session:
        request.session["chat_session_id"] = next_session.id
        return redirect("session", session_id=next_session.id)

    return redirect("chat")


@login_required
@require_POST
def send_message(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    vehicle, _ = VehicleProfile.objects.get_or_create(session=session)
    selection = GarageSelection.objects.filter(user=request.user).select_related("selected_vehicle").first()
    shared_vehicle = selection.selected_vehicle if selection else None
    if session.garage_vehicle_id is None and shared_vehicle is not None:
        session.garage_vehicle = shared_vehicle
        session.save(update_fields=["garage_vehicle"])
    contextual_vehicle = session.garage_vehicle or shared_vehicle
    vehicle_context = contextual_vehicle.as_context() if contextual_vehicle else vehicle.as_context()

    user_text = (request.POST.get("text") or request.POST.get("message") or "").strip()
    uploaded_file = request.FILES.get("file")
    file_path = None

    if not user_text and not uploaded_file:
        return JsonResponse(
            {"text": "Type a message or attach a file to continue.", "finding": None},
            status=400,
        )

    if uploaded_file:
        error = _upload_error(uploaded_file)
        if error:
            return JsonResponse({"text": error, "finding": None}, status=400)

    try:
        if uploaded_file:
            file_path = save_upload(uploaded_file)

        Message.objects.create(
            session=session,
            role="user",
            text=user_text,
            file=uploaded_file if uploaded_file else None,
        )

        if not session.title or session.title == "New session":
            session.title = (user_text or uploaded_file.name)[:80]
            session.save(update_fields=["title"])

        if not is_car_related(user_text, uploaded_file_path=file_path):
            reply_text = (
                "I'm a car-focused assistant. I can only help with "
                "automobile-related questions, diagnostics, maintenance, "
                "specifications, components, repairs, and driving-related "
                "technical information."
            )
            finding = None
        else:
            reply_text, finding = get_response(
                user_text, file_path, vehicle_context
            )

        Message.objects.create(
            session=session,
            role="assistant",
            text=reply_text,
            finding=finding,
        )
        return JsonResponse({"text": reply_text, "finding": finding})
    except Exception:
        # The chat UI always expects JSON. Returning a structured error here
        # prevents a server-side exception from becoming an opaque browser
        # parsing error.
        logger.exception("Unable to process chat message for session %s", session.id)
        return JsonResponse(
            {
                "text": (
                    "I couldn't process that message right now. Please try again. "
                    "If it continues, check the server log for the detailed error."
                ),
                "finding": None,
            },
            status=500,
        )
    finally:
        if file_path:
            try:
                os.remove(file_path)
            except OSError:
                pass


@login_required
@require_POST
def select_garage_vehicle(request):
    vehicle_id = (request.POST.get("vehicle_id") or "").strip()
    selection, _ = GarageSelection.objects.get_or_create(user=request.user)
    if not vehicle_id:
        selection.selected_vehicle = None
    else:
        try:
            vehicle = Vehicle.objects.get(pk=int(vehicle_id), user=request.user)
        except (ValueError, TypeError, Vehicle.DoesNotExist):
            return JsonResponse({"error": "Choose a vehicle from your own garage."}, status=400)
        selection.selected_vehicle = vehicle
    selection.save(update_fields=["selected_vehicle", "updated_at"])
    current_session_id = request.session.get("chat_session_id")
    if current_session_id:
        ChatSession.objects.filter(id=current_session_id, user=request.user).update(garage_vehicle=selection.selected_vehicle)
    next_url = request.POST.get("next")
    if not next_url or not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("chat")
    return redirect(next_url)


@login_required
@require_POST
def add_garage_vehicle(request):
    serializer = VehicleSerializer(data=request.POST)
    if not serializer.is_valid():
        return JsonResponse({"errors": serializer.errors}, status=400)
    vehicle = serializer.save(user=request.user)
    selection, _ = GarageSelection.objects.get_or_create(user=request.user)
    selection.selected_vehicle = vehicle
    selection.save(update_fields=["selected_vehicle", "updated_at"])
    current_session_id = request.session.get("chat_session_id")
    if current_session_id:
        ChatSession.objects.filter(id=current_session_id, user=request.user).update(garage_vehicle=vehicle)
    next_url = request.POST.get("next")
    if not next_url or not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("chat")
    return redirect(next_url)
