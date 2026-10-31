"""Contracts for reporting, applicability, encodings, batching and CLI exits."""

from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from BitInput import read_bits, split_sequences
import Suite
from Validation import InsufficientDataError, positive_int, validate_bits


REPOSITORY = Path(__file__).resolve().parents[1]
BALANCED = "01" * 50


@pytest.mark.parametrize("pattern", ["0", "1", "01", "0011"])
def test_full_profile_handles_million_bit_degenerate_sequences(pattern):
    bits = pattern * (1000000 // len(pattern))
    results = {row["test_id"]: row for row in Suite.run_suite(bits)["results"]}
    assert all(row["status"] != "error" for row in results.values())
    if len(pattern) == 1:
        assert results["frequency"]["decisions"] == {"p": "reject"}
        assert results["runs"]["status"] == "not_applicable"
        assert results["random_excursions"]["status"] == "not_applicable"
    else:
        assert results["frequency"]["p_values"] == {"p": 1.0}
        assert results["spectral"]["decisions"] == {"p": "reject"}
    assert results["linear_complexity"]["decisions"] == {"p": "reject"}


def test_short_sequences_are_not_applicable_without_invented_p_values():
    report = Suite.run_suite("0101")
    assert len(report["results"]) == len(Suite.TEST_NAMES)
    assert {result["status"] for result in report["results"]} == {"not_applicable"}
    for result in report["results"]:
        assert result["p_values"] == result["decisions"] == {}
        assert result["bits_used"] == result["discarded_bits"] == 0
        assert result["reason"]
    assert not {"overall_p", "overall_p_value", "randomness_score", "passed"} & report.keys()


def test_biased_runs_prerequisite_is_distinct_from_rejecting_frequency():
    report = Suite.run_suite("1" * 100, tests=["frequency", "runs"])
    frequency, runs = report["results"]
    assert frequency["status"] == "evaluated"
    assert frequency["decisions"] == {"p": "reject"}
    assert runs["status"] == "not_applicable"
    assert runs["p_values"] == runs["decisions"] == {}
    assert "prerequisite" in runs["reason"]


def test_custom_alpha_uses_p_value_and_ignores_legacy_boolean(monkeypatch):
    monkeypatch.setattr(Suite.FrequencyTest, "monobit_test", lambda _: (0.03, True))
    assert Suite.run_test(BALANCED, "frequency", alpha=0.05).decisions == {"p": "reject"}
    assert Suite.run_test(BALANCED, "frequency", alpha=0.03).decisions == {"p": "not_rejected"}
    assert Suite.run_test(BALANCED, "frequency", alpha=0.01).decisions == {"p": "not_rejected"}


def test_serial_preserves_both_channels_and_their_individual_decisions(monkeypatch):
    monkeypatch.setattr(Suite.Serial, "serial_test", lambda *a, **kw: ((0.02, True), (0.6, False)))
    result = Suite.run_test("01" * 262144, "serial", alpha=0.05)
    assert result.status == "evaluated"
    assert result.p_values == {"delta1": 0.02, "delta2": 0.6}
    assert result.decisions == {"delta1": "reject", "delta2": "not_rejected"}


def test_all_templates_have_separate_channels(monkeypatch):
    seen = []

    def template_result(bits, template_pattern, block):
        seen.append((template_pattern, block))
        return int(template_pattern, 2) / 511, True

    monkeypatch.setattr(Suite.TemplateMatching, "non_overlapping_test", template_result)
    result = Suite.run_test("01" * 500000, "non_overlapping_template")
    assert result.status == "evaluated"
    assert len(result.p_values) == len(result.decisions) == len(seen) == 148
    assert set(result.p_values) == {word for word, _ in seen}
    assert all(len(word) == 9 and block == 8 for word, block in seen)
    assert "p" not in result.p_values


@pytest.mark.parametrize("test_id,function_name,states", [
    ("random_excursions", "random_excursions_test", tuple(range(-4, 0)) + tuple(range(1, 5))),
    ("random_excursions_variant", "variant_test", tuple(range(-9, 0)) + tuple(range(1, 10))),
])
def test_excursions_preserve_every_state_channel(monkeypatch, test_id, function_name, states):
    monkeypatch.setattr(Suite.RandomExcursions, "cycle_count", lambda _: 500)
    monkeypatch.setattr(Suite.RandomExcursions, function_name,
                        lambda _: [(f"{x:+d}", x, 7, 0.01, False) for x in states])
    result = Suite.run_test("01" * 500000, test_id)
    assert result.status == "evaluated"
    assert set(result.p_values) == {f"{state:+d}" for state in states}
    assert set(result.decisions.values()) == {"not_rejected"}


def test_excursion_cycle_requirement_is_not_a_failure():
    result = Suite.run_test("0" * 1000000, "random_excursions_variant")
    assert result.status == "not_applicable"
    assert result.parameters["cycles"] == 1
    assert result.parameters["minimum_cycles"] == 500
    assert result.p_values == result.decisions == {}


@pytest.mark.parametrize("p", [float("nan"), float("inf"), -0.01, 1.01])
def test_invalid_computed_p_value_is_an_error_not_a_rejection(monkeypatch, p):
    monkeypatch.setattr(Suite.FrequencyTest, "monobit_test", lambda _: (p, True))
    result = Suite.run_test(BALANCED, "frequency")
    assert result.status == "error"
    assert result.p_values == result.decisions == {}
    assert "invalid p-value" in result.reason


def test_computational_errors_and_insufficient_data_remain_distinct(monkeypatch):
    def unavailable(_):
        raise InsufficientDataError("not enough observations")

    def invalid(_):
        raise ArithmeticError("unstable calculation")

    monkeypatch.setattr(Suite.FrequencyTest, "monobit_test", unavailable)
    assert Suite.run_test(BALANCED, "frequency").status == "not_applicable"
    monkeypatch.setattr(Suite.FrequencyTest, "monobit_test", invalid)
    result = Suite.run_test(BALANCED, "frequency")
    assert result.status == "error"
    assert result.decisions == {}
    assert "ArithmeticError" in result.reason


def test_report_preserves_requested_order_progress_provenance_and_all_input_bits():
    bits = BALANCED + "101"
    updates = []
    report = Suite.run_suite(bits, tests=["block_frequency", "frequency"], progress=updates.append)
    assert [row["test_id"] for row in report["results"]] == ["block_frequency", "frequency"]
    assert [result.test_id for result in updates] == ["block_frequency", "frequency"]
    assert report["input"] == {"n_bits": len(bits), "sha256_ascii_bits": sha256(bits.encode("ascii")).hexdigest()}
    assert report["suite_version"] == Suite.VERSION
    assert report["schema_version"] == 1
    assert set(report["environment"]) == {"python", "numpy", "scipy"}
    assert report["created_utc"].endswith("+00:00")
    block, frequency = report["results"]
    assert block["bits_used"] == 100 and block["discarded_bits"] == 3
    assert frequency["bits_used"] == 103 and frequency["discarded_bits"] == 0
    # Reports must remain strict JSON, including machine-readable statuses.
    assert json.loads(json.dumps(report, allow_nan=False)) == report


@pytest.mark.parametrize("test_id,minimum", [
    ("frequency", 100), ("longest_run", 128), ("matrix_rank", 38912),
    ("universal", 387840), ("serial", 524288), ("approximate_entropy", 65536),
    ("linear_complexity", 1000000), ("overlapping_template", 1000000),
])
def test_profile_rejects_samples_just_below_minimum(test_id, minimum):
    assert Suite.run_test("0" * (minimum - 1), test_id).status == "not_applicable"


def test_spectral_profile_requires_exact_million_without_silent_truncation(monkeypatch):
    calls = []
    monkeypatch.setattr(Suite.SpectralTest, "spectral_test", lambda bits: (calls.append(len(bits)) or 0.5, True))
    for n in (999999, 1000001, 2000000):
        result = Suite.run_test("0" * n, "spectral")
        assert result.status == "not_applicable"
        assert result.p_values == {}
    assert calls == []
    result = Suite.run_test("0" * 1000000, "spectral")
    assert result.status == "evaluated"
    assert calls == [1000000]
    assert result.bits_used == 1000000


@pytest.mark.parametrize("alpha", [0, 1, -0.1, 1.1, float("nan"), float("inf"), True, "0.01", None])
def test_all_public_inference_entry_points_reject_invalid_alpha(alpha):
    for operation in (
        lambda: Suite.run_test(BALANCED, "frequency", alpha),
        lambda: Suite.run_suite(BALANCED, ["frequency"], alpha),
        lambda: Suite.summarize_p_values([0.5], alpha),
    ):
        with pytest.raises(ValueError):
            operation()


@pytest.mark.parametrize("selection", [[], ["missing"], ["frequency", "frequency"], "frequency"])
def test_invalid_or_duplicate_test_selection_is_rejected(selection):
    with pytest.raises(ValueError):
        Suite.run_suite(BALANCED, selection)


@pytest.mark.parametrize("bits", ["", "01 ", "01\n", "０１", "0x1", 0.1, float("nan"), b"01", [0, 1]])
def test_runner_and_validation_reject_malformed_bits(bits):
    for operation in (lambda: validate_bits(bits), lambda: Suite.run_suite(bits, ["frequency"])):
        with pytest.raises((TypeError, ValueError)):
            operation()


@pytest.mark.parametrize("value", [0, -1, 1.0, 0.5, float("nan"), float("inf"), True, "100"])
def test_integer_contract_does_not_silently_round_or_coerce(value):
    with pytest.raises(ValueError):
        positive_int(value, "size")
    with pytest.raises(ValueError):
        split_sequences(BALANCED, value)


def test_second_level_uniformity_starts_at_55_and_keeps_one_in_last_bin():
    below = Suite.summarize_p_values([0.5] * 54, assume_calibrated=True)
    assert below["uniformity_p"] is None
    assert below["uniformity_not_rejected"] is None
    assert below["uniformity_reason"]
    result = Suite.summarize_p_values([0.0] * 27 + [1.0] * 28, assume_calibrated=True)
    assert result["sequences"] == 55
    assert result["uniformity_histogram"] == [27] + [0] * 8 + [28]
    assert result["non_rejections"] == 28
    assert result["uniformity_p"] is not None
    assert result["uniformity_not_rejected"] is False
    assert result["uniformity_reason"] == ""


def test_second_level_alpha_boundary_interval_and_exact_binomial_extreme():
    result = Suite.summarize_p_values([0.049, 0.05, 1.0], alpha=0.05, assume_calibrated=True)
    assert result["non_rejections"] == 2
    assert result["proportion"] == pytest.approx(2 / 3)
    radius = 3 * math.sqrt(0.05 * 0.95 / 3)
    assert result["nist_three_sigma_interval"] == pytest.approx([0.95 - radius, 1.0])
    all_rejected = Suite.summarize_p_values([0.0] * 10, alpha=0.05, assume_calibrated=True)
    assert all_rejected["excess_rejections_binomial_p"] == pytest.approx(0.05 ** 10, rel=1e-14)


def test_second_level_decimal_boundaries_follow_nist_integer_bins():
    values = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1] * 5
    result = Suite.summarize_p_values(values, assume_calibrated=True)
    assert result["uniformity_histogram"] == [5] * 9 + [10]
    # Chi-square = 9*(5-5.5)^2/5.5 + (10-5.5)^2/5.5 = 45/11.
    from scipy.special import gammaincc
    assert result["uniformity_p"] == pytest.approx(gammaincc(4.5, 45 / 22))


