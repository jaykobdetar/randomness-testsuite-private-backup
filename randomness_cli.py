"""Command-line interface; run ``python randomness_cli.py --help``."""

import argparse
import json
from pathlib import Path

from BitInput import read_bits, split_sequences
from Suite import INTERPRETATION, TEST_NAMES, run_suite, summarize_reports


def main(argv=None):
    parser = argparse.ArgumentParser(description="Statistical diagnostics of binary sequences; no randomness certification.")
    parser.add_argument("file", nargs="?", type=Path, help="input file (never silently truncated)")
    parser.add_argument("--bits", help="literal ASCII 0/1 string instead of a file")
    parser.add_argument("--format", choices=("ascii", "bytes"), default="ascii",
                        help="ASCII bits with whitespace, or packed bytes in MSB-first order")
    parser.add_argument("--tests", nargs="+", choices=TEST_NAMES, help="test IDs; default: all families")
    parser.add_argument("--alpha", type=float, default=0.01)
    parser.add_argument("--sequence-length", type=int, help="split into equal disjoint sequences for a batch")
    parser.add_argument("--discard-remainder", action="store_true", help="explicitly allow dropping an incomplete final sequence")
    parser.add_argument("--output", type=Path, help="save a full JSON report")
    args = parser.parse_args(argv)
    if (args.file is None) == (args.bits is None):
        parser.error("provide exactly one of file or --bits")
    if args.discard_remainder and args.sequence_length is None:
        parser.error("--discard-remainder requires --sequence-length")
    if args.bits is not None and args.format != "ascii":
        parser.error("--format bytes applies only to file input")
    try:
        if args.file is not None and args.output is not None:
            if (args.file.resolve() == args.output.resolve()
                    or (args.output.exists() and args.file.samefile(args.output))):
                parser.error("output must not overwrite the input file")
        if args.file is not None:
            bits, source = read_bits(args.file, args.format)
        else:
            bits, source = args.bits, {"format": "literal-bits"}
        if args.sequence_length is None:
            report = run_suite(bits, args.tests, args.alpha)
            report["source"] = source
            reports = [report]
        else:
            sequences, discarded = split_sequences(bits, args.sequence_length, args.discard_remainder)
            reports = [run_suite(sequence, args.tests, args.alpha) for sequence in sequences]
            report = {"schema_version": 1, "source": source, "input_bits": len(bits),
                      "sequence_length": args.sequence_length, "discarded_trailing_bits": discarded,
                      "interpretation": INTERPRETATION, "reports": reports,
                      "second_level": summarize_reports(reports)}
        if args.output:
            args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        else:
            print(json.dumps(report, indent=2, allow_nan=False))
        return 1 if any(r["status"] == "error" for x in reports for r in x["results"]) else 0
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
