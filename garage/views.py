from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError

from .models import Vehicle
from .serializers import VehicleSerializer


def _parse_json(request):
    try:
        return JSONParser().parse(request)
    except (ParseError, ValueError):
        return None


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
