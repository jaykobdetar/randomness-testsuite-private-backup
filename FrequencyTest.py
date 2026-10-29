"""Frequency statistics from NIST SP 800-22 Rev. 1a, sections 2.1 and 2.2.

These low-level functions calculate asymptotic p-values even for short example
vectors. The structured runner checks the recommended calibration conditions.
A True result means only that this statistic does not reject at alpha=0.01.
"""

from math import erfc, fsum, sqrt

from scipy.special import gammaincc

from Validation import InsufficientDataError, positive_int, validate_bits


class FrequencyTest:
    @staticmethod
    def monobit_test(binary_data: str, verbose=False):
        """Return the two-sided normal approximation for the bit imbalance.

        NIST recommends n >= 100. This is not an exact binomial test and a large
        p-value does not prove randomness or physical entropy.
        """
        validate_bits(binary_data)
        n = len(binary_data)
        imbalance = 2 * binary_data.count("1") - n
        statistic = abs(imbalance) / sqrt(n)
        p_value = erfc(statistic / sqrt(2.0))
        if verbose:
            print(f"Monobit: n={n}, S_n={imbalance}, statistic={statistic}, p={p_value}")
        return p_value, p_value >= 0.01

    @staticmethod
    def block_frequency(binary_data: str, block_size=128, verbose=False):
        """Test counts in complete, nonoverlapping blocks of the requested size.

        Trailing bits are discarded. The block size is never silently reduced. For
        one *block* this equals the monobit test on that block; block size one is
        not a useful chi-square approximation. NIST recommends n >= 100, M >= 20,
        M > 0.01*n and N < 100 (section 2.2.7).
        """
        validate_bits(binary_data)
        positive_int(block_size, "block_size")
        block_size = int(block_size)
        n = len(binary_data)
        blocks = n // block_size
        if blocks == 0:
            raise InsufficientDataError("Block frequency requires at least one complete block.")
        # This is algebraically 4*M*sum((pi_i - 1/2)**2), expressed in counts.
        chi_squared = fsum(
            (2 * binary_data[start:start + block_size].count("1") - block_size) ** 2
            / block_size
            for start in range(0, blocks * block_size, block_size)
        )
        p_value = float(gammaincc(blocks / 2.0, chi_squared / 2.0))
        if verbose:
            print(f"Block frequency: n={n}, M={block_size}, N={blocks}, "
                  f"discarded={n - blocks * block_size}, chi2={chi_squared}, p={p_value}")
        return p_value, p_value >= 0.01
