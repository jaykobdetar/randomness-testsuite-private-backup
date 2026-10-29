"""Diagnostic example for packed byte file."""
from pathlib import Path
from randomness_cli import main

if __name__ == "__main__":
    raise SystemExit(main([str(Path(__file__).parent / "data" / "test_data.bin"), "--format", "bytes"]))
