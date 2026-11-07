# 10-Hunch Graveyard & Statistical Deflation

To prevent multiple-testing data-mining (where testing dozens of strategies guarantees one will look good by pure luck), the Referee calculates the Effective Independent Trials ($K_{eff}$) using the correlation matrix of trial returns.

### The Mathematics
- **$K_{eff}$:** Eigenvalue variance of the $N \times M$ trial excess-return correlation matrix (Bailey & López de Prado / Šidák).
- **Trial-Adjusted p-value ($p_{adj}$):** $1 - (1 - p_{raw})^{K_{eff}}$
- **Deflated Sharpe Ratio (DSR):** The probability that the true Sharpe ratio exceeds 0, adjusted for variance and $K_{eff}$.

### The 10-Hunch Graveyard Data
Out of 10 logical hypotheses tested by Gemini 4 Argon, 9 were systematically rejected by the Referee. Only H10 survived the mathematical gate.

| ID  | Hunch Type | $K_{eff}$ | Train Excess | Held-Out Excess | W/L/T | Raw p ($p_{raw}$) | Adjusted p ($p_{adj}$) | DSR | Verdict |
|-----|------------|-----------|--------------|-----------------|-------|-------------------|------------------------|-----|---------|
| H01 | Naive Mom. | 1.05      | -412 bps     | -102 bps        | 6/11  | 0.8320            | 0.8510                 | 0.12| REJECT  |
| H04 | RSI MeanRev| 2.15      | +110 bps     | -50 bps         | 8/9   | 0.2100            | 0.3980                 | 0.45| REJECT  |
| H07 | Vol Break. | 3.80      | +204 bps     | +15 bps         | 10/7  | 0.0800            | 0.2714                 | 0.76| UNDERPOW|
| **H10** | **Cost-Gated Reversion** | **4.38** | **+1210 bps**| **+912 bps** | **16/1** | **0.0003** | **0.0012** | **0.999** | **SURVIVES** |

*Note: H10's adjusted p-value (0.0012) easily clears the strict 0.05 threshold despite the heavy multiple-testing penalty.*
