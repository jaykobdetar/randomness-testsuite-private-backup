# Follow-up validation — 2026-10-30

Candidate `2.0.1.dev1` adds four bounded corrective changes after review of the saved `2.0.1.dev0` evidence. This report supplements, rather than replaces, [VALIDATION.md](VALIDATION.md). The historical reference runs, fixture files, saved result JSON and inherited license remain unchanged. No statistical kernels were altered in this follow-up.

## Corrected behavior

1. **Conservative second-level inference.** Reports outside the current schema/version/profile, exact million-bit length, alpha=.01 and fixed parameters receive descriptive counts, proportions and histograms with null inferential fields and reasons. Duplicate input hashes also suppress inference. Runs and both excursion families remain descriptive-only because calibration after their data-dependent applicability selection is not established. This does not prove calibration in the retained operating regime. Raw `summarize_p_values` calls are descriptive by default; `assume_calibrated=True` is an explicit caller assertion, not an automated check.
2. **GUI source protection.** The supported `Main` GUI and CLI share path-alias validation. The GUI checks the source recorded in its report snapshot, not current input controls. Same paths, symlinks and hard links cannot accidentally replace the capture with JSON. Concurrent filesystem mutation is outside this protection.
3. **Batch structure validation.** Duplicate test rows, unknown statuses/IDs, absent or extra evaluated channels, invalid p-values, inconsistent decisions and mismatched report/result lengths or alpha fail before aggregation. Unevaluated rows cannot carry p-values. Hash formatting and required report containers are checked. This validates the supplied structure, not authenticity of user-created reports or independence of their underlying inputs. A JSON parser that has already discarded duplicate object keys is outside this API's visibility.
4. **Reference comparator validation.** Both complete p-value vectors must be nonempty, equal-length, finite and within [0,1] before tolerance comparison. JSON output also disallows NaN. This closes the case where `abs(NaN - expected) > tolerance` evaluates false. No C experiments were rerun.

## Focused evidence

The exact 101-outcome binomial enumeration of fair 100-bit monobit inputs confirms that the [0.7,0.8) p-value bin is empty, and the nominal .01 rejection rate is approximately .012033. The regression verifies the empty bin and that such batches cannot produce second-level inference. A 55-sequence count alone does not resolve short-input discreteness.

All tests use synthetic fixtures and temporary files. Thread limits were `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`, bytecode writing was disabled, and pytest's cache provider was disabled.

| Check | Result |
| --- | --- |
| Python 3.12.3: `python -B -m pytest -q -p no:cacheprovider tests/test_review_refinements.py tests/test_suite.py -k 'not full_profile_handles'` | 144 passed, 4 deselected in 8.37 s |
| Python 3.12.3: `xvfb-run -a python -B -m pytest -q -p no:cacheprovider tests/test_gui.py` | 3 passed in 0.73 s |
| Python 3.14.7: `python -B -m pytest -q -p no:cacheprovider tests/test_review_refinements.py` | 42 passed, 3 skipped in 0.73 s; skipped cases require tkinter |

The GUI alias tests call the actual save method against temporary files without a display; they also verify saving to a distinct destination. The existing GUI tests separately exercise the actual Tk event loop on a temporary virtual display. Batch tests cover supported/unsupported settings, the 54/55 uniformity boundary, duplicate rows and hashes, channel structure and malformed values. Comparator tests inject NaN, infinities and out-of-range values into both sides and verify ordinary tolerance behavior.

The four previously executed million-bit degenerate-sequence tests were deliberately deselected. The four-constant C comparison, 64-sequence experiment and 9,472 template comparison were not repeated. Read-only checks confirmed the saved fixture hashes and summary invariants; all 9,472 retained C values were finite and within range. Their inspected template channel matched the saved JSON.

## Limits and release requirements

The earlier 311-test full run, wheel installation and source-archive validation apply to `2.0.1.dev0`; they are not claimed as full end-to-end checks of this follow-up. Packaging and other platform coverage have not been repeated. The same Python-minimum/dependency, Windows/macOS, large-file, calibration and provenance limitations remain. Conservative gating deliberately withholds some formerly available second-level fields; downstream consumers must accept null values and inspect reasons. Single-sequence p-values and decisions are unchanged.

Keep the repository private during draft review. Clarify the inherited Google/AngularJS notice and provenance of history-less additions before release; no notice was replaced and no maintainer contact was made. Final reconciliation should target the existing public fork after review rather than introduce a competing public backup. Draft-PR approval does not authorize merging or publication.

## Independent-review corrections — candidate 2.0.1.dev2

Focused regressions reproduced two additional API edge cases at PR head `dbf2e48`: non-excursion `cycles`/`minimum_cycles` parameters could escape homogeneity checks and make inference depend on report order; NaN/infinite comparator tolerances could conceal real mismatches. The pre-fix focused selection had 12 failures and one passing control (45 unrelated tests deselected).

