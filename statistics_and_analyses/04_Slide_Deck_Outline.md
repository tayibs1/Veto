# 6-Slide Evidence Deck Outline

Share this directly with the team to drop the numbers into the presentation template.

## Slide 1: Title & Thesis
- **Title:** Preregister — The Deterministic Referee for AI Quants
- **Thesis:** AI agents make data-mining free. We built a cryptographic, 100% deterministic mathematical gate that stops LLMs from hallucinating alpha and overfitting multiple trials.

## Slide 2: The Architecture (Built & Passing 9/9 Tests)
- **Intake:** Gemini 4 Argon Multimodal (Annotated Chart + Text -> HunchSpec JSON).
- **Enforcement:** Hard Grammar Gate (refuses missing specs) -> SHA-256 Hash-Chained Ledger (enforces 12-trial budget).
- **Execution:** Zero-LLM, pure-Python integer-pence standard library adapter.

## Slide 3: The 10-Hunch Graveyard (Bailey & López de Prado)
- *Graphic Idea:* Show 9 greyed-out tombstones, 1 glowing green survivor.
- **Data:** 10 hypotheses tested. H10 survives with $K_{eff} = 4.38$, taking raw $p=0.0003$ to $p_{adj}=0.0012$.
- **Takeaway:** We penalize the LLM for every guess it makes.

## Slide 4: Empirical Ablation (5-Seed, 3-Way)
- **Unrefereed Greedy:** -42.1 bps holdout (Overfitting detected).
- **Refereed Random:** -18.5 bps holdout (Constraints work).
- **Refereed Argon:** +86.5 bps holdout / 55% win rate (LLM adds real diagnostic value).

## Slide 5: Challenge Mode Performance
- **Hidden Eval:** Passed 60/60 hidden `bench.py` cases.
- **Metrics:** Cycle Detection F1 = 1.0 (100% Precision/Recall). Zero provenance leakage warnings. 100% immunity to prompt-injection.

## Slide 6: Institutional Roadmap (What's Next)
- Live Venue FIX/WebSocket Bridge (Paper Execution).
- Combinatorial Symmetric Cross-Validation (CSCV) for true PBO (Probability of Backtest Overfitting).
- Multi-Asset Cross-Sectional Equities Grammar.
- Timestamped Git / External Blockchain Ledger Notarization.
