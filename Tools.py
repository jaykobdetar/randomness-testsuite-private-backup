"""Encoding helpers. Encodings are deterministic and do not create entropy."""
import warnings


class Tools:
    @staticmethod
    def bytes_to_binary(input: bytes):
        if not isinstance(input, (bytes, bytearray)):
            raise TypeError("input must be bytes or bytearray")
        return "".join(f"{byte:08b}" for byte in input)

    @staticmethod
    def string_to_binary(input: str):
        """Encode as UTF-8 bytes, MSB first, preserving leading zero bits."""
        if not isinstance(input, str):
            raise TypeError("input must be str")
        return Tools.bytes_to_binary(input.encode("utf-8"))

    @staticmethod
    def string_to_binary_no_concat(input: str):
        """Legacy variable-width code point encoding; ambiguous, not byte data."""
        warnings.warn("Variable-width encoding is ambiguous; use string_to_binary.", DeprecationWarning, stacklevel=2)
        return "".join(bin(ord(char))[2:] for char in input)

    @staticmethod
    def url_to_binary(input: str):
        """Legacy filename-stem extraction; does NOT download or return bits."""
        warnings.warn("url_to_binary only extracts a filename stem; it does not fetch data or return binary.", DeprecationWarning, stacklevel=2)
        return input.split("/")[-1].split(".")[0]
