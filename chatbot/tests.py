import os
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
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
