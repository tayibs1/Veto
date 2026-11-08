# 5-Seed x 12-Trial Multi-Arm Ablation Study Results (Offline Policy vs. Live Gemini 4 Argon API)

To prove both (1) 100% offline bit-for-bit reproducibility for judges running without an API key, and (2) genuine live LLM diagnostic value when connected to `gemini-4-argon` across the full **12-trial budget**, we report **both** the offline deterministic diagnostic policy (`eval/results/ablation_summary.json`) and the live `gemini-4-argon` 12-trial API benchmark (`eval/results/live_argon_ablation.json`).

## 1. 5-Seed x 12-Trial Multi-Arm Comparison (Seeds: 101, 202, 303, 404, 505)

| Evaluation Arm (5 Seeds x 12 Trials) | Engine / Mode | Mean Train Excess | Mean Held-Out Excess | Mean Held-Out Win Rate vs B&H |
| :--- | :--- | ---: | ---: | ---: |
| **1. Unrefereed Greedy (No Gate)** | Unpenalized best-of-12 churn | +24.8 bps | +26.4 bps | 53.3% |
| **2. Refereed Random (12 Trials)** | Random grammar sampler + Referee | -382.8 bps | -116.0 bps | 50.0% |
| **3a. Refereed Diagnostic (Offline Policy, 12 Trials)** | Deterministic fallback (`ablation_summary.json`) | **+5.6 bps** | **+148.2 bps** | **55.0%** |
| **3b. Refereed Gemini 4 Argon (Live API, 12 Trials)** | Live `gemini-4-argon` (`live_argon_ablation.json`) | **+68.8 bps** | **+148.2 bps** | **55.0%** |

## 2. Per-Seed Live Gemini 4 Argon Breakdown (12 Trials / Seed — `eval/results/live_argon_ablation.json`)

| Seed | Engine | Trials Run | Train Median Excess | Holdout Median Excess | Holdout W/L | Win Rate | K_eff | Ledger Anchor |
| :--- | :--- | ---: | ---: | ---: | :--- | ---: | ---: | :--- |
| **101** | `gemini-4-argon` (live) | 12 | +26 bps | **+584 bps** | 25W / 11L | 69.4% | 2.66 | `3a3cf5b95f697a53` |
| **202** | `gemini-4-argon` (live) | 12 | -393 bps | -314 bps | 15W / 21L | 41.7% | 2.63 | `6778584e0e4ec250` |
| **303** | `gemini-4-argon` (live) | 12 | -2 bps | **+205 bps** | 20W / 16L | 55.6% | 3.00 | `37249059f87e18df` |
| **404** | `gemini-4-argon` (live) | 12 | +263 bps | **+369 bps** | 22W / 14L | 61.1% | 3.10 | `bfa623eb490d271a` |
| **505** | `gemini-4-argon` (live) | 12 | +450 bps | -103 bps | 17W / 19L | 47.2% | 2.60 | `1ac5fb3bc7997ca8` |
| **Mean** | **Live Gemini 4 Argon** | **12** | **+68.8 bps** | **+148.2 bps** | — | **55.0%** | **2.80** | — |

## 3. Interactive Sandbox Runs

**Correction on the holdout seed:** during the build the interactive demo's holdout seed was changed from `10808` to `10290`. On `10290`, the Cost-Gated spec `0260cadd` went 27W/9L and showed SURVIVES. On the original `10808` it went 18W/18L and does not survive. Changing test data can flip a verdict, so we restored `10808` and withdrew the SURVIVES claim. Those five interactive verdicts also reused one set of 36 paths, so they are not independent evidence.

### Key Findings for the Slide Deck
1. **Why We Include Both Offline & Live 12-Trial Benchmarks:**
   - **Arm 3a (Offline Deterministic Diagnostic Policy, `+5.6 bps` train / `+148.2 bps` holdout)** guarantees that any judge cloning the repo without a `GEMINI_API_KEY` can run `eval/run_ablation.py` offline in 2 seconds and reproduce `ablation_summary.json` bit-for-bit.
   - **Arm 3b (Live `gemini-4-argon` API, 12 trials per seed, `+148.2 bps` holdout, `+68.8 bps` train)** selected the starting rule (`0260cadd`) on all 5 seeds, so its per-seed holdout results match the offline policy. Argon's refinements did not beat the original rule, this run shows no added value from them, and no seed was certified (best `p_adj` 0.0749).
