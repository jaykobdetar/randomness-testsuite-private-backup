"""Known answers and independent finite-space checks for NIST core statistics.

Published vectors: NIST SP 800-22 Rev. 1a sections 2.1--2.6,
https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-22r1a.pdf
Small vectors check arithmetic, not calibration of asymptotic p-values.
"""

import cmath
import itertools
import math
from pathlib import Path

import numpy as np
import pytest

from BinaryMatrix import BinaryMatrix
from FrequencyTest import FrequencyTest
from Matrix import Matrix, _rank_probabilities
from RunTest import RunTest, _longest_run_probabilities
from Spectral import SpectralTest
from Validation import InsufficientDataError


NIST_100 = (
    "11001001000011111101101010100010001000010110100011"
    "00001000110100110001001100011001100010100010111000"
)
NIST_LONGEST = (
    "11001100000101010110110001001100111000000000001001"
    "00110101010001000100111101011010000000110101111100"
    "1100111001101101100010110010"
)


def test_published_monobit_and_block_frequency_examples():
    assert len(NIST_100) == 100
    assert FrequencyTest.monobit_test(NIST_100)[0] == pytest.approx(0.109599, abs=5e-7)
    assert FrequencyTest.block_frequency(NIST_100, 10)[0] == pytest.approx(0.706438, abs=5e-7)
    assert FrequencyTest.block_frequency("0110011010", 3)[0] == pytest.approx(0.801252, abs=5e-7)


def test_block_frequency_uses_requested_blocks_and_discards_only_remainder():
    assert FrequencyTest.block_frequency("11110000", 4) == FrequencyTest.block_frequency("11110000111", 4)
    assert FrequencyTest.block_frequency("11110000", 8)[0] == 1.0
    assert FrequencyTest.block_frequency("11110000", 4)[0] == pytest.approx(math.exp(-4))
    # N=1 equals monobit on the used block, not the entire input including remainder.
    assert FrequencyTest.block_frequency("111100101", 8)[0] == pytest.approx(
        FrequencyTest.monobit_test("11110010")[0]
    )
    with pytest.raises(InsufficientDataError):
        FrequencyTest.block_frequency("01", 128)


def test_published_runs_example_and_frequency_prerequisite():
    assert RunTest.run_test("1001101011")[0] == pytest.approx(0.147232, abs=5e-7)
    for bits in ("0", "1", "0" * 15, "1" * 100, "1" * 80 + "0" * 20):
        assert RunTest.run_test(bits) == (0.0, False)


def test_runs_detects_excessively_fast_and_slow_oscillations():
    assert RunTest.run_test("01" * 500)[0] < 1e-100
    assert RunTest.run_test("0" * 500 + "1" * 500)[0] < 1e-100


def test_published_longest_run_example():
    assert len(NIST_LONGEST) == 128
    # This is the full-precision result in section 2.4.8; section 2.4.4
    # obtains 0.180598 from rounded four-decimal category probabilities.
    assert RunTest.longest_one_block_test(NIST_LONGEST)[0] == pytest.approx(0.180609, abs=5e-7)
    assert RunTest.longest_one_block_test(NIST_LONGEST) == RunTest.longest_one_block_test(NIST_LONGEST + "1111111")


def test_longest_run_probabilities_agree_with_exhaustive_eight_bit_space():
    frequencies = [0] * 4
    blocks = [format(value, "08b") for value in range(256)]
    for block in blocks:
        longest = max(map(len, block.split("0")))
        category = 0 if longest <= 1 else 1 if longest == 2 else 2 if longest == 3 else 3
        frequencies[category] += 1
    assert frequencies == [55, 94, 59, 48]
    assert _longest_run_probabilities(8, 1, 4) == tuple(count / 256 for count in frequencies)
    # A complete sample space has precisely the expected bin counts.
    assert RunTest.longest_one_block_test("".join(blocks)) == (1.0, True)


def test_exact_longest_probabilities_match_nist_128_bit_table():
    rounded = [0.1174, 0.2430, 0.2493, 0.1752, 0.1027, 0.1124]
    probabilities = _longest_run_probabilities(128, 4, 9)
    assert sum(probabilities) == pytest.approx(1.0, abs=2e-16)
    # NIST's rounded table is itself approximate, notably the M=128 run=6 cell.
    assert probabilities == pytest.approx(rounded, abs=7e-5)


