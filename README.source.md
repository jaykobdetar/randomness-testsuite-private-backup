> Historical documentation preserved from the private snapshot. Paths, bundled lengths, CI statements and past verification claims may be stale. Use README.md and VALIDATION.md for the reviewed state.

# Randomness test suite

A scientific diagnostic tool for binary sequences, based on the 15 test families in NIST SP 800-22 Rev. 1a. The supported profile produces up to **188 separate p-values**, including all 148 length-nine non-overlapping templates and every excursion state.

**Passing a statistical test does not establish physical randomness, entropy, or cryptographic security.** The null model is independent, equally probable bits. Results say `reject`, `not_rejected`, or `not_applicable`; they never label a source “truly random.” See [Scientific notes](SCIENTIFIC_NOTES.md) for assumptions, operating limits, physical measurements, and deliberate refinements of the NIST formulas.

## Install and run

Python 3.10 or later, NumPy and SciPy are required. From this directory:

```sh
python -m pip install -e '.[test]'
python Main.py
```

The desktop interface requires Tk (provided separately by some Python distributions). It runs computations in a worker thread, shows all result channels, explains unavailable tests, and saves complete JSON reports. The command line works without Tk or a display:

```sh
# ASCII 0/1 file, with ASCII whitespace allowed; the whole file is read.
python randomness_cli.py data/data.e --output report.json

# Full reference profile: explicitly use its first million bits.
# The bundled constants include 4,882 or 4,883 extra bits.
python randomness_cli.py data/data.e --sequence-length 1000000 --discard-remainder --output reference-report.json

# Packed binary file: each byte becomes eight bits, most significant bit first.
python randomness_cli.py capture.bin --format bytes --output capture-report.json

# Select a small set of tests explicitly.
python randomness_cli.py data/data.pi --tests frequency runs cusum_forward

# Divide a capture into equal, disjoint million-bit sequences.
python randomness_cli.py capture.bin --format bytes --sequence-length 1000000 --output batch.json
```

An incomplete final sequence is an error unless `--discard-remainder` is supplied; the discarded length is recorded. Full-file and bitstream hashes, exact sample lengths, parameters, thresholds, package versions, and UTC timestamps make reports reproducible. Test-specific incomplete blocks are also recorded. Invalid characters, empty input, and invalid parameters are rejected. A computational error is distinct from statistical rejection. CLI exit status is 0 for a completed report (including rejections/inapplicable tests), 1 for a reported computation error, and 2 for invalid input or arguments.

## Scientific improvements

- Correct GF(2) matrix rank, including rectangular matrices; finite-dimensional null probabilities.
- Exact finite-block category probabilities for longest runs and overlapping templates, with independent enumeration tests.
- Corrected linear-complexity probabilities and exact, fast Berlekamp–Massey arithmetic.
- Correct cumulative-sum bounds, excursion cycle accounting, and all 18 variant states, including unvisited states.
- Explicit sample-size and runs-prerequisite checks. Unavailable results have no fabricated p-value.
- Per-channel batch summaries: pass proportions, the NIST three-sigma interval, a binomial diagnostic, and a ten-bin uniformity test only with at least 55 eligible sequences. Reports from different settings or implementation versions cannot be combined.

Parameters in the supported profile depend only on sample length, not observed outcomes. The spectral test is restricted to exactly one million bits following NIST's software guidance. Longer data can be explicitly split. Other operating limits are listed in [Scientific notes](SCIENTIFIC_NOTES.md).

This is **not a bit-for-bit clone or a NIST-certified implementation**. Three category probability models deliberately improve the approximations/typo in the old implementation. The notes identify these changes and known inconsistencies in published short examples. Chi-square and normal tail calibration remain asymptotic; more precise category probabilities do not make those tail approximations exact.

## Python API

```python
from BitInput import read_bits
from Suite import run_suite

bits, source = read_bits('data/data.e', 'ascii')
report = run_suite(bits, tests=['frequency', 'runs'], alpha=0.01)
report['source'] = source
for result in report['results']:
    print(result['test_id'], result['status'], result['p_values'], result['reason'])
```

The original mathematical classes remain available for reproducing calculations. Their `(p_value, bool)` returns retain the fixed 1% threshold. They can permit short instructional examples without valid asymptotic calibration; use `run_suite` for scientific reports. Invalid inputs now raise explicit exceptions instead of returning sentinel p-values or silently changing requested parameters. The legacy runs function retains NIST's `(0, False)` prerequisite convention; the structured API reports this as `not_applicable`. Variant state labels are normalized to signed integers. `Tools.string_to_binary` now uses explicit UTF-8 bytes. Deprecated variable-width and URL-filename helpers are not used by the application.

## Verification

```sh
python -m pytest -q
```

Tests include published known answers, exhaustive small GF(2) and pattern checks, independent mathematical oracles, input/report contracts, and all 188 channels on each of four bundled million-bit constants. Checked-in fixtures come from the official NIST STS 2.1.2 C code: 740 p-values compare directly at the reference output's precision; 12 observed category histograms match exactly for the three refined families. The refined probabilities have separate independent tests. Deterministic constants are regression fixtures, not physical entropy sources.

To regenerate the independent reference fixtures, download and build the official [NIST STS software](https://csrc.nist.gov/projects/random-bit-generation/documentation-and-software), then run:

```sh
python tools/reference_compare.py --help
```

The reference source hashes and explicit parameters are recorded in `tests/fixtures/nist_sts_2_1_2.json`. Ordinary tests need no network or C compiler. CI is configured for Python 3.10 and 3.13. Desktop tests run when a display is available (`xvfb-run -a python -m pytest tests/test_gui.py -q` on Linux).

## Scientific scope and attribution

This project continues [stevenang/randomness_testsuite](https://github.com/stevenang/randomness_testsuite) through the jaykobdetar fork. The existing license is retained. Historical files in `result/` are old outputs, not current validation evidence.

[NIST SP 800-22 Rev. 1a](https://doi.org/10.6028/NIST.SP.800-22r1a) supplies the statistical methods. NIST's [2022 revision decision](https://www.nist.gov/news-events/news/2022/04/decision-revise-nist-sp-800-22-rev-1a) explicitly rejects using this suite to assess cryptographic random-number generators. Physical entropy-source work requires a source model, raw measurements, and analysis such as [SP 800-90B](https://doi.org/10.6028/NIST.SP.800-90B); that assessment is not implemented here.
