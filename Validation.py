"""Shared contracts for the mathematical test functions.

Low-level functions retain their historical return shapes. Use ``Suite.run_suite``
for sample-size checks, explicit applicability and reproducible reports.
"""

from numbers import Integral


class InsufficientDataError(ValueError):
    """The input does not meet a test's data requirements."""


def validate_bits(binary_data):
    """Require a nonempty string containing only ASCII zero and one.

    Whitespace normalization belongs to the explicit text-file reader, never
    the mathematical routines. Invalid observations must not disappear.
    """
    if not isinstance(binary_data, str):
        raise TypeError("binary_data must be a string of ASCII 0 and 1")
    if not binary_data:
        raise InsufficientDataError("binary_data must contain at least one bit")
    if binary_data.count("0") + binary_data.count("1") != len(binary_data):
        raise ValueError("binary_data must contain only ASCII 0 and 1")


def positive_int(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
