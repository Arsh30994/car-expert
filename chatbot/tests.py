import os
import tempfile
from unittest.mock import patch
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.templatetags.static import static
from django.urls import reverse

from .models import ChatSession, Message, VehicleProfile


class ChatAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="driver",
            password="test-pass-123",
        )

    def test_public_routes_render(self):
        login_response = self.client.get(reverse("login"))
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, "Sign in")

        register_response = self.client.get(reverse("register"))
        self.assertEqual(register_response.status_code, 200)
        self.assertContains(register_response, "Create account")

    def test_health_check_reports_database_and_ai_readiness(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["database"], "connected")

    def test_register_creates_an_authenticated_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-driver",
                "password1": "safe-test-password-123",
                "password2": "safe-test-password-123",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="new-driver").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_static_css_is_resolved_from_the_expected_app_path(self):
        from django.contrib.staticfiles import finders

        static_path = finders.find("chatbot/style.css")
        expected_tail = os.path.normpath("chatbot/static/chatbot/style.css")

        self.assertIsNotNone(static_path)
        self.assertTrue(os.path.normpath(static_path).endswith(expected_tail))

    @override_settings(
        DEBUG=False,
        MIDDLEWARE=[
            "django.middleware.security.SecurityMiddleware",
            "whitenoise.middleware.WhiteNoiseMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
        ],
        STORAGES={
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        },
    )
    def test_z_production_serves_collected_css_and_javascript(self):
        # Collection is a temporary deployment concern, not project source.
        with tempfile.TemporaryDirectory() as static_root:
            with override_settings(STATIC_ROOT=static_root):
                call_command("collectstatic", interactive=False, verbosity=0)

                for asset in ("chatbot/style.css", "chatbot/chat.js"):
                    response = self.client.get(static(asset))

                    self.assertEqual(response.status_code, 200)
                    body = b"".join(response.streaming_content)
                    self.assertGreater(len(body), 0)

    def test_chat_requires_login(self):
        response = self.client.get(reverse("chat"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_authenticated_chat_creates_user_owned_session(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("chat"))

        self.assertEqual(response.status_code, 200)
        session = ChatSession.objects.get(user=self.user)
        self.assertEqual(session.title, "New session")
        self.assertTrue(VehicleProfile.objects.filter(session=session).exists())

    def test_user_cannot_open_another_users_session(self):
        other = User.objects.create_user(username="other", password="pass")
        other_session = ChatSession.objects.create(user=other, title="Private")

        self.client.force_login(self.user)
        response = self.client.get(reverse("session", args=[other_session.id]))

        self.assertEqual(response.status_code, 404)

    def test_session_history_can_rename_and_delete(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user, title="Old title")
        VehicleProfile.objects.create(session=session)

        rename_response = self.client.post(
            reverse("rename_session", args=[session.id]),
            {"title": "Brake noise"},
        )
        session.refresh_from_db()

        self.assertEqual(rename_response.status_code, 302)
        self.assertEqual(session.title, "Brake noise")

        delete_response = self.client.post(reverse("delete_session", args=[session.id]))

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(ChatSession.objects.filter(id=session.id).exists())

    def test_new_session_requires_post_and_creates_only_on_post(self):
        self.client.force_login(self.user)

        get_response = self.client.get(reverse("new_session"))
        self.assertEqual(get_response.status_code, 405)
        self.assertFalse(ChatSession.objects.filter(user=self.user).exists())

        post_response = self.client.post(reverse("new_session"))
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(ChatSession.objects.filter(user=self.user).count(), 1)

    @patch("chatbot.views.get_response", return_value=("Check the brake pads.", None))
    @patch("chatbot.views.is_car_related", return_value=True)
    def test_send_message_stores_user_and_assistant_messages(
        self,
        _is_car_related,
        _get_response,
    ):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user, title="Brakes")
        VehicleProfile.objects.create(session=session)

        response = self.client.post(
            reverse("send_message", args=[session.id]),
            {"text": "Why are my brakes squealing?"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Message.objects.filter(session=session).count(), 2)
        self.assertEqual(
            Message.objects.filter(session=session, role="assistant").get().text,
            "Check the brake pads.",
        )

    @patch("chatbot.views.get_response", side_effect=RuntimeError("Provider unavailable"))
    @patch("chatbot.views.is_car_related", return_value=True)
    def test_send_message_returns_json_when_processing_fails(
        self,
        _is_car_related,
        _get_response,
    ):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user, title="Electrical")
        VehicleProfile.objects.create(session=session)

        response = self.client.post(
            reverse("send_message", args=[session.id]),
            {"text": "The battery light is on"},
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("couldn't process", response.json()["text"])

    def test_send_message_rejects_unsupported_uploads(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user, title="Files")
        VehicleProfile.objects.create(session=session)
        document = SimpleUploadedFile("invoice.pdf", b"%PDF-1.4", content_type="application/pdf")

        response = self.client.post(
            reverse("send_message", args=[session.id]),
            {"file": document},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Only JPG", response.json()["text"])
        self.assertFalse(Message.objects.filter(session=session).exists())


class AimlApiClientTests(TestCase):
    def test_insufficient_credits_message_is_actionable(self):
        from .gemini_client import _provider_error_message

        error = type(
            "ProviderError",
            (Exception,),
            {"status_code": 403},
        )("You've run out of funds.")

        self.assertIn("no remaining credits", _provider_error_message(error))

    @patch("chatbot.gemini_client.client", None)
    def test_missing_aimlapi_configuration_returns_an_actionable_message(self):
        from .gemini_client import get_response

        text, finding = get_response("My car is not starting")

        self.assertIn("AI/ML API is not configured", text)
        self.assertIsNone(finding)

    @patch("chatbot.gemini_client.client")
    @override_settings(AIMLAPI_MODEL="text-model", AIMLAPI_VISION_MODEL="vision-model")
    def test_non_image_attachment_uses_the_text_classifier(self, client):
        result = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="YES"))]
        )
        client.chat.completions.create.return_value = result

        with tempfile.NamedTemporaryFile(suffix=".pdf") as document:
            from .gemini_client import is_car_related

            self.assertTrue(is_car_related("Please check this invoice", document.name))

        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["model"], "text-model")
        self.assertIsInstance(request["messages"][0]["content"], str)


