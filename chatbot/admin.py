from django.contrib import admin

from .models import ChatSession, Message, VehicleProfile


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "browser_key", "created_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "created_at")


@admin.register(VehicleProfile)
class VehicleProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "year", "make", "model")
