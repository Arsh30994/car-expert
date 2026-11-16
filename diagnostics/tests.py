from django.contrib.auth import get_user_model
from django.test import TestCase

from garage.models import Vehicle
from .models import DiagnosticReport
from .schema import DiagnosticPayloadError, validate_diagnostic_payload

User = get_user_model()


class DiagnosticSchemaTests(TestCase):
    def valid_payload(self):
        return {
            "summary": "Possible cooling-system issue based on visible residue.",
            "observations": [{
                "source": "image", "finding": "Residue near reservoir cap",
                "confidence": "medium", "evidence": "Visible pale deposit",
            }],
            "possible_causes": [{
                "cause": "Coolant leak", "likelihood": "medium",
                "supporting_evidence": ["Residue near reservoir"],
                "contradicting_evidence": [],
            }],
            "urgency": "high",
            "safety_warnings": ["Do not open the coolant system while hot."],
            "recommended_actions": ["Check coolant level only when engine is cold."],
            "follow_up_questions": ["Is the temperature warning active?"],
            "data_gaps": ["No OBD-II codes provided"],
        }

    def test_valid_diagnostic_payload_is_accepted(self):
        result = validate_diagnostic_payload(self.valid_payload())
        self.assertEqual(result["urgency"], "high")
        self.assertEqual(result["observations"][0]["source"], "image")

    def test_missing_required_fields_are_rejected(self):
        payload = self.valid_payload()
        del payload["observations"]
        with self.assertRaises(DiagnosticPayloadError):
            validate_diagnostic_payload(payload)

    def test_unknown_urgency_is_rejected(self):
        payload = self.valid_payload()
        payload["urgency"] = "catastrophic"
        with self.assertRaises(DiagnosticPayloadError):
            validate_diagnostic_payload(payload)

    def test_observation_confidence_must_be_categorical(self):
        payload = self.valid_payload()
        payload["observations"][0]["confidence"] = 99
        with self.assertRaises(DiagnosticPayloadError):
            validate_diagnostic_payload(payload)


class DiagnosticReportPersistenceTests(TestCase):
    def test_report_is_attached_to_vehicle_and_owner(self):
        owner = User.objects.create_user(username="owner", password="test-pass-123")
        vehicle = Vehicle.objects.create(user=owner, make="Hyundai", model="i20", year=2022)
        payload = DiagnosticSchemaTests().valid_payload()
        report_data = validate_diagnostic_payload(payload)
        report = DiagnosticReport.objects.create(
            vehicle=vehicle,
            title="Cooling system inspection",
            summary=report_data["summary"],
            urgency=report_data["urgency"],
            report_data=report_data,
        )
        self.assertEqual(report.vehicle.user, owner)
        self.assertEqual(vehicle.diagnostic_reports.get(), report)
