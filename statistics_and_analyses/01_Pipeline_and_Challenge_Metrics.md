# Pipeline & Challenge Mode Metrics

## End-to-End Pipeline Latency & Scope
- **Test Suite Performance:** 8/8 core integration and provenance tests pass in **< 1.0 second**.
- **Adapter Footprint:** 100% Python Standard Library. Zero LLM calls at runtime, zero network requests at runtime.
- **Deterministic Math:** GBP integer-pence execution across all backtest and live modes to prevent floating-point drift.
- **Risk Gate Latency:** Hard-coded paper order gate executes in **< 5ms** per bar.

## Official Dockerized Challenge Check Results
Run against the AgentVerse hidden `bench.py` evaluator using `--pack mixed --cases 60`.

*   **Total Hidden Cases Processed:** 60/60
*   **Compliance:** 0 Provenance Warnings (No illegal imports, no unauthorized testbed access)
*   **Cashflow Precision:** 20/20 parsed & solved flawlessly.
*   **Transactions (Cycle Detection):** 20/20 parsed & solved. **Cycle F1 Score: 1.0** (100% Precision / 100% Recall).
*   **Markets (Zero-LLM Adapter):** 20/20 paths survived the Paper-Order Risk Gate without crashing or timing out.