@pytest.mark.parametrize("alias", ["same", "symlink", "hardlink"])
def test_cli_does_not_destroy_source_when_output_aliases_input(tmp_path, alias):
    source = tmp_path / "bits.txt"
    source.write_text(BALANCED)
    output = source if alias == "same" else tmp_path / "report.json"
    if alias == "symlink":
        output.symlink_to(source)
    elif alias == "hardlink":
        output.hardlink_to(source)
    completed = _cli(str(source), "--output", str(output), "--tests", "frequency")
    assert completed.returncode == 2
    assert "must not overwrite" in completed.stderr
    assert source.read_text() == BALANCED


@pytest.mark.parametrize("p_values", [[], [-0.01], [1.01], [float("nan")], [float("inf")], [[0.1, 0.2]]])
def test_second_level_invalid_values_are_rejected(p_values):
    with pytest.raises(ValueError):
        Suite.summarize_p_values(p_values)


def test_second_level_keeps_tests_separate_and_reports_duplicate_sequences():
    report = Suite.run_suite(BALANCED, tests=["frequency", "runs"])
    result = Suite.summarize_reports([report, deepcopy(report)])
    assert result["sequences"] == 2
    assert result["duplicate_sequences"] == 1
    assert {(row["test_id"], row["channel"]) for row in result["channels"]} == {
        ("frequency", "p"), ("runs", "p")
    }
    assert all(row["sequences"] == 2 for row in result["channels"])
    assert "independence" in result["assumptions"]
    assert not {"overall_p", "pooled_p_values", "randomness_score"} & result.keys()


