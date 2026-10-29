"""Maurer's universal test, NIST SP 800-22 Rev. 1a section 2.9."""

from math import erfc, fsum, log2, sqrt

from Validation import InsufficientDataError, validate_bits


class Universal:
    # Minimum bit lengths in NIST table 2.9.7, for L=6,...,16.
    _MIN_LENGTHS = (
        387840, 904960, 2068480, 4654080, 10342400, 22753280,
        49643520, 107560960, 231669760, 496435200, 1059061760,
    )
    _EXPECTED = (5.2177052, 6.1962507, 7.1836656, 8.1764248, 9.1723243,
                 10.170032, 11.168765, 12.168070, 13.167693, 14.167488, 15.167379)
    _VARIANCE = (2.954, 3.125, 3.238, 3.311, 3.356, 3.384, 3.401, 3.410, 3.416, 3.419, 3.421)

    @staticmethod
    def _pattern_size(n):
        if n < Universal._MIN_LENGTHS[0]:
            raise InsufficientDataError(
                f"Maurer's universal test requires at least 387840 bits; received {n}."
            )
        return max(size for size, minimum in enumerate(Universal._MIN_LENGTHS, 6) if n >= minimum)

    @staticmethod
    def statistical_test(binary_data: str, verbose=False):
        """Return ``(p_value, p_value >= .01)`` using NIST's automatic L.

        At least 387840 bits are required. L ranges from 6 through 16, with
        Q=10*2**L initialization blocks. Fewer than L trailing bits are unused.
        This detects certain compressibility departures from independent fair
        bits; it does not estimate physical entropy or establish randomness.
        """
        validate_bits(binary_data)
        n = len(binary_data)
        size = Universal._pattern_size(n)
        q = 10 * (1 << size)
        total_blocks = n // size
        k = total_blocks - q
        last_seen = [0] * (1 << size)
        for i in range(1, q + 1):
            block = int(binary_data[(i - 1) * size:i * size], 2)
            last_seen[block] = i

        def recurrence_logs():
            for i in range(q + 1, total_blocks + 1):
                block = int(binary_data[(i - 1) * size:i * size], 2)
                distance = i - last_seen[block]
                last_seen[block] = i
                yield log2(distance)

        statistic = fsum(recurrence_logs()) / k
        correction = 0.7 - 0.8 / size + (4 + 32 / size) * k ** (-3 / size) / 15
        sigma = correction * sqrt(Universal._VARIANCE[size - 6] / k)
        p_value = erfc(abs(statistic - Universal._EXPECTED[size - 6]) / (sqrt(2) * sigma))
        if verbose:
            print(f"Maurer's universal test: n={n}, L={size}, Q={q}, K={k}, "
                  f"discarded={n % size}, statistic={statistic}, p={p_value}")
        return p_value, p_value >= .01
