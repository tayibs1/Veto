"""3-Template Log-Return Cost-Gated Strategy Grammar & Validator.

Enforces:
1. Only the 3 locked templates are accepted.
2. Every parameter slot must be within valid bounds and backed by a quote/annotation
   or declared in defaults_used (no silent LLM parameter invention).
3. All signal math operates on log-returns (Delta ln p_t) so return-inversion is exact,
   and checks per-path round-trip fee + slippage hurdles before entering.
"""

from __future__ import annotations

import math
from typing import Any

from preregister.schemas import HunchSpec

TEMPLATE_SCHEMAS: dict[str, dict[str, tuple[float, float, float]]] = {
    # param_name: (min_val, max_val, declared_default)
    "cost_gated_log_mean_reversion": {
        "lookback_bars": (3, 48, 12),
        "entry_z": (0.8, 3.5, 1.75),
        "hold_bars": (2, 36, 8),
        "cost_hurdle_mult": (1.0, 4.0, 1.5),
        "trend_filter_bars": (0, 72, 24),
    },
    "symmetric_volatility_breakout": {
        "lookback_bars": (6, 60, 18),
        "breakout_sigma": (1.0, 3.5, 1.8),
        "trailing_stop_bps": (40, 600, 180),
        "cost_hurdle_mult": (1.0, 4.0, 1.5),
    },
    "regime_cash_standdown": {
        "vol_window": (6, 48, 16),
        "drift_window": (6, 48, 16),
        "max_vol_bps": (30, 500, 180),
        "min_drift_bps": (-60, 60, 0),
        "cost_hurdle_mult": (1.0, 4.0, 1.5),
    },
}

REQUIRED_USER_SLOTS: dict[str, tuple[str, ...]] = {
    "cost_gated_log_mean_reversion": ("lookback_bars", "entry_z", "hold_bars"),
    "symmetric_volatility_breakout": ("lookback_bars", "breakout_sigma", "trailing_stop_bps"),
    "regime_cash_standdown": ("vol_window", "max_vol_bps"),
}


class GrammarRefusalError(ValueError):
    """Raised when a hunch is outside the grammar or missing required quoted slots."""


def validate_hunch_spec(
    spec: HunchSpec,
    hunch_text: str | None = None,
    require_quotes: bool = True,
) -> HunchSpec:
    """Validate template, parameter bounds, and quote/default provenance."""
    if spec.template not in TEMPLATE_SCHEMAS:
        raise GrammarRefusalError(
            f"Unsupported template '{spec.template}'. Allowed: {sorted(TEMPLATE_SCHEMAS)}"
        )
    schema = TEMPLATE_SCHEMAS[spec.template]
    unknown = set(spec.params) - set(schema)
    if unknown:
        raise GrammarRefusalError(f"Unknown parameters for {spec.template}: {sorted(unknown)}")

    # Auto-inject defaults for non-core parameters if the LLM omitted them
    for name, (_, _, default_val) in schema.items():
        if name not in spec.params and name not in REQUIRED_USER_SLOTS.get(spec.template, ()):
            spec.params[name] = default_val
            if name not in spec.defaults_used:
                spec.defaults_used.append(name)

    missing = set(schema) - set(spec.params)
    if missing:
        raise GrammarRefusalError(
            f"Underspecified hunch: missing parameters {sorted(missing)} for {spec.template}. "
            "Refusing to guess unstated parameters."
        )
    for name, (low, high, default_val) in schema.items():
        val = spec.params[name]
        if not isinstance(val, (int, float)) or not math.isfinite(val):
            raise GrammarRefusalError(f"Parameter '{name}' must be a finite number")
        if not (low <= float(val) <= high):
            raise GrammarRefusalError(
                f"Parameter '{name}'={val} outside allowed range [{low}, {high}]"
            )
        if require_quotes:
            has_quote = bool(spec.source_quotes.get(name, "").strip())
            is_default = name in spec.defaults_used
            if not has_quote and not is_default:
                raise GrammarRefusalError(
                    f"Parameter '{name}' has neither a source quote nor a declared default."
                )
            if is_default and name in REQUIRED_USER_SLOTS[spec.template]:
                raise GrammarRefusalError(
                    f"Core parameter '{name}' cannot use a silent default; ask the human to specify it."
                )
            if has_quote and hunch_text:
                quote_str = spec.source_quotes[name].strip().lower()
                if quote_str not in hunch_text.lower() and not quote_str.startswith("[chart:"):
                    raise GrammarRefusalError(
                        f"Source quote '{spec.source_quotes[name]}' for '{name}' not found in user text."
                    )
    return spec


