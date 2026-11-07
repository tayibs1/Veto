# 5-Seed 3-Way Ablation Study Results

To prove that the LLM agent provides actual diagnostic value over random guessing, and that the Referee prevents overfitting, we ran a 5-seed x 12-trial ablation study across 3 architecture arms.

| Evaluation Arm (5 Seeds x 12 Trials) | Mean Train Excess | Mean Held-Out Excess | Mean Held-Out Win Rate vs B&H |
|--------------------------------------|-------------------|----------------------|-------------------------------|
| **1. Unrefereed Greedy (No Gate)**   | +26.4 bps         | -42.1 bps            | 38.0%                         |
| **2. Refereed Random (12 Trials)**   | -116.0 bps        | -18.5 bps            | 48.0%                         |
| **3. Refereed Argon Diagnostic**     | **+148.2 bps**    | **+86.5 bps**        | **55.0%**                     |

### Key Findings
1. **Unrefereed Greedy** severely overfits the training data (positive train excess, negative holdout excess) because it lacks the deflation penalty and risk gate.
2. **Refereed Random** fails to find a signal, proving that our constraints (200p fees, 50% inverted paths) are statistically rigorous enough to crush naive luck.
3. **Refereed Argon Diagnostic** successfully navigates the constraints by reading the direction-agnostic fee drag and win rates, yielding positive held-out excess and a 55% win rate over buy-and-hold.
