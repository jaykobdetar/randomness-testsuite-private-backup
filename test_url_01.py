"""Diagnostic example for literal text bytes (no URL fetching or filename extraction)."""
from pathlib import Path
from randomness_cli import main

if __name__ == "__main__":
    raise SystemExit(main([str(Path(__file__).parent / "data" / "test_data_01.txt"), "--format", "bytes"]))
