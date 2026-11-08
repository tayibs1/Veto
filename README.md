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
2. **The K_eff Penalty:** The AI is given a strict 12-trial budget to test its parameters. Every guess is recorded on a **SHA-256 Hash-Chained Ledger**. We penalize the AI for multiple-testing by calculating the average pairwise correlation of trial returns (*Effective Independent Trials, $K_{eff}$*).
3. **The Verdict:** The system deflates the AI's p-value ($p_{adj}$) using Bailey & López de Prado's Deflated Sharpe Ratio. If the AI just got lucky, it is mathematically rejected. 
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

**5-Seed x 12-Trial Ablation Study:**
| Agent Architecture | Mean Train Excess | Mean Holdout Excess | Win Rate vs B&H | Multiple-Testing Control |
| :--- | ---: | ---: | ---: | :--- |
| Unrefereed Greedy (No Gate) | +24.8 bps | +26.4 bps | 53.3% | ❌ None |
| Refereed Random (No AI) | -382.8 bps | -116.0 bps | 50.0% | ✅ Constraints hold |
| **Refereed Argon (Veto)** | **+5.6 bps** | **+148.2 bps** | **55.0%** | **✅ Trials charged and deflated** |

*Synthetic markets only. Source: `eval/results/ablation_summary.json`. See `statistics_and_analyses/` for full $K_{eff}$ calculations and the 10-Hunch Graveyard.*

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