def round_trip_cost_bps(price_pence: int, cash_pence: int, fee_pence: int, slippage_bps: int) -> float:
    """Exact round-trip transaction cost in basis points of capital."""
    denom = max(1, cash_pence if cash_pence > 0 else price_pence * 100)
    fee_bps = (2.0 * fee_pence * 10000.0) / denom
    return fee_bps + 2.0 * slippage_bps


def evaluate_signal(
    spec: HunchSpec,
    history: list[dict[str, Any]],
    cash_pence: int,
    shares: int,
    fee_pence: int,
    slippage_bps: int,
    state: dict[str, Any] | None = None,
) -> str:
    """Pure deterministic bar-by-bar signal evaluation using log-returns only.

    Returns 'buy', 'hold', or 'sell'.
    """
    prices = [int(bar["price_pence"]) for bar in history]
    n = len(prices)
    if n < 3:
        return "hold"
    cur_price = prices[-1]
    rt_cost_bps = round_trip_cost_bps(cur_price, cash_pence, fee_pence, slippage_bps)
    params = spec.params
    cost_mult = float(params.get("cost_hurdle_mult", 1.5))

    # Compute log returns in bps (10000 * Delta ln p)
    log_rets_bps = [
        10000.0 * math.log(max(1, prices[i]) / max(1, prices[i - 1]))
        for i in range(1, n)
    ]

    if spec.template == "cost_gated_log_mean_reversion":
        lb = int(params["lookback_bars"])
        hold_bars = int(params["hold_bars"])
        entry_z = float(params["entry_z"])
        tf_bars = int(params.get("trend_filter_bars", 0))
        if len(log_rets_bps) < lb:
            return "hold"

        if shares > 0:
            bars_held = int((state or {}).get("bars_held", 0))
            recent_cum = sum(log_rets_bps[-min(lb, len(log_rets_bps)) :])
            if bars_held >= hold_bars or recent_cum >= 0:
                return "sell"
            return "hold"

        window = log_rets_bps[-lb:]
        mean_r = sum(window) / lb
        var_r = sum((r - mean_r) ** 2 for r in window) / max(1, lb - 1)
        std_r = math.sqrt(max(1e-6, var_r))
        cum_drop_bps = sum(window)
        sigma_cum_bps = std_r * math.sqrt(lb)
        z_score = cum_drop_bps / max(1.0, sigma_cum_bps)

        if tf_bars > 0 and len(log_rets_bps) >= tf_bars:
            long_drift = sum(log_rets_bps[-tf_bars:])
            if long_drift < -1.5 * sigma_cum_bps:
                return "hold"

        expected_reversion_bps = abs(cum_drop_bps) * 0.5
        if z_score <= -entry_z and expected_reversion_bps >= cost_mult * rt_cost_bps:
            return "buy"
        return "hold"

    if spec.template == "symmetric_volatility_breakout":
        lb = int(params["lookback_bars"])
        k_sigma = float(params["breakout_sigma"])
        stop_bps = float(params["trailing_stop_bps"])
        if len(log_rets_bps) < lb:
            return "hold"

        if shares > 0:
            peak_price = int((state or {}).get("peak_price", cur_price))
            dd_bps = 10000.0 * math.log(max(1, peak_price) / max(1, cur_price))
            if dd_bps >= stop_bps:
                return "sell"
            return "hold"

        window = log_rets_bps[-lb:]
        std_r = math.sqrt(max(1.0, sum(r * r for r in window) / lb))
        recent_move_bps = sum(log_rets_bps[-min(3, lb) :])
        threshold_bps = k_sigma * std_r * math.sqrt(min(3, lb))
        if recent_move_bps >= threshold_bps and recent_move_bps >= cost_mult * rt_cost_bps:
            return "buy"
        return "hold"

    if spec.template == "regime_cash_standdown":
        vol_w = int(params["vol_window"])
        drift_w = int(params["drift_window"])
        max_vol = float(params["max_vol_bps"])
        min_drift = float(params["min_drift_bps"])
        need = max(vol_w, drift_w)
        if len(log_rets_bps) < need:
            return "hold"

        v_slice = log_rets_bps[-vol_w:]
        d_slice = log_rets_bps[-drift_w:]
        vol_bps = math.sqrt(sum(r * r for r in v_slice) / vol_w)
        drift_bps = sum(d_slice) / drift_w

        favorable = (
            vol_bps <= max_vol
            and drift_bps >= min_drift
            and (drift_bps * drift_w) >= cost_mult * rt_cost_bps
        )
        if shares == 0 and favorable:
            return "buy"
        if shares > 0 and not favorable:
            return "sell"
        return "hold"

    return "hold"
