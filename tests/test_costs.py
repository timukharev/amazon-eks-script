import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("costs", ROOT / "scripts/compare_costs.py")
costs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(costs)


class CostComparisonTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "samples/costs.json").read_text())

    def test_synthetic_reduction(self):
        result = costs.analyze(self.data)
        self.assertEqual(result["reduction_percent"], "25.00")
        self.assertEqual(result["cost_reduction"], "250.00")
        self.assertEqual(result["days_per_window"], 30)

    def test_increase_keeps_negative_sign(self):
        self.data["after"]["amount"] = "1200"
        self.assertEqual(costs.analyze(self.data)["reduction_percent"], "-20.00")

    def test_zero_after_is_full_reduction(self):
        self.data["after"]["amount"] = "0"
        self.assertEqual(costs.analyze(self.data)["reduction_percent"], "100.00")

    def test_invalid_baselines_and_amounts(self):
        for field, amount in [("before", "0"), ("before", "NaN"), ("after", "Infinity"), ("after", "-1"), ("after", True)]:
            with self.subTest(field=field, amount=amount):
                data = copy.deepcopy(self.data)
                data[field]["amount"] = amount
                with self.assertRaises(ValueError):
                    costs.analyze(data)

    def test_unequal_windows_are_rejected(self):
        self.data["after"]["end_exclusive"] = "2025-03-04"
        with self.assertRaises(ValueError):
            costs.analyze(self.data)

    def test_overlap_is_rejected(self):
        self.data["after"] = dict(self.data["before"])
        with self.assertRaises(ValueError):
            costs.analyze(self.data)

    def test_missing_comparability_is_rejected(self):
        self.data["comparison_notes"] = ""
        with self.assertRaises(ValueError):
            costs.analyze(self.data)

    def test_billing_scope_and_basis_are_required(self):
        for key, value in [("scope", ""), ("currency", "EUR"), ("basis", "unknown")]:
            with self.subTest(key=key):
                data = copy.deepcopy(self.data)
                data[key] = value
                with self.assertRaises(ValueError):
                    costs.analyze(data)