class SharedGarageChatContextTests(TestCase):
    def setUp(self):
        from garage.models import GarageSelection, Vehicle

        self.user = User.objects.create_user(username="garage-driver", password="test-pass-123")
        self.vehicle = Vehicle.objects.create(
            user=self.user, make="Tata", model="Nexon EV", year=2023,
            fuel_type="Electric", transmission="Automatic", mileage_km=12500,
        )
        GarageSelection.objects.create(user=self.user, selected_vehicle=self.vehicle)
        self.client.force_login(self.user)

    @patch("chatbot.views.get_response", return_value=("Battery health depends on diagnostics.", None))
    @patch("chatbot.views.is_car_related", return_value=True)
    def test_chatbot_receives_account_selected_vehicle_context(self, _classifier, response_generator):
        session = ChatSession.objects.create(user=self.user, title="Battery question")
        VehicleProfile.objects.create(session=session, make="Old", model="Session profile", year=2001)

        response = self.client.post(
            reverse("send_message", args=[session.id]),
            {"text": "How should I maintain the battery?"},
        )

        self.assertEqual(response.status_code, 200)
        context = response_generator.call_args.args[2]
        self.assertIn("2023 Tata Nexon EV", context)
        self.assertIn("Electric", context)
        self.assertNotIn("Old Session profile", context)

    def test_selected_vehicle_is_visible_in_every_chat_session(self):
        first = ChatSession.objects.create(user=self.user, title="First")
        second = ChatSession.objects.create(user=self.user, title="Second")
        VehicleProfile.objects.create(session=first)
        VehicleProfile.objects.create(session=second)

        first_response = self.client.get(reverse("session", args=[first.id]))
        second_response = self.client.get(reverse("session", args=[second.id]))

        self.assertContains(first_response, "2023 Tata Nexon EV")
        self.assertContains(second_response, "2023 Tata Nexon EV")

    def test_user_cannot_select_a_vehicle_owned_by_another_user(self):
        from garage.models import Vehicle

        other = User.objects.create_user(username="foreign-driver", password="test-pass-123")
        foreign_vehicle = Vehicle.objects.create(user=other, make="Tesla", model="Model 3", year=2024)
        session = ChatSession.objects.create(user=self.user, title="Current")
        response = self.client.post(
            reverse("select_garage_vehicle"),
            {"vehicle_id": foreign_vehicle.id, "next": reverse("session", args=[session.id])},
        )
        self.assertEqual(response.status_code, 400)
