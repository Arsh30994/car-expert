from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError

from .models import GarageSelection, Vehicle
from .serializers import VehicleSerializer


def _parse_json(request):
    try:
        return JSONParser().parse(request)
    except (ParseError, ValueError):
        return None


def _selection_payload(selection):
    vehicle = selection.selected_vehicle
    return {
        "selected_vehicle": VehicleSerializer(vehicle).data if vehicle else None,
        "updated_at": selection.updated_at.isoformat(),
    }


@login_required
@require_http_methods(["GET", "PATCH"])
def vehicle_selection(request):
    selection, _ = GarageSelection.objects.get_or_create(user=request.user)
    if request.method == "GET":
        return JsonResponse(_selection_payload(selection))

    data = _parse_json(request)
    if not isinstance(data, dict) or "vehicle_id" not in data:
        return JsonResponse({"errors": {"vehicle_id": ["Provide a vehicle ID or null to clear selection."]}}, status=400)

    vehicle_id = data["vehicle_id"]
    if vehicle_id is None:
        selection.selected_vehicle = None
    else:
        try:
            vehicle_id = int(vehicle_id)
        except (TypeError, ValueError):
            return JsonResponse({"errors": {"vehicle_id": ["Vehicle ID must be an integer or null."]}}, status=400)
        selection.selected_vehicle = get_object_or_404(Vehicle, pk=vehicle_id, user=request.user)

    selection.save(update_fields=["selected_vehicle", "updated_at"])
    return JsonResponse(_selection_payload(selection))


@login_required
@require_http_methods(["GET", "POST"])
def vehicle_list(request):
    if request.method == "GET":
        vehicles = Vehicle.objects.filter(user=request.user)
        return JsonResponse({"results": VehicleSerializer(vehicles, many=True).data})
    data = _parse_json(request)
    if not isinstance(data, dict):
        return JsonResponse({"errors": {"body": ["Valid JSON object required."]}}, status=400)
    serializer = VehicleSerializer(data=data)
    if not serializer.is_valid():
        return JsonResponse({"errors": serializer.errors}, status=400)
    vehicle = serializer.save(user=request.user)
    return JsonResponse(VehicleSerializer(vehicle).data, status=201)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
def vehicle_detail(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, user=request.user)
    if request.method == "GET":
        return JsonResponse(VehicleSerializer(vehicle).data)
    if request.method == "DELETE":
        vehicle.delete()
        return JsonResponse({}, status=204)
    data = _parse_json(request)
    if not isinstance(data, dict):
        return JsonResponse({"errors": {"body": ["Valid JSON object required."]}}, status=400)
    serializer = VehicleSerializer(vehicle, data=data, partial=True)
    if not serializer.is_valid():
        return JsonResponse({"errors": serializer.errors}, status=400)
    serializer.save()
    return JsonResponse(serializer.data)
