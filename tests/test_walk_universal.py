"""Known answers and independent references for NIST SP 800-22 Rev. 1a.

Source: https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-22r1a.pdf
Fixtures are deterministic mathematical constants, not physical entropy sources.
"""

from collections import Counter
from hashlib import shake_256
from itertools import accumulate
from math import erf, erfc, floor, fsum, log2, sqrt
from pathlib import Path

import pytest
from scipy.special import gammaincc

from CumulativeSum import CumulativeSums
from RandomExcursions import RandomExcursions
from Universal import Universal
from Validation import InsufficientDataError


NIST_100 = (
    "11001001000011111101101010100010001000010110100011"
    "00001000110100110001001100011001100010100010111000"
)


@pytest.fixture(scope="module")
def e_bits():
    text = (Path(__file__).resolve().parents[1] / "data" / "data.e").read_text()
    return "".join(text.split())[:1000000]


@pytest.mark.parametrize("mode,expected", [(0, .219194), (1, .114866)])
def test_cusum_published_100_bit_example(mode, expected):
    assert len(NIST_100) == 100
    assert CumulativeSums.cumulative_sums_test(NIST_100, mode)[0] == pytest.approx(expected, abs=5e-7)


def test_cusum_ten_bit_floor_bound_example():
    # Section 2.13's printed .4116588 uses truncation toward zero in the
    # reference C implementation. Mathematical floor bounds give this result.
    assert CumulativeSums.cumulative_sums_test("1011010111")[0] == pytest.approx(.411584718252598)


def _reference_cusum(bits):
    n = len(bits)
    z = max(abs(x) for x in accumulate(1 if bit == "1" else -1 for bit in bits))
    phi = lambda x: (1 + erf(x / sqrt(2))) / 2
    a = sum(phi((4*k+1)*z/sqrt(n)) - phi((4*k-1)*z/sqrt(n))
            for k in range(floor((-n/z+1)/4), floor((n/z-1)/4)+1))
    b = sum(phi((4*k+3)*z/sqrt(n)) - phi((4*k+1)*z/sqrt(n))
            for k in range(floor((-n/z-3)/4), floor((n/z-1)/4)+1))
    return 1 - a + b


@pytest.mark.parametrize("mode", [0, 1])
@pytest.mark.parametrize("bits", [NIST_100, "01"*51, "11100"*37, "000011"*28])
def test_cusum_independent_formula_and_reversal(bits, mode):
    assert CumulativeSums.cumulative_sums_test(bits, mode)[0] == pytest.approx(
        _reference_cusum(bits if mode == 0 else bits[::-1]), abs=2e-15
    )


def test_cusum_preserves_small_tail_probability():
    actual, passed = CumulativeSums.cumulative_sums_test("1"*100)
    assert actual == pytest.approx(2*erfc(10/sqrt(2)), rel=1e-13, abs=0)
    assert actual > 0
    assert not passed


@pytest.mark.parametrize("mode", [-1, 2, .5, True, "0"])
def test_cusum_rejects_invalid_mode(mode):
    with pytest.raises(ValueError):
        CumulativeSums.cumulative_sums_test(NIST_100, mode)


def test_nist_e_appendix_b(e_bits):
    # Allow the last printed digit to differ from the older normal-CDF routine.
    assert CumulativeSums.cumulative_sums_test(e_bits, 0)[0] == pytest.approx(.669887, abs=1e-6)
    assert CumulativeSums.cumulative_sums_test(e_bits, 1)[0] == pytest.approx(.724266, abs=1e-6)
    assert Universal.statistical_test(e_bits)[0] == pytest.approx(.282568, abs=5e-7)
    rows = RandomExcursions.random_excursions_test(e_bits)
    assert RandomExcursions.cycle_count(e_bits) == 1490
    # Appendix B's +1 value corrects the section 2.14.8 table, whose positive
    # states omit the final incomplete cycle's visits while still counting it.
    assert rows[4][3] == pytest.approx(.786868, abs=5e-7)
    for row, expected in zip(rows[:4], [.573306, .197996, .164011, .007779]):
        assert row[3] == pytest.approx(expected, abs=5e-7)


def test_excursion_variant_full_published_e_vector(e_bits):
    expected_counts = [1450,1435,1380,1366,1412,1475,1480,1468,1502,
                       1409,1369,1396,1479,1599,1628,1619,1620,1610]
    expected_p = [.858946,.794755,.576249,.493417,.633873,.917283,.934708,.816012,.826009,
                  .137861,.200642,.441254,.939291,.505683,.445935,.512207,.538635,.593930]
    rows = RandomExcursions.variant_test(e_bits)
    assert len(rows) == 18
    assert [row[2] for row in rows] == expected_counts
    assert [row[3] for row in rows] == pytest.approx(expected_p, abs=5e-7)