def test_second_level_keeps_serial_channels_separate(monkeypatch):
    monkeypatch.setattr(Suite.Serial, "serial_test", lambda *a, **kw: ((0.001, False), (0.5, True)))
    report = Suite.run_suite("01" * 262144, tests=["serial"])
    summary = Suite.summarize_reports([report] * 3)
    channels = {row["channel"]: row for row in summary["channels"]}
    assert set(channels) == {"delta1", "delta2"}
    assert channels["delta1"]["sequences"] == channels["delta2"]["sequences"] == 3
    assert channels["delta1"]["non_rejections"] == 0
    assert channels["delta2"]["non_rejections"] == 3


def test_second_level_excludes_inapplicable_channels_without_assigning_zero():
    balanced = Suite.run_suite(BALANCED, tests=["frequency", "runs"])
    biased = Suite.run_suite("1" * 100, tests=["frequency", "runs"])
    summary = Suite.summarize_reports([balanced, biased])
    channels = {row["test_id"]: row for row in summary["channels"]}
    assert channels["frequency"]["sequences"] == 2
    assert channels["frequency"]["excluded_sequences"] == 0
    assert channels["runs"]["sequences"] == 1
    assert channels["runs"]["excluded_sequences"] == 1


@pytest.mark.parametrize("field,value", [
    ("alpha", 0.05), ("profile", "other-profile"), ("suite_version", "different-implementation"),
    ("schema_version", 999),
])
def test_batch_refuses_different_inference_or_implementation_versions(field, value):
    original = Suite.run_suite(BALANCED, tests=["frequency"])
    changed = deepcopy(original)
    changed[field] = value
    with pytest.raises(ValueError):
        Suite.summarize_reports([original, changed])


