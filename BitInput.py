"""Explicit input encodings: ASCII bit text or packed bytes (MSB first)."""

from hashlib import sha256
from pathlib import Path

from Validation import positive_int, validate_bits


def read_bits(path, input_format="ascii"):
    data = Path(path).read_bytes()
    if input_format == "ascii":
        # Only ASCII whitespace may be removed; punctuation, byte order marks
        # and non-ASCII digits are errors, not observations to silently drop.
        bits = data.decode("ascii").translate(str.maketrans("", "", " \t\r\n\v\f"))
    elif input_format == "bytes":
        bits = "".join(f"{byte:08b}" for byte in data)
    else:
        raise ValueError("input_format must be 'ascii' or 'bytes'")
    validate_bits(bits)
    return bits, {"path": str(Path(path).resolve()), "format": input_format,
                  "bit_order": "msb-first" if input_format == "bytes" else "as-written",
                  "file_bytes": len(data), "sha256_file": sha256(data).hexdigest()}


def split_sequences(bits, sequence_length, discard_remainder=False):
    validate_bits(bits)
    positive_int(sequence_length, "sequence_length")
    if not isinstance(discard_remainder, bool):
        raise TypeError("discard_remainder must be a boolean")
    sequence_length = int(sequence_length)
    count, remainder = divmod(len(bits), sequence_length)
    if count == 0:
        raise ValueError("input is shorter than one requested sequence")
    if remainder and not discard_remainder:
        raise ValueError(f"{remainder} trailing bits would be discarded; explicitly enable discard_remainder")
    return [bits[i * sequence_length:(i + 1) * sequence_length] for i in range(count)], remainder


def require_distinct_output(source, output):
    """Reject ordinary path, symlink and hard-link aliases before writing.

    This is accidental-overwrite protection, not protection against concurrent
    filesystem changes. A removed source need not prevent saving elsewhere.
    """
    source, output = Path(source), Path(output)
    if (source.resolve() == output.resolve()
            or (source.exists() and output.exists() and source.samefile(output))):
        raise ValueError("output must not overwrite the input file")
