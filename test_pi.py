"""Run the bundled deterministic pi regression example, not a physical source."""
from pathlib import Path
from randomness_cli import main

if __name__ == "__main__":
    raise SystemExit(main([str(Path(__file__).parent / "data" / "data.pi")]))
