import argparse
import json
from datetime import date
from decimal import Decimal, InvalidOperation


def analyze(data):
    if data.get("currency") != "USD" or not data.get("scope", "").strip():
        raise ValueError("USD currency and an explicit cost scope are required")
    if data.get("basis") not in {"net", "amortized", "unblended"}:
        raise ValueError("declare one consistent billing basis: net, amortized, or unblended")
    if not isinstance(data.get("comparison_notes"), str) or not data["comparison_notes"].strip():
        raise ValueError("describe workload comparability and discount treatment")
    windows = []
    for key in ("before", "after"):
        row = data[key]
        start, end = date.fromisoformat(row["start"]), date.fromisoformat(row["end_exclusive"])
        days = (end - start).days
        raw_amount = row["amount"]
        if isinstance(raw_amount, bool):
            raise ValueError("cost must be a finite non-negative number")
        amount = Decimal(str(raw_amount))
        if days <= 0 or not amount.is_finite() or amount < 0:
            raise ValueError("periods must be positive and costs finite and non-negative")
        windows.append((start, end, days, amount))
    before, after = windows
    if before[1] > after[0]:
        raise ValueError("before and after periods must not overlap or be reversed")
    if before[2] != after[2]:
        raise ValueError("compare equal-duration windows; do not infer equal workloads from daily averages")
    if before[3] == 0:
        raise ValueError("a zero baseline has no percentage saving")
    delta = before[3] - after[3]
    return {
        "scope": data["scope"], "currency": "USD", "basis": data["basis"],
        "days_per_window": before[2], "before": str(before[3]), "after": str(after[3]),
        "cost_reduction": str(delta),
        "reduction_percent": str((delta / before[3] * 100).quantize(Decimal("0.01"))),
        "comparison_notes": data["comparison_notes"],
        "qualification": "Arithmetic comparison only; does not establish causation or independently verify billing inputs.",
    }


def main():
    parser = argparse.ArgumentParser(description="Compare two supplied billing totals offline. End dates are exclusive.")
    parser.add_argument("input")
    args = parser.parse_args()
    try:
        with open(args.input) as stream:
            report = analyze(json.load(stream))
    except (ValueError, KeyError, TypeError, OSError, InvalidOperation) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
