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

    def test_list_only_returns_the_current_users_vehicles(self):
        other = User.objects.create_user(username="another-driver", password="safe-password-123")
        own_vehicle = Vehicle.objects.create(user=self.user, make="Maruti Suzuki", model="Swift", year=2020)
        Vehicle.objects.create(user=other, make="Hyundai", model="i20", year=2022)

        response = self.client.get(reverse("garage:vehicle-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["results"]], [own_vehicle.id])

    def test_owner_can_retrieve_vehicle_detail(self):
        vehicle = Vehicle.objects.create(user=self.user, make="Tata", model="Nexon", year=2023)

        response = self.client.get(reverse("garage:vehicle-detail", args=[vehicle.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["display_name"], "2023 Tata Nexon")

    def test_owner_can_delete_vehicle(self):
        vehicle = Vehicle.objects.create(user=self.user, make="Honda", model="City", year=2021)

        response = self.client.delete(reverse("garage:vehicle-detail", args=[vehicle.id]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Vehicle.objects.filter(pk=vehicle.id).exists())

    def test_patch_cannot_transfer_vehicle_ownership(self):
        other = User.objects.create_user(username="third-driver", password="safe-password-123")
        vehicle = Vehicle.objects.create(user=self.user, make="Toyota", model="Innova", year=2020)

        response = self.client.patch(
            reverse("garage:vehicle-detail", args=[vehicle.id]),
            data=json.dumps({"user": other.id, "mileage_km": 50000}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.user_id, self.user.id)

    def test_malformed_json_is_rejected(self):
        response = self.client.post(
            reverse("garage:vehicle-list"),
            data="{not-json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("body", response.json()["errors"])

    def test_vehicle_creation_rejects_missing_required_fields(self):
        response = self.client.post(
            reverse("garage:vehicle-list"),
            data=json.dumps({"make": "Toyota"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("model", response.json()["errors"])
        self.assertIn("year", response.json()["errors"])

    def test_vehicle_creation_rejects_future_year_outside_allowed_range(self):
        response = self.client.post(
            reverse("garage:vehicle-list"),
            data=json.dumps({"make": "Toyota", "model": "Supra", "year": 2201}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("year", response.json()["errors"])

    def test_vehicle_creation_rejects_invalid_vin_length(self):
        response = self.client.post(
            reverse("garage:vehicle-list"),
            data=json.dumps({"make": "Toyota", "model": "Camry", "year": 2022, "vin": "TOO-SHORT"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("vin", response.json()["errors"])

    def test_vehicle_detail_returns_404_for_unknown_id(self):
        response = self.client.get(reverse("garage:vehicle-detail", args=[999999]))

        self.assertEqual(response.status_code, 404)

    def test_list_endpoint_rejects_put(self):
        response = self.client.put(
            reverse("garage:vehicle-list"),
            data=json.dumps({"make": "Toyota", "model": "Yaris", "year": 2021}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 405)
