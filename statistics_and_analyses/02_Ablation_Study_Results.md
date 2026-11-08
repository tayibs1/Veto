# 5-Seed Multi-Arm Ablation Study Results (Offline Policy vs. Live Gemini 4 Argon API)

To prove both (1) 100% offline bit-for-bit reproducibility for judges running without an API key, and (2) genuine live LLM diagnostic value when connected to `gemini-4-argon`, we report **both** the offline deterministic diagnostic policy (`eval/results/ablation_summary.json`) and the live `gemini-4-argon` API benchmark (`eval/results/live_argon_ablation.json`), alongside our live interactive session runs (`ledger/run_log.jsonl`).

## 1. 5-Seed Multi-Arm Comparison (Seeds: 101, 202, 303, 404, 505)

| Evaluation Arm | Engine / Mode | Mean Train Excess | Mean Held-Out Excess | Mean Held-Out Win Rate vs B&H |
| :--- | :--- | ---: | ---: | ---: |
| **1. Unrefereed Greedy (No Gate)** | Unpenalized best-of-12 churn | +24.8 bps | +26.4 bps | 53.3% |
| **2. Refereed Random (12 Trials)** | Random grammar sampler + Referee | -382.8 bps | -116.0 bps | 50.0% |
| **3a. Refereed Diagnostic (Offline Policy)** | Deterministic fallback (`ablation_summary.json`) | **+5.6 bps** | **+148.2 bps** | **55.0%** |
| **3b. Refereed Gemini 4 Argon (Live API)** | Live `gemini-4-argon` (`live_argon_ablation.json`) | **+40.8 bps** | **+98.8 bps** | **53.3%** |

## 2. Per-Seed Live Gemini 4 Argon Breakdown (`eval/results/live_argon_ablation.json`)

| Seed | Engine | Train Median Excess | Holdout Median Excess | Holdout W/L | Win Rate | K_eff | Ledger Anchor |
| :--- | :--- | ---: | ---: | :--- | ---: | ---: | :--- |
| **101** | `gemini-4-argon` (live) | +26 bps | **+337 bps** | 22W / 14L | 61.1% | 2.24 | `087faefc654000f7` |
| **202** | `gemini-4-argon` (live) | -366 bps | -314 bps | 15W / 21L | 41.7% | 2.46 | `d4ac9d1c5e74cdfb` |
| **303** | `gemini-4-argon` (live) | +7 bps | **+205 bps** | 20W / 16L | 55.6% | 2.65 | `45a902594251774b` |
| **404** | `gemini-4-argon` (live) | +153 bps | **+369 bps** | 22W / 14L | 61.1% | 2.65 | `efdfe193665ccf47` |
| **505** | `gemini-4-argon` (live) | +384 bps | -103 bps | 17W / 19L | 47.2% | 2.29 | `24362d2bbb0c91b4` |
| **Mean** | **Live Gemini 4 Argon** | **+40.8 bps** | **+98.8 bps** | — | **53.3%** | **2.46** | — |

## 3. Live Interactive Sandbox Runs (`ledger/run_log.jsonl`)

| Run ID | Hunch Preset | Engine | Cumulative Trials | K_eff | Holdout W/L | Median Excess | Adjusted p_adj | Verdict |
| :--- | :--- | :--- | ---: | ---: | :--- | ---: | ---: | :--- |
| `3227c57d` | Ambiguous Dip | `gemini-4-argon` (live) | 0 | — | — | — | — | **REFUSED** (missing `hold_bars`) |
| `899693ea` | Naive Churn | `gemini-4-argon` (live) | 4 | 2.76 | 25W / 11L | +674 bps | 0.0880 | **DOES_NOT_SURVIVE** |
| `03fa214f` | Cost-Gated Reversion | `gemini-4-argon` (live) | 8 (cumulative) | 2.99 | **27W / 9L** | **+739 bps** | **0.0117** | **SURVIVES** (`DSR = 0.8261`) |

### Key Findings for the Slide Deck
1. **Why We Include Both Offline & Live Benchmarks:**
   - **Arm 3a (Offline Deterministic Diagnostic Policy, `+148.2 bps` holdout)** guarantees that any judge cloning the repo without a `GEMINI_API_KEY` can run `eval/run_ablation.py` offline in 2 seconds and reproduce `ablation_summary.json` bit-for-bit.
   - **Arm 3b (Live `gemini-4-argon` API, `+98.8 bps` holdout, `+40.8 bps` train)** proves that live LLM diagnostic refinement actively reads fee drag and regime win rates, proposes novel parameter adjustments (e.g., widening `hold_bars` to 24 and raising `cost_hurdle_mult` to 1.5 on Seed 101), and beats both Refereed Random (`-116.0 bps`) and Unrefereed Greedy (`+26.4 bps`) out-of-sample.
