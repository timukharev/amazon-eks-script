import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("failure_capacity", ROOT / "scripts/check_capacity.py")
capacity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capacity)


def render(env="production", *settings):
    command = ["helm", "template", "sample", str(ROOT / "helm/workload"), "--namespace", env, "-f", str(ROOT / f"environments/{env}.yaml")]
    for setting in settings:
        command += ["--set", setting]
    return subprocess.run(command, capture_output=True, text=True)


class ScheduledScalingTests(unittest.TestCase):
    def test_single_owner_and_confirmed_window(self):
        result = render("production", "scheduledScaling.enabled=true")
        self.assertEqual(result.returncode, 0, result.stderr)
        objects = {o["kind"]: o for o in yaml.safe_load_all(result.stdout) if o}
        self.assertNotIn("HorizontalPodAutoscaler", objects)
        self.assertNotIn("replicas", objects["Deployment"]["spec"])
        scaled = objects["ScaledObject"]["spec"]
        self.assertEqual(scaled["scaleTargetRef"]["name"], "sample")
        cron = next(t for t in scaled["triggers"] if t["type"] == "cron")
        self.assertEqual(cron["metadata"]["timezone"], "America/New_York")
        self.assertEqual(cron["metadata"]["start"], "0 17 * * *")
        self.assertEqual(cron["metadata"]["end"], "0 22 * * *")
        self.assertTrue(any(t["type"] == "cpu" for t in scaled["triggers"]))

    def test_plain_hpa_remains_default(self):
        result = render()
        self.assertEqual(result.returncode, 0, result.stderr)
        kinds = {o["kind"] for o in yaml.safe_load_all(result.stdout) if o}
        self.assertIn("HorizontalPodAutoscaler", kinds)
        self.assertNotIn("ScaledObject", kinds)

    def test_fixed_replicas_cannot_conflict_with_keda(self):
        self.assertNotEqual(render("production", "scheduledScaling.enabled=true", "autoscaling.enabled=false").returncode, 0)

    def test_unconfigured_timezone_is_rejected(self):
        result = render("preprod", "scheduledScaling.enabled=true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("timezone is required", result.stderr)

    def test_peak_cannot_exceed_autoscaler_ceiling(self):
        result = render("production", "scheduledScaling.enabled=true", "scheduledScaling.peakReplicas=30")
        self.assertNotEqual(result.returncode, 0)


class FailureCapacityTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "samples/capacity.json").read_text())

    def test_each_zone_loss_in_baseline_and_peak(self):
        result = capacity.check(self.data)
        self.assertTrue(result["passes"])
        self.assertEqual(len(result["checks"]), 6)
        self.assertEqual({c["lostAZ"] for c in result["checks"]}, {"zone-a", "zone-b", "zone-c"})

    def test_memory_can_fail_independently_of_cpu(self):
        self.data["scenarios"][1]["productionDemand"]["memoryGi"] = 225
        result = capacity.check(self.data)
        self.assertFalse(result["passes"])
        failures = [c for c in result["checks"] if not c["passes"]]
        self.assertTrue(all(set(c["deficits"]) == {"memoryGi"} for c in failures))

    def test_nonuniform_zones_check_each_pair(self):
        self.data["scenarios"][0]["usableCapacityByAZ"]["zone-a"]["cpu"] = 1
        failures = [c for c in capacity.check(self.data)["checks"] if not c["passes"]]
        self.assertEqual({c["lostAZ"] for c in failures}, {"zone-b", "zone-c"})

    def test_ip_capacity_is_checked(self):
        self.data["scenarios"][0]["productionDemand"]["podIPs"] = 41
        self.assertFalse(capacity.check(self.data)["passes"])

    def test_negative_nonfinite_and_boolean_inputs_are_rejected(self):
        for value in (-1, "NaN", "Infinity", True):
            with self.subTest(value=value):
                data = copy.deepcopy(self.data)
                data["scenarios"][0]["productionDemand"]["cpu"] = value
                with self.assertRaises(ValueError):
                    capacity.check(data)

    def test_empty_input_is_not_a_passing_capacity_check(self):
        self.data["scenarios"] = []
        with self.assertRaises(ValueError):
            capacity.check(self.data)


class IdentityTests(unittest.TestCase):
    def test_runtime_accounts_have_no_bindings_or_secret_read_roles(self):
        objects = json.loads((ROOT / "k8s/environments.json").read_text())["items"]
        for namespace in ("production", "preprod", "testing"):
            account = next(o for o in objects if o["kind"] == "ServiceAccount" and o["metadata"] == {"name": "workload", "namespace": namespace})
            self.assertFalse(account["automountServiceAccountToken"])
        self.assertFalse(any(o["kind"] in {"RoleBinding", "ClusterRoleBinding"} for o in objects))
        for role in (o for o in objects if o["kind"] == "Role"):
            for rule in role["rules"]:
                self.assertNotIn("secrets", rule["resources"])
                self.assertLessEqual(set(rule["verbs"]), {"get", "list", "watch"})
