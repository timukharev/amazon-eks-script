import argparse
import json
from decimal import Decimal, InvalidOperation

RESOURCES = ("cpu", "memoryGi", "podSlots", "podIPs")


def number(value):
    if isinstance(value, bool):
        raise ValueError("resource values must be finite non-negative numbers")
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("resource values must be finite non-negative numbers")
    return result


def check(data):
    scenarios = data["scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("supply at least one capacity scenario")
    output = []
    for scenario in scenarios:
        zones = scenario["usableCapacityByAZ"]
        if len(zones) != 3:
            raise ValueError("exactly three zones are required")
        demand = {r: number(scenario["productionDemand"][r]) for r in RESOURCES}
        capacity = {z: {r: number(c[r]) for r in RESOURCES} for z, c in zones.items()}
        for lost in zones:
            survivors = {r: sum(c[r] for z, c in capacity.items() if z != lost) for r in RESOURCES}
            deficits = {r: str(demand[r] - survivors[r]) for r in RESOURCES if survivors[r] < demand[r]}
            output.append({"scenario": scenario["name"], "lostAZ": lost, "passes": not deficits, "deficits": deficits})
    return {"passes": all(x["passes"] for x in output), "checks": output,
            "qualification": "Supplied usable-capacity arithmetic only; does not provision or protect spare capacity or validate scheduling, SLOs, bandwidth, and dependencies."}


def main():
    parser = argparse.ArgumentParser(description="Check supplied three-AZ capacity after loss of each zone, offline.")
    parser.add_argument("input")
    args = parser.parse_args()
    try:
        with open(args.input) as stream:
            result = check(json.load(stream))
    except (KeyError, TypeError, ValueError, OSError, InvalidOperation) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passes"] else 1)


if __name__ == "__main__":
    main()
