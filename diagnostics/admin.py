from django.contrib import admin

from .models import DiagnosticReport


@admin.register(DiagnosticReport)
class DiagnosticReportAdmin(admin.ModelAdmin):
    list_display = ("title", "vehicle", "urgency", "created_by", "created_at")
    list_filter = ("urgency", "created_at")
    search_fields = ("title", "summary", "vehicle__make", "vehicle__model", "created_by__username")
    readonly_fields = ("created_at", "updated_at")
