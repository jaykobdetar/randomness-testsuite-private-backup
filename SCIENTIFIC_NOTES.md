# Statistical scope and operating profile

The null hypothesis is a sequence of independent Bernoulli(1/2) bits. These are departure diagnostics, not entropy estimators or cryptographic certification. A p-value is a tail probability under the model, not the probability that the model is true. Select tests, parameters and alpha before examining outcomes. Dependent channels can reject by chance; there is no pooled score.

The reference is [NIST SP 800-22 Rev. 1a (April 2010)](https://doi.org/10.6028/NIST.SP.800-22r1a), sections 2–4, and [STS 2.1.2](https://csrc.nist.gov/projects/random-bit-generation/documentation-and-software). NIST's [revision decision](https://www.nist.gov/news-events/news/2022/04/decision-revise-nist-sp-800-22-rev-1a) identifies limitations including cryptographic-generator assessment and two-level testing. This implementation fixes one documented profile; it is not a claim to implement a later revision.

## Profile `conservative-sp800-22-v1`

`n` is the complete input length. Every complete block is used; remainders are reported. Length gates are operating recommendations, not guarantees of finite-sample calibration. The lower-level classes allow shorter educational examples and retain a fixed 0.01 threshold; use `Suite.run_suite` for applicability reporting and configurable alpha.

| Test ID | Length requirement and parameters |
| --- | --- |
| frequency | n >= 100 |
| block_frequency | n >= 100; M=max(20, floor(n/100)+1), N=floor(n/M) |
| runs | n >= 100; additionally abs(proportion of ones - 0.5) < 2/sqrt(n) |
| longest_run | n >= 128; M=8 below 6272, M=128 below 750000, otherwise M=10000 |
| matrix_rank | >=38 complete 32x32 matrices (38912 bits) |
| spectral | Exactly 1000000 bits, following NIST's 2010 software guidance |
| non_overlapping_template | n >= 1000000; all 148 unbordered m=9 words, eight blocks |
| overlapping_template | n >= 1000000; all-one m=9 template, M=1032 |
| universal | n >= 387840; NIST length table chooses L=6 through 16; Q=10*2^L |
| linear_complexity | n >= 1000000; M=500 |
| serial | n >= 524288; m=16, two channels |
| approximate_entropy | n >= 65536; m=10 |
| cusum_forward, cusum_backward | n >= 100 |
| random_excursions, random_excursions_variant | n >= 1000000 and J >= ceil(max(500, .005*sqrt(n))); 8 and 18 states |

There are 15 conventional families, represented by 16 IDs because cumulative sums has two directions, and up to 188 channels. `not_applicable` and `error` contain no p-values; neither is a statistical rejection. The runs prerequisite deliberately reports inapplicability instead of treating the legacy zero sentinel as an evaluated p-value. Excursions count a final incomplete walk as a cycle, but do not add a fictitious empty cycle when the last observed step already returns to zero.

## Deliberate differences from the official C reference

- Longest runs use finite-block counts from an integer recurrence, rather than rounded probability tables. Independent state propagation verifies M=128 and M=10000; exhaustive enumeration verifies M=8.
- Overlapping templates use finite-block state probabilities for counts 0,1,2,3,4,>=5. These differ from the compound-Poisson approximation actually used by STS 2.1.2. Exhaustive small-block enumeration and the revised NIST probability table provide checks.
- Linear complexity uses limiting masses (1/96,1/32,1/8,1/2,1/4,1/16,1/48), replacing rounded cells including C's 0.01047 first cell. These are limiting probabilities, not exact finite-M probabilities. Berlekamp–Massey is checked against exhaustive recurrence search on small strings.
- Cumulative sums uses mathematical floor bounds and stable normal tails. STS truncation and its older CDF approximation can produce different short-example answers. Direct formula tests and million-bit comparisons have explicit tolerances.
- Matrix rank uses finite-dimensional GF(2) probabilities and exact binary elimination. Rectangular low-level calls require their own calibration assessment.
- At one million bits the block-frequency profile uses M=10001. The reference runner explicitly configures C to match; Appendix B's default M=128 is a different experiment.

More accurate cell probabilities do not make the chi-square or normal tail approximations exact. Tests of observed counts, reference p-values and mathematical oracles establish different kinds of evidence; they should not be conflated. Small published examples contain inconsistencies identified in the individual tests. The test expectations are not an endorsement of every printed number in the publication.

## Batch interpretation

Only structurally valid, homogeneous reports are grouped, by family and channel separately. Duplicate test rows, missing/extra evaluated channels, invalid p-values and inconsistent decisions are rejected before aggregation.

Starting with `2.0.1.dev1`, automatic second-level inference is restricted to schema 1 reports from the current suite version, profile `conservative-sp800-22-v1`, exactly 1,000,000 bits, alpha=0.01, and the profile's fixed parameters. Duplicate input hashes disable inference. Runs and both excursion families are descriptive-only because calibration after their data-dependent applicability selection is not established here. All other lengths/settings retain descriptive counts, proportions and histograms; inferential fields are `null`, with `inference_supported=false` and an explicit reason. This is a conservative operating restriction, not a new calibration theorem. A million-bit experiment alone does not validate every tail probability or batch size.

The reason for restricting short sequences is concrete: for monobit at n=100 under independent fair bits, the p-value has discrete support and the [0.7,0.8) histogram cell is impossible. Its actual rejection probability at nominal alpha=.01 is approximately .012033. Increasing the number of such sequences does not make their null p-values uniform or their rejection probability exactly .01.

The low-level `summarize_p_values` helper now defaults to descriptive-only output because bare p-values carry no length, test or sampling context. Its explicit `assume_calibrated=True` option retains the mathematical diagnostics for callers who assert the independent uniform-p-value and nominal-alpha assumptions. That flag is an assumption, not validation; the ordinary CLI batch path uses the stricter report-aware checks instead.

For the supported approximate regime, Sequences must come independently from one stationary source; separate hashes, disjoint segments and a deterministic seed do not establish independence. The ten-bin uniformity diagnostic uses floor(10*p), capped at bin 9 for p=1, and requires at least 55 eligible values. Its threshold is 0.0001. The non-rejection proportion uses the NIST three-sigma approximation; an additional one-sided exact binomial tail measures excess rejections under the nominal alpha. These diagnostics inherit individual-test calibration and selection limitations, especially channels conditioned on applicability.

Some rejection proportions and uniformity tests can reject across 188 dependent channels by chance. Do not change a generator, sample selection or formulas simply to improve these outputs. The checked-in seeded experiment is a small reproducible diagnostic, not a power study or proof of calibration. There is no multiplicity-adjusted overall decision.

## Practical limits

Inputs and reports are held in memory. Packed input expands to eight ASCII characters per byte; walk and FFT arrays add overhead. Use bounded files and explicit sequence splitting. Very large universal-test thresholds are unit-tested for selection, not executed at billion-bit scale. Subnormal tails may underflow to zero. GUI computations use a worker thread but do not offer cancellation. Source reports include absolute input paths; inspect them before sharing.

Physical measurements require a source model, collection protocol, independence assessment and separate entropy-source analysis. Those tasks are outside this package.
