"""NIST linear-complexity test with exact arithmetic over GF(2)."""

from bisect import bisect_left
from math import fsum, ldexp

from scipy.special import gammaincc

from Validation import InsufficientDataError, positive_int, validate_bits


class ComplexityTest:
    @staticmethod
    def linear_complexity_test(binary_data: str, verbose=False, block_size=500):
        """Return the section 2.10 p-value and its 1% threshold decision.

        Incomplete final blocks are discarded. NIST recommends n >= 10**6,
        500 <= M <= 5000 and at least 200 blocks; the chi-square law and
        seven cell probabilities are asymptotic, not exact for small M.
        """
        validate_bits(binary_data)
        positive_int(block_size, "block_size")
        block_size = int(block_size)
        n = len(binary_data)
        number_of_blocks = n // block_size
        if number_of_blocks == 0:
            raise InsufficientDataError("Linear complexity needs one complete block")

        # Exact limiting probabilities (the original 0.01047 was a typo).
        probabilities = (1 / 96, 1 / 32, 1 / 8, 1 / 2, 1 / 4, 1 / 16, 1 / 48)
        mean = (block_size / 2 + (9 + (-1) ** (block_size + 1)) / 36
                - ldexp(block_size / 3 + 2 / 9, -block_size))
        frequencies = [0] * 7
        boundaries = (-2.5, -1.5, -0.5, 0.5, 1.5, 2.5)
        for start in range(0, number_of_blocks * block_size, block_size):
            complexity = ComplexityTest.berlekamp_massey_algorithm(
                binary_data[start:start + block_size])
            transformed = (-1) ** block_size * (complexity - mean) + 2 / 9
            frequencies[bisect_left(boundaries, transformed)] += 1
        statistic = fsum((observed - number_of_blocks * probability) ** 2
                         / (number_of_blocks * probability)
                         for observed, probability in zip(frequencies, probabilities))
        p_value = float(gammaincc(3, statistic / 2))
        if verbose:
            print("Linear complexity: n={}, M={}, blocks={}, bins={}, chi-square={}, p={}".format(
                n, block_size, number_of_blocks, frequencies, statistic, p_value))
        return (p_value, p_value >= 0.01)

    @staticmethod
    def berlekamp_massey_algorithm(block_data):
        """Find the minimum binary LFSR length for a nonempty bit string.

        Polynomial coefficients and history are integer bitsets. XOR is exact
        addition in GF(2); bit-count parity gives the discrepancy. This avoids
        floating arithmetic and per-step copies of length-M arrays.
        """
        validate_bits(block_data)
        connection = previous = 1
        length, last_update, history = 0, -1, 0
        for index, bit in enumerate(block_data):
            history = (history << 1) | (bit == "1")
            if (history & connection).bit_count() & 1:
                old_connection = connection
                connection ^= previous << (index - last_update)
                if 2 * length <= index:
                    length = index + 1 - length
                    last_update = index
                    previous = old_connection
        return length