@pytest.mark.parametrize("size,lower,upper", [(128, 4, 9), (10000, 10, 16)])
def test_exact_longest_probabilities_match_independent_run_state_automaton(size, lower, upper):
    # Independently propagate the probability of each current suffix of ones.
    # Paths reaching a forbidden run are dropped. Unlike the production integer
    # recurrence, this oracle tracks each of the finite-state machine's states.
    cumulative = []
    for limit in range(lower, upper):
        states = [1.0] + [0.0] * limit
        for _ in range(size):
            states = [sum(states) / 2] + [value / 2 for value in states[:-1]]
        cumulative.append(sum(states))
    expected = [cumulative[0]]
    expected.extend(right - left for left, right in zip(cumulative, cumulative[1:]))
    expected.append(1 - cumulative[-1])
    assert _longest_run_probabilities(size, lower, upper) == pytest.approx(expected, abs=2e-14)


def _span_rank(rows):
    """Independent GF(2) oracle: enumerate the entire row span, no elimination."""
    span = {0}
    for row in rows:
        row_mask = int("".join(map(str, row)), 2)
        span |= {value ^ row_mask for value in tuple(span)}
    return len(span).bit_length() - 1


@pytest.mark.parametrize("rows,columns", [(1, 4), (4, 1), (2, 3), (3, 2), (3, 3)])
def test_gf2_rank_exhaustively_matches_row_span(rows, columns):
    for bits in itertools.product((0, 1), repeat=rows * columns):
        array = np.array(bits, dtype=np.uint8).reshape(rows, columns)
        ranker = BinaryMatrix(array, rows, columns)
        expected = _span_rank(array.tolist())
        assert ranker.compute_rank() == expected
        assert ranker.compute_rank() == expected
        np.testing.assert_array_equal(array.ravel(), bits)


def test_rank_is_binary_not_real_and_handles_skipped_pivot_columns():
    array = np.array([[1, 1, 0], [1, 0, 1], [0, 1, 1]])
    assert np.linalg.matrix_rank(array) == 3
    assert BinaryMatrix(array, 3, 3).determine_rank() == 2
    assert BinaryMatrix([[0, 1, 0], [0, 0, 1]], 2, 3).compute_rank() == 2
    assert BinaryMatrix(np.zeros((4, 2)), 4, 2).compute_rank() == 0


@pytest.mark.parametrize("rows,columns,expected", [
    (2, 2, (6 / 16, 9 / 16, 1 / 16)),
    (2, 3, (42 / 64, 21 / 64, 1 / 64)),
    (3, 2, (42 / 64, 21 / 64, 1 / 64)),
])
def test_rank_null_probabilities_and_exact_complete_sample_spaces(rows, columns, expected):
    assert _rank_probabilities(rows, columns) == pytest.approx(expected, abs=1e-16)
    block_size = rows * columns
    bits = "".join(format(value, f"0{block_size}b") for value in range(1 << block_size))
    p_value, decision = Matrix.binary_matrix_rank_text(
        bits, rows_in_matrix=rows, columns_in_matrix=columns
    )
    assert p_value == pytest.approx(1.0, abs=1e-15)
    assert decision is True


def test_rectangular_rank_tail_does_not_disappear_by_subtraction():
    assert _rank_probabilities(2, 64)[2] == 2.0 ** -128


def test_numpy_integral_parameters_satisfy_the_shared_integer_contract():
    bits = "01100110"
    assert Matrix.binary_matrix_rank_text(bits, rows_in_matrix=np.int64(2), columns_in_matrix=np.int64(2)) == (
        Matrix.binary_matrix_rank_text(bits, rows_in_matrix=2, columns_in_matrix=2)
    )
    assert FrequencyTest.block_frequency(bits, np.int64(2)) == FrequencyTest.block_frequency(bits, 2)


def test_rank_on_published_e_prefix():
    bits = "".join((Path(__file__).parents[1] / "data" / "data.e").read_text().split())[:100000]
    # Section 2.5.8: 97 matrices, rank categories (23, 60, 14).
    assert Matrix.binary_matrix_rank_text(bits)[0] == pytest.approx(0.532069, abs=5e-7)