def test_batch_refuses_different_lengths_test_selections_or_parameters():
    original = Suite.run_suite(BALANCED, tests=["block_frequency", "frequency"])
    changes = []
    changed = deepcopy(original)
    changed["input"]["n_bits"] += 1
    changes.append(changed)
    changed = deepcopy(original)
    changed["results"] = changed["results"][1:]
    changes.append(changed)
    changed = deepcopy(original)
    changed["results"][0]["parameters"]["block_size"] += 1
    changes.append(changed)
    for changed in changes:
        with pytest.raises(ValueError):
            Suite.summarize_reports([original, changed])


def test_batch_allows_different_observed_excursion_cycle_counts(monkeypatch):
    monkeypatch.setattr(Suite.RandomExcursions, "cycle_count", lambda _: 500)
    monkeypatch.setattr(Suite.RandomExcursions, "variant_test",
                        lambda _: [(f"{x:+d}", x, 500, 0.5, True) for x in Suite.RandomExcursions.VARIANT_STATES])
    original = Suite.run_suite("01" * 500000, tests=["random_excursions_variant"])
    changed = deepcopy(original)
    changed["results"][0]["parameters"]["cycles"] = 700
    changed["input"]["sha256_ascii_bits"] = "a" * 64
    summary = Suite.summarize_reports([original, changed])
    assert summary["channels"][0]["sequences"] == 2
    assert summary["duplicate_sequences"] == 0


def test_empty_batch_is_invalid():
    with pytest.raises(ValueError):
        Suite.summarize_reports([])


def test_ascii_reader_removes_only_explicit_whitespace_and_preserves_digest(tmp_path):
    source = b" 01\t10\r\n01\v10\f" + b"01" * 500001 + b"1"
    path = tmp_path / "bits.txt"
    path.write_bytes(source)
    bits, metadata = read_bits(path)
    expected = "01100110" + "01" * 500001 + "1"
    assert bits == expected and len(bits) > 1000000
    assert metadata == {"path": str(path.resolve()), "format": "ascii", "bit_order": "as-written",
                        "file_bytes": len(source), "sha256_file": sha256(source).hexdigest()}


def test_packed_byte_reader_is_explicit_msb_first_with_leading_zeros(tmp_path):
    path = tmp_path / "sample.bin"
    source = b"\x00\x81\xff"
    path.write_bytes(source)
    bits, metadata = read_bits(path, "bytes")
    assert bits == "000000001000000111111111"
    assert metadata["bit_order"] == "msb-first"
    assert metadata["sha256_file"] == sha256(source).hexdigest()
    with pytest.raises(ValueError):
        read_bits(path, "ascii")
    path.write_bytes(b"01")
    assert read_bits(path, "ascii")[0] == "01"
    assert read_bits(path, "bytes")[0] == "0011000000110001"