def _reference_cycles(bits):
    cycles, counts, position = [], Counter(), 0
    for bit in bits:
        position += 1 if bit == "1" else -1
        if position:
            counts[position] += 1
        else:
            cycles.append(counts)
            counts = Counter()
    if position:
        cycles.append(counts)
    return cycles


@pytest.mark.parametrize("tail", ["", "111101"])
def test_excursions_independent_streaming_reference(tail):
    # Each piece returns to zero; exercise visit categories 0 through >=5
    # and optionally one final unclosed excursion.
    cycles_with_revisits = "".join("1" + "10"*k + "0" for k in (2, 3, 6))
    bits = ("01" + "10" + "0011" + "1100" + "111000" + cycles_with_revisits)*100 + tail
    cycles = _reference_cycles(bits)
    assert RandomExcursions.cycle_count(bits) == len(cycles)
    for label, state, statistic, p_value, passed in RandomExcursions.random_excursions_test(bits):
        p = 1/(2*abs(state))
        probabilities = [1-p] + [p*p*(1-p)**(k-1) for k in range(1,5)] + [p*(1-p)**4]
        observations = Counter(min(cycle[state], 5) for cycle in cycles)
        expected = [len(cycles)*p for p in probabilities]
        chi = sum((observations[k]-value)**2/value for k, value in enumerate(expected))
        assert statistic == pytest.approx(chi)
        assert p_value == pytest.approx(gammaincc(2.5, chi/2))
        assert passed == (p_value >= .01)


def test_cycle_endpoint_and_absent_variant_states():
    bits = "01"*500
    assert RandomExcursions.cycle_count(bits) == 500  # no fictitious empty cycle
    assert RandomExcursions.cycle_count(bits+"1") == 501
    rows = RandomExcursions.variant_test(bits)
    assert [row[1] for row in rows] == list(range(-9, 0)) + list(range(1,10))
    assert rows[8][2:5] == (500, 1.0, True)
    assert rows[9][2] == 0
    assert rows[9][3] == pytest.approx(erfc(sqrt(500)/2))


@pytest.mark.parametrize("function", [RandomExcursions.random_excursions_test, RandomExcursions.variant_test])
@pytest.mark.parametrize("bits", ["01"*499, "1"*1000000])
def test_excursions_require_sufficient_cycles(function, bits):
    with pytest.raises(InsufficientDataError, match="observed J="):
        function(bits)


def test_excursion_cycle_requirement_scales_with_n():
    with pytest.raises(InsufficientDataError, match="1000 cycles"):
        RandomExcursions._require_cycles(40_000_000_000, 999)
    RandomExcursions._require_cycles(40_000_000_000, 1000)


@pytest.mark.parametrize("n,size", [(387840,6),(904960,7),(2068480,8),
                                  (496435200,15),(1059061759,15),(1059061760,16)])
def test_universal_block_size_thresholds_including_sixteen(n, size):
    assert Universal._pattern_size(n) == size


def test_universal_rejects_insufficient_sample():
    with pytest.raises(InsufficientDataError, match="387840"):
        Universal.statistical_test("0"*387839)


def test_universal_matches_independent_dictionary_reference_and_discards_tail():
    n = 387840
    bits = "".join(f"{value:08b}" for value in shake_256(b"NIST reference fixture").digest(n//8))
    blocks = [bits[i:i+6] for i in range(0,n,6)]
    history = {block: i for i, block in enumerate(blocks[:640],1)}
    distances = []
    for i, block in enumerate(blocks[640:],641):
        distances.append(i - history.get(block,0))
        history[block] = i
    k = len(distances)
    statistic = fsum(log2(d) for d in distances)/k
    sigma = (0.7 - 0.8/6 + (4+32/6)*k**(-.5)/15)*sqrt(2.954/k)
    expected = erfc(abs(statistic-5.2177052)/(sqrt(2)*sigma))
    result = Universal.statistical_test(bits)
    assert result[0] == pytest.approx(expected, rel=1e-12, abs=1e-15)
    assert Universal.statistical_test(bits+"10101") == result


@pytest.mark.parametrize("function", [
    CumulativeSums.cumulative_sums_test, RandomExcursions.random_excursions_test,
    RandomExcursions.variant_test, RandomExcursions.cycle_count, Universal.statistical_test,
])
@pytest.mark.parametrize("bits,error", [("", InsufficientDataError),("012",ValueError),
                                       ("01\n",ValueError),("０１",ValueError),(b"01",TypeError)])
def test_bit_input_contract(function, bits, error):
    with pytest.raises(error):
        function(bits)
