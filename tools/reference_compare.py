"""Regenerate offline regression fixtures using an unpacked official NIST STS 2.1.2.

Usage:
    python tools/reference_compare.py --sts-root /path/to/sts-2.1.2
The assess executable must already be built. This overwrites that installation's
experiments/AlgorithmTesting outputs. It downloads nothing and changes no C code.

The C block-frequency parameter is explicitly set to M=10001 to match the
conservative Python profile at n=1,000,000, rather than Appendix B's M=128.
Official six-decimal p-values are retained unchanged. For longest-run,
overlapping-template and linear-complexity tests, observed category counts
are also retained so tests can isolate deliberate null-probability refinements.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess


N = 1000000
SOURCE_URL = "https://csrc.nist.gov/CSRC/media/Projects/Random-Bit-Generation/documents/sts-2_1_2.zip"
FAMILIES = {
    "Frequency": ("frequency", ["p"]),
    "BlockFrequency": ("block_frequency", ["p"]),
    "CumulativeSums": ("cusum", ["forward", "backward"]),
    "Runs": ("runs", ["p"]),
    "LongestRun": ("longest_run", ["p"]),
    "Rank": ("matrix_rank", ["p"]),
    "FFT": ("spectral", ["p"]),
    "NonOverlappingTemplate": ("non_overlapping_template", None),
    "OverlappingTemplate": ("overlapping_template", ["p"]),
    "Universal": ("universal", ["p"]),
    "ApproximateEntropy": ("approximate_entropy", ["p"]),
    "RandomExcursions": ("random_excursions", [f"{x:+d}" for x in (-4,-3,-2,-1,1,2,3,4)]),
    "RandomExcursionsVariant": ("random_excursions_variant", [f"{x:+d}" for x in (*range(-9,0), *range(1,10))]),
    "Serial": ("serial", ["delta1", "delta2"]),
    "LinearComplexity": ("linear_complexity", ["p"]),
}


def category_counts(path, width):
    candidates = []
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) >= width and all(item.isdecimal() for item in fields[:width]):
            candidates.append([int(item) for item in fields[:width]])
    if len(candidates) != 1:
        raise ValueError(f"Could not unambiguously read category counts from {path}")
    return candidates[0]


def capture(sts, name, source):
    bits = "".join(source.read_text(encoding="ascii").split())[:N]
    if len(bits) != N or set(bits) != {"0","1"}:
        raise ValueError(f"Invalid reference bit fixture: {source}")
    reference_bits = "".join((sts/"data"/f"data.{name}").read_text(encoding="ascii").split())[:N]
    if bits != reference_bits:
        raise ValueError(f"Bundled data.{name} differs from official NIST data")

    # file source, select all tests, set block M, end parameter selection,
    # one sequence, ASCII input. NIST assess returns 1 on successful completion.
    user_input = f"0\ndata/data.{name}\n1\n1\n10001\n0\n1\n0\n"
    process = subprocess.run([str(sts/"assess"),str(N)], cwd=sts,
                             input=user_input, text=True, capture_output=True, timeout=180)
    if process.returncode != 1 or "Statistical Testing Complete" not in process.stdout:
        raise RuntimeError(f"NIST assess did not complete: {process.stdout}\n{process.stderr}")
    root = sts/"experiments"/"AlgorithmTesting"
    frequency = (root/"freq.txt").read_text()
    expected_frequency = f"0s = {bits.count('0')} 1s = {bits.count('1')}"
    if f"data/data.{name}" not in frequency or expected_frequency not in frequency:
        raise ValueError("Official reference input accounting does not match")
    templates = ["".join(line.split()) for line in (sts/"templates"/"template9").read_text().splitlines()]
    if len(templates) != 148:
        raise ValueError("Expected exactly 148 official templates")
    p_values = {}
    for directory, (family, channels) in FAMILIES.items():
        values = [float(value) for value in (root/directory/"results.txt").read_text().split()]
        channels = templates if channels is None else channels
        if len(values) != len(channels):
            raise ValueError(f"Unexpected C result count for {family}: {len(values)}")
        for channel, value in zip(channels, values):
            key = f"cusum_{channel}:p" if family == "cusum" else f"{family}:{channel}"
            p_values[key] = value
    if len(p_values) != 188:
        raise ValueError("Expected 188 reference channels")
    categories = {
        "longest_run": category_counts(root/"LongestRun"/"stats.txt",7),
        "overlapping_template": category_counts(root/"OverlappingTemplate"/"stats.txt",6),
        "linear_complexity": category_counts(root/"LinearComplexity"/"stats.txt",7),
    }
    return {"n_bits":N, "sha256_ascii_bits":sha256(bits.encode()).hexdigest(),
            "p_values":p_values, "category_counts":categories}


def main():
    repository = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sts-root",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=repository/"tests"/"fixtures"/"nist_sts_2_1_2.json")
    args = parser.parse_args()
    sts = args.sts_root.resolve()
    if not (sts/"assess").is_file():
        parser.error("--sts-root must contain a compiled assess executable")
    fixture = {
        "source":SOURCE_URL, "reference_version":"NIST STS 2.1.2",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "parameters":{"n_bits":N,"sequences":1,"block_frequency_M":10001,
                      "non_overlapping_m":9,"overlapping_m":9,"approximate_entropy_m":10,
                      "serial_m":16,"linear_complexity_M":500},
        "reference_precision_decimal_places":6,
        "deliberate_differences":{
            "longest_run":"Exact finite-block category probabilities replace rounded C tables.",
            "overlapping_template":"Exact finite-block category probabilities replace C's compound-Poisson approximation (which overwrites its initialized table).",
            "linear_complexity":"Exact limiting probabilities replace C's 0.01047 typo and rounded cells.",
            "block_frequency":"C is configured with M=10001 to match the conservative profile, not default M=128."
        },
        "reference_source_sha256":{path.name:sha256(path.read_bytes()).hexdigest()
                                   for path in sorted((sts/"src").glob("*.c"))},
        "vectors":{}
    }
    for name in ("e","pi","sqrt2","sqrt3"):
        fixture["vectors"][name] = capture(sts,name,repository/"data"/f"data.{name}")
        print(f"Captured {name}: 188 channels",flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(fixture,indent=2,sort_keys=True)+"\n")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
