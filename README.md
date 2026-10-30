# Randomness test suite

Statistical diagnostics of binary sequences based on the 15 families in NIST SP 800-22 Rev. 1a. The structured API, command line and Tk interface report up to 188 separate p-values, applicability, parameters and input hashes.

**This is a private release candidate under review.** Non-rejection does not prove randomness, entropy, independence or cryptographic security. The tests use asymptotic approximations and do not provide an overall certification. Read [scientific notes](SCIENTIFIC_NOTES.md), [saved validation evidence](VALIDATION.md), [local follow-up checks](LOCAL_REFINEMENTS.md) and the unresolved [license/provenance review](PROVENANCE.md).

## Install

Python 3.10+ is declared; see validation evidence for environments actually tested. NumPy and SciPy are installed as dependencies. In a virtual environment, from this checkout:

```sh
python -m venv .venv
# Activate the environment using your platform's activation command.
python -m pip install -e '.[test]'
python -m pytest -q
```

The installed CLI needs no Tk or display. Desktop use requires a Python distribution with Tk and a display:

```sh
python -m Main
```

## Run diagnostics

```sh
# Each bundled reference constant contains exactly one million bits.
randomness-suite data/data.e --output report.json

# A selected subset of diagnostics.
randomness-suite data/data.pi --tests frequency runs cusum_forward

# Packed bytes, most significant bit first, explicitly split into equal sequences.
randomness-suite capture.bin --format bytes --sequence-length 1000000 --output batch.json

# Literal input is strictly ASCII 0/1; this short example reports inapplicability.
randomness-suite --bits 00110101 --tests frequency
```

ASCII files may contain ASCII whitespace. Other characters are rejected. Packed bytes must be selected explicitly with `--format bytes`. An incomplete final sequence is an error unless `--discard-remainder` is supplied, and the discarded length is recorded. The CLI and supported GUI refuse report destinations that alias their input path, including symlinks and hard links. This protects against accidental overwrites; concurrent filesystem changes are outside this check.

Batch inference is restricted to the documented million-bit regime. Unsupported settings, duplicate inputs, and data-conditioned runs/excursion channels keep descriptive summaries with null inferential fields and an explanation. See the scientific notes for the raw p-value API’s explicit calibration assumption.

CLI exit codes are 0 for a completed report, including statistical rejections or inapplicable tests; 1 for reported computation errors; and 2 for invalid input, arguments or file errors. Inspect result statuses, rather than treating exit 0 as statistical success. Reports include absolute source paths; review them before sharing.

```python
from BitInput import read_bits
from Suite import run_suite

bits, source = read_bits('data/data.e')
report = run_suite(bits, tests=['frequency', 'runs'], alpha=0.01)
report['source'] = source
for result in report['results']:
    print(result['test_id'], result['status'], result['p_values'])
```

Use the structured runner for applicability checks. Legacy mathematical classes retain their return shapes and fixed 1% decisions; their support for small worked examples is not a calibration guarantee. `OLD_Main.py` and `GUI.py` are legacy compatibility code, not the supported desktop entrypoint.

## Reproduce the evidence

Ordinary tests are offline and include all four reference constants. They compare 740 p-values against official C results, 12 observed histograms for deliberately refined families, and independent finite-space or mathematical oracles. To regenerate reference results, separately download and build [NIST STS 2.1.2](https://csrc.nist.gov/projects/random-bit-generation/documentation-and-software), then run:

```sh
python tools/reference_compare.py --sts-root /path/to/sts-2.1.2 --output /tmp/fresh-reference.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python tools/seeded_validation.py --output /tmp/seeded.json
```

The reference tool overwrites that external STS installation's experiment outputs; use a disposable reference checkout. The seeded diagnostic uses 64 deterministic million-bit sequences and one process. It records rejections rather than tuning the implementation to avoid them. See [VALIDATION.md](VALIDATION.md) for results and remaining coverage limits.

This project continues [stevenang/randomness_testsuite](https://github.com/stevenang/randomness_testsuite) through the [jaykobdetar fork](https://github.com/jaykobdetar/randomness_testsuite). The inherited license remains unchanged; its unusual notice needs clarification before release. [README.source.md](README.source.md) preserves earlier documentation, whose historical execution claims are not evidence for this release candidate.
