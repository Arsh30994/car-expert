from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from chatbot.models import ChatSession, Message
from diagnostics.models import DiagnosticReport
from garage.models import GarageSelection, MaintenanceTask, ServiceRecord, Vehicle


DEMO_USERNAME = "car_expert_demo"
DEMO_MARKER = "DEMO • illustrative"

VEHICLES = [
    ("Hyundai", "i20", 2022, "Sportz 1.2", "1.2L petrol (illustrative)", "Petrol", "Manual", 34820),
    ("Maruti Suzuki", "Baleno", 2021, "Alpha", "1.2L petrol (illustrative)", "Petrol", "Automatic", 41750),
    ("Tata", "Altroz", 2023, "XZ+", "1.2L petrol (illustrative)", "Petrol", "Manual", 18240),
    ("Honda", "City", 2020, "ZX", "1.5L petrol (illustrative)", "Petrol", "Automatic", 56600),
    ("Hyundai", "Verna", 2023, "SX", "1.5L petrol (illustrative)", "Petrol", "Automatic", 16400),
    ("Skoda", "Slavia", 2022, "Style", "1.5L petrol (illustrative)", "Petrol", "Automatic", 29100),
    ("Tata", "Nexon", 2022, "XZ+", "1.5L diesel (illustrative)", "Diesel", "Manual", 43800),
    ("Mahindra", "XUV700", 2023, "AX7", "2.2L diesel (illustrative)", "Diesel", "Automatic", 28700),
    ("Hyundai", "Creta", 2021, "SX(O)", "1.5L diesel (illustrative)", "Diesel", "Automatic", 49500),
    ("Mahindra", "Thar", 2024, "LX", "2.2L diesel (illustrative)", "Diesel", "Manual", 9400),
    ("Tata", "Nexon EV", 2023, "Empowered+", "Battery details illustrative", "Electric", "Automatic", 22500),
    ("MG", "ZS EV", 2022, "Exclusive", "Battery details illustrative", "Electric", "Automatic", 31500),
    ("Hyundai", "IONIQ 5", 2024, "Long Range", "Battery details illustrative", "Electric", "Automatic", 11600),
    ("BMW", "3 Series", 2021, "330i", "2.0L petrol (illustrative)", "Petrol", "Automatic", 38700),
    ("Mercedes-Benz", "C-Class", 2022, "C 200", "1.5L petrol (illustrative)", "Petrol", "Automatic", 26300),
]

REPORTS = [
    ("Engine temperature rising", "high"), ("12V battery voltage low", "medium"),
    ("Front brake pad wear", "high"), ("Tyre pressure imbalance", "low"),
    ("Intermittent engine misfire", "high"), ("OBD P0420 example", "medium"),
    ("EV battery health advisory", "medium"), ("Charging-system warning", "high"),
    ("Coolant seepage observation", "high"), ("Front suspension noise", "medium"),
    ("OBD P0301 example", "medium"), ("Cabin blower noise", "low"),
    ("Brake fluid age reminder", "medium"), ("Tyre tread inspection", "medium"),
    ("Steering vibration at speed", "high"),
]


