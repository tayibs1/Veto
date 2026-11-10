"""Gemini 4 Argon Multimodal Hunch Translator, Bounded 12-Trial Diagnostic Researcher,
and Numbers-Only Verdict Memo Generator.

Trust Boundary:
- The LLM never computes returns, Sharpe ratios, p-values, or drawdowns.
- Every proposed specification passes through validate_hunch_spec() and TrialLedger.
- Uses google-genai SDK when GEMINI_API_KEY is present in the environment, with a
  deterministic diagnostic policy when running offline tests or replays.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from preregister.backtest import build_verdict, evaluate_on_paths
from preregister.grammar import (
    REQUIRED_USER_SLOTS,
    TEMPLATE_SCHEMAS,
    GrammarRefusalError,
    validate_hunch_spec,
)
from preregister.ledger import LedgerViolationError, TrialLedger
from preregister.schemas import HunchSpec, TrialDiagnostics, VerdictRecord

DEFAULT_MODEL_ID = "gemini-4-argon"

PRESET_HUNCHES: dict[str, dict[str, Any]] = {
    "ambiguous_dip": {
        "title": "1. Ambiguous Chart Hunch (Missing Hold Period -> Refused)",
        "text": "Buy after a 12-bar drop of 1.8 sigma on the chart.",
        "chart": "chart_1_ambiguous_dip.svg",
        "raw_candidate": {
            "template": "cost_gated_log_mean_reversion",
            "params": {
                "lookback_bars": 12,
                "entry_z": 1.8,
                "cost_hurdle_mult": 1.5,
                "trend_filter_bars": 24,
            },
            "source_quotes": {
                "lookback_bars": "12-bar",
                "entry_z": "1.8 sigma",
            },
            "defaults_used": ["cost_hurdle_mult", "trend_filter_bars"],
            "rationale": "User stated 12-bar lookback and 1.8 sigma drop, but omitted hold_bars.",
        },
    },
    "naive_churn": {
        "title": "2. Naive Overfit Churn Hunch (Looks Active, Fails Cost & Holdout Gate)",
        "text": "Buy every 4-bar 0.9 sigma dip and hold for 3 bars with low 1.0x cost hurdle.",
        "chart": "chart_2_naive_churn.svg",
        "raw_candidate": {
            "template": "cost_gated_log_mean_reversion",
            "params": {
                "lookback_bars": 4,
                "entry_z": 0.9,
                "hold_bars": 3,
                "cost_hurdle_mult": 1.0,
                "trend_filter_bars": 0,
            },
            "source_quotes": {
                "lookback_bars": "4-bar",
                "entry_z": "0.9 sigma",
                "hold_bars": "hold for 3 bars",
                "cost_hurdle_mult": "1.0x cost hurdle",
            },
            "defaults_used": ["trend_filter_bars"],
            "rationale": "High-frequency dip buying with minimal cost filter.",
        },
    },
    "cost_gated_reversion": {
        "title": "3. Cost-Gated Log Mean Reversion (Starting Rule for Argon Refinement)",
        "text": "Buy after a 12-bar 1.65 sigma log drop and hold for 8 bars when expected move clears cost hurdle.",
        "chart": "chart_3_cost_gated_reversion.svg",
        "raw_candidate": {
            "template": "cost_gated_log_mean_reversion",
            "params": {
                "lookback_bars": 12,
                "entry_z": 1.65,
                "hold_bars": 8,
                "cost_hurdle_mult": 1.2,
                "trend_filter_bars": 12,
            },
            "source_quotes": {
                "lookback_bars": "12-bar",
                "entry_z": "1.65 sigma",
                "hold_bars": "hold for 8 bars",
            },
            "defaults_used": ["cost_hurdle_mult", "trend_filter_bars"],
            "rationale": "12-bar log-return mean-reversion with 8-bar hold.",
        },
    },
}


def _call_gemini_json(prompt: str, image_path: Path | None = None, model_id: str = DEFAULT_MODEL_ID) -> dict[str, Any] | None:
    """Invoke Gemini 4 Argon via google-genai SDK if GEMINI_API_KEY is configured."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        contents: list[Any] = [prompt]
        if image_path and image_path.exists() and image_path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
            contents.append(types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime))
        resp = client.models.generate_content(
            model=model_id,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        if resp and resp.text:
            return json.loads(resp.text)
    except Exception as e:
        import traceback
        print("GEMINI EXCEPTION:", e, traceback.format_exc(), flush=True)
        return None
    return None


def _parse_text_hunch_deterministically(text: str, chart_name: str | None = None) -> dict[str, Any]:
    """Deterministic fallback parser extracting quoted numbers and template intent."""
    lower = text.lower()
    for key, preset in PRESET_HUNCHES.items():
        if text.strip() == preset["text"].strip() or key == text.strip():
            return dict(preset["raw_candidate"])

    template = "cost_gated_log_mean_reversion"
    if "breakout" in lower:
        template = "symmetric_volatility_breakout"
    elif "stand down" in lower or "stand-down" in lower or "regime" in lower:
        template = "regime_cash_standdown"

    params: dict[str, float | int] = {}
    quotes: dict[str, str] = {}
    defaults_used: list[str] = []

    lb_match = re.search(r"(\d+)\s*[- ]?(?:bar|day|hour)", lower)
    if lb_match:
        val = int(lb_match.group(1))
        slot = "vol_window" if template == "regime_cash_standdown" else "lookback_bars"
        params[slot] = val
        quotes[slot] = lb_match.group(0)

    sigma_match = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?(?:sigma|z|std)", lower)
    if sigma_match:
        val_f = float(sigma_match.group(1))
        slot = "breakout_sigma" if template == "symmetric_volatility_breakout" else "entry_z"
        params[slot] = val_f
        quotes[slot] = sigma_match.group(0)

    hold_match = re.search(r"hold.*?(\d+)\s*(?:bar|day|hour)", lower)
    if hold_match and template == "cost_gated_log_mean_reversion":
        params["hold_bars"] = int(hold_match.group(1))
        quotes["hold_bars"] = hold_match.group(0)

    stop_match = re.search(r"(\d+)\s*bps\s*stop", lower)
    if stop_match and template == "symmetric_volatility_breakout":
        params["trailing_stop_bps"] = int(stop_match.group(1))
        quotes["trailing_stop_bps"] = stop_match.group(0)

    vol_match = re.search(r"(\d+)\s*bps\s*vol", lower)
    if vol_match and template == "regime_cash_standdown":
        params["max_vol_bps"] = int(vol_match.group(1))
        quotes["max_vol_bps"] = vol_match.group(0)

    schema = TEMPLATE_SCHEMAS[template]
    required = REQUIRED_USER_SLOTS[template]
    for name, (_, _, default_val) in schema.items():
        if name not in params and name not in required:
            params[name] = default_val
            defaults_used.append(name)

    return {
        "template": template,
        "params": params,
        "source_quotes": quotes,
        "defaults_used": defaults_used,
        "rationale": f"Parsed from user hunch ({chart_name or 'text-only'}).",
    }


def translate_hunch(
    text: str,
    image_path: Path | None = None,
    model_id: str = DEFAULT_MODEL_ID,
) -> dict[str, Any]:
    if text.strip() in PRESET_HUNCHES:
        text = PRESET_HUNCHES[text.strip()]["text"]
    """Translate multimodal hunch (text + optional chart image) into a validated HunchSpec.

    Never guesses missing required slots; returns status='refused' with the exact reason if incomplete.
    """
    slot_lines = "\n".join(
        f"- {name}: required {list(REQUIRED_USER_SLOTS[name])}; optional {[k for k in schema if k not in REQUIRED_USER_SLOTS[name]]}"
        for name, schema in TEMPLATE_SCHEMAS.items()
    )
    prompt = (
        "You are the Preregister Spec Translator running on Gemini 4 Argon. "
        "Extract the user's trading hunch into JSON with keys: template, params, source_quotes, defaults_used, rationale.\n"
        "Allowed templates and their ONLY allowed parameter names:\n"
        f"{slot_lines}\n"
        "Rules:\n"
        "1. params contains only parameters from the chosen template that the user explicitly stated, as numbers. Never add any other key.\n"
        "2. source_quotes maps every key in params to the exact substring of the user's text that states it.\n"
        "3. Never invent or infer a required parameter. If the user did not state it, leave it out of params and source_quotes so the validator refuses the hunch.\n"
        "4. defaults_used lists only the template's optional parameters the user did not state. Never list a required parameter there.\n\n"
        f"User hunch: {text}"
    )
    llm_raw = _call_gemini_json(prompt, image_path=image_path, model_id=model_id)
    used_llm = isinstance(llm_raw, dict) and "template" in llm_raw
    engine = model_id if used_llm else "deterministic_fallback"
    candidate_dict = llm_raw if used_llm else _parse_text_hunch_deterministically(
        text, chart_name=image_path.name if image_path else None
    )
    try:
        spec = HunchSpec(
            template=str(candidate_dict.get("template", "")),
            params=dict(candidate_dict.get("params", {})),
            source_quotes=dict(candidate_dict.get("source_quotes", {})),
            defaults_used=list(candidate_dict.get("defaults_used", [])),
            rationale=str(candidate_dict.get("rationale", "")),
        )
        validated = validate_hunch_spec(spec, hunch_text=text, require_quotes=True)
        return {
            "status": "ok",
            "model_id": model_id,
            "engine": engine,
            "spec": validated.to_dict(),
        }
    except GrammarRefusalError as err:
        return {
            "status": "refused",
            "model_id": model_id,
            "engine": engine,
            "reason": str(err),
            "partial_candidate": candidate_dict,
        }


def propose_diagnostic_refinement(
    current_spec: HunchSpec,
    diag: TrialDiagnostics,
    step_index: int,
    model_id: str = DEFAULT_MODEL_ID,
) -> tuple[HunchSpec, str, str]:
    """Propose the next structural parameter refinement from observable training diagnostics.

    Returns (next_spec, diagnosis_text, hypothesis_text).
    """
    view = diag.agent_view()
    prompt = (
        "You are the Gemini 4 Argon Quant Research Agent operating under a strict 12-trial budget. "
        "Inspect the observable training diagnostics (never raw prices) and propose one parameter refinement "
        "within the allowed bounds to reduce fee drag and improve win rate vs buy-and-hold.\n"
        f"Current Spec: {json.dumps(current_spec.to_dict())}\n"
        f"Observable Diagnostics: {json.dumps(view)}\n"
        "Return JSON with keys: template, params, diagnosis, hypothesis."
    )
    llm_out = _call_gemini_json(prompt, model_id=model_id)
    if isinstance(llm_out, dict) and "params" in llm_out:
        try:
            cand = HunchSpec(
                template=str(llm_out.get("template", current_spec.template)),
                params=dict(llm_out["params"]),
                source_quotes=current_spec.source_quotes,
                defaults_used=current_spec.defaults_used,
                rationale=str(llm_out.get("hypothesis", "Argon diagnostic refinement")),
            )
            validate_hunch_spec(cand, require_quotes=False)
            return (
                cand,
                str(llm_out.get("diagnosis", "Evaluated training cost drag and regime win rates.")),
                str(llm_out.get("hypothesis", "Adjusted cost hurdle and filter parameters.")),
            )
        except Exception:
            pass

    # Deterministic diagnostic refinement policy (used when offline or as fallback)
    params = dict(current_spec.params)
    template = current_spec.template
    if template == "cost_gated_log_mean_reversion":
        if diag.mean_fee_drag_bps > 18 or diag.high_cost_excess_bps < 0:
            old_m = float(params["cost_hurdle_mult"])
            new_m = min(3.8, round(old_m + 0.45 + 0.1 * step_index, 2))
            params["cost_hurdle_mult"] = new_m
            diagnosis = (
                f"Trial #{diag.trial_number} suffered {diag.mean_fee_drag_bps} bps mean fee drag "
                f"(high-cost path excess: {diag.high_cost_excess_bps} bps)."
            )
            hypothesis = f"Increase cost_hurdle_mult from {old_m} to {new_m} to stand down on high-fee paths."
        elif diag.neg_drift_win_rate < 0.55 and int(params.get("trend_filter_bars", 0)) < 36:
            old_tf = int(params.get("trend_filter_bars", 12))
            new_tf = min(48, old_tf + 12)
            params["trend_filter_bars"] = new_tf
            diagnosis = (
                f"Negative-drift path win rate ({diag.neg_drift_win_rate:.1%}) lagged positive-drift paths "
                f"({diag.pos_drift_win_rate:.1%})."
            )
            hypothesis = f"Widen trend_filter_bars from {old_tf} to {new_tf} to avoid catching falling knives."
        else:
            old_z = float(params["entry_z"])
            new_z = min(3.0, round(old_z + 0.15 * ((step_index % 3) - 0.5), 2))
            params["entry_z"] = new_z
            params["hold_bars"] = max(4, min(16, int(params["hold_bars"]) + (2 if step_index % 2 == 0 else -1)))
            diagnosis = (
                f"Current median excess is {diag.median_excess_bps} bps ({diag.wins_vs_buy_and_hold}W/{diag.losses_vs_buy_and_hold}L, "
                f"K_eff={diag.effective_trials_k_eff})."
            )
            hypothesis = f"Refine entry_z={new_z} and hold_bars={params['hold_bars']} to sharpen signal-to-turnover ratio."
    elif template == "symmetric_volatility_breakout":
        old_m = float(params["cost_hurdle_mult"])
        params["cost_hurdle_mult"] = min(3.5, round(old_m + 0.4, 2))
        params["breakout_sigma"] = min(3.0, round(float(params["breakout_sigma"]) + 0.2, 2))
        diagnosis = f"Breakout turnover averaged {diag.mean_trades_per_path} trades/path with {diag.mean_fee_drag_bps} bps fee drag."
        hypothesis = f"Raise cost_hurdle_mult to {params['cost_hurdle_mult']} and breakout_sigma to {params['breakout_sigma']}."
    else:
        params["max_vol_bps"] = max(60, int(params["max_vol_bps"]) - 15)
        params["cost_hurdle_mult"] = min(3.5, round(float(params["cost_hurdle_mult"]) + 0.3, 2))
        diagnosis = f"Drawdown averaged {diag.mean_max_drawdown_bps} bps across {diag.paths_evaluated} paths."
        hypothesis = f"Tighten max_vol_bps to {params['max_vol_bps']} and cost_hurdle_mult to {params['cost_hurdle_mult']}."

    next_spec = HunchSpec(
        template=template,
        params=params,
        source_quotes=current_spec.source_quotes,
        defaults_used=current_spec.defaults_used,
        rationale=hypothesis,
    )
    validate_hunch_spec(next_spec, require_quotes=False)
    return next_spec, diagnosis, hypothesis


def run_research_loop(
    initial_spec: HunchSpec,
    train_cases: list[dict[str, Any]],
    ledger: TrialLedger,
    max_steps: int = 6,
    model_id: str = DEFAULT_MODEL_ID,
    prior_excess_vectors: list[list[int]] | None = None,
) -> dict[str, Any]:
    """Execute bounded diagnostic research loop on training paths, charging every trial to the ledger."""
    trials_log: list[dict[str, Any]] = []
    excess_vectors: list[list[int]] = []
    cumulative_vectors: list[list[int]] = list(prior_excess_vectors or [])
    specs_by_hash: dict[str, HunchSpec] = {}

    cur_spec = initial_spec
    cur_diagnosis = "Initial human-confirmed pre-registered specification."
    cur_hypothesis = initial_spec.rationale or "Baseline hypothesis before diagnostic refinement."

    for step in range(1, max_steps + 1):
        shash = cur_spec.spec_hash()
        specs_by_hash[shash] = cur_spec
        if not ledger.is_locked(shash):
            ledger.lock_spec(shash, cur_spec.to_dict())

        trial_num = ledger.trial_count() + 1
        diag = evaluate_on_paths(
            cur_spec,
            train_cases,
            trial_number=trial_num,
            max_trials=ledger.max_trials,
            prior_excess_vectors=cumulative_vectors + excess_vectors,
        )
        ledger.charge_train_trial(shash, diag.agent_view())
        excess_vectors.append(diag.excess_vector_bps)

        trials_log.append(
            {
                "trial_number": trial_num,
                "spec_hash": shash,
                "spec": cur_spec.to_dict(),
                "diagnosis": cur_diagnosis,
                "hypothesis": cur_hypothesis,
                "diagnostics": diag.agent_view(),
            }
        )
        if step < max_steps and ledger.trial_count() < ledger.max_trials:
            cur_spec, cur_diagnosis, cur_hypothesis = propose_diagnostic_refinement(
                cur_spec, diag, step_index=step, model_id=model_id
            )

    # Select candidate with best trial-adjusted p-value and positive median excess (or lowest fee-adjusted loss)
    best_entry = min(
        trials_log,
        key=lambda item: (
            item["diagnostics"]["trial_adjusted_p_value"],
            -item["diagnostics"]["median_excess_bps"],
        ),
    )
    return {
        "model_id": model_id,
        "trials_run": len(trials_log),
        "budget_max": ledger.max_trials,
        "selected_spec_hash": best_entry["spec_hash"],
        "selected_spec": best_entry["spec"],
        "trials": trials_log,
        "excess_vectors": excess_vectors,
        "ledger_head_hash": ledger.head_hash(),
    }


def draft_verdict_memo(verdict: VerdictRecord, model_id: str = DEFAULT_MODEL_ID) -> str:
    """Draft a concise plain-English audit summary strictly from the locked VerdictRecord numbers."""
    v = verdict.to_dict()
    deterministic_memo = (
        f"Verdict: {verdict.verdict}. Spec {verdict.spec_hash[:10]} ({verdict.template}) was evaluated once on "
        f"{verdict.paths_tested} unseen market paths after {verdict.total_trials_run} registered training trials "
        f"(effective independent trials K_eff={verdict.effective_trials_k_eff:.2f}). "
        f"It recorded {verdict.wins_vs_buy_and_hold} wins, {verdict.losses_vs_buy_and_hold} losses, and "
        f"{verdict.ties_vs_buy_and_hold} ties vs Buy-and-Hold, with median excess return {verdict.median_excess_bps:+d} bps "
        f"and mean max drawdown {verdict.mean_max_drawdown_bps} bps. "
        f"Raw binomial sign-test p={verdict.raw_sign_p_value:.4f} adjusted to p_adj={verdict.trial_adjusted_p_value:.4f} "
        f"(Deflated Sharpe probability={verdict.deflated_sharpe_prob:.4f}; MDE={verdict.min_detectable_excess_bps} bps). "
        f"Ledger anchor: {verdict.ledger_head_hash[:12]}."
    )
    prompt = (
        "Write a 3-sentence plain-English institutional audit summary of this VerdictRecord JSON. "
        "Every single number you mention MUST appear verbatim in the JSON below; do not invent or round any statistic.\n"
        f"{json.dumps(v)}"
    )
    llm_resp = _call_gemini_json(prompt, model_id=model_id)
    if isinstance(llm_resp, dict) and isinstance(llm_resp.get("memo"), str):
        return llm_resp["memo"]
    return deterministic_memo
