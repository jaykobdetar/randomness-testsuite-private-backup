# Release-candidate validation — 2026-10-29

Status: private review candidate; publication is not approved. Work started from private commit `9681a825b2b6d8318d9e6627232d652833d97712` on branch `validation/public-readiness`. See [provenance and release blockers](PROVENANCE.md).

## Changes and regression evidence

1. Restored four missing million-bit mathematical constants from official NIST STS 2.1.2, with source and content digests. Before restoration the test run had 279 passes, 3 failures, 18 setup errors and one skipped module. Missing fixtures caused every failure/error. With restored data the unchanged baseline had 300 passes and one skipped module.
2. Fixed second-level histogram edges. For five copies of `[0,.1,.2,.3,.4,.5,.6,.7,.8,.9,1]`, the old linspace histogram produced `[5,5,10,0,5,10,5,0,5,10]`; the NIST integer-bin convention produces `[5,5,5,5,5,5,5,5,5,10]`. The regression also checks the resulting chi-square tail.
3. Prevented CLI output from overwriting its input via identical paths, symlinks or hard links. Regression tests verify exit 2 and unchanged source contents for all three cases.
4. Added finite/degenerate full-profile checks, a bounded seeded diagnostic, C template cross-check tooling, source-distribution fixture inclusion, scientific scope documentation and honest release instructions. Generated build products stay ignored.
5. Incremented both distribution and report version to `2.0.1.dev0`, so the batch homogeneity check rejects mixing reports from the original 2.0.0 implementation with the histogram fix.

## Independent reference reproduction

The official archive digest is `0238d2f1d26e120e3cc748ed2d4c674cdc636de37fc4027c76cc2a394fff9157`. Download location and vector digests are in `data/provenance.json`. A fresh, unmodified C build using `make -j1` and the included comparison script reproduced all values, category counts and C source hashes in `tests/fixtures/nist_sts_2_1_2.json`; only the generation timestamp differed. Build warnings from the legacy C code were present; successful execution and output accounting were checked.

```sh
make -j1                       # inside the disposable official STS root
python tools/reference_compare.py --sts-root /path/to/sts-2.1.2 --output /tmp/fresh-reference.json
```

Across e, pi, sqrt2 and sqrt3: 740 Python p-values compare directly with C's six-decimal results (5.1e-7 tolerance, or 1.1e-6 for cumulative sums). Twelve histograms match C exactly for longest runs, overlapping templates and linear complexity; their refined null probabilities are checked separately. This is execution evidence beyond merely trusting the pre-existing JSON. Independent exhaustive tests cover small GF(2) ranks, recurrence complexity and pattern counts; state propagation checks longest-run probabilities at larger sizes.

## Fixed seeded experiment

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python tools/seeded_validation.py --output validation/seeded-v1.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python tools/check_seeded_templates.py --sts-root /path/to/sts-2.1.2 --output validation/seeded-template-reference.json
```

64 million-bit SHAKE256 fixtures, generated sequentially with the prefix and indexes recorded in the report, produced no computation errors. There were 188 channels. Non-excursion channels had 64 observations; all 26 excursion channels had 39 eligible observations and correctly omitted uniformity p-values. No channel's non-rejection proportion lay outside its nominal three-sigma interval.

One non-overlapping template, `000110111`, had uniformity p=0.00007484605705774294, below 0.0001. It is retained without seed selection or implementation tuning. The follow-up compared **all 9,472 template values** against official C: zero disagreements beyond 5.1e-7, maximum absolute difference 4.999552479234559e-7. C and Python produce the same outlier histogram `[3,4,8,6,3,6,3,19,3,9]`. This rules out an observed Python/C disagreement for this experiment; it does not prove that the diagnostic's calibration or the deterministic generator is ideal.

A small seeded experiment is not a proof of calibration, independence, entropy or cryptographic fitness. Multiple dependent tests can reject by chance. No overall statistical pass/fail claim is made.

## Installation and runtime checks

Validation uses Linux and isolated virtual environments. BLAS/OpenMP thread counts were limited to one; reference C builds and seeded experiments use one process. No GPU, paid service, external user data or credentials were added.

- Python 3.14.7, NumPy 2.5.4, SciPy 1.18.1, pytest 9.2.0: full tests run without Tk; its module is skipped explicitly.
- Python 3.12.3 with the same NumPy/SciPy/pytest versions: full tests run under `xvfb-run`, including actual Tk worker/event-loop, snapshot, error-recovery and JSON-saving checks. Sandbox display restrictions required running the virtual display outside the filesystem/network sandbox; there was no change to the user's display.
- A wheel was installed into a fresh environment. From `/tmp`, imports resolved to site-packages and the installed `randomness-suite` command produced valid JSON and expected decisions.
- The source archive contains the four data vectors, fixture JSON, tests, tools, scientific/provenance notes and original license. Tests were run from the extracted archive, outside the original checkout.

Final candidate `2.0.1.dev0` checks:

| Check | Result |
| --- | --- |
| Python 3.12.3, `xvfb-run -a python -m pytest -q` | 311 passed in 26.65 s, no skips |
| Python 3.14.7, `python -m pytest -q` | 308 passed, 1 skipped Tk module in 23.65 s |
| `python -m build --no-isolation` | Source archive and wheel built successfully |
| Fresh wheel environment, working directory outside checkout | site-packages import, installed CLI JSON and 2.0.1.dev0 metadata/report version verified |

The exact seeded timing and runtime versions are stored in `validation/seeded-v1.json`. Build outputs were checked locally and are not checked into Git.

## Remaining limits and publication decisions

- Clarify the inherited Google/AngularJS license notice and source/ownership of additions whose original history was not preserved. The notice has not been removed or replaced; nobody has been contacted on the user's behalf.
- Python 3.10/3.11/3.13, Windows and macOS were not executed here. Declared minimum dependency combinations were not exercised. No remote CI result is claimed; the preserved historical README's CI statement is not current evidence.
- Billion-bit universal-test regimes were checked through threshold selection only. Large-file memory scalability, cancellation, full power studies, distribution-wide calibration and all source models remain unvalidated.
- The supported desktop is `Main`; legacy `OLD_Main`/`GUI` compatibility paths are not release-quality UI claims. Tk rendering was exercised under a virtual display, not manually audited across desktops.
- A final maintainer review should reconcile changes into the existing public fork and approve release. Do not make the backup a competing public project. No merge, public push, visibility change or deletion has occurred.
