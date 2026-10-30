"""A conservative, reproducible interface to the SP 800-22 test families.

The supported profile fixes parameters before looking at the data. Mathematical
functions remain available separately for reproducing short textbook examples.
No result certifies randomness, physical entropy, or cryptographic security.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import math
import json
import platform

import numpy as np
import scipy
from scipy.special import gammaincc
from scipy.stats import binomtest

from ApproximateEntropy import ApproximateEntropy
from Complexity import ComplexityTest
from CumulativeSum import CumulativeSums
from FrequencyTest import FrequencyTest
from Matrix import Matrix
from RandomExcursions import RandomExcursions
from RunTest import RunTest
from Serial import Serial
from Spectral import SpectralTest
from TemplateMatching import TemplateMatching
from Universal import Universal
from Validation import InsufficientDataError, validate_bits

VERSION = "2.0.1.dev1"
INTERPRETATION = (
    "The null model is independent, equally probable bits. A p-value is not the "
    "probability that the source is random. Non-rejection does not prove physical "
    "randomness, entropy, independence, or cryptographic security. Multiple tests "
    "can reject by chance; their p-values are dependent. No overall randomness "
    "score or certification is computed."
)
TEST_NAMES = {
    "frequency": "Frequency (monobit)",
    "block_frequency": "Block frequency",
    "runs": "Runs",
    "longest_run": "Longest run of ones",
    "matrix_rank": "Binary matrix rank",
    "spectral": "Discrete Fourier transform",
    "non_overlapping_template": "Non-overlapping templates (all 148, m=9)",
    "overlapping_template": "Overlapping template",
    "universal": "Maurer universal",
    "linear_complexity": "Linear complexity",
    "serial": "Serial",
    "approximate_entropy": "Approximate entropy",
    "cusum_forward": "Cumulative sums (forward)",
    "cusum_backward": "Cumulative sums (backward)",
    "random_excursions": "Random excursions",
    "random_excursions_variant": "Random excursions variant",
}


@dataclass
class TestResult:
    test_id: str
    name: str
    status: str
    n_bits: int
    alpha: float
    parameters: dict = field(default_factory=dict)
    p_values: dict = field(default_factory=dict)
    decisions: dict = field(default_factory=dict)
    bits_used: int = 0
    discarded_bits: int = 0
    reason: str = ""

    def to_dict(self):
        return asdict(self)


def _validate_alpha(alpha):
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not 0 < alpha < 1:
        raise ValueError("alpha must be a finite number strictly between 0 and 1")


def _templates():
    # An unbordered word has no proper prefix equal to a suffix. These are the
    # 148 length-nine templates supplied with NIST STS, in binary order.
    for i in range(512):
        word = f"{i:09b}"
        if all(word[:k] != word[-k:] for k in range(1, 9)):
            yield word


def run_test(binary_data, test_id, alpha=0.01):
    """Evaluate one family in the supported profile, or explain inapplicability.

    Sample-size gates are conservative operating recommendations, not a proof
    of calibration. They are specified in SCIENTIFIC_NOTES.md. ``error`` denotes
    a computational failure, never statistical evidence against the null.
    """
    validate_bits(binary_data)
    _validate_alpha(alpha)
    if test_id not in TEST_NAMES:
        raise ValueError(f"unknown test: {test_id}")
    n = len(binary_data)
    result = TestResult(test_id, TEST_NAMES[test_id], "not_applicable", n, alpha)

    def require(condition, reason):
        if not condition:
            raise InsufficientDataError(reason)

    def blocks(size):
        result.bits_used = n // size * size
        result.discarded_bits = n - result.bits_used

    try:
        result.bits_used = n
        if test_id == "frequency":
            require(n >= 100, "Requires at least 100 bits for the normal approximation.")
            raw = FrequencyTest.monobit_test(binary_data)
        elif test_id == "block_frequency":
            m = max(20, n // 100 + 1)
            result.parameters = {"block_size": m, "blocks": n // m}
            require(n >= 100, "Requires at least 100 bits; M>=20, M>0.01n, N<100.")
            blocks(m)
            raw = FrequencyTest.block_frequency(binary_data, block_size=m)
        elif test_id == "runs":
            require(n >= 100, "Requires at least 100 bits for the normal approximation.")
            pi = binary_data.count("1") / n
            require(abs(pi - 0.5) < 2 / math.sqrt(n),
                    "Runs prerequisite failed: |proportion of ones - 0.5| must be < 2/sqrt(n). "
                    "Inspect the frequency result; no runs p-value was evaluated.")
            raw = RunTest.run_test(binary_data)
        elif test_id == "longest_run":
            require(n >= 128, "Requires at least 128 bits.")
            m = 8 if n < 6272 else 128 if n < 750000 else 10000
            result.parameters = {"block_size": m, "blocks": n // m}
            blocks(m)
            raw = RunTest.longest_one_block_test(binary_data)
        elif test_id == "matrix_rank":
            result.parameters = {"rows": 32, "columns": 32, "blocks": n // 1024}
            require(n // 1024 >= 38, "Requires at least 38 complete 32 by 32 matrices (38,912 bits).")
            blocks(1024)
            raw = Matrix.binary_matrix_rank_text(binary_data)
        elif test_id == "spectral":
            require(n == 1000000,
                    "Supported profile requires exactly 1,000,000 bits, following NIST's "
                    "2010 software guidance. Split longer data explicitly with --sequence-length.")
            raw = SpectralTest.spectral_test(binary_data)
        elif test_id == "non_overlapping_template":
            result.parameters = {"pattern_length": 9, "template_count": 148,
                                 "blocks": 8, "block_size": n // 8}
            require(n >= 1000000,
                    "This conservative template profile requires at least 1,000,000 bits.")
            result.bits_used = n // 8 * 8
            result.discarded_bits = n % 8
            values = {word: TemplateMatching.non_overlapping_test(
                binary_data, template_pattern=word, block=8)[0] for word in _templates()}
            raw = None
        elif test_id == "overlapping_template":
            result.parameters = {"pattern_size": 9, "block_size": 1032, "blocks": n // 1032}
            require(n >= 1000000, "Requires at least 1,000,000 bits in the supported overlap profile.")
            blocks(1032)
            raw = TemplateMatching.overlapping_patterns(binary_data)
        elif test_id == "universal":
            require(n >= 387840, "Requires at least 387,840 bits (L=6).")
            thresholds = [387840, 904960, 2068480, 4654080, 10342400, 22753280,
                          49643520, 107560960, 231669760, 496435200, 1059061760]
            m = max(i + 6 for i, lower in enumerate(thresholds) if n >= lower)
            q = 10 * 2 ** m
            result.parameters = {"pattern_length": m, "initialization_blocks": q,
                                 "test_blocks": n // m - q}
            blocks(m)
            raw = Universal.statistical_test(binary_data)
        elif test_id == "linear_complexity":
            result.parameters = {"block_size": 500, "blocks": n // 500}
            require(n >= 1000000, "Requires at least 1,000,000 bits with M=500.")
            blocks(500)
            raw = ComplexityTest.linear_complexity_test(binary_data)
        elif test_id == "serial":
            result.parameters = {"pattern_length": 16}
            require(16 < n.bit_length() - 1 - 2,
                    "Fixed m=16 requires m < floor(log2(n))-2 (n >= 524,288).")
            raw = Serial.serial_test(binary_data, pattern_length=16)
            values = {"delta1": raw[0][0], "delta2": raw[1][0]}
            raw = None
        elif test_id == "approximate_entropy":
            result.parameters = {"pattern_length": 10}
            require(10 < n.bit_length() - 1 - 5,
                    "Fixed m=10 requires m < floor(log2(n))-5 (n >= 65,536).")
            raw = ApproximateEntropy.approximate_entropy_test(binary_data, pattern_length=10)
        elif test_id.startswith("cusum_"):
            mode = int(test_id == "cusum_backward")
            result.parameters = {"mode": mode}
            require(n >= 100, "Requires at least 100 bits for the asymptotic approximation.")
            raw = CumulativeSums.cumulative_sums_test(binary_data, mode=mode)
        else:
            require(n >= 1000000, "Requires at least 1,000,000 bits in the supported excursion profile.")
            result.parameters = {"cycles": RandomExcursions.cycle_count(binary_data),
                                 "minimum_cycles": math.ceil(max(500, 0.005 * math.sqrt(n)))}
            function = (RandomExcursions.variant_test if test_id.endswith("variant")
                        else RandomExcursions.random_excursions_test)
            raw = function(binary_data)
            values = {f"{int(float(row[0])):+d}": row[3] for row in raw}
            raw = None
        if raw is not None:
            values = {"p": raw[0]}
        values = {key: float(p) for key, p in values.items()}
        if not values or any(not math.isfinite(p) or not 0 <= p <= 1 for p in values.values()):
            raise ArithmeticError("The test produced an invalid p-value.")
        result.status = "evaluated"
        result.p_values = values
        result.decisions = {key: "reject" if p < alpha else "not_rejected" for key, p in values.items()}
    except InsufficientDataError as exc:
        result.bits_used = result.discarded_bits = 0
        result.reason = str(exc)
    except (ArithmeticError, ValueError) as exc:
        result.status = "error"
        result.bits_used = result.discarded_bits = 0
        result.reason = f"{type(exc).__name__}: {exc}"
    return result


def run_suite(binary_data, tests=None, alpha=0.01, progress=None):
    """Run selected families. Selection is fixed before any p-values are seen."""
    validate_bits(binary_data)
    _validate_alpha(alpha)
    selected = list(TEST_NAMES if tests is None else tests)
    if not selected or len(set(selected)) != len(selected) or any(t not in TEST_NAMES for t in selected):
        raise ValueError("tests must contain unique, known test IDs and must not be empty")
    results = []
    for test_id in selected:
        result = run_test(binary_data, test_id, alpha)
        results.append(result.to_dict())
        if progress is not None:
            progress(result)
    return {
        "schema_version": 1, "suite_version": VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input": {"n_bits": len(binary_data),
                  "sha256_ascii_bits": sha256(binary_data.encode("ascii")).hexdigest()},
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "scipy": scipy.__version__},
        "alpha": alpha, "profile": "conservative-sp800-22-v1",
        "interpretation": INTERPRETATION, "results": results,
    }


def summarize_p_values(p_values, alpha=0.01, *, assume_calibrated=False):
    """Second-level diagnostics for independent sequences of ONE test channel.

    Never pool different tests, states or templates. This API cannot establish
    independence of submitted sequences. The 3-sigma interval is the NIST
    approximation, not a confidence interval for an unknown physical entropy.
    By default return descriptive counts only: p-values alone cannot identify
    their calibration or sampling regime. Explicit ``assume_calibrated=True``
    asserts independent uniform null p-values and nominal rejection rate alpha;
    it does not verify these assumptions. Prefer summarize_reports for gating.
    """
    if not isinstance(assume_calibrated, bool):
        raise TypeError("assume_calibrated must be a boolean")
    _validate_alpha(alpha)
    values = np.asarray(list(p_values), dtype=float)
    if values.ndim != 1 or len(values) == 0 or not np.all(np.isfinite(values)) or np.any((values < 0) | (values > 1)):
        raise ValueError("p_values must be a nonempty sequence of finite values in [0, 1]")
    count = len(values)
    passes = int(np.count_nonzero(values >= alpha))
    radius = 3 * math.sqrt(alpha * (1 - alpha) / count)
    interval = [max(0.0, 1 - alpha - radius), min(1.0, 1 - alpha + radius)]
    # STS uses floor(10*p), with p=1 assigned to the final cell. linspace
    # edges can round upward (e.g. 0.3), misclassifying exact decimal inputs.
    histogram = np.bincount(np.minimum((10 * values).astype(int), 9), minlength=10)
    uniformity = None
    if assume_calibrated and count >= 55:
        chi2 = float(np.sum((histogram - count / 10) ** 2 / (count / 10)))
        uniformity = float(gammaincc(9 / 2, chi2 / 2))
    return {
        "sequences": count, "non_rejections": passes, "proportion": passes / count,
        "nist_three_sigma_interval": interval if assume_calibrated else None,
        "proportion_in_interval": interval[0] <= passes / count <= interval[1] if assume_calibrated else None,
        "excess_rejections_binomial_p": float(binomtest(count - passes, count, alpha, alternative="greater").pvalue) if assume_calibrated else None,
        "uniformity_histogram": histogram.tolist(), "uniformity_p": uniformity,
        "uniformity_not_rejected": None if uniformity is None else uniformity >= 0.0001,
        "inference_supported": assume_calibrated,
        "inference_reason": "" if assume_calibrated else "Calibration and independence are not established from p-values alone.",
        "uniformity_reason": ("Calibration and independence are not established from p-values alone."
                              if not assume_calibrated else
                              "At least 55 eligible independent sequences required." if uniformity is None else ""),
    }


def _validate_report_structure(report):
    """Reject malformed observations before comparing or pooling reports."""
    try:
        if not isinstance(report, dict):
            raise ValueError("report must be an object")
        _validate_alpha(report["alpha"])
        n = report["input"]["n_bits"]
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError("n_bits must be a positive integer")
        digest = report["input"]["sha256_ascii_bits"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid input SHA-256")
        rows = report["results"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("results must be a nonempty list")
        seen = set()
        for row in rows:
            key = row["test_id"]
            if not isinstance(key, str) or key not in TEST_NAMES or key in seen:
                raise ValueError("results must have unique, known test IDs")
            seen.add(key)
            if not isinstance(row["parameters"], dict):
                raise ValueError("parameters must be an object")
            if row["n_bits"] != n or row["alpha"] != report["alpha"]:
                raise ValueError("result length/alpha differs from report")
            status, values, decisions = row["status"], row["p_values"], row["decisions"]
            if status not in ("evaluated", "not_applicable", "error"):
                raise ValueError("unknown result status")
            if not isinstance(values, dict) or not isinstance(decisions, dict):
                raise ValueError("p_values and decisions must be objects")
            if status != "evaluated":
                if values or decisions:
                    raise ValueError("unevaluated results must have no p-values or decisions")
                continue
            channels = ({"delta1", "delta2"} if key == "serial" else
                        set(_templates()) if key == "non_overlapping_template" else
                        {f"{x:+d}" for x in RandomExcursions.STATES} if key == "random_excursions" else
                        {f"{x:+d}" for x in RandomExcursions.VARIANT_STATES} if key == "random_excursions_variant" else {"p"})
            if set(values) != channels or set(decisions) != channels:
                raise ValueError("evaluated result must contain exactly the expected channels")
            for channel, p in values.items():
                if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
                    raise ValueError("invalid p-value")
                if decisions[channel] != ("reject" if p < report["alpha"] else "not_rejected"):
                    raise ValueError("decision disagrees with p-value and alpha")
        # Verify the fields used by signature even for a one-report batch.
        if isinstance(report["schema_version"], bool) or not isinstance(report["schema_version"], int):
            raise ValueError("invalid schema version")
        if not all(isinstance(report[k], str) for k in ("suite_version", "profile")):
            raise ValueError("invalid version/profile")
    except (KeyError, TypeError) as exc:
        raise ValueError("Malformed batch report") from exc


def _batch_inference_reason(report, test_id, duplicates):
    # This is a conservative operating restriction, not proof of calibration.
    if (report["schema_version"] != 1 or report["suite_version"] != VERSION
            or report["profile"] != "conservative-sp800-22-v1"
            or report["input"]["n_bits"] != 1000000 or report["alpha"] != 0.01):
        return "Second-level inference supports only current-profile 1,000,000-bit reports at alpha=0.01."
    if duplicates:
        return "Duplicate input hashes: independence is not established; inference is withheld."
    if test_id in ("runs", "random_excursions", "random_excursions_variant"):
        return "Second-level calibration after data-dependent applicability selection is not established."
    parameters = {
        "frequency": {}, "block_frequency": {"block_size": 10001, "blocks": 99},
        "longest_run": {"block_size": 10000, "blocks": 100},
        "matrix_rank": {"rows": 32, "columns": 32, "blocks": 976}, "spectral": {},
        "non_overlapping_template": {"pattern_length": 9, "template_count": 148, "blocks": 8, "block_size": 125000},
        "overlapping_template": {"pattern_size": 9, "block_size": 1032, "blocks": 968},
        "universal": {"pattern_length": 7, "initialization_blocks": 1280, "test_blocks": 141577},
        "linear_complexity": {"block_size": 500, "blocks": 2000},
        "serial": {"pattern_length": 16}, "approximate_entropy": {"pattern_length": 10},
        "cusum_forward": {"mode": 0}, "cusum_backward": {"mode": 1},
    }
    row = next(row for row in report["results"] if row["test_id"] == test_id)
    if row["parameters"] != parameters[test_id]:
        return "Parameters do not match the supported second-level regime."
    return ""


def summarize_reports(reports):
    """Group a homogeneous batch by test and p-value channel, never across them."""
    reports = list(reports)
    if not reports:
        raise ValueError("reports must not be empty")
    for report in reports:
        _validate_report_structure(report)
    first = reports[0]
    duplicates = len(reports) - len({r["input"]["sha256_ascii_bits"] for r in reports})
    def signature(report):
        return (report["schema_version"], report["suite_version"], report["alpha"],
                report["profile"], report["input"]["n_bits"],
                tuple((row["test_id"], json.dumps(
                    {key: value for key, value in row["parameters"].items()
                     if key not in ("cycles", "minimum_cycles")}, sort_keys=True, allow_nan=False))
                    for row in report["results"]))
    if any(signature(r) != signature(first) for r in reports):
        raise ValueError("Batch reports must have equal schema/suite versions, lengths, alpha, profile, test selection and parameters.")
    groups = {}
    for report in reports:
        for result in report["results"]:
            if result["status"] == "evaluated":
                for channel, p in result["p_values"].items():
                    groups.setdefault((result["test_id"], channel), []).append(p)
    summaries = []
    for (test_id, channel), values in groups.items():
        item = {"test_id": test_id, "channel": channel, "excluded_sequences": len(reports) - len(values)}
        reason = _batch_inference_reason(first, test_id, duplicates)
        item.update(summarize_p_values(values, first["alpha"], assume_calibrated=not reason))
        item["inference_reason"] = reason
        if reason:
            item["uniformity_reason"] = reason
        summaries.append(item)
    return {"sequences": len(reports), "duplicate_sequences": duplicates,
            "assumptions": "Requires independently obtained sequences from one stationary source. "
                           "Distinct hashes or disjoint segments do not establish independence. "
                           "Second-level tests are approximate and are not an overall certification.",
            "channels": summaries}
