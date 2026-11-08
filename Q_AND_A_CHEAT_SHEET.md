# Veto. — Q&A Judge Defense Cheat Sheet

**Memorize these responses for the 3-minute Q&A with the Jane Street / DeepMind judges.**
If they attack the architecture, use these exact mathematical and structural defenses.

### Attack 1: Data Leakage / "Hallucinated Alpha"
**The Judge:** *"Gemini's pre-training data includes the whole internet, including historical crypto prices from Binance Vision. Aren't you just testing on data the LLM has already memorized?"*

**The Defense:**
> "That would be true if we fed the time-series data to the LLM, but we don't. The LLM operates completely blind to the market data. We feed it an anonymized chart and text, and it generates a frozen JSON specification. The backtesting is done by our **100% deterministic Python referee**, not the LLM. Furthermore, during the diagnostic loop, we intentionally hide the prices and only feed the LLM **direction-agnostic diagnostics** (like fee drag and win-rate against negative drift). The LLM is mathematically isolated from the time series."

### Attack 2: The "Next-Bar Execution" Delusion
**The Judge:** *"Next-bar execution is retail nonsense. You're simulating unlimited liquidity, which guarantees phantom backtest returns. Where is your market impact model?"*

**The Defense:**
> "We explicitly built our **Paper-Order Risk Gate** to counter the infinite liquidity assumption. Our synthetic training windows inject random adverse rounded slippage (up to 40 bps) and severe fixed fees (up to 200 pence) to heavily penalize high-turnover strategies. Furthermore, our risk gate enforces a 2,500 bps max drawdown breaker and hard position caps. We treat execution hostility as a first-class citizen."

### Attack 3: $K_{eff}$ Trickery & Multiple-Testing
**The Judge:** *"You claim a K_eff of 4.38 for 10 trials. But K_eff is derived from correlation. If the LLM generates 10 highly correlated variations of the same strategy, K_eff stays artificially low, giving you a falsely significant Adjusted p-value."*

**The Defense:**
> "That is exactly why we use Bailey & López de Prado's Eigenvalue Variance method instead of a naive Bonferroni correction. If the LLM just spits out 10 identical moving average crossovers, they *should* be treated as 1 effective trial ($K_{eff} \approx 1$), because no new statistical ground was explored. We only penalize the strategy (higher $K_{eff}$) when the LLM attempts orthogonal, uncorrelated hypotheses. It is the most mathematically rigorous way to measure true data mining without over-penalizing iterative refinement."

### Attack 4: Target Audience / Business Case
**The Judge:** *"No hedge fund Chief Risk Officer is letting a student trader loose with an LLM that writes direct strategy code to a risk gate."*

**The Defense:**
> "We completely agree. That is why our core philosophy is: **'Let the AI propose. Never let it authorise.'** The AI is treated as a junior ideation researcher. The CRO is the human at the end of the line who reviews the immutable SHA-256 ledger of the AI's failed attempts, analyzes the Deflated Sharpe Ratio, and pushes the final approval gate. The AI has zero execution authority."
