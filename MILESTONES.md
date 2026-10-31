# Release-readiness work checkpoints

1. Verify access, heads and source scope; reproduce baseline failures. Completed: isolated branch, 279 baseline passes, 3 failures and 18 errors caused by missing constants; GUI module unavailable in the first interpreter.
2. Restore independently sourced fixtures and rebuild the NIST oracle. Completed: four million-bit constants with digests; fresh C output and source hashes reproduce the archived fixture exactly; restored baseline 300 passed, one skipped.
3. Refine correctness and preservation contracts. Completed: decimal histogram-boundary fix and input/report alias protection with regressions. Existing statistical implementations remain subject to the documented asymptotic limitations.
4. Run bounded seeded diagnostics, clean distribution installs and GUI checks. Completed: bounded 64-sequence experiment and 9,472 independent C template comparisons; final test totals in VALIDATION.md.
5. Prepare a private review branch/PR and state release blockers. No publication, merge or visibility change is authorized by this checkpoint.