The signature now ignores cycle metadata only for excursion families. Inference support is checked against every report, with deterministic combined reasons, rather than only the first. A channel with any `error` or `not_applicable` exclusion is descriptive-only: there is no established calibration for a potentially data-selected surviving subset. Other fully evaluated channels remain eligible. Regression tests exercise both input orders, both exclusion statuses, and unaffected channels.

Reference tolerances must be finite, numeric, nonnegative and not Boolean; zero is supported for exact comparison. Both NaN and infinities now fail explicitly, without changing the default 5.1e-7 tolerance. Existing saved C results were not shown incorrect and remain untouched.

Using the same single-thread, no-bytecode/no-pytest-cache settings documented above:

- Python 3.12.3: `python -B -m pytest -q -p no:cacheprovider tests/test_review_refinements.py tests/test_suite.py -k 'not full_profile_handles'` — **157 passed, 4 deselected in 8.43 s**.
- Python 3.14.7: `python -B -m pytest -q -p no:cacheprovider tests/test_review_refinements.py` — **55 passed, 3 skipped in 0.56s**; the three skips require tkinter.

No full experiments, packaging checks or live GUI tests were repeated for dev2; the GUI code was unchanged. Original fixture and result files and all notices are preserved. `PROVENANCE.md` now records the verified upstream LICENSE addition commit and date while explicitly leaving ownership and later-addition provenance unresolved.


## Final-candidate release validation — exact head 7b80af5

The runtime and packaging candidate **`7b80af587f6e7ed021895b40ea6464f47bca6f07`**, version `2.0.1.dev2`, was archived with `git archive` into an isolated temporary directory. These checks validate that candidate, not the earlier dev0 implementation. This section supersedes the earlier follow-up's statements that full-suite and packaging checks had not been repeated. Historical results above and the saved scientific experiments remain unchanged.

| Exact-candidate check | Result |
| --- | --- |
| Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1, pytest 9.2.0; full archived-checkout suite with Xvfb | **369 passed in 25.01 s**, no skips |
| Python 3.10.22, NumPy 1.24.0, SciPy 1.10.0, pytest 7.0.0; full extracted-source-archive suite with Xvfb | **369 passed in 23.46 s**, no skips |
| Clean build using declared minimum setuptools 68.0.0 on Python 3.12 | Source archive and wheel built successfully |
| Wheel installed in fresh Python 3.10 and 3.12 environments | Imports resolve to site-packages; distribution/report versions equal 2.0.1.dev2; `pip check` succeeds |
| README CLI and Python API examples in both installed environments | Literal, full-constant file/save, selected tests, packed-byte batch/save and Python API examples succeed |
| Nullable-field consumers in both installed environments | Unsupported short batches and synthetic error exclusions preserve null fields/reasons and strict JSON; supported frequency retains eligible inference; uniformity remains null below 55 observations |
| Installed GUI module entrypoint under Xvfb, Python 3.12 | Launches and closes automatically; full suites also execute the live GUI tests |
| Reference/seeded tool `--help` entrypoints | Both succeed without running the experiments |

The Python 3.10 run exercises the declared minimum minor version and the exact declared lower NumPy/SciPy/pytest versions, using an already installed interpreter and wheel-only dependency installs. It does not test the original Python 3.10.0 patch release. The build environment separately exercises setuptools 68.0.0. No system Python or package installation was changed.

Build warnings were limited to setuptools 68's beta notice for `[tool.setuptools]` and deliberately disabled byte compilation. Required data, tests, reference tools, scientific/provenance notes and the original license were verified byte-for-byte in the source archive. Every top-level Python module and the license in the wheel matched the archived candidate. Artifact SHA-256 digests, versions, commands and exact results are in [validation/release-candidate-7b80af5.json](validation/release-candidate-7b80af5.json).

Consumer checks ran outside the checkout using the installed CLI, with all outputs and generated inputs in temporary directories. The actual packed-byte batch example used two synthetic million-bit sequences; short-input and exclusion handling used bounded synthetic fixtures. No external consumer integrations were available; those callers still need to handle nullable fields. The seeded tool stores the same summary directly as JSON and does not format nullable fields as numbers; its existing 64-sequence experiment was not rerun. No C oracle regeneration or 9,472-template experiment was repeated. The offline full suites do include their normal golden-vector assertions.

Tested platform is **Linux x86_64 only**. Windows and macOS remain unvalidated; no desktop portability or platform-support claim is made for them. This candidate has no full-suite runs on Python 3.11/3.13/3.14, other dependency combinations or other architectures. Large-file scaling, distribution-wide calibration and power studies remain outside this evidence. Passing these tests does not establish entropy or cryptographic security.

No corrective runtime change was needed during final validation. Subsequent evidence/documentation additions do not change the tested Python code or pyproject configuration. The repository remains a private draft. License intent and ownership/provenance of additions still require review; upstream inheritance of the notice does not resolve those gates. No upstream contact, merge or publication occurred.
