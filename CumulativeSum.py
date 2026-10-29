"""NIST SP 800-22 Rev. 1a, section 2.13: cumulative sums."""

from math import fsum, sqrt

import numpy as np
from scipy.special import ndtr

from Validation import positive_int, validate_bits


class CumulativeSums:
    @staticmethod
    def cumulative_sums_test(binary_data: str, mode=0, verbose=False):
        """Return ``(p_value, p_value >= .01)`` for a forward/reverse walk.

        The null model is independent fair bits. The normal approximation is
        recommended for n >= 100; smaller inputs are accepted for instructional
        examples, not calibrated statistical inference. A large p-value is not
        evidence that a physical source is random.
        """
        validate_bits(binary_data)
        positive_int(mode, "mode", minimum=0)
        if mode not in (0, 1):
            raise ValueError("mode must be 0 (forward) or 1 (reverse)")

        n = len(binary_data)
        steps = np.frombuffer(binary_data.encode("ascii"), dtype=np.int8) * 2 - 97
        if mode == 1:
            steps = steps[::-1]
        walk = np.cumsum(steps, dtype=np.int64)
        z = int(np.max(np.abs(walk)))
        scale = z / sqrt(n)

        # Integer division is floor, including for negative limits. Both sums
        # in SP 800-22 (2.13.4) have the SAME upper bound.
        first_lower = (-n + z) // (4 * z)
        upper = (n - z) // (4 * z)
        second_lower = (-n - 3 * z) // (4 * z)

        def normal_interval(low, high):
            # Reflect positive intervals to avoid subtracting CDFs near one.
            if low >= 0:
                return float(ndtr(-low) - ndtr(-high))
            return float(ndtr(high) - ndtr(low))

        # Separate k=0 analytically: 1 - [Phi(z)-Phi(-z)] = 2*Phi(-z).
        # This preserves tiny positive tails on strongly biased strings.
        first_tail = fsum(
            normal_interval((4 * k - 1) * scale, (4 * k + 1) * scale)
            for k in range(first_lower, upper + 1) if k != 0
        )
        second = fsum(
            normal_interval((4 * k + 1) * scale, (4 * k + 3) * scale)
            for k in range(second_lower, upper + 1)
        )
        p_value = float(np.clip(2 * ndtr(-scale) - first_tail + second, 0, 1))
        if verbose:
            print(f"Cumulative sums: n={n}, mode={mode}, z={z}, p={p_value}")
        return p_value, p_value >= 0.01
