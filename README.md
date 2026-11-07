# Preregister — The Referee for AI Quant Research Agents

**AgentVerse 2026 — Finance Track ("Agents you would let near your own money")**

## 1. The Problem & Named User
- **Who it helps:** A junior quant or student trader testing trading hunches with an AI research agent.
- **The failure mode it prevents:** AI agents make strategy data-mining free—an agent can test dozens of backtest variations in minutes until one looks brilliant by pure luck (multiple-testing bias / p-hacking) or only works before transaction costs.
- **What Preregister does:** Lets a **Gemini 4 Argon** (`gemini-4-argon`) research agent translate multimodal hunches (annotated candlestick chart images + plain English) and iteratively search for strategy refinements on training windows, while a **100% deterministic Python Referee** owns all arithmetic, charges every backtest to a SHA-256 hash-chained trial ledger, enforces a hard 12-trial budget, blocks access to unseen holdout data, and grades the single human-approved candidate on unseen market paths using **Trial-Adjusted Exact Binomial Sign-Test p-values ($p_{\text{adj}}$)** and **Bailey & López de Prado's (2014) Deflated Sharpe Ratio (DSR)**.

## 2. Core Trust Boundary
> **The AI agent proposes and explains. Deterministic Python code does 100% of the maths, enforces the trial budget, and executes orders behind a hard code risk gate. A human signs off at every gate.**

## 3. Verification Loop & Prior Art Attribution
- Built on the statistical framework of **Bailey & López de Prado (2012, 2014)** (Probabilistic & Deflated Sharpe Ratio, effective independent trials $K_{\text{eff}}$ from trial correlation matrices) and exact binomial sign testing.
- All market accounting uses exact integer GBP pence with next-bar execution, per-path fixed fees (`fee_pence`), adverse rounded slippage (`slippage_bps`), and forced final liquidation.

## 4. Quick Start & Running Tests
```bash
# Run deterministic unit & provenance tests (Python 3.11+ stdlib only)
python -m unittest discover -s tests -v

# Start the Operate Web UI
python app/server.py
```

## 5. Dataset & Licence Attribution
- Historical price windows derived from **Binance Vision** public data (CC BY-NC-SA 4.0, non-commercial educational backtesting use; not endorsed by Binance).
- Synthetic calibration series generated deterministically with recorded seeds and explicitly labelled as synthetic calibration checks.
