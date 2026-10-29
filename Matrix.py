"""Binary matrix rank test, NIST SP 800-22 Rev. 1a sections 2.5 and 3.5."""

from functools import lru_cache
from math import exp, fsum, ldexp

import numpy as np

from BinaryMatrix import BinaryMatrix
from Validation import InsufficientDataError, positive_int, validate_bits


@lru_cache(maxsize=32)
def _rank_probabilities(rows, columns):
    """Finite-dimensional probabilities of full, one-less, and lower rank.

    Use the finite GF(2) rank law in section 3.5, rather than applying the
    32x32 asymptotic constants to matrices of arbitrary shape. Sum the lower
    tail directly to avoid cancellation for rectangular matrices.
    """
    maximum = min(rows, columns)
    probabilities = []
    for rank in range(maximum + 1):
        probability = ldexp(1.0, rank * (rows + columns - rank) - rows * columns)
        for i in range(rank):
            probability *= ((1.0 - ldexp(1.0, i - rows))
                            * (1.0 - ldexp(1.0, i - columns))
                            / (1.0 - ldexp(1.0, i - rank)))
        probabilities.append(probability)
    grouped = (probabilities[-1], probabilities[-2], fsum(probabilities[:-2]))
    if any(probability == 0 for probability in grouped):
        raise ValueError("Matrix dimensions produce rank probabilities below floating-point range.")
    return grouped


class Matrix:
    @staticmethod
    def binary_matrix_rank_text(binary_data: str, verbose=False,
                                rows_in_matrix=32, columns_in_matrix=32):
        """Return the rank statistic's asymptotic p-value and alpha=.01 decision.

        The historical method name is retained. Both dimensions must be >= 2
        so there are three nonempty rank categories. Trailing bits are discarded.
        The NIST 32x32 profile requires at least 38 matrices; other shapes need
        adequate expected counts in each category for chi-square calibration.
        """
        validate_bits(binary_data)
        positive_int(rows_in_matrix, "rows_in_matrix", minimum=2)
        positive_int(columns_in_matrix, "columns_in_matrix", minimum=2)
        rows_in_matrix, columns_in_matrix = int(rows_in_matrix), int(columns_in_matrix)
        block_size = rows_in_matrix * columns_in_matrix
        blocks = len(binary_data) // block_size
        if blocks == 0:
            raise InsufficientDataError("Matrix rank requires at least one complete matrix.")
        probabilities = _rank_probabilities(rows_in_matrix, columns_in_matrix)
        maximum = min(rows_in_matrix, columns_in_matrix)
        frequencies = [0, 0, 0]
        for start in range(0, blocks * block_size, block_size):
            bits = np.frombuffer(binary_data[start:start + block_size].encode("ascii"), dtype=np.uint8) - 48
            array = bits.reshape(rows_in_matrix, columns_in_matrix)
            rank = BinaryMatrix(array, rows_in_matrix, columns_in_matrix).compute_rank()
            frequencies[min(maximum - rank, 2)] += 1
        chi_squared = fsum(
            (observed - blocks * probability) ** 2 / (blocks * probability)
            for observed, probability in zip(frequencies, probabilities)
        )
        p_value = exp(-chi_squared / 2.0)
        if verbose:
            print(f"Matrix rank: shape={rows_in_matrix}x{columns_in_matrix}, N={blocks}, "
                  f"discarded={len(binary_data) - blocks * block_size}, "
                  f"counts={frequencies}, probabilities={probabilities}, "
                  f"chi2={chi_squared}, p={p_value}")
        return p_value, p_value >= 0.01

    # Correctly spelled alias for new callers; old imports continue to work.
    binary_matrix_rank_test = binary_matrix_rank_text
