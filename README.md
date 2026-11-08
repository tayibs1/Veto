# Veto. 
**Let the AI propose. Never let it authorise.**

[![AgentVerse Finance Track](https://img.shields.io/badge/Track-Finance-blue)](https://agentverse.com)
[![Model](https://img.shields.io/badge/Model-Gemini_4_Argon-0A84FF)](https://deepmind.google/technologies/gemini/)

*AgentVerse 2026 Finance Track Submission (Jane Street & Google DeepMind)*

<img width="2848" height="1800" alt="image" src="https://github.com/user-attachments/assets/80782950-e823-48e2-9bba-83d660428eca" />

Demo Link: https://youtu.be/aqG9N3me-rg




## The Problem
**Named User:** Quantitative Risk Officers & Execution Traders at institutional hedge funds.

LLMs are pathological optimizers. If you give an AI agent access to historical market data and ask it to find a trading strategy, it will overfit, data-mine, and hallucinate "Alpha" by picking the one run out of 1,000 that got lucky. Hedge funds cannot let AI anywhere near real capital because they cannot trust its math, and they cannot trace its reasoning.

## The Solution: Veto.
Veto is a mathematical circuit-breaker. It treats the AI (Gemini 4 Argon) as a creative researcher, but forces it to submit every idea to a **100% deterministic, zero-LLM Python Referee**.

1. **Multimodal Intake:** You give Gemini 4 Argon a candlestick chart and a text hunch. It translates this into a strict, frozen JSON specification.
2. **The K_eff Penalty:** The AI is given a strict 12-trial budget to test its parameters. Every guess is recorded on a **SHA-256 Hash-Chained Ledger**. We penalize the AI for multiple-testing by calculating the average pairwise correlation of trial returns (*Effective Independent Trials, `K_eff`*).
3. **The Verdict:** The system deflates the AI's p-value (`p_adj`) using Bailey & López de Prado's Deflated Sharpe Ratio. If the AI just got lucky, it is mathematically rejected. 
4. **Zero-LLM Execution:** The surviving strategy is executed on unseen market data by pure, lightning-fast Python. The LLM never sees the live data, and never makes a trade.

---

## 🔒 Mandatory Judging Criteria & Risk Controls

### 1. What the Agent Does Alone
*   **Gemini 4 Argon** is permitted to read charts and text to draft a `HunchSpec` JSON.
*   **Gemini 4 Argon** is permitted to read *direction-agnostic* diagnostics (like fee drag) on training data to propose up to 12 parameter refinements.
*   **Models Used:** `gemini-4-argon` (Lead reasoning, multimodal intake, and research loop).

### 2. What Requires Human Approval (Risk Controls)
*   **Spec Lock:** A human must review the AI's translated JSON and click *Confirm & Lock* before it is hashed into the immutable ledger.
*   **Holdout Sign-Off:** The AI cannot see unseen market data. A human must explicitly sign off on a locked candidate to unlock the one-shot holdout evaluation.
*   **Paper-Order Gate:** Before any paper trade is executed, the deterministic Python risk gate enforces a 100% cash cap, a 2500 bps maximum drawdown breaker, and a 250 bps round-trip cost limit. A human can toggle the Kill Switch at any time.

### 3. Separation of Powers & Data Privacy
No user financial records or account details ever leave the device. Gemini 4 Argon is restricted strictly to strategy ideation on the `Interactions API`. **100% of arithmetic, execution, and statistical grading is done by pure Python locally.**

---

## 📊 Empirical Evidence & Ablation Study

We did not train Veto on a historical dataset (which causes look-ahead bias). We trained it on synthetic, 50%-inverted, high-fee hostile market windows, and then ran the **Official AgentVerse 60-Case Hidden Challenge** (`bench.py challenge --pack mixed`).

**Challenge Results (0 Provenance Warnings, 0 Leakage):**
*   **Cashflow & Transactions:** 100% Accuracy (Cycle Detection F1 = 1.0)
*   **Markets:** 20/20 unseen paths successfully navigated the Paper-Order Risk Gate in < 5 seconds.

**5-Seed Multi-Arm Ablation Study (Offline Reproducible vs. Live Gemini 4 Argon API):**
| Agent Architecture | Engine / Mode | Mean Train Excess | Mean Holdout Excess | Win Rate vs B&H | Multiple-Testing Control |
| :--- | :--- | ---: | ---: | ---: | :--- |
| 1. Unrefereed Greedy (No Gate) | Random Churn (No Referee) | +24.8 bps | +26.4 bps | 53.3% | ❌ None (unpenalized) |
| 2. Refereed Random (No AI) | Random Grammar + Referee | -382.8 bps | -116.0 bps | 50.0% | ✅ Constraints hold |
| 3a. **Refereed Diagnostic (Offline Policy)** | Deterministic Fallback (`ablation_summary.json`) | **+5.6 bps** | **+148.2 bps** | **55.0%** | **✅ Trials charged & deflated** |
| 3b. **Refereed Gemini 4 Argon (Live API, 12 Trials)** | Live `gemini-4-argon` (`live_argon_ablation.json`) | **+68.8 bps** | **+148.2 bps** | **55.0%** | **✅ Live LLM + K_eff deflated** |

**Live interactive checks (`gemini-4-argon`):** an underspecified hunch such as Ambiguous Dip is refused by `grammar.py` (`missing parameters ['hold_bars']`).

**Correction on the holdout seed:** during the build the interactive demo's holdout seed was changed from `10808` to `10290`. On `10290`, the Cost-Gated spec `0260cadd` went 27W/9L and showed SURVIVES. On the original `10808` it went 18W/18L and does not survive. Changing test data can flip a verdict, so we restored `10808` and withdrew the SURVIVES claim. Those five interactive verdicts also reused one set of 36 paths, so they are not independent evidence.

**Reading the live arm:** the live run used 4 trials per seed. Argon's own tweak was selected on 1 of 5 seeds (seed 101: +337 bps, `p_adj` 0.46). On the other 4 the starting rule was selected. No seed was certified.

*Synthetic markets only. Sources: `eval/results/ablation_summary.json` (offline reproducible) and `eval/results/live_argon_ablation.json` (live Gemini 4 Argon API). See `statistics_and_analyses/` for full `K_eff` calculations and the 10-Hunch Graveyard.*

**Honest limits**
*   On the hidden challenge's market paths the strategy went 12W/8L against buy-and-hold (sign-test p = 0.503): not distinguishable from buy-and-hold.
*   Passing defined checks does not validate a product. Synthetic results are not real-world performance. Paper trading only.
*   The bundled chart fixtures are SVG. They are displayed beside the hunch, but only PNG/JPG charts are sent to Argon.
*   The ledger is tamper-evident, not tamper-proof.

## Run It

```bash
pip install google-genai
export GEMINI_API_KEY=your_key   # optional: without it, a labelled offline parser is used
python app/server.py             # http://127.0.0.1:8765
python -m unittest discover -s tests -v
```