class Command(BaseCommand):
    help = "Create or refresh isolated, clearly-labelled Car Expert demo data."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete only the dedicated demo account and its cascaded demo records first.")

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        if options["reset"]:
            User.objects.filter(username=DEMO_USERNAME).delete()
        demo_user, created = User.objects.get_or_create(username=DEMO_USERNAME)
        if created:
            demo_user.set_password("DemoOnly2026!")
            demo_user.save(update_fields=["password"])

        vehicles = []
        for index, values in enumerate(VEHICLES, start=1):
            make, model, year, variant, engine, fuel, transmission, mileage = values
            vehicle, _ = Vehicle.objects.update_or_create(
                user=demo_user, registration_number=f"DEMO-{index:02d}-CE",
                defaults={
                    "make": make, "model": model, "year": year, "variant": variant, "engine": engine,
                    "nickname": f"Demo {make} {model}", "fuel_type": fuel, "transmission": transmission,
                    "mileage_km": mileage, "vin": f"DEMO{index:02d}CARX000000X",
                    "purchase_date": date(2025, 1, 1) - timedelta(days=index * 37),
                    "ownership_notes": "Demo ownership profile — illustrative data only.",
                    "service_status": "Attention recommended" if index % 4 == 0 else "Service history current",
                },
            )
            vehicles.append(vehicle)
            for offset, service in enumerate(("Oil and filter service", "Brake and tyre inspection"), start=1):
                if fuel == "Electric" and offset == 1:
                    service = "Battery and charging system check"
                ServiceRecord.objects.update_or_create(
                    vehicle=vehicle, service_type=service, provider=f"{DEMO_MARKER} Workshop {index}",
                    defaults={"service_date": date.today() - timedelta(days=90 * offset), "odometer_km": max(mileage - offset * 7000, 1000), "description": "Illustrative demo invoice and service record.", "cost": Decimal("2800.00") + Decimal(index * 175)},
                )

        GarageSelection.objects.update_or_create(user=demo_user, defaults={"selected_vehicle": vehicles[0]})
        DiagnosticReport.objects.filter(created_by=demo_user, report_data__demo=True).delete()
        for index, (title, urgency) in enumerate(REPORTS):
            vehicle = vehicles[index % len(vehicles)]
            DiagnosticReport.objects.create(
                vehicle=vehicle, created_by=demo_user, title=f"{DEMO_MARKER}: {title}", urgency=urgency,
                summary="Illustrative diagnostic example only. Confirm symptoms with a qualified technician before repairs.",
                report_data={"demo": True, "status": "open" if index % 3 else "monitor", "symptoms": ["Illustrative observation"], "possible_causes": ["Requires confirmation"], "recommended_checks": ["Inspect safely and consult the handbook"]},
            )

        MaintenanceTask.objects.filter(vehicle__user=demo_user, source="Demo seed").delete()
        states = ("pending", "scheduled", "completed", "dismissed")
        for index in range(24):
            vehicle = vehicles[index % len(vehicles)]
            status = states[index % len(states)]
            task = MaintenanceTask.objects.create(
                vehicle=vehicle, title=f"{DEMO_MARKER}: {['Inspect brake pads', 'Rotate tyres', 'Review coolant level', 'Plan annual service'][index % 4]}",
                description="Illustrative maintenance reminder generated for the demo environment.", priority=("low", "medium", "high", "critical")[index % 4], status=status,
                due_date=date.today() + timedelta(days=(index - 8) * 5), due_odometer_km=vehicle.mileage_km + (index - 8) * 600,
                estimated_cost=Decimal("1500.00") + Decimal(index * 325), source="Demo seed",
                completed_at=timezone.now() if status == "completed" else None,
            )

        ChatSession.objects.filter(user=demo_user, title__startswith="[Demo]").delete()
        conversations = [
            ("Fuel efficiency analysis", "How can I improve fuel efficiency on my commute?"),
            ("Engine warning light", "What should I check first for an engine warning light?"),
            ("Brake inspection", "What are safe signs that brake pads need inspection?"),
            ("EV charging advice", "How should I prepare this EV for a long trip?"),
            ("Trip preparation", "Build a pre-drive checklist for a highway journey."),
            ("Maintenance cost estimate", "What affects the cost of a routine service?"),
        ]
        for index, (title, question) in enumerate(conversations):
            session = ChatSession.objects.create(user=demo_user, garage_vehicle=vehicles[index], title=f"[Demo] {title}")
            Message.objects.create(session=session, role="user", text=question)
            Message.objects.create(session=session, role="assistant", text="Demo response: this is illustrative guidance, not a diagnosis. Check the vehicle handbook and use a qualified technician for safety-critical work.")

        self.stdout.write(self.style.SUCCESS(f"Demo data ready for {DEMO_USERNAME}: {len(vehicles)} vehicles, {len(REPORTS)} diagnostics, 24 maintenance tasks."))
