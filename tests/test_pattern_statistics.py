"""Primary NIST examples and independent finite-state/exhaustive checks.

SP 800-22r1a has numerical typos in several examples. These tests use its
specified formulas or published occurrence counts, not inconsistent p-values.
"""

from collections import Counter
from itertools import product
from math import exp, fsum, log
from pathlib import Path

import pytest
from scipy.special import gammaincc

from ApproximateEntropy import ApproximateEntropy
from Complexity import ComplexityTest
from Serial import Serial
from TemplateMatching import TemplateMatching, _overlapping_probabilities
from Validation import InsufficientDataError


def bit_strings(n):
    return (''.join(bits) for bits in product('01', repeat=n))


def circular_counts(bits, m):
    return Counter(''.join(bits[(start + offset) % len(bits)] for offset in range(m))
                   for start in range(len(bits)))


def brute_force_linear_complexity(bits):
    """Enumerate recurrences directly, without Berlekamp-Massey."""
    sequence = [int(bit) for bit in bits]
    for length in range(len(sequence) + 1):
        for coefficients in product((0, 1), repeat=length):
            if all(sequence[index] == sum(coefficients[delay - 1] * sequence[index - delay]
                                          for delay in range(1, length + 1)) % 2
                   for index in range(length, len(sequence))):
                return length
    raise AssertionError('Every finite string has an LFSR representation')


def exact_overlap_by_enumeration(m, size):
    frequencies = [0] * 6
    pattern = '1' * m
    for bits in bit_strings(size):
        matches = sum(bits[start:start + m] == pattern for start in range(size - m + 1))
        frequencies[min(matches, 5)] += 1
    return tuple(count / 2 ** size for count in frequencies)


def test_nonoverlap_nist_worked_example():
    # Section 2.7.4: W=(2,1), mean=1, variance=.46875.
    p, accepted = TemplateMatching.non_overlapping_test(
        '10100100101110010110', template_pattern='001', block=2)
    assert p == pytest.approx(exp(-16 / 15), abs=1e-14)
    assert accepted is True


@pytest.mark.parametrize('template', ['00', '11', '010', '00100', '01010'])
def test_nonoverlap_rejects_self_overlapping_templates(template):
    with pytest.raises(ValueError, match='unbordered'):
        TemplateMatching.non_overlapping_test('01' * 100, template_pattern=template)


def test_nonoverlap_confines_matches_to_blocks_and_discards_remainder():
    bits = '100' '100'
    p, _ = TemplateMatching.non_overlapping_test(bits, template_pattern='001', block=2)
    expected_statistic = 2 * (1 / 8) ** 2 / (3 * (1 / 8 - 5 / 64))
    assert p == pytest.approx(gammaincc(1, expected_statistic / 2))
    assert TemplateMatching.non_overlapping_test(bits + '1', template_pattern='001', block=2)[0] == p


@pytest.mark.parametrize('m', [1, 2, 3, 4])
def test_overlapping_probabilities_agree_with_exhaustive_fair_bits(m):
    assert _overlapping_probabilities(m, 8) == pytest.approx(exact_overlap_by_enumeration(m, 8), abs=1e-15)


def test_overlapping_default_masses_match_revised_nist_values():
    probabilities = _overlapping_probabilities(9, 1032)
    assert probabilities == pytest.approx(
        (0.364091, 0.185659, 0.139381, 0.100571, 0.0704323, 0.139865), abs=5e-7)
    assert sum(probabilities) == pytest.approx(1, abs=2e-14)
    # Demonstrate the corrected finite-block value differs from exp(-eta).
    assert abs(probabilities[0] - TemplateMatching.get_prob(0, 1)) > .003


def test_overlap_statistic_against_exact_enumeration():
    blocks = ['11111111', '00000000', '01011101', '11100111', '10101010']
    probabilities = exact_overlap_by_enumeration(2, 8)
    counts = [0] * 6
    for bits in blocks:
        counts[min(sum(bits[i:i + 2] == '11' for i in range(7)), 5)] += 1
    chi_square = sum((count - 5 * probability) ** 2 / (5 * probability)
                     for count, probability in zip(counts, probabilities))
    p, _ = TemplateMatching.overlapping_patterns(''.join(blocks), pattern_size=2, block_size=8)
    assert p == pytest.approx(gammaincc(2.5, chi_square / 2), abs=1e-14)
    assert TemplateMatching.overlapping_patterns(''.join(blocks) + '111', pattern_size=2, block_size=8)[0] == p


def test_legacy_compound_poisson_helper():
    assert TemplateMatching.get_prob(0, 1) == pytest.approx(exp(-1))
    assert TemplateMatching.get_prob(1, 1) == pytest.approx(exp(-1) / 2)
    assert TemplateMatching.get_prob(2, 1) == pytest.approx(3 * exp(-1) / 8)
    assert TemplateMatching.get_prob(4, 0) == 0
    assert TemplateMatching.get_prob(4, 10000) == 0


def test_serial_nist_worked_example():
    result = Serial.serial_test('0011011101', pattern_length=3)
    # Correct values also appear in section 2.11.6; section 2.11.4 has typos.
    assert result[0][0] == pytest.approx(0.8087921354109989, abs=1e-14)
    assert result[1][0] == pytest.approx(0.6703200460356394, abs=1e-14)


