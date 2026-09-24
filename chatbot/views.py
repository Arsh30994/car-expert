import os
import tempfile

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .gemini_client import get_response, is_car_related
from .models import ChatSession, Message, VehicleProfile


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
    return {
        "messages": session.messages.order_by("created_at"),
        "vehicle": vehicle,
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

    user_text = (request.POST.get("text") or request.POST.get("message") or "").strip()
    uploaded_file = request.FILES.get("file")
    file_path = None

    if not user_text and not uploaded_file:
        return JsonResponse(
            {"text": "Type a message or attach a file to continue.", "finding": None},
            status=400,
        )

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
                user_text, file_path, vehicle.as_context()
            )

        Message.objects.create(
            session=session,
            role="assistant",
            text=reply_text,
            finding=finding,
        )
        return JsonResponse({"text": reply_text, "finding": finding})
    finally:
        if file_path:
            try:
                os.remove(file_path)
            except OSError:
                pass
