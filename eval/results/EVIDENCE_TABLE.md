# Empirical Evaluation: 3-Way Ablation & 10-Hunch Graveyard

## 1. Multi-Seed 3-Way Ablation (5 Independent Seeds, 12-Trial Budget Each)

| Research Arm | Mean Train Excess (bps) | Mean Held-Out Excess (bps) | Mean Held-Out Win Rate vs B&H |
| --- | ---: | ---: | ---: |
| `unrefereed_greedy_12` (No Referee) | +24.8 bps | +26.4 bps | 53.3% |
| `refereed_random_12` (Random + Referee) | -382.8 bps | -116.0 bps | 50.0% |
| `refereed_argon_diagnostic_12` (Offline Reproducible Policy) | +5.6 bps | +148.2 bps | 55.0% |
| `refereed_gemini_4_argon_live_12` (Live `gemini-4-argon` API, 12 Trials) | +68.8 bps | +148.2 bps | 55.0% |

## 2. The 10-Hunch Graveyard (Cumulative Trial Ledger Deflation)

| ID | Hunch | K_eff | Train Excess | Held-Out Excess | W/L/T vs B&H | Raw p | Adjusted p_adj | DSR | Verdict |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| H01 | H01: Naive 3-Bar 0.8σ Dip Buy (No Cost Filter) | 2.00 | -18 bps | -472 bps | 12W/28L/0T | 0.0166 | 0.0329 | 0.000 | **DOES_NOT_SURVIVE** |
| H02 | H02: Tight 4-Bar 1.0σ Dip Churn | 2.43 | -88 bps | -292 bps | 13W/27L/0T | 0.0385 | 0.0910 | 0.000 | **DOES_NOT_SURVIVE** |
| H03 | H03: Unfiltered 6-Bar 1.1σ Breakout | 3.00 | -53 bps | -467 bps | 13W/27L/0T | 0.0385 | 0.1109 | 0.000 | **DOES_NOT_SURVIVE** |
| H04 | H04: Loose Volatility Stand-Down (Max Vol 450 bps) | 3.40 | -657 bps | -910 bps | 9W/31L/0T | 0.0007 | 0.0023 | 0.000 | **DOES_NOT_SURVIVE** |
| H05 | H05: Over-Tight 50 bps Trailing Breakout | 3.65 | +252 bps | -453 bps | 17W/23L/0T | 0.4296 | 0.8713 | 0.000 | **DOES_NOT_SURVIVE** |
| H06 | H06: Moderate 8-Bar 1.4σ Reversion (1.3x Cost Gate) | 3.89 | +152 bps | -320 bps | 16W/24L/0T | 0.2682 | 0.7028 | 0.000 | **DOES_NOT_SURVIVE** |
| H07 | H07: Extreme 3.3σ Tail Reversion (Rare Signal -> Underpowered) | 4.00 | -16 bps | -325 bps | 5W/7L/0T | 0.7744 | 0.9974 | 0.014 | **UNDERPOWERED** |
| H08 | H08: High-Threshold 2.4σ Breakout (2.2x Cost Gate) | 4.11 | -48 bps | -190 bps | 18W/22L/0T | 0.6358 | 0.9842 | 0.000 | **DOES_NOT_SURVIVE** |
| H09 | H09: Conservative Cash Stand-Down (Max Vol 140 bps, 2.0x Cost Gate) | 4.28 | +3 bps | -525 bps | 12W/28L/0T | 0.0166 | 0.0691 | 0.000 | **DOES_NOT_SURVIVE** |
| H10 | H10: Argon-Refined 12-Bar 1.65σ Cost-Gated Log Reversion (2.1x Cost Gate) | 4.38 | +34 bps | +912 bps | 16W/1L/0T | 0.0003 | 0.0012 | 0.999 | **SURVIVES** |
