import os
import tempfile
import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .gemini_client import get_response, is_car_related
from garage.models import GarageSelection, Vehicle
from garage.serializers import VehicleSerializer

from .models import ChatSession, Message, VehicleProfile


logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


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
            "ai_provider": "configured" if settings.AIMLAPI_API_KEY else "not_configured",
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

    session = ChatSession.objects.create(
        user=request.user,
        browser_key=key,
        title="New session",
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
        "selected_vehicle": selection.selected_vehicle,
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
        return redirect("chat")

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("chat")

    return render(request, "chatbot/register.html", {"form": form})


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
    session = ChatSession.objects.create(
        user=request.user,
        browser_key=key,
        title="New session",
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
    vehicle_context = shared_vehicle.as_context() if shared_vehicle else vehicle.as_context()

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
    next_url = request.POST.get("next")
    if not next_url or not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("chat")
    return redirect(next_url)
