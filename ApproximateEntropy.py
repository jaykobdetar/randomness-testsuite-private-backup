"""NIST SP 800-22r1a section 2.12 (not an entropy-source estimator)."""

from collections import Counter
from math import fsum, ldexp, log

from scipy.special import gammaincc

from Serial import _circular_pattern_counts
from Validation import InsufficientDataError, positive_int, validate_bits


class ApproximateEntropy:
    @staticmethod
    def approximate_entropy_test(binary_data: str, verbose=False, pattern_length=10):
        """Return the NIST approximate-entropy p-value and a 1% decision.

        Counts n circular windows of lengths m and m+1. NIST recommends
        m < floor(log2(n)) - 5 for calibrated inference. This statistic does
        not estimate physical entropy or certify unpredictability.
        """
        validate_bits(binary_data)
        positive_int(pattern_length, "pattern_length")
        pattern_length = int(pattern_length)
        n = len(binary_data)
        if n < pattern_length + 1:
            raise InsufficientDataError("Approximate entropy needs at least m+1 bits")
        if pattern_length > 1023:
            raise ValueError("pattern_length exceeds the floating-point range (1023)")
        longer = _circular_pattern_counts(binary_data, pattern_length + 1)
        shorter = Counter()
        for pattern, count in longer.items():
            shorter[pattern >> 1] += count

        # Equivalent to phi(m)-phi(m+1), evaluated as conditional entropy to
        # avoid subtracting two nearly equal negative sums.
        ap_en = -fsum(count / n * log(count / shorter[pattern >> 1])
                      for pattern, count in longer.items())
        statistic = max(0.0, 2.0 * n * (log(2.0) - ap_en))
        p_value = float(gammaincc(ldexp(1.0, pattern_length - 1), statistic / 2.0))
        if verbose:
            print("Approximate entropy: n={}, m={}, ApEn={}, chi-square={}, p={}".format(
                n, pattern_length, ap_en, statistic, p_value))
        return (p_value, p_value >= 0.01)
