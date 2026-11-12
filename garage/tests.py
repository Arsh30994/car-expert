import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Vehicle


User = get_user_model()


class VehicleGarageApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="driver", password="safe-password-123")
        self.client.force_login(self.user)

    def test_authenticated_user_can_create_and_list_vehicles(self):
        response = self.client.post(
            reverse("garage:vehicle-list"),
            data=json.dumps({
                "make": "Toyota",
                "model": "Corolla",
                "year": 2022,
                "fuel_type": "Petrol",
                "mileage_km": 18500,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        vehicle_id = response.json()["id"]
        self.assertEqual(response.json()["display_name"], "2022 Toyota Corolla")

        listing = self.client.get(reverse("garage:vehicle-list"))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()["results"]), 1)
        self.assertEqual(listing.json()["results"][0]["id"], vehicle_id)

    def test_vehicle_detail_is_scoped_to_the_authenticated_owner(self):
        other = User.objects.create_user(username="other", password="safe-password-123")
        vehicle = Vehicle.objects.create(user=other, make="Honda", model="City", year=2021)

        response = self.client.get(reverse("garage:vehicle-detail", args=[vehicle.id]))

        self.assertEqual(response.status_code, 404)

    def test_vehicle_creation_rejects_invalid_year_and_empty_make(self):
        response = self.client.post(
            reverse("garage:vehicle-list"),
            data=json.dumps({"make": " ", "model": "Civic", "year": 1890}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("make", response.json()["errors"])
        self.assertIn("year", response.json()["errors"])

    def test_vehicle_can_be_updated_without_changing_ownership(self):
        vehicle = Vehicle.objects.create(user=self.user, make="Honda", model="City", year=2021)

        response = self.client.patch(
            reverse("garage:vehicle-detail", args=[vehicle.id]),
            data=json.dumps({"mileage_km": 42000}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.mileage_km, 42000)
        self.assertEqual(vehicle.user_id, self.user.id)

    def test_garage_api_requires_authentication(self):
        self.client.logout()

        response = self.client.get(reverse("garage:vehicle-list"))

        self.assertEqual(response.status_code, 302)
