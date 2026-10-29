"""Circular pattern-frequency test from NIST SP 800-22r1a, section 2.11."""

from collections import Counter
from math import ldexp

from scipy.special import gammaincc

from Validation import InsufficientDataError, positive_int, validate_bits


def _circular_pattern_counts(binary_data, width):
    """Count all n circular windows without allocating an array of size 2**m."""
    if width == 0:
        return Counter({0: len(binary_data)})
    mask = (1 << width) - 1
    window = int(binary_data[:width], 2)
    counts = Counter({window: 1})
    extended = binary_data + binary_data[:width - 1]
    for bit in extended[width:]:
        window = ((window << 1) & mask) | (bit == "1")
        counts[window] += 1
    return counts


class Serial:
    @staticmethod
    def serial_test(binary_data: str, verbose=False, pattern_length=16):
        """Return the two NIST Serial p-values and their 1% threshold decisions.

        This two-statistic interface requires m >= 2 (psi_0 is zero).
        For calibrated inference NIST recommends m < floor(log2(n)) - 2.
        A returned True means failure to reject the fair independent-bit null,
        not proof of randomness. Sample-size recommendations are reported by
        the structured suite runner; this function also supports worked examples.
        """
        validate_bits(binary_data)
        positive_int(pattern_length, "pattern_length", minimum=2)
        pattern_length = int(pattern_length)
        n = len(binary_data)
        if n < pattern_length:
            raise InsufficientDataError("Serial test needs at least pattern_length bits")
        if pattern_length > 1023:
            raise ValueError("pattern_length exceeds the floating-point range (1023)")

        counts = _circular_pattern_counts(binary_data, pattern_length)
        square_sums = []
        for _ in range(3):
            square_sums.append(sum(count * count for count in counts.values()))
            shorter = Counter()
            for pattern, count in counts.items():
                shorter[pattern >> 1] += count
            counts = shorter

        # Integer differences avoid cancellation in almost-uniform samples.
        a, b, c = square_sums
        try:
            delta = ldexp((2 * a - b) / n, pattern_length - 1)
        except OverflowError:
            delta = float("inf")
        try:
            delta2 = ldexp((4 * a - 4 * b + c) / n, pattern_length - 2)
        except OverflowError:
            delta2 = float("inf")
        p1 = float(gammaincc(ldexp(1.0, pattern_length - 2), delta / 2))
        p2 = float(gammaincc(ldexp(1.0, pattern_length - 3), delta2 / 2))
        if verbose:
            print("Serial test: n={}, m={}, delta={}, delta2={}, p-values={}".format(
                n, pattern_length, delta, delta2, (p1, p2)))
        return ((p1, p1 >= 0.01), (p2, p2 >= 0.01))
