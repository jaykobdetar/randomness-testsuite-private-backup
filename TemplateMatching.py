"""Template tests under independent Bernoulli(1/2) bits (SP 800-22r1a)."""

from functools import lru_cache
from math import exp, fsum, isfinite, ldexp, log
from numbers import Real

import numpy as np
from scipy.special import gammaincc, gammaln, logsumexp

from Validation import InsufficientDataError, positive_int, validate_bits


@lru_cache(maxsize=32)
def _overlapping_probabilities(pattern_size, block_size):
    """Exact finite-block probabilities for 0,1,2,3,4,>=5 all-one matches.

    State (c,r) records capped count c and trailing ones r, capped at m-1.
    A zero resets r; a one advances r or creates another overlapping match.
    Each transition has probability 1/2. At m=9,M=1032 this reproduces
    the revised probabilities in NIST sections 2.8/3.8 without rounding.
    The subsequent chi-square calibration is still asymptotic in block count.
    """
    state = np.zeros((6, pattern_size), dtype=float)
    state[0, 0] = 1.0
    for _ in range(block_size):
        following = np.zeros_like(state)
        following[:, 0] = state.sum(axis=1) / 2
        following[:, 1:] = state[:, :-1] / 2
        following[1:, -1] += state[:-1, -1] / 2
        following[-1, -1] += state[-1, -1] / 2
        state = following
    return tuple(float(probability) for probability in state.sum(axis=1))


class TemplateMatching:
    @staticmethod
    def non_overlapping_test(binary_data: str, verbose=False,
                             template_pattern='000000001', block=8):
        """Test one unbordered template; return (p-value, p-value >= 0.01).

        The NIST mean and asymptotic variance require no proper prefix
        equal to a suffix (no possible self-overlap). Merely being different
        from a repetition of a shorter word is insufficient. This tests one
        specified template, not the complete 148-template m=9 family.
        `block` is the number of blocks; trailing remainder bits are discarded.
        """
        validate_bits(binary_data)
        validate_bits(template_pattern)
        positive_int(block, "block")
        block = int(block)
        m = len(template_pattern)
        if any(template_pattern[:width] == template_pattern[-width:]
               for width in range(1, m)):
            raise ValueError("template_pattern must be unbordered (no self-overlap)")
        block_size = len(binary_data) // block
        if block_size < m:
            raise InsufficientDataError("Each block must contain at least one full template")
        probability = ldexp(1.0, -m)
        variance = block_size * probability * (1 - (2 * m - 1) * probability)
        if variance <= 0:
            raise ValueError("Template probability is below floating-point resolution")
        mean = (block_size - m + 1) * probability
        # str.count counts non-overlapping matches, and confines them to each
        # block. It implements the corrected NIST skip-after-match behavior.
        counts = [binary_data.count(template_pattern, index * block_size,
                                    (index + 1) * block_size)
                  for index in range(block)]
        statistic = fsum((count - mean) ** 2 / variance for count in counts)
        p_value = float(gammaincc(block / 2, statistic / 2))
        if verbose:
            print("Non-overlapping template: m={}, M={}, mean={}, variance={}, counts={}, p={}".format(
                m, block_size, mean, variance, counts, p_value))
        return (p_value, p_value >= 0.01)

    @staticmethod
    def overlapping_patterns(binary_data: str, verbose=False, pattern_size=9,
                             block_size=1032):
        """Test overlapping all-one templates with six exact null cell masses.

        The 0,1,2,3,4,>=5 histogram uses a chi-square approximation with
        five degrees of freedom. Meaningful inference requires adequately
        populated expected cells (N*min(pi)>5); NIST recommends n>=10**6
        and m=9 or 10. Remainder bits after complete blocks are discarded.
        """
        validate_bits(binary_data)
        positive_int(pattern_size, "pattern_size")
        positive_int(block_size, "block_size")
        pattern_size, block_size = int(pattern_size), int(block_size)
        if block_size < pattern_size + 4:
            raise ValueError("block_size must allow at least five overlapping matches (m+4)")
        number_of_blocks = len(binary_data) // block_size
        if number_of_blocks == 0:
            raise InsufficientDataError("Overlapping template test needs one complete block")
        probabilities = _overlapping_probabilities(pattern_size, block_size)
        if any(probability <= 0 for probability in probabilities):
            raise ValueError("Parameters produce cell probabilities below floating-point resolution")

        counts = [0] * 6
        for start in range(0, number_of_blocks * block_size, block_size):
            # A run of r ones contains max(0,r-m+1) overlapping matches.
            matches = sum(max(0, len(run) - pattern_size + 1)
                          for run in binary_data[start:start + block_size].split('0'))
            counts[min(matches, 5)] += 1
        statistic = fsum((count - number_of_blocks * probability) ** 2
                         / (number_of_blocks * probability)
                         for count, probability in zip(counts, probabilities))
        p_value = float(gammaincc(2.5, statistic / 2))
        if verbose:
            print("Overlapping template: m={}, M={}, blocks={}, bins={}, probabilities={}, p={}".format(
                pattern_size, block_size, number_of_blocks, counts, probabilities, p_value))
        return (p_value, p_value >= 0.01)

    @staticmethod
    def get_prob(u, x):
        """Legacy compound-Poisson approximation, with eta=x, from section 3.8.

        Retained for compatibility; the test itself uses the more accurate
        finite-block probabilities above. Log-domain summation avoids the
        overflow/underflow product in the old hypergeometric expression.
        """
        positive_int(u, "u", minimum=0)
        u = int(u)
        if isinstance(x, bool) or not isinstance(x, Real) or not isfinite(x) or x < 0:
            raise ValueError("x must be a finite nonnegative number")
        if u == 0:
            return exp(-x)
        if x == 0:
            return 0.0
        terms = [gammaln(u) - gammaln(index) - gammaln(u - index + 1)
                 + index * log(x) - gammaln(index + 1)
                 for index in range(1, u + 1)]
        return float(exp(-x - u * log(2) + logsumexp(terms)))
