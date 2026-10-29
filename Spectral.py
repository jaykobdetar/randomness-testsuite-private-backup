"""NIST SP 800-22 Rev. 1a discrete Fourier transform statistic."""

from math import erfc, log, sqrt

import numpy as np
from scipy.fft import rfft

from Validation import InsufficientDataError, validate_bits


class SpectralTest:
    @staticmethod
    def spectral_test(binary_data: str, verbose=False):
        """Return the NIST spectral p-value and the alpha=.01 decision.

        Count the first floor(n/2) FFT magnitudes, including DC and excluding
        Nyquist for even n, as in NIST's implementation. No bits are removed
        before transformation. This low-level method accepts teaching examples;
        NIST's 2010 software note recommends n=1,000,000 for calibration of this
        test. A p-value is not a measurement of entropy or physical randomness.
        """
        validate_bits(binary_data)
        n = len(binary_data)
        if n < 2:
            raise InsufficientDataError("Spectral test requires at least two bits.")
        # Signed conversion before subtraction prevents uint8 wraparound.
        samples = np.frombuffer(binary_data.encode("ascii"), dtype=np.uint8).astype(np.int8)
        samples = 2 * (samples - 48) - 1
        magnitudes = np.abs(rfft(samples)[:n // 2])
        threshold = sqrt(log(20.0) * n)
        expected = 0.95 * n / 2.0
        observed = int(np.count_nonzero(magnitudes < threshold))
        statistic = (observed - expected) / sqrt(n * 0.95 * 0.05 / 4.0)
        p_value = erfc(abs(statistic) / sqrt(2.0))
        if verbose:
            print(f"Spectral: n={n}, T={threshold}, N_0={expected}, N_1={observed}, "
                  f"d={statistic}, p={p_value}")
        return p_value, p_value >= 0.01
