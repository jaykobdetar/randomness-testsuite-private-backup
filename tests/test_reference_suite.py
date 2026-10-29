"""Independent official-C regression for every supported-profile p-value channel.

Regenerate tests/fixtures/nist_sts_2_1_2.json with tools/reference_compare.py
and an official NIST STS 2.1.2 checkout. Normal tests require no C compiler,
external program or network. Each of four bundled constants covers 188 channels.

185 channels compare directly with the official C output at its six-decimal
precision (with 1.1e-6 tolerance for legacy cusum normal-CDF accuracy). Three families
deliberately refine null-cell probabilities: their observed histograms must
match C exactly, and their p-values must match the refined calculation.
This is regression evidence, not NIST certification or proof of calibration.
"""

import ast
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from math import fsum
from pathlib import Path
import re

import pytest
from scipy.special import gammaincc

from Complexity import ComplexityTest
from RunTest import RunTest, _longest_run_probabilities
from Suite import TEST_NAMES, run_suite
from TemplateMatching import TemplateMatching, _overlapping_probabilities


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = json.loads((ROOT/"tests"/"fixtures"/"nist_sts_2_1_2.json").read_text())
REFINED_FAMILIES = {
    "longest_run": (RunTest.longest_one_block_test, "counts", 6),
    "overlapping_template": (TemplateMatching.overlapping_patterns, "bins", 5),
    "linear_complexity": (ComplexityTest.linear_complexity_test, "bins", 6),
}


@pytest.fixture(scope="module", params=("e","pi","sqrt2","sqrt3"))
def reference_run(request):
    name = request.param
    vector = REFERENCE["vectors"][name]
    bits = "".join((ROOT/"data"/f"data.{name}").read_text().split())[:1000000]
    assert len(bits) == vector["n_bits"]
    assert sha256(bits.encode("ascii")).hexdigest() == vector["sha256_ascii_bits"]
    report = run_suite(bits)
    assert all(row["status"] == "evaluated" for row in report["results"])
    return name, bits, vector, report


def test_all_188_reference_channels(reference_run):
    name, _, vector, report = reference_run
    actual = {f"{row['test_id']}:{channel}": p
              for row in report["results"] for channel,p in row["p_values"].items()}
    expected = vector["p_values"]
    assert len(actual) == len(expected) == 188
    assert actual.keys() == expected.keys()
    compared = 0
    for channel, expected_p in expected.items():
        if channel.split(":")[0] not in REFINED_FAMILIES:
            tolerance = 1.1e-6 if channel.startswith("cusum_") else 5.1e-7
            assert actual[channel] == pytest.approx(expected_p, rel=0, abs=tolerance), (name, channel)
            compared += 1
    assert compared == 185
    # The C run is configured to match the deterministic profile; Appendix B
    # uses M=128, which must not be compared directly with this profile's M.
    block = next(row for row in report["results"] if row["test_id"] == "block_frequency")
    assert block["parameters"]["block_size"] == REFERENCE["parameters"]["block_frequency_M"] == 10001


@pytest.mark.parametrize("family", tuple(REFINED_FAMILIES))
def test_refined_family_observations_match_c_exactly(reference_run, family):
    _, bits, vector, report = reference_run
    function, label, degrees = REFINED_FAMILIES[family]
    output = StringIO()
    with redirect_stdout(output):
        p_value, _ = function(bits, verbose=True)
    # The legacy API exposes observed counts through verbose diagnostics.
    match = re.search(rf"{label}=(\[[^\]]*\])", output.getvalue())
    assert match, output.getvalue()
    counts = ast.literal_eval(match.group(1))
    assert counts == vector["category_counts"][family]
    if family == "longest_run":
        probabilities = _longest_run_probabilities(10000,10,16)
    elif family == "overlapping_template":
        probabilities = _overlapping_probabilities(9,1032)
    else:
        probabilities = (1/96,1/32,1/8,1/2,1/4,1/16,1/48)
    n = sum(counts)
    statistic = fsum((observed-n*probability)**2/(n*probability)
                     for observed, probability in zip(counts, probabilities))
    expected = gammaincc(degrees/2, statistic/2)
    assert p_value == pytest.approx(expected, rel=1e-12, abs=1e-15)
    result = next(row for row in report["results"] if row["test_id"] == family)
    assert result["p_values"]["p"] == pytest.approx(expected, rel=1e-12, abs=1e-15)


def test_reference_fixture_identity_and_profile():
    assert len(REFERENCE["vectors"]) == 4
    assert len(TEST_NAMES) == 16  # forward/reverse cusum are separate families
    assert REFERENCE["reference_version"] == "NIST STS 2.1.2"
    assert len(REFERENCE["reference_source_sha256"]) > 15
