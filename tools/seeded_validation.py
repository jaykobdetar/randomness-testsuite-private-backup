"""Bounded, reproducible diagnostics, without optimizing code to pass a seed.

Run from an installed checkout: python tools/seeded_validation.py --output run.json
SHAKE256 is a deterministic fixture generator, not a physical entropy source.
The report is evidence to inspect, not a calibration certificate or pass/fail gate.
"""
import argparse
from hashlib import shake_256
import json
from pathlib import Path
import time

from Suite import run_suite, summarize_reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequences", type=int, default=64)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.sequences <= 128:
        parser.error("--sequences must be between 1 and 128")
    prefix = b"randomness-testsuite release audit v1:"
    reports = []
    start = time.monotonic()
    durations = []
    for index in range(args.sequences):
        bits = "".join(f"{byte:08b}" for byte in shake_256(prefix + str(index).encode("ascii")).digest(125000))
        then = time.monotonic()
        report = run_suite(bits)
        durations.append(time.monotonic() - then)
        reports.append(report)
        print(f"Sequence {index + 1}/{args.sequences}: {durations[-1]:.2f}s", flush=True)
    output = {
        "generator": "SHAKE256(prefix + ASCII decimal index), 125000 output bytes, MSB first",
        "prefix": prefix.decode("ascii"), "first_index": 0,
        "n_bits_per_sequence": 1000000,
        "environment": reports[0]["environment"],
        "suite_version": reports[0]["suite_version"], "profile": reports[0]["profile"],
        "alpha": reports[0]["alpha"], "created_utc": reports[0]["created_utc"],
        "input_sha256_ascii_bits": [r["input"]["sha256_ascii_bits"] for r in reports],
        "seconds_per_sequence": durations, "total_seconds": time.monotonic() - start,
        "errors": [{"sequence": i, "test_id": row["test_id"], "reason": row["reason"]}
                   for i, report in enumerate(reports) for row in report["results"] if row["status"] == "error"],
        "second_level": summarize_reports(reports),
        "interpretation": "Fixed deterministic fixtures. Rejections are expected by chance across dependent channels. "
                          "This small experiment neither proves calibration nor establishes independence or source quality. "
                          "Excursion channels may have fewer than 55 eligible sequences; then uniformity is unavailable.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return bool(output["errors"])


if __name__ == "__main__":
    raise SystemExit(main())
