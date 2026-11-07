"""Deterministic Plain-Code Paper-Order Risk Gate.

Enforces hard position size, per-trade cost hurdle, max drawdown breaker, and kill switch.
The LLM cannot override or modify these checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskPolicy:
    max_position_pct: float = 1.0  # 100% of cash (no leverage)
    max_drawdown_bps: int = 2500   # 25% max path drawdown halt
    max_round_trip_cost_bps: int = 250  # Refuse buy if 2*fee + 2*slippage > 250 bps
    kill_switch_engaged: bool = False


def enforce_order_gate(
    proposed_action: str,
    price_pence: int,
    cash_pence: int,
    shares: int,
    fee_pence: int,
    slippage_bps: int,
    current_drawdown_bps: int,
    policy: RiskPolicy | None = None,
) -> tuple[str, str]:
    """Validate proposed_action ('buy'|'hold'|'sell') against deterministic risk limits.

    Returns (approved_action, gate_reason). Risk reduction ('sell') is always permitted.
    """
    policy = policy or RiskPolicy()
    if proposed_action not in ("buy", "hold", "sell"):
        return "hold", "invalid_action_blocked"

    if policy.kill_switch_engaged:
        if shares > 0:
            return "sell", "kill_switch_liquidate"
        return "hold", "kill_switch_halt"

    if current_drawdown_bps >= policy.max_drawdown_bps:
        if shares > 0:
            return "sell", "max_drawdown_breaker_liquidate"
        return "hold", "max_drawdown_breaker_halt"

    if proposed_action == "buy":
        if shares > 0:
            return "hold", "already_invested_cap"
        fill = (price_pence * (10000 + slippage_bps) + 9999) // 10000
        units = max(0, cash_pence - fee_pence) // max(1, fill)
        if units <= 0:
            return "hold", "insufficient_cash_for_one_share"
        # Check whether round-trip cost is excessive relative to capital
        rt_cost_bps = ((2 * fee_pence * 10000) // max(1, cash_pence)) + 2 * slippage_bps
        if rt_cost_bps > policy.max_round_trip_cost_bps:
            return "hold", f"cost_gate_blocked_{rt_cost_bps}bps"

    return proposed_action, "approved"