@pytest.mark.parametrize("data", [b"", b" \n\t", b"010,1", b"0x01", b"\xef\xbb\xbf01", "０１".encode(), "01\u00a0".encode()])
def test_ascii_reader_does_not_silently_filter_invalid_observations(tmp_path, data):
    path = tmp_path / "invalid.txt"
    path.write_bytes(data)
    with pytest.raises(ValueError):
        read_bits(path)


def test_unknown_file_encoding_is_rejected(tmp_path):
    path = tmp_path / "bits.txt"
    path.write_text("01")
    with pytest.raises(ValueError):
        read_bits(path, "autodetect")


def test_splitting_requires_explicit_remainder_discard_and_preserves_sequence_order():
    bits = "00110111"
    assert split_sequences(bits, 4) == (["0011", "0111"], 0)
    with pytest.raises(ValueError, match="explicitly"):
        split_sequences(bits, 3)
    assert split_sequences(bits, 3, discard_remainder=True) == (["001", "101"], 2)
    with pytest.raises(ValueError, match="shorter"):
        split_sequences(bits, 9)


def _cli(*arguments, code=None):
    command = [sys.executable, str(REPOSITORY / "randomness_cli.py"), *arguments]
    if code is not None:
        command = [sys.executable, "-c", code]
    return subprocess.run(command, cwd=REPOSITORY, text=True, capture_output=True, timeout=30)


def test_cli_outputs_json_and_statistical_rejections_are_successful_execution():
    completed = _cli("--bits", "0" * 100, "--tests", "frequency", "runs", "--alpha", "0.05")
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["alpha"] == 0.05
    assert report["source"] == {"format": "literal-bits"}
    assert report["results"][0]["decisions"] == {"p": "reject"}
    assert report["results"][1]["status"] == "not_applicable"


def test_cli_can_save_strict_json_for_packed_file_input(tmp_path):
    path = tmp_path / "input.bin"
    output = tmp_path / "report.json"
    path.write_bytes(b"\xaa" * 13)
    completed = _cli(str(path), "--format", "bytes", "--tests", "frequency", "--output", str(output))
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""
    report = json.loads(output.read_text())
    assert report["input"]["n_bits"] == 104
    assert report["source"]["format"] == "bytes"
    assert report["source"]["sha256_file"] == sha256(path.read_bytes()).hexdigest()


def test_cli_explicit_batch_discard_is_recorded_and_channels_stay_separate():
    completed = _cli("--bits", BALANCED * 2 + "111", "--tests", "frequency", "runs",
                     "--sequence-length", "100", "--discard-remainder")
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["input_bits"] == 203
    assert report["discarded_trailing_bits"] == 3
    assert len(report["reports"]) == 2
    assert len(report["second_level"]["channels"]) == 2
    assert report["second_level"]["duplicate_sequences"] == 1


@pytest.mark.parametrize("arguments", [
    [], ["--bits", "01x"], ["--bits", ""],
    ["--bits", "01", "--alpha", "nan"],
    ["--bits", "01", "--format", "bytes"],
    ["--bits", "01", "--discard-remainder"],
    ["--bits", "010", "--sequence-length", "2"],
    ["--bits", "010", "--sequence-length", "0"],
    ["--bits", "01", "--tests", "frequency", "frequency"],
])
def test_cli_invalid_requests_exit_as_errors_without_json_results(arguments):
    completed = _cli(*arguments)
    assert completed.returncode == 2
    assert "error:" in completed.stderr
    assert completed.stdout == ""


def test_cli_computational_failure_emits_error_report_and_exit_one():
    code = (
        "import Suite,randomness_cli; "
        "Suite.FrequencyTest.monobit_test=lambda _: (float('nan'),False); "
        "raise SystemExit(randomness_cli.main(['--bits','01'*50,'--tests','frequency']))"
    )
    completed = _cli(code=code)
    assert completed.returncode == 1, completed.stderr
    report = json.loads(completed.stdout)
    assert report["results"][0]["status"] == "error"
    assert report["results"][0]["p_values"] == {}
