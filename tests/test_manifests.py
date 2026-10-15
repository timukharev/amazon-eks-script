import copy
import importlib.util
import tempfile
import json
from pathlib import Path
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("capacity", ROOT / "scripts/render_capacity.py")
capacity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capacity)


def chart(environment, *overrides):
    command = ["helm", "template", "sample", str(ROOT / "helm/workload"), "--namespace", environment, "-f", str(ROOT / f"environments/{environment}.yaml")]
    result = subprocess.run(command + list(overrides), check=True, capture_output=True, text=True)
    return {obj["kind"]: obj for obj in yaml.safe_load_all(result.stdout) if obj}


class WorkloadTests(unittest.TestCase):
    def test_environment_pool_and_capacity(self):
        for env in ("production", "preprod", "testing"):
            with self.subTest(environment=env):
                objects = chart(env)
                pod = objects["Deployment"]["spec"]["template"]["spec"]
                self.assertEqual(pod["priorityClassName"], "production" if env == "production" else "nonproduction")
                expected = "testing" if env == "testing" else "applications"
                self.assertEqual(pod["nodeSelector"]["workload.example.com/pool"], expected)
                self.assertEqual(pod["nodeSelector"]["karpenter.sh/capacity-type"], "spot" if env == "testing" else "on-demand")
                self.assertEqual(pod["tolerations"], [{"key": "workload.example.com/pool", "operator": "Equal", "value": expected, "effect": "NoSchedule"}])

    def test_hpa_owns_replicas_and_cpu_requests_exist(self):
        objects = chart("production")
        self.assertNotIn("replicas", objects["Deployment"]["spec"])
        container = objects["Deployment"]["spec"]["template"]["spec"]["containers"][0]
        self.assertIn("cpu", container["resources"]["requests"])
        self.assertEqual(objects["HorizontalPodAutoscaler"]["spec"]["scaleTargetRef"]["name"], "sample")

    def test_fixed_replicas_when_hpa_disabled(self):
        objects = chart("testing", "--set", "autoscaling.enabled=false,replicas=3")
        self.assertNotIn("HorizontalPodAutoscaler", objects)
        self.assertEqual(objects["Deployment"]["spec"]["replicas"], 3)

    def test_restricted_container_settings(self):
        pod = chart("preprod")["Deployment"]["spec"]["template"]["spec"]
        self.assertFalse(pod["automountServiceAccountToken"])
        self.assertTrue(pod["securityContext"]["runAsNonRoot"])
        security = pod["containers"][0]["securityContext"]
        self.assertFalse(security["allowPrivilegeEscalation"])
        self.assertEqual(security["capabilities"]["drop"], ["ALL"])

    def test_unknown_environment_fails_closed(self):
        result = subprocess.run(["helm", "template", "sample", str(ROOT / "helm/workload"), "--namespace", "other", "--set", "environment=other"], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_mismatched_namespace_fails_closed(self):
        result = subprocess.run(["helm", "template", "sample", str(ROOT / "helm/workload"), "--namespace", "preprod", "--set", "environment=production"], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_each_environment_has_default_deny_and_bounded_resources(self):
        objects = json.loads((ROOT / "k8s/environments.json").read_text())["items"]
        for env in ("production", "preprod", "testing"):
            namespace = next(x for x in objects if x["kind"] == "Namespace" and x["metadata"]["name"] == env)
            self.assertEqual(namespace["metadata"]["labels"]["pod-security.kubernetes.io/enforce"], "restricted")
            deny = next(x for x in objects if x["kind"] == "NetworkPolicy" and x["metadata"]["namespace"] == env and x["metadata"]["name"] == "default-deny")
            self.assertEqual(set(deny["spec"]["policyTypes"]), {"Ingress", "Egress"})
            self.assertNotIn("ingress", deny["spec"])
            self.assertNotIn("egress", deny["spec"])
            quota = next(x for x in objects if x["kind"] == "ResourceQuota" and x["metadata"]["namespace"] == env)
            self.assertIn("requests.cpu", quota["spec"]["hard"])


    def test_load_generator_requires_spot_and_testing_pool(self):
        job = yaml.safe_load((ROOT / "k8s/load-test-job.yaml").read_text())
        self.assertEqual(job["metadata"]["namespace"], "testing")
        pod = job["spec"]["template"]["spec"]
        self.assertEqual(pod["nodeSelector"], {"workload.example.com/pool": "testing", "karpenter.sh/capacity-type": "spot"})
        self.assertFalse(pod["automountServiceAccountToken"])
        self.assertEqual(pod["priorityClassName"], "nonproduction")
        self.assertEqual(pod["tolerations"][0]["value"], "testing")
        self.assertEqual(job["spec"]["backoffLimit"], 0)


class CapacityTests(unittest.TestCase):
    def test_capacity_types_and_required_taints(self):
        docs = capacity.render("demo", "DemoNodeRole", "ami-0123456789abcdef0", ["subnet-a", "subnet-b", "subnet-c"], ["sg-demo"], ["us-east-1a", "us-east-1b", "us-east-1c"])["items"]
        for pool, expected in zip(docs[1:], ("on-demand", "spot")):
            template = pool["spec"]["template"]
            req = next(x for x in template["spec"]["requirements"] if x["key"] == "karpenter.sh/capacity-type")
            self.assertEqual(req["values"], [expected])
            self.assertEqual(template["spec"]["taints"][0]["value"], pool["metadata"]["name"])
        self.assertEqual(docs[0]["spec"]["metadataOptions"]["httpTokens"], "required")

    def test_duplicate_zones_are_rejected(self):
        with self.assertRaises(ValueError):
            capacity.render("demo", "DemoNodeRole", "ami-0123456789abcdef0", ["subnet-a", "subnet-b", "subnet-c"], ["sg-demo"], ["zone-a"] * 3)


    def test_config_controls_instance_allowlist_and_limits(self):
        config = capacity.load_config()
        config["pools"]["applications"]["instanceTypes"] = ["m6i.2xlarge"]
        config["pools"]["applications"]["limits"]["cpu"] = "64"
        docs = capacity.render("demo", "DemoNodeRole", "ami-0123456789abcdef0", ["subnet-a", "subnet-b", "subnet-c"], ["sg-demo"], ["us-east-1a", "us-east-1b", "us-east-1c"], config=config)["items"]
        pool = docs[1]
        req = next(r for r in pool["spec"]["template"]["spec"]["requirements"] if r["key"] == "node.kubernetes.io/instance-type")
        self.assertEqual(req["values"], ["m6i.2xlarge"])
        self.assertEqual(pool["spec"]["limits"]["cpu"], "64")

    def test_loader_rejects_spot_for_applications(self):
        config = copy.deepcopy(capacity.load_config())
        config["pools"]["applications"]["capacityType"] = "spot"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capacity.yaml"
            path.write_text(yaml.safe_dump(config))
            with self.assertRaisesRegex(ValueError, "on-demand"):
                capacity.load_config(path)
