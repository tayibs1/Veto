"""Exact Integer-Pence Walk-Forward Market Backtester & Referee Engine.

Matches the exact accounting equations of the AgentVerse evaluator:
- Next-bar execution
- Adverse integer-pence slippage rounding:
    buy fill  = (next_price * (10000 + bps) + 9999) // 10000
    sell fill = (next_price * (10000 - bps)) // 10000
- Forced final-bar liquidation
- Exact Buy-and-Hold and Cash benchmarks
"""

from __future__ import annotations

from typing import Any

from preregister.gate import RiskPolicy, enforce_order_gate
from preregister.grammar import evaluate_signal
from preregister.schemas import HunchSpec, TrialDiagnostics, VerdictRecord
from preregister.stats import (
    deflated_sharpe_probability,
    effective_independent_trials,
    min_detectable_excess_bps,
    sign_test_p_value,
    trial_adjusted_p_value,
)


def buy_and_hold_final_pence(case_input: dict[str, Any]) -> int:
    """Exact closed-form buy-and-hold final cash in integer pence."""
    prices = [int(p) for p in case_input["prices_pence"]]
    cash = int(case_input["initial_cash_pence"])
    fee = int(case_input["fee_pence"])
    bps = int(case_input["slippage_bps"])
    buy_price = (prices[1] * (10000 + bps) + 9999) // 10000
    sell_price = (prices[-1] * (10000 - bps)) // 10000
    units = max(0, cash - fee) // buy_price
    return cash + units * (sell_price - buy_price) - (2 * fee if units else 0)


