"""NIST SP 800-22 Rev. 1a, sections 2.14 and 2.15: excursions."""

from math import ceil, sqrt

import numpy as np
from scipy.special import erfc, gammaincc

from Validation import InsufficientDataError, positive_int, validate_bits


class RandomExcursions:
    STATES = (-4, -3, -2, -1, 1, 2, 3, 4)
    VARIANT_STATES = tuple(range(-9, 0)) + tuple(range(1, 10))

    @staticmethod
    def _walk(binary_data):
        validate_bits(binary_data)
        steps = np.frombuffer(binary_data.encode("ascii"), dtype=np.int8) * 2 - 97
        walk = np.cumsum(steps, dtype=np.int64)
        # A zero at the last observed step already closes the final cycle.
        # Only a nonzero endpoint needs an artificial return to zero.
        returns = np.flatnonzero(walk == 0)
        starts = np.concatenate(([0], returns[returns + 1 < len(walk)] + 1))
        return walk, starts

    @staticmethod
    def cycle_count(binary_data: str):
        """Count nonempty cycles, including a final incomplete excursion."""
        _, starts = RandomExcursions._walk(binary_data)
        return len(starts)

    @staticmethod
    def _require_cycles(n, cycles):
        required = max(500, ceil(0.005 * sqrt(n)))
        if cycles < required:
            raise InsufficientDataError(
                f"Random excursions require J >= max(500, 0.005*sqrt(n)) "
                f"({required} cycles for n={n}); observed J={cycles}. "
                "No inferential p-value is available."
            )

    @staticmethod
    def random_excursions_test(binary_data: str, verbose=False, state=1):
        """Return eight ``(label, state, chi_square, p_value, passed)`` rows.

        Counts of visits per cycle are compared in categories 0,1,2,3,4,>=5.
        NIST recommends n >= 1,000,000. This low-level method enforces the
        cycle requirement J >= max(500, .005*sqrt(n)); callers must also consider
        the sequence-length recommendation. ``state`` is retained for legacy
        callers and validated, but all eight states are always returned.
        """
        if isinstance(state, bool) or not isinstance(state, (int, np.integer)) or state not in RandomExcursions.STATES:
            raise ValueError("state must be one of -4,-3,-2,-1,1,2,3,4")
        walk, starts = RandomExcursions._walk(binary_data)
        cycles = len(starts)
        RandomExcursions._require_cycles(len(binary_data), cycles)
        result = []
        for x in RandomExcursions.STATES:
            counts = np.add.reduceat(walk == x, starts, dtype=np.int64)
            observed = np.bincount(np.minimum(counts, 5), minlength=6)
            expected = cycles * np.array([RandomExcursions.get_pi_value(k, x) for k in range(6)])
            statistic = float(np.sum((observed - expected) ** 2 / expected))
            p_value = float(gammaincc(2.5, statistic / 2))
            result.append((f"{x:+d}", x, statistic, p_value, p_value >= .01))
        if verbose:
            print(f"Random excursions: n={len(binary_data)}, J={cycles}")
            for row in result:
                print(row)
        return result

    @staticmethod
    def variant_test(binary_data: str, verbose=False):
        """Return eighteen ``(label, state, visit_count, p_value, passed)`` rows.

        Include states with zero visits. NIST recommends n >= 1,000,000;
        J >= max(500, .005*sqrt(n)) is enforced before computing p-values.
        """
        walk, starts = RandomExcursions._walk(binary_data)
        cycles = len(starts)
        RandomExcursions._require_cycles(len(binary_data), cycles)
        result = []
        for x in RandomExcursions.VARIANT_STATES:
            count = int(np.count_nonzero(walk == x))
            p_value = float(erfc(abs(count - cycles) / sqrt(2 * cycles * (4 * abs(x) - 2))))
            result.append((f"{x:+d}", x, count, p_value, p_value >= .01))
        if verbose:
            print(f"Random excursions variant: n={len(binary_data)}, J={cycles}")
            for row in result:
                print(row)
        return result

    @staticmethod
    def get_pi_value(k, x):
        """Probability of k visits (category 5 means >=5) in one cycle."""
        positive_int(k, "k", minimum=0)
        if k > 5:
            raise ValueError("k must be a visit-count category from 0 through 5")
        if isinstance(x, bool) or not isinstance(x, (int, np.integer)) or x == 0:
            raise ValueError("x must be a nonzero integer state")
        reciprocal = 1.0 / (2 * abs(x))
        if k == 0:
            return 1 - reciprocal
        if k == 5:
            return reciprocal * (1 - reciprocal) ** 4
        return reciprocal ** 2 * (1 - reciprocal) ** (k - 1)

    @staticmethod
    def get_frequency(list_data, trigger):
        """Legacy helper: return the count for a state, or zero if absent."""
        for state, frequency in list_data:
            if state == trigger:
                return frequency
        return 0
