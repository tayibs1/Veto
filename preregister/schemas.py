"""Strict data contracts for Preregister. Plain Python stdlib only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


def canonical_json(data: Any) -> str:
    """Deterministic JSON encoding with sorted keys and no NaN/Infinity."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_hex(data: Any) -> str:
    """SHA-256 hex digest of a canonical JSON object or raw string."""
    raw = data if isinstance(data, str) else canonical_json(data)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HunchSpec:
    """A pre-registered strategy specification within the 3-template log-return grammar."""

    template: str
    params: dict[str, float | int]
    source_quotes: dict[str, str]
    defaults_used: list[str] = field(default_factory=list)
    rationale: str = ""

    def canonical_payload(self) -> dict[str, Any]:
        """Hashable specification payload (excludes free-text rationale and quotes)."""
        return {
            "template": self.template,
            "params": {
                k: round(float(v), 6) if isinstance(v, float) else int(v)
                for k, v in sorted(self.params.items())
            },
        }

    def spec_hash(self) -> str:
        return sha256_hex(self.canonical_payload())

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["spec_hash"] = self.spec_hash()
        return out


@dataclass(frozen=True)
class TrialDiagnostics:
    """Direction-agnostic observable training diagnostics returned to the Argon researcher."""

    spec_hash: str
    trial_number: int
    budget_remaining: int
    paths_evaluated: int
    wins_vs_buy_and_hold: int
    losses_vs_buy_and_hold: int
    ties_vs_buy_and_hold: int
    median_excess_bps: int
    mean_max_drawdown_bps: int
    pos_drift_win_rate: float
    neg_drift_win_rate: float
    high_cost_excess_bps: int
    low_cost_excess_bps: int
    mean_fee_drag_bps: int
    mean_trades_per_path: float
    raw_sign_p_value: float
    trial_adjusted_p_value: float
    deflated_sharpe_prob: float
    effective_trials_k_eff: float
    excess_vector_bps: list[int] = field(default_factory=list)

    def agent_view(self) -> dict[str, Any]:
        """Sanitized summary exposed to the LLM researcher (excludes raw path vectors)."""
        d = asdict(self)
        d.pop("excess_vector_bps", None)
        return d


@dataclass(frozen=True)
class VerdictRecord:
    """Final deterministic referee verdict on unseen evaluation paths."""

    spec_hash: str
    template: str
    params: dict[str, float | int]
    total_trials_run: int
    effective_trials_k_eff: float
    paths_tested: int
    wins_vs_buy_and_hold: int
    losses_vs_buy_and_hold: int
    ties_vs_buy_and_hold: int
    median_excess_bps: int
    mean_max_drawdown_bps: int
    raw_sign_p_value: float
    trial_adjusted_p_value: float
    observed_sharpe: float
    deflated_sharpe_prob: float
    min_detectable_excess_bps: int
    verdict: str  # "SURVIVES" | "DOES_NOT_SURVIVE" | "UNDERPOWERED"
    reasons: list[str]
    ledger_head_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
