"""Small synthetic regressions; no reference experiments or display required."""
from copy import deepcopy
from hashlib import sha256
from math import comb, erfc, sqrt
from types import SimpleNamespace

import pytest

import Suite
from BitInput import read_bits
from tools.check_seeded_templates import compare_p_values


def report_for(n=1000000, test_id="frequency", parameters=None):
    # Reuse a real small report's structure without doing million-bit work.
    report = Suite.run_suite("01" * 50, tests=["frequency"])
    report["input"]["n_bits"] = n
    row = report["results"][0]
    row.update(n_bits=n, test_id=test_id, parameters=parameters or {},
               p_values={"p": .5}, decisions={"p": "not_rejected"})
    return report


def batch(report, count=55):
    reports = [deepcopy(report) for _ in range(count)]
    for i, item in enumerate(reports):
        item["input"]["sha256_ascii_bits"] = sha256(str(i).encode()).hexdigest()
    return reports


def assert_descriptive_only(channel):
    assert channel["inference_supported"] is False
    for key in ("nist_three_sigma_interval", "proportion_in_interval",
                "excess_rejections_binomial_p", "uniformity_p", "uniformity_not_rejected"):
        assert channel[key] is None
    assert channel["inference_reason"] and channel["uniformity_reason"]
    assert sum(channel["uniformity_histogram"]) == channel["sequences"]


def test_raw_p_values_default_to_descriptive_counts():
    result = Suite.summarize_p_values([.5] * 55)
    assert_descriptive_only(result)
    assert result["non_rejections"] == 55 and result["proportion"] == 1
    with pytest.raises(TypeError):
        Suite.summarize_p_values([.5], assume_calibrated="yes")


def test_exact_short_monobit_null_has_empty_uniformity_bin():
    # Exhaust the 101 possible counts, with their exact binomial masses.
    cells = [0.] * 10
    for ones in range(101):
        p = erfc(abs(2 * ones - 100) / sqrt(200))
        cells[min(int(10 * p), 9)] += comb(100, ones) / 2**100
    assert sum(cells) == pytest.approx(1)
    assert cells[7] == 0  # uniform ten-bin calibration is wrong at n=100
    assert_descriptive_only(Suite.summarize_reports(batch(report_for(100)))["channels"][0])


@pytest.mark.parametrize("change", [
    {"n": 999999}, {"n": 1000001}, {"alpha": .05},
    {"profile": "other"}, {"suite_version": "2.0.1.dev0"}, {"schema_version": 2},
    {"parameters": {"unexpected": 1}},
])
def test_unsupported_homogeneous_batches_keep_counts_without_inference(change):
    report = report_for(n=change.get("n", 1000000), parameters=change.get("parameters"))
    for key in ("alpha", "profile", "suite_version", "schema_version"):
        if key in change:
            report[key] = change[key]
    report["results"][0]["alpha"] = report["alpha"]
    assert_descriptive_only(Suite.summarize_reports(batch(report))["channels"][0])


def test_supported_batch_and_55_sequence_boundary():
    below = Suite.summarize_reports(batch(report_for(), 54))["channels"][0]
    assert below["inference_supported"] is True
    assert below["uniformity_p"] is None and "55" in below["uniformity_reason"]
    result = Suite.summarize_reports(batch(report_for()))["channels"][0]
    assert result["inference_supported"] is True
    assert result["uniformity_p"] is not None
    assert result["inference_reason"] == ""


def test_duplicate_inputs_disable_inference_without_removing_observations():
    report = report_for()
    result = Suite.summarize_reports([report] * 55)
    assert result["duplicate_sequences"] == 54
    assert_descriptive_only(result["channels"][0])
    assert result["channels"][0]["sequences"] == 55


@pytest.mark.parametrize("test_id", ["runs", "random_excursions", "random_excursions_variant"])
def test_data_conditioned_channels_are_descriptive(test_id):
    report = report_for(test_id=test_id)
    if test_id.startswith("random_excursions"):
        states = (Suite.RandomExcursions.STATES if test_id == "random_excursions"
                  else Suite.RandomExcursions.VARIANT_STATES)
        row = report["results"][0]
        row["p_values"] = {f"{x:+d}": .5 for x in states}
        row["decisions"] = {key: "not_rejected" for key in row["p_values"]}
    for channel in Suite.summarize_reports(batch(report))["channels"]:
        assert_descriptive_only(channel)
        assert "selection" in channel["inference_reason"]


def test_duplicate_result_rows_fail_even_in_one_report():
    report = report_for()
    report["results"].append(deepcopy(report["results"][0]))
    with pytest.raises(ValueError, match="unique"):
        Suite.summarize_reports([report])


@pytest.mark.parametrize("field,value", [
    ("status", "unknown"), ("parameters", []), ("n_bits", 99), ("alpha", .05),
    ("p_values", {"p": float("nan")}), ("p_values", {"p": True}),
    ("p_values", {"p": 1.1}), ("p_values", {}), ("p_values", {"wrong": .5}),
    ("decisions", {}), ("decisions", {"p": "reject"}),
])
def test_malformed_result_rows_fail_before_aggregation(field, value):
    report = report_for()
    report["results"][0][field] = value
    with pytest.raises(ValueError):
        Suite.summarize_reports([report])


