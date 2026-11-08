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


---

## 🛑 BOSS-LEVEL ATTACKS (Round 2 Escalation)
If a judge pushes past your initial defenses, they will use these advanced institutional critiques. Use these exact responses to prove you understand market microstructure.

### Advanced Attack 1: The "Mona Lisa" Chart Leakage & Gradient Descent
**The Judge:** *"Stripping axes doesn't matter. LLMs have memorized the 2021 Bitcoin run and the 2020 COVID crash. They recognize the fractal geometry. Plus, your 'direction-agnostic feedback' is just a loss function. You built a slow gradient descent that will just overfit the parameters anyway."*

**The Defense:** 
> "That would be true if we were feeding it raw historical snapshots, but we aren't. Our training pipeline feeds the LLM **synthetic, rebased windows where 50% of the paths are inverted**. It is mathematically impossible for the LLM to 'recognize' a historical fractal because half of them are printed upside down. As for gradient descent—yes, we are optimizing, but a strict **12-trial budget** is far too small for an LLM to blindly walk a gradient to an overfit without blowing the cryptographic ledger budget. It forces the LLM to use zero-shot reasoning rather than brute-force iteration."

### Advanced Attack 2: Endogenous Market Impact
**The Judge:** *"Random slippage is amateur hour. Slippage is endogenous—if your LLM finds a breakout, liquidity vanishes. Also, assuming a fill just because the high/low touched your price is a lethal look-ahead bias."*

**The Defense:** 
> "We completely concede that we are not modeling full Limit Order Book (LOB) queue position—doing so requires tick-level Level 3 data which isn't feasible for a two-day hackathon. However, our risk gate explicitly defends against this by enforcing a massive **250 bps round-trip cost hurdle**. We assume the worst-case endogenous impact. If a strategy relies on micro-structure queue priority to be profitable, our cost hurdle kills it instantly. Moving to true LOB market impact is exactly why our Roadmap (Slide 6) lists a Live Venue FIX Bridge."

### Advanced Attack 3: The Covariance Matrix Hack
**The Judge:** *"K_eff relies on the covariance matrix. If the LLM generates 11 highly correlated garbage strategies, and 1 completely orthogonal bizarre strategy that gets lucky, K_eff won't penalize the 12th strategy because it's orthogonal to the failures. You just gave the LLM a free lottery ticket."*

**The Defense:** 
> "That is a fantastic point, and it's exactly why we don't just rely on K_eff; we pass it into the **Deflated Sharpe Ratio (DSR)**. If the LLM generates a lucky, orthogonal outlier, that strategy's return distribution will almost certainly exhibit extreme non-normality (high variance, negative skewness, or fat tails). DSR explicitly incorporates skewness and kurtosis. The 'lucky outlier' gets crushed by the DSR penalty and fails the final verdict gate."
