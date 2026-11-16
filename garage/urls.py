from django.urls import path
from . import views

app_name = "garage"

urlpatterns = [
    path("vehicles/", views.vehicle_list, name="vehicle-list"),
    path("vehicles/<int:vehicle_id>/", views.vehicle_detail, name="vehicle-detail"),
    path("selection/", views.vehicle_selection, name="vehicle-selection"),
]
