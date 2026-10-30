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