def test_unevaluated_results_cannot_smuggle_p_values():
    report = report_for()
    report["results"][0]["status"] = "not_applicable"
    with pytest.raises(ValueError, match="no p-values"):
        Suite.summarize_reports([report])


@pytest.mark.parametrize("report", [None, {}, {"alpha": .01, "input": {}}, []])
def test_invalid_report_containers_raise_value_error(report):
    with pytest.raises(ValueError):
        Suite.summarize_reports([report])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), -.01, 1.01])
@pytest.mark.parametrize("side", ["actual", "expected"])
def test_reference_comparison_rejects_invalid_values_before_tolerance(bad, side):
    args = {"actual": [.5, .6], "expected": [.5, .6]}
    args[side][1] = bad
    with pytest.raises(ValueError, match="nonfinite or out-of-range"):
        compare_p_values(**args)


def test_reference_comparison_validates_lengths_and_tolerance():
    assert compare_p_values([0, 1, .5], [0, 1, .5000004]) == []
    assert compare_p_values([0, 1, .5], [0, 1, .500002]) == [2]
    for actual, expected in (([], []), ([.5], [.5, .6])):
        with pytest.raises(ValueError):
            compare_p_values(actual, expected)


@pytest.mark.parametrize("alias", ["same", "symlink", "hardlink"])
def test_gui_does_not_overwrite_input_snapshot(tmp_path, monkeypatch, alias):
    pytest.importorskip("tkinter")
    import Main
    source = tmp_path / "bits.txt"
    source.write_text("01" * 50)
    bits, metadata = read_bits(source)
    report = Suite.run_suite(bits, tests=["frequency"])
    report["source"] = metadata
    output = source if alias == "same" else tmp_path / "report.json"
    if alias == "symlink":
        output.symlink_to(source)
    elif alias == "hardlink":
        output.hardlink_to(source)
    errors = []
    monkeypatch.setattr(Main.filedialog, "asksaveasfilename", lambda **kw: str(output))
    monkeypatch.setattr(Main.messagebox, "showerror", lambda *args: errors.append(args))
    # Exercise the real save method without starting Tk; protect the stored
    # report's source even when current input controls have changed.
    widget = SimpleNamespace(report=report, status=SimpleNamespace(set=lambda _: None))
    Main.Main.save_result_to_file(widget)
    assert source.read_text() == bits
    assert errors and "must not overwrite" in errors[0][1]
    output = tmp_path / "distinct-report.json"
    monkeypatch.setattr(Main.filedialog, "asksaveasfilename", lambda **kw: str(output))
    Main.Main.save_result_to_file(widget)
    import json
    assert json.loads(output.read_text()) == report


@pytest.mark.parametrize("field", ["cycles", "minimum_cycles"])
def test_nonexcursion_metadata_cannot_bypass_signature_in_either_order(field):
    reports = batch(report_for(), 2)
    reports[1]["results"][0]["parameters"][field] = 123
    for ordered in (reports, reports[::-1]):
        with pytest.raises(ValueError, match="parameters"):
            Suite.summarize_reports(ordered)


@pytest.mark.parametrize("status", ["error", "not_applicable"])
def test_excluded_observations_disable_inference_independently_of_order(status):
    reports = batch(report_for(), 56)
    row = reports[-1]["results"][0]
    row.update(status=status, p_values={}, decisions={}, reason="synthetic exclusion")
    forward = Suite.summarize_reports(reports)
    backward = Suite.summarize_reports(reports[::-1])
    assert forward == backward
    channel = forward["channels"][0]
    assert_descriptive_only(channel)
    assert channel["sequences"] == 55 and channel["excluded_sequences"] == 1
    assert "excluded observations" in channel["inference_reason"]


def test_exclusion_does_not_disable_unaffected_test_channels():
    reports = batch(report_for(), 55)
    for report in reports:
        other = deepcopy(report["results"][0])
        other.update(test_id="spectral")
        report["results"].append(other)
    reports[0]["results"][1].update(status="error", p_values={}, decisions={})
    channels = {row["test_id"]: row for row in Suite.summarize_reports(reports)["channels"]}
    assert channels["frequency"]["inference_supported"] is True
    assert_descriptive_only(channels["spectral"])


@pytest.mark.parametrize("tolerance", [float("nan"), float("inf"), -float("inf"), -.01, True, None, "0.1"])
def test_reference_comparison_rejects_invalid_tolerance(tolerance):
    with pytest.raises(ValueError, match="tolerance"):
        compare_p_values([.1], [.9], tolerance=tolerance)


def test_reference_comparison_accepts_zero_and_finite_tolerances():
    assert compare_p_values([.1], [.1], tolerance=0) == []
    assert compare_p_values([.1], [.9], tolerance=0) == [0]
    assert compare_p_values([.1], [.9], tolerance=1.0) == []
