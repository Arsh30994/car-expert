from django.test import SimpleTestCase

from marketplace.services import calculate_emi, rank_cars


class RecommendationEngineTests(SimpleTestCase):
    def setUp(self):
        self.cars = [
            {"id": 1, "name": "Family Crossover", "price": 1100000, "fuel_type": "Petrol", "seats": 5, "mileage": 17, "safety_score": 4, "maintenance_cost": 18000, "ground_clearance": 190},
            {"id": 2, "name": "Compact Hatchback", "price": 750000, "fuel_type": "Petrol", "seats": 5, "mileage": 22, "safety_score": 3, "maintenance_cost": 14000, "ground_clearance": 165},
            {"id": 3, "name": "Seven Seat MPV", "price": 1250000, "fuel_type": "Diesel", "seats": 7, "mileage": 20, "safety_score": 4, "maintenance_cost": 22000, "ground_clearance": 185},
        ]

    def test_budget_and_family_constraints_filter_unsuitable_cars(self):
        results = rank_cars(self.cars, {"budget": 1300000, "family_size": 6, "fuel_preferences": ["Petrol", "Diesel"]})
        self.assertEqual([item["car"]["id"] for item in results], [3])
        self.assertTrue(all("reasons" in item for item in results))

    def test_recommendations_include_transparent_score_breakdown(self):
        results = rank_cars(self.cars, {"budget": 1300000, "family_size": 4, "fuel_preferences": ["Petrol"]})
        self.assertTrue(results)
        self.assertIn("score", results[0])
        self.assertIn("score_breakdown", results[0])
        self.assertIn("reasons", results[0])
        self.assertIn("tradeoffs", results[0])

    def test_recommendations_are_deterministically_ordered(self):
        profile = {"budget": 1300000, "family_size": 4, "fuel_preferences": ["Petrol"]}
        first = rank_cars(self.cars, profile)
        second = rank_cars(self.cars, profile)
        self.assertEqual([item["car"]["id"] for item in first], [item["car"]["id"] for item in second])

    def test_no_match_returns_empty_list_instead_of_inventing_a_car(self):
        results = rank_cars(self.cars, {"budget": 500000, "family_size": 8, "fuel_preferences": ["Electric"]})
        self.assertEqual(results, [])


class FinanceCalculatorTests(SimpleTestCase):
    def test_emi_uses_reducing_balance_formula(self):
        result = calculate_emi(principal=1000000, annual_interest_rate=9, tenure_months=60)
        self.assertAlmostEqual(result["monthly_emi"], 20758.0, delta=2)
        self.assertGreater(result["total_interest"], 240000)

    def test_zero_interest_rate_divides_principal_evenly(self):
        result = calculate_emi(principal=120000, annual_interest_rate=0, tenure_months=12)
        self.assertEqual(result["monthly_emi"], 10000)
        self.assertEqual(result["total_interest"], 0)

    def test_invalid_loan_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_emi(principal=-1, annual_interest_rate=9, tenure_months=60)
        with self.assertRaises(ValueError):
            calculate_emi(principal=100000, annual_interest_rate=-1, tenure_months=60)
        with self.assertRaises(ValueError):
            calculate_emi(principal=100000, annual_interest_rate=9, tenure_months=0)
