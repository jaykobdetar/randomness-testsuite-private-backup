"""Check the seeded experiment's 148 template channels against official C.

Uses a disposable, already built STS 2.1.2 installation. Overwrites its
AlgorithmTesting outputs. Temporary input is removed even on failure.
"""
import argparse
from hashlib import shake_256
import json
import math
from pathlib import Path
import subprocess
import tempfile

from Suite import _templates, summarize_p_values
from TemplateMatching import TemplateMatching


def compare_p_values(actual, expected, tolerance=5.1e-7):
    """Validate both vectors before computing any tolerance comparisons."""
    if not actual or len(actual) != len(expected):
        raise ValueError("Reference vectors must be nonempty and have equal lengths")
    for label, values in (("official", actual), ("Python", expected)):
        if any(not math.isfinite(p) or not 0 <= p <= 1 for p in values):
            raise ValueError(f"{label} vector contains a nonfinite or out-of-range p-value")
    return [i for i, (a, b) in enumerate(zip(actual, expected)) if abs(a - b) > tolerance]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sts-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sts = args.sts_root.resolve()
    templates = list(_templates())
    official = ["".join(row.split()) for row in (sts / "templates/template9").read_text().splitlines()]
    if templates != official:
        parser.error("official template9 order differs from this profile")
    expected = []
    with tempfile.NamedTemporaryFile(mode="w+", encoding="ascii", dir=sts / "data", prefix="audit-") as handle:
        for index in range(64):
            bits = "".join(f"{byte:08b}" for byte in shake_256(
                b"randomness-testsuite release audit v1:" + str(index).encode("ascii")).digest(125000))
            handle.write(bits + "\n")
            expected.extend(TemplateMatching.non_overlapping_test(bits, template_pattern=t)[0] for t in templates)
        handle.flush()
        relative = Path(handle.name).relative_to(sts)
        choices = f"0\n{relative}\n0\n000000010000000\n0\n64\n0\n"
        completed = subprocess.run([str(sts / "assess"), "1000000"], cwd=sts,
                                   input=choices, text=True, capture_output=True, timeout=180)
        if completed.returncode != 1 or "Statistical Testing Complete" not in completed.stdout:
            raise RuntimeError(f"C reference failed: {completed.stdout}\n{completed.stderr}")
    actual = [float(value) for value in (sts / "experiments/AlgorithmTesting/NonOverlappingTemplate/results.txt").read_text().split()]
    if len(actual) != len(expected):
        raise ValueError(f"Expected {len(expected)} reference results, got {len(actual)}")
    mismatches = compare_p_values(actual, expected)
    index = templates.index("000110111")
    output = {"sequences": 64, "templates": 148, "comparisons": len(actual),
              "reference": "NIST STS 2.1.2; source hashes in tests/fixtures/nist_sts_2_1_2.json",
              "absolute_tolerance": 5.1e-7,
              "max_absolute_difference": max(abs(a - b) for a, b in zip(actual, expected)),
              "mismatch_indices": mismatches,
              "inspected_channel": "000110111",
              "official_p_values": actual[index::148],
              "python_p_values": expected[index::148],
              "official_summary": summarize_p_values(actual[index::148], assume_calibrated=True),
              "python_summary": summarize_p_values(expected[index::148], assume_calibrated=True)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    return bool(mismatches)


if __name__ == "__main__":
    raise SystemExit(main())
