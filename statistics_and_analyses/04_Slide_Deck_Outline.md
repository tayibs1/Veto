# 6-Slide Evidence Deck Outline

Share this directly with the team to drop the numbers into the presentation template.

## Slide 1: Title & Thesis
- **Title:** Veto. — Let the AI propose. Never let it authorise.
- **Thesis:** AI agents make data-mining free. We built a cryptographic, 100% deterministic mathematical gate that stops LLMs from hallucinating alpha and overfitting multiple trials.

## Slide 2: The Architecture (Built & Passing 8/8 Tests)
- **Intake:** Gemini 4 Argon Multimodal (Annotated Chart + Text -> HunchSpec JSON).
- **Enforcement:** Hard Grammar Gate (refuses missing specs) -> SHA-256 Hash-Chained Ledger (enforces 12-trial budget & cumulative K_eff across hunches).
- **Execution:** Zero-LLM, pure-Python integer-pence standard library adapter.

## Slide 3: The 10-Hunch Graveyard & Live Interactive Verdicts (Bailey & López de Prado)
- **10-Hunch Graveyard:** 10 hypotheses tested; 9 rejected, only H10 survives with $K_{eff} = 4.38$, taking raw $p=0.0003$ to $p_{adj}=0.0012$.
- **Live Gemini 4 Argon demo:** Ambiguous Dip is **REFUSED** by the grammar validator (missing `hold_bars`).
- **Correction:** the demo holdout seed was changed during the build and flipped Cost-Gated to SURVIVES. We restored the original seed (18W/18L, does not survive) and withdrew the claim.

## Slide 4: Empirical Ablation (5 Seeds x 12 Trials: Offline Reproducible vs. Live Gemini 4 Argon API)
- **1. Unrefereed Greedy (No Gate, 12 Trials):** +24.8 bps train / +26.4 bps holdout (53.3% win rate, zero multiple-testing control).
- **2. Refereed Random (No AI, 12 Trials):** -382.8 bps train / -116.0 bps holdout (50.0% win rate — constraints crush naive luck).
- **3a. Refereed Diagnostic (Offline Policy, 12 Trials — `ablation_summary.json`):** **+5.6 bps train / +148.2 bps holdout (55.0% win rate)** — 100% bit-for-bit reproducible without an API key.
- **3b. Refereed Gemini 4 Argon (Live API, 12 Trials — `live_argon_ablation.json`):** **+68.8 bps train / +148.2 bps holdout (55.0% win rate)** — live `gemini-4-argon` parameter refinement across all 5 seeds x 12 trials (+584 bps on Seed 101, +205 bps on Seed 303, +369 bps on Seed 404; mean $K_{eff}=2.80$).

## Slide 5: Challenge Mode Performance
- **Hidden Eval:** 40/40 exact checks passed and 20/20 market simulations completed (12W/8L vs buy-and-hold, p = 0.503, not distinguishable — "Veto said no to us too").
- **Metrics:** Cycle Detection F1 = 1.0 (100% Precision/Recall). Zero provenance leakage warnings. 100% immunity to prompt-injection.

## Slide 6: Institutional Roadmap (What's Next)
- Live Venue FIX/WebSocket Bridge (Paper Execution).
- Combinatorial Symmetric Cross-Validation (CSCV) for true PBO (Probability of Backtest Overfitting).
- Multi-Asset Cross-Sectional Equities Grammar.
- Timestamped Git / External Blockchain Ledger Notarization.
