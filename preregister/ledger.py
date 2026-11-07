"""Append-only SHA-256 hash-chained trial ledger and holdout gate."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from preregister.schemas import canonical_json, sha256_hex


class LedgerViolationError(RuntimeError):
    """Raised when the trial budget is exhausted or an illegal holdout read is attempted."""


class TrialLedger:
    """Persistent, tamper-evident hash-chained ledger of every spec lock, trial, and denial."""

    def __init__(self, ledger_path: Path, max_trials: int = 12) -> None:
        self.ledger_path = ledger_path
        self.max_trials = max_trials
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            self.ledger_path.write_text("", encoding="utf-8")

    def entries(self) -> list[dict[str, Any]]:
        lines = [
            line.strip()
            for line in self.ledger_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return [json.loads(line) for line in lines]

    def head_hash(self) -> str:
        items = self.entries()
        return items[-1]["entry_hash"] if items else "GENESIS"

    def verify_chain(self) -> bool:
        """Verify that no historical entry has been modified or reordered."""
        prev = "GENESIS"
        for idx, item in enumerate(self.entries(), start=1):
            if item.get("seq") != idx or item.get("prev_hash") != prev:
                return False
            check_payload = {k: v for k, v in item.items() if k != "entry_hash"}
            if sha256_hex(check_payload) != item.get("entry_hash"):
                return False
            prev = item["entry_hash"]
        return True

    def _append(self, event: str, spec_hash: str, payload: dict[str, Any]) -> dict[str, Any]:
        items = self.entries()
        seq = len(items) + 1
        prev_hash = items[-1]["entry_hash"] if items else "GENESIS"
        record_body = {
            "seq": seq,
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "spec_hash": spec_hash,
            "payload_hash": sha256_hex(payload),
            "payload": payload,
            "prev_hash": prev_hash,
        }
        entry_hash = sha256_hex(record_body)
        full_record = {**record_body, "entry_hash": entry_hash}
        with self.ledger_path.open("a", encoding="utf-8") as stream:
            stream.write(canonical_json(full_record) + "\n")
        head_file = self.ledger_path.parent / "HEAD_HASH.txt"
        head_file.write_text(entry_hash + "\n", encoding="utf-8")
        return full_record

    def trial_count(self) -> int:
        return sum(1 for item in self.entries() if item["event"] == "train_trial")

    def is_locked(self, spec_hash: str) -> bool:
        return any(
            item["event"] == "lock_spec" and item["spec_hash"] == spec_hash
            for item in self.entries()
        )

    def lock_spec(self, spec_hash: str, spec_dict: dict[str, Any]) -> dict[str, Any]:
        return self._append("lock_spec", spec_hash, spec_dict)

    def charge_train_trial(self, spec_hash: str, summary: dict[str, Any]) -> dict[str, Any]:
        if not self.is_locked(spec_hash):
            self._append("unregistered_denied", spec_hash, {"reason": "Spec not locked before train run"})
            raise LedgerViolationError(f"Spec {spec_hash[:10]} must be locked before running a backtest.")
        current = self.trial_count()
        if current >= self.max_trials:
            self._append(
                "budget_denied",
                spec_hash,
                {"trial_attempted": current + 1, "max_trials": self.max_trials},
            )
            raise LedgerViolationError(
                f"Trial budget exhausted ({current}/{self.max_trials} trials used). Refusing further backtests."
            )
        return self._append("train_trial", spec_hash, {"trial_number": current + 1, **summary})

    def record_human_signoff(self, spec_hash: str, reviewer: str = "human_operator") -> dict[str, Any]:
        if not self.is_locked(spec_hash):
            raise LedgerViolationError("Cannot sign off on an unlocked spec.")
        return self._append("human_signoff", spec_hash, {"reviewer": reviewer})

    def authorize_holdout_run(self, spec_hash: str) -> dict[str, Any]:
        items = self.entries()
        if not any(i["event"] == "human_signoff" and i["spec_hash"] == spec_hash for i in items):
            self._append(
                "holdout_denied",
                spec_hash,
                {"reason": "Attempted holdout evaluation without prior human_signoff"},
            )
            raise LedgerViolationError("Holdout evaluation denied: missing human sign-off.")
        if any(i["event"] == "holdout_run" and i["spec_hash"] == spec_hash for i in items):
            self._append(
                "holdout_denied",
                spec_hash,
                {"reason": "Single-use holdout lock: spec_hash already evaluated on holdout"},
            )
            raise LedgerViolationError(
                f"Holdout evaluation denied: spec {spec_hash[:10]} already consumed its one-shot holdout test."
            )
        return self._append("holdout_run", spec_hash, {"trials_charged": self.trial_count()})
