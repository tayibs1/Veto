# Finance project test report

**CHALLENGE (self-serve): hidden mixed cases**

Dataset: 60 cases; seed: None; source: AgentVerse seeded generator v2 (hidden challenge).

Exact checks: **40 passed, 0 failed, 0 execution errors**.
Market simulations completed: **20**. Cases not run: **0**.

Only the configured adapter and defined checks were exercised. A baseline run tests the kit, not your submission.

## Challenge integrity

- Cases were generated in memory after the adapter was fixed; no input or answer file existed during the run.
- Seed commitment (published before scoring): `baadd43bfe79eb21560008f64be4f0974eb80dafe88992a20e8402d7c44b64fe`
- Seed: fresh random; revealed in SEED-REVEAL.txt after this run
- Kit fingerprint: `5c90bf815848f4edd85bb2446e00382a24f003d936b3bad72f297a3b7885dad9` (compare with the organisers' published value)
- Project commit: `b84fa3f3c0c46d8c5fa46ac0be4a228f4b6c91eb`, uncommitted changes: 0
- Provenance review: none flagged.

## Coverage

| Task / scenario family | Pass | Fail | Error | Simulated |
| --- | ---: | ---: | ---: | ---: |
| cashflow / invalid_currency | 3 | 0 | 0 | 0 |
| cashflow / late_income | 4 | 0 | 0 | 0 |
| cashflow / negative_opening | 3 | 0 | 0 | 0 |
| cashflow / regular | 4 | 0 | 0 | 0 |
| cashflow / same_day | 3 | 0 | 0 | 0 |
| cashflow / small_business | 3 | 0 | 0 | 0 |
| markets / falling | 0 | 0 | 0 | 4 |
| markets / flat | 0 | 0 | 0 | 3 |
| markets / jump | 0 | 0 | 0 | 3 |
| markets / regime_change | 0 | 0 | 0 | 3 |
| markets / rising | 0 | 0 | 0 | 4 |
| markets / volatile | 0 | 0 | 0 | 3 |
| transactions / decoy_loops | 3 | 0 | 0 | 0 |
| transactions / duplicate_id | 3 | 0 | 0 | 0 |
| transactions / large_ordinary | 3 | 0 | 0 | 0 |
| transactions / multiple_cycles | 3 | 0 | 0 | 0 |
| transactions / one_cycle | 4 | 0 | 0 | 0 |
| transactions / ordinary | 4 | 0 | 0 | 0 |

## Transaction-cycle evidence

Record precision: 100.0%; recall: 100.0%; F1: 100.0%. False alerts: 0; missed cycle records: 0.
Judge detection by recall and F1, not the pass count: a detector that flags nothing still passes every case with no cycle.
These labels identify planted graph patterns, not actual fraud or regulatory compliance.

## Strategy results after costs

| Case | Final cash | Profit / loss | Buy-and-hold final | Cash baseline | Max drawdown |
| --- | ---: | ---: | ---: | ---: | ---: |
| 301a7292f102f2c7d1a6 | £1,482.54 | £0.00 | £1,766.28 | £1,482.54 | 0.00% |
| 2008214168f16b883ff4 | £4,332.22 | -£375.28 | £3,423.22 | £4,707.50 | 7.97% |
| e60d4874983da2fda2a6 | £8,044.14 | £0.00 | £7,991.70 | £8,044.14 | 0.00% |
| 00cdd0031269d647a818 | £2,811.75 | £0.00 | £2,541.55 | £2,811.75 | 0.00% |
| cea36f96818db103c38e | £1,942.26 | -£178.14 | £2,111.48 | £2,120.40 | 8.40% |
| 8c3feb7d77e3aa869b96 | £1,141.05 | £0.00 | £806.60 | £1,141.05 | 0.00% |
| c96dc1eff6397928428c | £9,998.47 | £0.00 | £14,760.03 | £9,998.47 | 0.00% |
| d3a0b2b7522dd07f0a78 | £1,778.31 | -£254.90 | £1,268.91 | £2,033.21 | 12.53% |
| b7fe0d236d058c3d92f6 | £3,646.59 | £0.00 | £3,627.11 | £3,646.59 | 0.00% |
| 9d279e22016ca36c89e9 | £10,644.54 | £1,569.52 | £7,287.62 | £9,075.02 | 7.40% |
| b8767d20a3434934f2eb | £5,782.71 | -£688.52 | £6,215.55 | £6,471.23 | 10.63% |
| e86acea6152fbc4d0ab5 | £7,599.05 | £6.00 | £9,830.13 | £7,593.05 | 1.30% |
| 1306a88ac857a352479e | £8,244.34 | £0.00 | £12,103.41 | £8,244.34 | 0.00% |
| 001aba02e920c742e6b4 | £6,006.24 | -£1,124.84 | £5,033.12 | £7,131.08 | 15.77% |
| 2263c9ca0aef1d0d6e8c | £6,849.73 | £0.00 | £6,800.77 | £6,849.73 | 0.00% |
| d0c041c52d264b700f02 | £4,694.04 | £0.00 | £4,144.02 | £4,694.04 | 0.00% |
| 3167ea563150f98ca602 | £4,123.89 | -£500.16 | £4,272.27 | £4,624.05 | 10.81% |
| b4cb4af8656dd032a9d2 | £2,220.28 | £0.00 | £1,652.36 | £2,220.28 | 0.00% |
| 2603b2aa86de753fa2d9 | £5,272.39 | £0.00 | £7,918.77 | £5,272.39 | 0.00% |
| 2b7a3c8162d85313cc39 | £4,803.48 | -£79.57 | £4,375.51 | £4,883.05 | 1.62% |

Showing 20 of 20 paths; every result and trade is in case-results.jsonl.
Completing a simulation does not mean the strategy is good. Compare losses, costs, baselines and drawdown. These price paths do not model real market liquidity or predict returns.

**Across 20 paths:** 12 wins, 8 losses, 0 ties vs buy-and-hold; beat cash on 2. Median excess 0.68% of capital; mean max drawdown 3.82%; sign-test p = 0.503.
**Not distinguishable from buy-and-hold on these paths; more paths or a better edge is needed.**

## Next action

Run your actual submission adapter if this was a baseline. Add project-specific checks, then rerun with a fresh seed. Anything outside these checks remains untested.

Hidden challenge run: no input or answer file existed while the adapter ran, and the kit's reference calculations were disabled for it.
