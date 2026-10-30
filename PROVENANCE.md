# Provenance and release review

## Repository lineage

The private preservation snapshot was verified at `9681a825b2b6d8318d9e6627232d652833d97712`. Its original development history was not imported. The public user fork [jaykobdetar/randomness_testsuite](https://github.com/jaykobdetar/randomness_testsuite) was verified at `01af6c3b1c6cf46f8cda9c993ef7d6ffa2542a63`; [stevenang/randomness_testsuite](https://github.com/stevenang/randomness_testsuite) at `428f1036b6436fa90896a496528c4f9174befd6d`. These are review anchors, not permanently current branch claims.

The project continues that upstream Python implementation. The private snapshot contains substantial rewritten mathematics, strict input handling, structured reports, CLI/GUI and tests. Absence of its original history means the authorship and source of every local addition cannot be reconstructed from this repository alone. The preservation documentation described AI-assisted work; tests establish behavior, not authorship or license ownership.

## Existing license: clarification outstanding

`LICENSE` is retained byte for byte. It matches the upstream repository's license at the verified commit: SHA-256 `f4fdecb45a48f627ba1134542bb14309fc868e64b14a0d1343d75f6e7d8ad444`. It contains the MIT terms and a Google/AngularJS copyright notice dated 2010–2019. That unusual notice is inherited, not introduced by this audit. Do not replace it with a new author notice or assume that its provenance is resolved. Before public release, establish the upstream licensing intent and provenance of local additions with the owner/maintainers. No maintainer contact has been made and no permission has been inferred from unrelated projects.

The upstream commit [b63bf639c051b33a8dc0397702969c9c56751508](https://github.com/stevenang/randomness_testsuite/commit/b63bf639c051b33a8dc0397702969c9c56751508), dated 2019-12-12 03:36:10 UTC, adds `LICENSE` with this same Google/AngularJS notice. The commit diff and timestamp were checked during draft review. This establishes the notice's upstream inheritance; it does not establish copyright ownership, explain why that notice was used, or resolve the provenance of later additions.

This is a factual provenance finding, not legal advice or a finding that the code is unlicensed.

## NIST fixtures

`data/data.e`, `data/data.pi`, `data/data.sqrt2`, and `data/data.sqrt3` are fresh copies of the first million normalized bits of the corresponding files in the official STS 2.1.2 archive. They are public mathematical constants, not user measurements or historical experiment evidence. `data/provenance.json` records the download URL, archive digest, original-file digests, bitstream digests and transformation. All four archived reference-result vectors were reproduced by a fresh C build; the source hashes and values match the saved JSON.

NIST's [distribution page](https://csrc.nist.gov/projects/random-bit-generation/documentation-and-software) describes its government-developed software as public domain and experimental, gives no quality or reliability guarantee, and requests acknowledgment. We acknowledge NIST as the reference software and fixture source. No C sources or compiled reference binary are redistributed here. The downloaded distribution contains third-party implementation material (including FFT code); its government notice must not be generalized to erase third-party notices.

## Canonical destination

Keep development private until review. Reconcile reviewed changes into the existing public user fork, preserving its GitHub fork relationship and upstream attribution, rather than publishing a competing backup repository. The private PR is a review artifact; it does not authorize a merge, release, visibility change or deletion.