@pytest.mark.parametrize('m', [2, 3, 4])
def test_serial_exhaustive_independent_pattern_counts(m):
    for bits in bit_strings(6):
        psi = [(2 ** width / len(bits)) * sum(count * count for count in circular_counts(bits, width).values())
               - len(bits) for width in (m, m - 1, m - 2)]
        expected = (gammaincc(2 ** (m - 2), (psi[0] - psi[1]) / 2),
                    gammaincc(2 ** (m - 3), (psi[0] - 2 * psi[1] + psi[2]) / 2))
        result = Serial.serial_test(bits, pattern_length=m)
        assert (result[0][0], result[1][0]) == pytest.approx(expected, abs=1e-13)


def test_approximate_entropy_nist_worked_example():
    p, _ = ApproximateEntropy.approximate_entropy_test('0100110101', pattern_length=3)
    assert p == pytest.approx(0.2619611048816655, abs=1e-14)


@pytest.mark.parametrize('m', [1, 2, 3])
def test_approximate_entropy_against_independent_phi_definition(m):
    for bits in bit_strings(6):
        phi = [fsum((count / len(bits)) * log(count / len(bits))
                    for count in circular_counts(bits, width).values()) for width in (m, m + 1)]
        statistic = max(0, 2 * len(bits) * (log(2) - phi[0] + phi[1]))
        p, _ = ApproximateEntropy.approximate_entropy_test(bits, pattern_length=m)
        assert p == pytest.approx(gammaincc(2 ** (m - 1), statistic / 2), abs=1e-13)


def test_berlekamp_massey_nist_and_extreme_examples():
    assert ComplexityTest.berlekamp_massey_algorithm('1101011110001') == 4
    assert ComplexityTest.berlekamp_massey_algorithm('0' * 500) == 0
    assert ComplexityTest.berlekamp_massey_algorithm('1' * 500) == 1
    assert ComplexityTest.berlekamp_massey_algorithm('0' * 499 + '1') == 500


def test_berlekamp_massey_exhaustively_against_enumerated_recurrences():
    for size in range(1, 8):
        for bits in bit_strings(size):
            assert ComplexityTest.berlekamp_massey_algorithm(bits) == brute_force_linear_complexity(bits)


def test_linear_complexity_e_published_counts_with_correct_probabilities():
    bits = ''.join((Path(__file__).parents[1] / 'data' / 'data.e').read_text().split())[:1000000]
    # The observed counts are NIST 2.10.8's; its printed p-value reflects an
    # erroneous .01047 rather than pi_0=1/96. The exact limiting masses sum to 1.
    counts = (11, 31, 116, 501, 258, 57, 26)
    probabilities = (1 / 96, 1 / 32, 1 / 8, 1 / 2, 1 / 4, 1 / 16, 1 / 48)
    statistic = fsum((count - 1000 * probability) ** 2 / (1000 * probability)
                     for count, probability in zip(counts, probabilities))
    assert statistic == pytest.approx(2.706)
    p, _ = ComplexityTest.linear_complexity_test(bits, block_size=1000)
    assert p == pytest.approx(gammaincc(3, statistic / 2), abs=1e-13)


def test_overlapping_e_published_counts_with_correct_probabilities():
    bits = ''.join((Path(__file__).parents[1] / 'data' / 'data.e').read_text().split())[:1000000]
    # SP800-22 2.8.8 reports these counts but a stale approximate p-value.
    counts = (329, 164, 150, 111, 78, 136)
    probabilities = _overlapping_probabilities(9, 1032)
    statistic = fsum((count - 968 * probability) ** 2 / (968 * probability)
                     for count, probability in zip(counts, probabilities))
    p, _ = TemplateMatching.overlapping_patterns(bits)
    assert p == pytest.approx(gammaincc(2.5, statistic / 2), abs=1e-13)
    assert p == pytest.approx(.1590372537344, abs=1e-12)


@pytest.mark.parametrize('function', [Serial.serial_test, ApproximateEntropy.approximate_entropy_test,
                                    ComplexityTest.linear_complexity_test,
                                    TemplateMatching.non_overlapping_test,
                                    TemplateMatching.overlapping_patterns])
def test_pattern_functions_reject_invalid_input(function):
    with pytest.raises(TypeError):
        function([0, 1])
    with pytest.raises(ValueError):
        function('01 01')
    with pytest.raises(InsufficientDataError):
        function('')


@pytest.mark.parametrize('bad', [True, 0, -1, 1.5])
def test_pattern_functions_reject_invalid_parameters(bad):
    with pytest.raises(ValueError):
        Serial.serial_test('01' * 100, pattern_length=bad)
    with pytest.raises(ValueError):
        ApproximateEntropy.approximate_entropy_test('01' * 100, pattern_length=bad)
    with pytest.raises(ValueError):
        ComplexityTest.linear_complexity_test('01' * 100, block_size=bad)
    with pytest.raises(ValueError):
        TemplateMatching.non_overlapping_test('01' * 100, block=bad)
    with pytest.raises(ValueError):
        TemplateMatching.overlapping_patterns('01' * 100, pattern_size=bad)


def test_missing_complete_blocks_and_windows_are_explicit():
    with pytest.raises(InsufficientDataError):
        ComplexityTest.linear_complexity_test('01', block_size=500)
    with pytest.raises(InsufficientDataError):
        TemplateMatching.overlapping_patterns('01')
    with pytest.raises(InsufficientDataError):
        TemplateMatching.non_overlapping_test('01')
    with pytest.raises(InsufficientDataError):
        Serial.serial_test('01', pattern_length=3)
    with pytest.raises(InsufficientDataError):
        ApproximateEntropy.approximate_entropy_test('01', pattern_length=2)
    with pytest.raises(ValueError, match='five overlapping'):
        TemplateMatching.overlapping_patterns('01' * 100, pattern_size=9, block_size=10)
    with pytest.raises(ValueError):
        Serial.serial_test('01' * 100, pattern_length=1)
