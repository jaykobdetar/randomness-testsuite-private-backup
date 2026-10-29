"""Runs statistics following NIST SP 800-22 Rev. 1a, sections 2.3 and 2.4."""

from collections import deque
from functools import lru_cache
from math import erfc, fsum, sqrt

from scipy.special import gammaincc

from Validation import InsufficientDataError, validate_bits


@lru_cache(maxsize=3)
def _longest_run_probabilities(block_size, lower, upper):
    """Exact finite-string counts for bins <=lower, ..., >=upper.

    For a forbidden run of k ones, the number a(n) of allowed binary strings
    satisfies a(n)=a(n-1)+...+a(n-k), with a(j)=2**j for 0<=j<k.
    The terms correspond to strings ending in 0, 01, ..., 01...(k-1 ones).
    Integer arithmetic before the final division improves on the approximate
    NIST tables without accumulating floating-point error. For M=10000 the
    published probabilities differ by up to .00157 from these exact values;
    this is a deliberate finite-distribution refinement, not STS byte-for-byte
    compatibility. The asymptotic chi-square tail is unchanged.
    """
    total = 1 << block_size
    cumulative = []
    for limit in range(lower, upper):
        k = limit + 1
        previous = deque(1 << j for j in range(k))
        rolling = sum(previous)
        count = 0
        for _ in range(k, block_size + 1):
            count = rolling
            rolling += count - previous.popleft()
            previous.append(count)
        cumulative.append(count)
    counts = [cumulative[0]]
    counts.extend(right - left for left, right in zip(cumulative, cumulative[1:]))
    counts.append(total - cumulative[-1])
    return tuple(count / total for count in counts)


class RunTest:
    @staticmethod
    def run_test(binary_data: str, verbose=False):
        """Return the NIST runs statistic and its asymptotic p-value.

        NIST recommends n >= 100. For compatibility, (0.0, False) is returned when
        the frequency prerequisite fails or the sequence is constant. That zero
        is the NIST *not applicable* convention, not a computed runs p-value;
        the structured runner represents this distinction explicitly.
        """
        validate_bits(binary_data)
        n = len(binary_data)
        proportion = binary_data.count("1") / n
        tau = 2.0 / sqrt(n)
        if proportion in (0.0, 1.0) or abs(proportion - 0.5) >= tau:
            if verbose:
                print(f"Runs: n={n}, pi={proportion}; frequency prerequisite not satisfied.")
            return 0.0, False
        runs = 1 + sum(left != right for left, right in zip(binary_data, binary_data[1:]))
        product = proportion * (1.0 - proportion)
        statistic = abs(runs - 2.0 * n * product) / (2.0 * sqrt(2.0 * n) * product)
        p_value = erfc(statistic)
        if verbose:
            print(f"Runs: n={n}, pi={proportion}, tau={tau}, V_n={runs}, p={p_value}")
        return p_value, p_value >= 0.01

    @staticmethod
    def longest_one_block_test(binary_data: str, verbose=False):
        """Test the longest one-run in each complete NIST-sized block.

        The block size follows the NIST sample-size regimes. All complete blocks
        are used and trailing bits are discarded. Exact finite-block category
        probabilities refine the approximate NIST tables; the chi-square reference
        distribution remains an approximation.
        """
        validate_bits(binary_data)
        n = len(binary_data)
        if n < 128:
            raise InsufficientDataError("Longest run requires at least 128 bits.")
        if n < 6272:
            block_size, lower, upper = 8, 1, 4
        elif n < 750000:
            block_size, lower, upper = 128, 4, 9
        else:
            block_size, lower, upper = 10000, 10, 16
        probabilities = _longest_run_probabilities(block_size, lower, upper)
        frequencies = [0] * len(probabilities)
        blocks = n // block_size
        for start in range(0, blocks * block_size, block_size):
            longest = 0
            current = 0
            for bit in binary_data[start:start + block_size]:
                if bit == "1":
                    current += 1
                    longest = max(longest, current)
                else:
                    current = 0
            category = min(max(longest - lower, 0), upper - lower)
            frequencies[category] += 1
        chi_squared = fsum(
            (observed - blocks * probability) ** 2 / (blocks * probability)
            for observed, probability in zip(frequencies, probabilities)
        )
        degrees = len(probabilities) - 1
        p_value = float(gammaincc(degrees / 2.0, chi_squared / 2.0))
        if verbose:
            print(f"Longest run: n={n}, M={block_size}, N={blocks}, "
                  f"discarded={n - blocks * block_size}, counts={frequencies}, "
                  f"chi2={chi_squared}, p={p_value}")
        return p_value, p_value >= 0.01
