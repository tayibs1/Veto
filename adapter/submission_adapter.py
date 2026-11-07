#!/usr/bin/env python3
"""Official JSONL submission adapter for Preregister.

Reads one JSON request per line on stdin and writes one JSON response per line on stdout.
- For 'market_step': executes the frozen, pre-registered HunchSpec behind the deterministic
  risk gate (gate.py). Zero LLM calls per bar, zero network calls, 100% plain Python stdlib.
- Also includes deterministic 'cashflow' and 'transactions' solvers so if the evaluator runs
  the 'mixed' pack, every case is handled accurately and safely (ignoring untrusted text
  in descriptions).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

# Ensure repo root is importable when invoked from any working directory
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from preregister.gate import RiskPolicy, enforce_order_gate
from preregister.grammar import evaluate_signal
from preregister.schemas import HunchSpec

# Default frozen pre-registered candidate (can be overridden by preregister/fixtures/frozen_spec.json)
DEFAULT_FROZEN_SPEC = HunchSpec(
    template="cost_gated_log_mean_reversion",
    params={
        "lookback_bars": 12,
        "entry_z": 1.65,
        "hold_bars": 8,
        "cost_hurdle_mult": 1.5,
        "trend_filter_bars": 24,
    },
    source_quotes={
        "lookback_bars": "12-bar",
        "entry_z": "1.65 sigma drop",
        "hold_bars": "hold 8 bars",
    },
    defaults_used=["cost_hurdle_mult", "trend_filter_bars"],
    rationale="Frozen pre-registered cost-gated log-return mean-reversion rule.",
)


def load_frozen_spec() -> HunchSpec:
    spec_file = ROOT / "preregister" / "fixtures" / "frozen_spec.json"
    if spec_file.exists():
        raw = json.loads(spec_file.read_text(encoding="utf-8"))
        return HunchSpec(
            template=raw["template"],
            params=raw["params"],
            source_quotes=raw.get("source_quotes", {}),
            defaults_used=raw.get("defaults_used", []),
            rationale=raw.get("rationale", ""),
        )
    return DEFAULT_FROZEN_SPEC


FROZEN_SPEC = load_frozen_spec()
POLICY = RiskPolicy()
CASE_STATE: dict[str, dict[str, Any]] = {}


def solve_market_step(case_id: str, data: dict[str, Any]) -> dict[str, Any]:
    history = data.get("history", [])
    cash = int(data["cash_pence"])
    shares = int(data["shares"])
    fee = int(data["fee_pence"])
    bps = int(data["slippage_bps"])
    if not history:
        return {"action": "hold"}

    cur_price = int(history[-1]["price_pence"])
    cur_equity = cash + shares * cur_price

    st = CASE_STATE.setdefault(
        case_id,
        {"peak_equity": cur_equity, "bars_held": 0, "peak_price": cur_price},
    )
    st["peak_equity"] = max(int(st["peak_equity"]), cur_equity)
    if shares > 0:
        st["bars_held"] = int(st["bars_held"]) + 1
        st["peak_price"] = max(int(st["peak_price"]), cur_price)
    else:
        st["bars_held"] = 0
        st["peak_price"] = cur_price

    dd_bps = (int(st["peak_equity"]) - cur_equity) * 10000 // max(1, int(st["peak_equity"]))
    raw_action = evaluate_signal(
        FROZEN_SPEC,
        history=history,
        cash_pence=cash,
        shares=shares,
        fee_pence=fee,
        slippage_bps=bps,
        state=st,
    )
    action, _ = enforce_order_gate(
        raw_action,
        price_pence=cur_price,
        cash_pence=cash,
        shares=shares,
        fee_pence=fee,
        slippage_bps=bps,
        current_drawdown_bps=dd_bps,
        policy=POLICY,
    )
    return {"action": action}


def solve_cashflow(data: dict[str, Any]) -> dict[str, Any]:
    """Deterministic integer-pence cashflow schedule calculator.
    Ignores event['description'] completely so untrusted text injections have zero effect.
    """
    opening = data.get("opening_balance_pence")
    events = data.get("events")
    if type(opening) is not int or not isinstance(events, list) or len(events) > 500:
        return {"error": "invalid_input"}

    seen_ids: set[str] = set()
    for ev in events:
        if not isinstance(ev, dict):
            return {"error": "invalid_input"}
        ev_id = ev.get("id")
        amt = ev.get("amount_pence")
        cur = ev.get("currency", "GBP")
        dt = ev.get("date")
        if (
            not isinstance(ev_id, str)
            or not ev_id
            or ev_id in seen_ids
            or type(amt) is not int
            or cur != "GBP"
            or not isinstance(dt, str)
        ):
            return {"error": "invalid_input"}
        try:
            date.fromisoformat(dt)
        except ValueError:
            return {"error": "invalid_input"}
        seen_ids.add(ev_id)

    ordered = sorted(events, key=lambda e: (e["date"], e["id"]))
    balance = opening
    minimum = opening
    first_negative: str | None = None
    for ev in ordered:
        balance += ev["amount_pence"]
        minimum = min(minimum, balance)
        if balance < 0 and first_negative is None:
            first_negative = ev["date"]

    return {
        "closing_balance_pence": balance,
        "minimum_balance_pence": minimum,
        "shortfall_pence": max(0, -minimum),
        "first_negative_date": first_negative,
    }


def solve_transactions(data: dict[str, Any]) -> dict[str, Any]:
    """Deterministic directed 3-account cycle detector and threshold filter."""
    rows = data.get("rows")
    threshold = data.get("large_transfer_pence", 70000)
    if (
        not isinstance(rows, list)
        or len(rows) > 500
        or type(threshold) is not int
        or threshold < 1
    ):
        return {"error": "invalid_input"}

    seen_ids: set[str] = set()
    by_pair: dict[tuple[str, str], list[str]] = {}
    successors: dict[str, set[str]] = {}
    total_pence = 0
    large_ids: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            return {"error": "invalid_input"}
        tx_id = row.get("id")
        amt = row.get("amount_pence")
        cur = row.get("currency")
        sender = row.get("sender")
        recipient = row.get("recipient")
        dt = row.get("date")
        if (
            not isinstance(tx_id, str)
            or not tx_id
            or tx_id in seen_ids
            or type(amt) is not int
            or amt < 1
            or cur != "GBP"
            or not isinstance(sender, str)
            or not sender
            or not isinstance(recipient, str)
            or not recipient
            or not isinstance(dt, str)
        ):
            return {"error": "invalid_input"}
        try:
            date.fromisoformat(dt)
        except ValueError:
            return {"error": "invalid_input"}
        seen_ids.add(tx_id)
        total_pence += amt
        if amt >= threshold:
            large_ids.append(tx_id)
        by_pair.setdefault((sender, recipient), []).append(tx_id)
        successors.setdefault(sender, set()).add(recipient)

    cycle_txs: set[str] = set()
    for (a, b), first_ids in by_pair.items():
        if a == b:
            continue
        for c in successors.get(b, ()):
            if c not in (a, b) and (c, a) in by_pair:
                cycle_txs.update(first_ids)
                cycle_txs.update(by_pair[(b, c)])
                cycle_txs.update(by_pair[(c, a)])

    return {
        "cycle_transaction_ids": sorted(cycle_txs),
        "large_transfer_ids": sorted(large_ids),
        "total_transferred_pence": total_pence,
    }


def dispatch(request: dict[str, Any]) -> dict[str, Any]:
    task = request.get("task")
    inp = request.get("input", {})
    case_id = str(request.get("case_id", request.get("request_id", "default")))
    if task == "market_step":
        return solve_market_step(case_id, inp)
    if task == "cashflow":
        return solve_cashflow(inp)
    if task == "transactions":
        return solve_transactions(inp)
    return {"error": "unsupported_task"}


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        req = json.loads(line)
        out = dispatch(req)
        print(
            json.dumps({"request_id": req["request_id"], "output": out}, separators=(",", ":")),
            flush=True,
        )


if __name__ == "__main__":
    main()