def test_hundred_bit_spectral_example_uses_actual_peak_count():
    # Section 2.6.8 prints N1=46, but its input has 48 of the first 50 peaks
    # below sqrt(100*log(20)). The direct DFT oracle below also verifies this.
    assert SpectralTest.spectral_test(NIST_100)[0] == pytest.approx(0.6463551955394902, abs=1e-15)


def test_ten_bit_spectral_example_uses_computed_peaks_not_paper_typo():
    # In section 2.6.4 the printed N1=4 is inconsistent with its own input.
    # The first five magnitudes are 0, 2, sqrt(20), 2, sqrt(20), all below
    # sqrt(10*log(20)). Consequently N1=5 and p=.468160, not .029523.
    assert SpectralTest.spectral_test("1001010011")[0] == pytest.approx(0.468159909854428, abs=1e-15)


@pytest.mark.parametrize("bits", ["01", "101", "0000", "010101", "110100110", "110001101011", "1001010011", NIST_100])
def test_spectral_matches_direct_complex_dft(bits):
    # Direct O(n^2) transform independently checks FFT signs, DC, odd n and bin selection.
    samples = [2 * int(bit) - 1 for bit in bits]
    n = len(samples)
    magnitudes = [abs(sum(samples[j] * cmath.exp(-2j * math.pi * k * j / n)
                          for j in range(n))) for k in range(n // 2)]
    count = sum(value < math.sqrt(n * math.log(20)) for value in magnitudes)
    d = (count - 0.95 * n / 2) / math.sqrt(n * 0.95 * 0.05 / 4)
    expected = math.erfc(abs(d) / math.sqrt(2))
    assert SpectralTest.spectral_test(bits)[0] == pytest.approx(expected, abs=1e-15)


def test_spectral_detects_alternation_and_is_invariant_to_bit_complement():
    assert SpectralTest.spectral_test("01" * 500)[0] < 1e-10
    assert SpectralTest.spectral_test(NIST_100) == SpectralTest.spectral_test(
        NIST_100.translate(str.maketrans("01", "10"))
    )


@pytest.mark.parametrize("function", [
    FrequencyTest.monobit_test, FrequencyTest.block_frequency,
    RunTest.run_test, RunTest.longest_one_block_test,
    Matrix.binary_matrix_rank_text, SpectralTest.spectral_test,
])
@pytest.mark.parametrize("invalid", ["", "010 1", "01x", "０１", "01\n", 101, [0, 1], None])
def test_invalid_observations_are_rejected(function, invalid):
    with pytest.raises((ValueError, TypeError)):
        function(invalid)


@pytest.mark.parametrize("size", [0, -1, True, 2.5, "8"])
def test_block_size_must_be_a_positive_integer(size):
    with pytest.raises(ValueError):
        FrequencyTest.block_frequency("01" * 100, size)


@pytest.mark.parametrize("rows,columns", [(1, 32), (32, 1), (0, 2), (2.5, 2), (True, 2)])
def test_rank_dimensions_require_three_nonempty_categories(rows, columns):
    with pytest.raises(ValueError):
        Matrix.binary_matrix_rank_text("01" * 100, rows_in_matrix=rows, columns_in_matrix=columns)


def test_insufficient_data_and_invalid_matrices_are_explicit():
    with pytest.raises(InsufficientDataError):
        Matrix.binary_matrix_rank_text("01")
    with pytest.raises(InsufficientDataError):
        SpectralTest.spectral_test("0")
    with pytest.raises(InsufficientDataError):
        RunTest.longest_one_block_test("01" * 63)
    with pytest.raises(ValueError):
        BinaryMatrix([[0, 1]], 2, 2)
    with pytest.raises(ValueError):
        BinaryMatrix([[0, 2]], 1, 2)
    with pytest.raises(ValueError):
        BinaryMatrix([[0, float("nan")]], 1, 2)


def test_alpha_boundary_is_nonrejection_in_both_runs_tests(monkeypatch):
    monkeypatch.setattr("RunTest.erfc", lambda _: 0.01)
    monkeypatch.setattr("RunTest.gammaincc", lambda *_: 0.01)
    assert RunTest.run_test("01" * 50) == (0.01, True)
    assert RunTest.longest_one_block_test(NIST_LONGEST) == (0.01, True)
