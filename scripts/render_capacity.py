import argparse
import json
import re
from pathlib import Path

import yaml


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config/capacity.yaml"


def load_config(path=DEFAULT_CONFIG):
    with open(path) as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict) or set(config.get("pools", {})) != {"applications", "testing"}:
        raise ValueError("configure exactly the applications and testing pools")
    for name, capacity_type in [("applications", "on-demand"), ("testing", "spot")]:
        pool = config["pools"][name]
        if pool.get("capacityType") != capacity_type:
            raise ValueError(f"{name} requires capacityType {capacity_type}")
        instances = pool.get("instanceTypes")
        if not isinstance(instances, list) or not instances or not all(isinstance(i, str) and re.fullmatch(r"[a-z][a-z0-9-]*\.[a-z0-9]+", i) for i in instances):
            raise ValueError(f"{name} requires an explicit EC2 instance type allowlist")
        limits = pool.get("limits", {})
        if not re.fullmatch(r"[1-9][0-9]*", str(limits.get("cpu", ""))) or not re.fullmatch(r"[1-9][0-9]*Gi", str(limits.get("memory", ""))):
            raise ValueError(f"{name} requires positive CPU and Gi memory limits")
        if "disruption" not in pool or "expireAfter" not in pool:
            raise ValueError(f"{name} requires disruption and expiration settings")
    return config


def render(name, role, ami, subnets, security_groups, zones, config=None):
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,40}", name):
        raise ValueError("name must be a short lowercase DNS label")
    if len(set(zones)) != 3 or len(set(subnets)) != 3:
        raise ValueError("three distinct zones and subnets are required")
    if not role or not security_groups or not re.fullmatch(r"ami-[0-9a-f]{8,17}", ami):
        raise ValueError("a node role name, security group, and explicit AMI ID are required")
    node_class = {
        "apiVersion": "karpenter.k8s.aws/v1", "kind": "EC2NodeClass",
        "metadata": {"name": name},
        "spec": {"amiFamily": "AL2023", "amiSelectorTerms": [{"id": ami}], "role": role,
                 "subnetSelectorTerms": [{"id": s} for s in subnets],
                 "securityGroupSelectorTerms": [{"id": s} for s in security_groups],
                 "metadataOptions": {"httpEndpoint": "enabled", "httpTokens": "required", "httpPutResponseHopLimit": 1},
                 "tags": {"Project": name}},
    }
    config = load_config() if config is None else config
    pools = []
    for pool in ("applications", "testing"):
        settings = config["pools"][pool]
        pools.append({
            "apiVersion": "karpenter.sh/v1", "kind": "NodePool", "metadata": {"name": pool},
            "spec": {
                "template": {"metadata": {"labels": {"workload.example.com/pool": pool}}, "spec": {
                    "nodeClassRef": {"group": "karpenter.k8s.aws", "kind": "EC2NodeClass", "name": name},
                    "taints": [{"key": "workload.example.com/pool", "value": pool, "effect": "NoSchedule"}],
                    "expireAfter": settings["expireAfter"],
                    "requirements": [
                        {"key": "karpenter.sh/capacity-type", "operator": "In", "values": [settings["capacityType"]]},
                        {"key": "topology.kubernetes.io/zone", "operator": "In", "values": zones},
                        {"key": "kubernetes.io/arch", "operator": "In", "values": ["amd64"]},
                        {"key": "kubernetes.io/os", "operator": "In", "values": ["linux"]},
                        {"key": "node.kubernetes.io/instance-type", "operator": "In", "values": settings["instanceTypes"]},
                        {"key": "karpenter.k8s.aws/instance-hypervisor", "operator": "In", "values": ["nitro"]},
                    ]}},
                "limits": settings["limits"],
                "disruption": settings["disruption"],
            },
        })
    return {"apiVersion": "v1", "kind": "List", "items": [node_class, *pools]}


def main():
    parser = argparse.ArgumentParser(description="Render Karpenter resources to stdout; never contact AWS or Kubernetes.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--ami", required=True)
    parser.add_argument("--subnets", nargs=3, required=True)
    parser.add_argument("--security-groups", nargs="+", required=True)
    parser.add_argument("--zones", nargs=3, required=True)
    args = parser.parse_args()
    try:
        result = render(args.name, args.role, args.ami, args.subnets, args.security_groups, args.zones, config=load_config(args.config))
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