def simulate_path(
    spec: HunchSpec,
    case_input: dict[str, Any],
    policy: RiskPolicy | None = None,
) -> dict[str, Any]:
    """Walk-forward simulation on one price path using observed prefix only."""
    prices = [int(p) for p in case_input["prices_pence"]]
    dates = [str(d) for d in case_input["dates"]]
    initial_cash = int(case_input["initial_cash_pence"])
    fee = int(case_input["fee_pence"])
    bps = int(case_input["slippage_bps"])

    cash = initial_cash
    shares = 0
    fees_paid = 0
    trades: list[dict[str, Any]] = []
    equity = [cash]
    peak = cash
    max_dd_bps = 0
    state: dict[str, Any] = {"bars_held": 0, "peak_price": prices[0]}

    for idx in range(len(prices) - 1):
        history = [{"date": dates[i], "price_pence": prices[i]} for i in range(idx + 1)]
        cur_dd_bps = (peak - equity[-1]) * 10000 // max(1, peak)
        if shares > 0:
            state["bars_held"] = int(state.get("bars_held", 0)) + 1
            state["peak_price"] = max(int(state.get("peak_price", prices[idx])), prices[idx])
        else:
            state["bars_held"] = 0
            state["peak_price"] = prices[idx]

        raw_action = evaluate_signal(
            spec,
            history=history,
            cash_pence=cash,
            shares=shares,
            fee_pence=fee,
            slippage_bps=bps,
            state=state,
        )
        action, _ = enforce_order_gate(
            raw_action,
            price_pence=prices[idx],
            cash_pence=cash,
            shares=shares,
            fee_pence=fee,
            slippage_bps=bps,
            current_drawdown_bps=cur_dd_bps,
            policy=policy,
        )

        next_price = prices[idx + 1]
        if action == "buy":
            fill = (next_price * (10000 + bps) + 9999) // 10000
            units = max(0, cash - fee) // fill
            if units > 0:
                cash -= units * fill + fee
                shares += units
                fees_paid += fee
                state["bars_held"] = 0
                state["peak_price"] = next_price
                trades.append(
                    {
                        "signal_date": dates[idx],
                        "fill_date": dates[idx + 1],
                        "action": "buy",
                        "shares": units,
                        "fill_price_pence": fill,
                    }
                )
        elif action == "sell" and shares > 0:
            fill = (next_price * (10000 - bps)) // 10000
            cash += shares * fill - fee
            fees_paid += fee
            trades.append(
                {
                    "signal_date": dates[idx],
                    "fill_date": dates[idx + 1],
                    "action": "sell",
                    "shares": shares,
                    "fill_price_pence": fill,
                }
            )
            shares = 0

        cur_eq = cash + shares * next_price
        equity.append(cur_eq)
        peak = max(peak, cur_eq)
        max_dd_bps = max(max_dd_bps, (peak - cur_eq) * 10000 // max(1, peak))

    if shares > 0:
        fill = (prices[-1] * (10000 - bps)) // 10000
        cash += shares * fill - fee
        fees_paid += fee
        trades.append(
            {
                "fill_date": dates[-1],
                "action": "forced_final_sale",
                "shares": shares,
                "fill_price_pence": fill,
            }
        )
        shares = 0

    equity.append(cash)
    peak = max(peak, cash)
    max_dd_bps = max(max_dd_bps, (peak - cash) * 10000 // max(1, peak))
    hold_final = buy_and_hold_final_pence(case_input)
    excess_bps = (cash - hold_final) * 10000 // max(1, initial_cash)
    fee_drag_bps = (fees_paid * 10000) // max(1, initial_cash) + len(trades) * bps

    return {
        "final_cash_pence": cash,
        "profit_pence": cash - initial_cash,
        "buy_and_hold_final_pence": hold_final,
        "cash_baseline_final_pence": initial_cash,
        "excess_vs_buy_and_hold_bps": excess_bps,
        "max_drawdown_bps": max_dd_bps,
        "fees_paid_pence": fees_paid,
        "fee_drag_bps": fee_drag_bps,
        "trades": trades,
        "path_Positive_drift": prices[-1] > prices[1],
        "path_high_cost": (fee * 10000 // max(1, initial_cash) + bps) >= 25,
    }


def evaluate_on_paths(
    spec: HunchSpec,
    cases: list[dict[str, Any]],
    trial_number: int = 1,
    max_trials: int = 12,
    prior_excess_vectors: list[list[int]] | None = None,
    policy: RiskPolicy | None = None,
) -> TrialDiagnostics:
    """Evaluate a locked spec across a set of paths and compute observable diagnostics."""
    results = [simulate_path(spec, c["input"] if "input" in c else c, policy=policy) for c in cases]
    n = len(results)
    wins = sum(1 for r in results if r["final_cash_pence"] > r["buy_and_hold_final_pence"])
    losses = sum(1 for r in results if r["final_cash_pence"] < r["buy_and_hold_final_pence"])
    ties = n - wins - losses

    excess_vec = [int(r["excess_vs_buy_and_hold_bps"]) for r in results]
    ordered = sorted(excess_vec)
    mid = n // 2
    median_excess = ordered[mid] if n % 2 == 1 else (ordered[mid - 1] + ordered[mid]) // 2
    mean_dd = sum(int(r["max_drawdown_bps"]) for r in results) // max(1, n)

    pos_paths = [r for r in results if r["path_Positive_drift"]]
    neg_paths = [r for r in results if not r["path_Positive_drift"]]
    pos_win = (
        sum(1 for r in pos_paths if r["final_cash_pence"] >= r["buy_and_hold_final_pence"])
        / max(1, len(pos_paths))
    )
    neg_win = (
        sum(1 for r in neg_paths if r["final_cash_pence"] >= r["buy_and_hold_final_pence"])
        / max(1, len(neg_paths))
    )

    high_cost = [r["excess_vs_buy_and_hold_bps"] for r in results if r["path_high_cost"]]
    low_cost = [r["excess_vs_buy_and_hold_bps"] for r in results if not r["path_high_cost"]]
    high_cost_med = sum(high_cost) // max(1, len(high_cost)) if high_cost else 0
    low_cost_med = sum(low_cost) // max(1, len(low_cost)) if low_cost else 0

    mean_fee_drag = sum(int(r["fee_drag_bps"]) for r in results) // max(1, n)
    mean_trades = sum(len(r["trades"]) for r in results) / max(1, n)

    all_vectors = list(prior_excess_vectors or []) + [excess_vec]
    k_eff = effective_independent_trials(all_vectors)
    raw_p = sign_test_p_value(wins, losses)
    p_adj = trial_adjusted_p_value(raw_p, k_eff)
    _, dsr_prob = deflated_sharpe_probability(excess_vec, k_eff)

    return TrialDiagnostics(
        spec_hash=spec.spec_hash(),
        trial_number=trial_number,
        budget_remaining=max(0, max_trials - trial_number),
        paths_evaluated=n,
        wins_vs_buy_and_hold=wins,
        losses_vs_buy_and_hold=losses,
        ties_vs_buy_and_hold=ties,
        median_excess_bps=median_excess,
        mean_max_drawdown_bps=mean_dd,
        pos_drift_win_rate=round(pos_win, 3),
        neg_drift_win_rate=round(neg_win, 3),
        high_cost_excess_bps=high_cost_med,
        low_cost_excess_bps=low_cost_med,
        mean_fee_drag_bps=mean_fee_drag,
        mean_trades_per_path=round(mean_trades, 2),
        raw_sign_p_value=round(raw_p, 4),
        trial_adjusted_p_value=round(p_adj, 4),
        deflated_sharpe_prob=round(dsr_prob, 4),
        effective_trials_k_eff=round(k_eff, 2),
        excess_vector_bps=excess_vec,
    )


def build_verdict(
    spec: HunchSpec,
    holdout_cases: list[dict[str, Any]],
    total_trials_run: int,
    prior_excess_vectors: list[list[int]],
    ledger_head_hash: str,
) -> VerdictRecord:
    """Compute final one-shot holdout verdict."""
    diag = evaluate_on_paths(
        spec,
        holdout_cases,
        trial_number=total_trials_run,
        max_trials=total_trials_run,
        prior_excess_vectors=prior_excess_vectors,
    )
    sr, dsr = deflated_sharpe_probability(diag.excess_vector_bps, diag.effective_trials_k_eff)
    mde = min_detectable_excess_bps(diag.excess_vector_bps, diag.effective_trials_k_eff)

    reasons: list[str] = []
    if diag.paths_evaluated < 15 or (diag.wins_vs_buy_and_hold + diag.losses_vs_buy_and_hold) < 8:
        verdict = "UNDERPOWERED"
        reasons.append(
            f"Only {diag.wins_vs_buy_and_hold + diag.losses_vs_buy_and_hold} non-tied paths; "
            f"minimum detectable excess is {mde} bps."
        )
    elif diag.median_excess_bps > 0 and diag.trial_adjusted_p_value < 0.05:
        verdict = "SURVIVES"
        reasons.append(
            f"Beat buy-and-hold ({diag.wins_vs_buy_and_hold}W/{diag.losses_vs_buy_and_hold}L, "
            f"median +{diag.median_excess_bps} bps) with trial-adjusted p={diag.trial_adjusted_p_value:.4f} < 0.05 "
            f"across K_eff={diag.effective_trials_k_eff:.2f} effective trials."
        )
    else:
        verdict = "DOES_NOT_SURVIVE"
        reasons.append(
            f"Out-of-sample excess ({diag.median_excess_bps} bps, {diag.wins_vs_buy_and_hold}W/{diag.losses_vs_buy_and_hold}L) "
            f"did not clear trial-adjusted threshold (raw p={diag.raw_sign_p_value:.4f}, "
            f"adjusted p={diag.trial_adjusted_p_value:.4f} for K_eff={diag.effective_trials_k_eff:.2f})."
        )

    return VerdictRecord(
        spec_hash=spec.spec_hash(),
        template=spec.template,
        params=spec.params,
        total_trials_run=total_trials_run,
        effective_trials_k_eff=diag.effective_trials_k_eff,
        paths_tested=diag.paths_evaluated,
        wins_vs_buy_and_hold=diag.wins_vs_buy_and_hold,
        losses_vs_buy_and_hold=diag.losses_vs_buy_and_hold,
        ties_vs_buy_and_hold=diag.ties_vs_buy_and_hold,
        median_excess_bps=diag.median_excess_bps,
        mean_max_drawdown_bps=diag.mean_max_drawdown_bps,
        raw_sign_p_value=diag.raw_sign_p_value,
        trial_adjusted_p_value=diag.trial_adjusted_p_value,
        observed_sharpe=sr,
        deflated_sharpe_prob=dsr,
        min_detectable_excess_bps=mde,
        verdict=verdict,
        reasons=reasons,
        ledger_head_hash=ledger_head_hash,
    )
