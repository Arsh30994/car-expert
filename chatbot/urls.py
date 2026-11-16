from django.contrib.auth import views as auth_views
from django.urls import path

from chatbot import views

urlpatterns = [
    path("health/", views.health_check, name="health"),
    path("", views.chat_view, name="chat"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("garage/", views.garage_view, name="garage"),
    path("diagnostics/", views.diagnostics_view, name="diagnostics"),
    path("diagnostics/<int:report_id>/create-task/", views.create_task_from_report, name="create_task_from_report"),
    path("maintenance/", views.maintenance_view, name="maintenance"),
    path("maintenance/<int:task_id>/status/", views.update_maintenance_task, name="update_maintenance_task"),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="chatbot/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/register/", views.register_view, name="register"),
    path("send/<int:session_id>/", views.send_message, name="send_message"),
    path("session/new/", views.new_session, name="new_session"),
    path("session/<int:session_id>/", views.session_view, name="session"),
    path("session/<int:session_id>/rename/", views.rename_session, name="rename_session"),
    path("session/<int:session_id>/delete/", views.delete_session, name="delete_session"),
    path("vehicle/edit/", views.edit_vehicle, name="edit_vehicle"),
    path("vehicle/select/", views.select_garage_vehicle, name="select_garage_vehicle"),
    path("vehicle/add/", views.add_garage_vehicle, name="add_garage_vehicle"),
]
