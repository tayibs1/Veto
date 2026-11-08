#!/usr/bin/env python3
"""Preregister Operate Web UI Server (Python 3.11+ stdlib only, zero build step)."""

from __future__ import annotations
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.run_ablation import generate_market_windows
from preregister.agent import PRESET_HUNCHES, draft_verdict_memo, run_research_loop, translate_hunch
from preregister.backtest import build_verdict
from preregister.gate import RiskPolicy, enforce_order_gate
from preregister.ledger import LedgerViolationError, TrialLedger
from preregister.schemas import HunchSpec

RUN_LOG_FIELDS = ("seq", "ts", "event", "spec_hash", "prev_hash", "entry_hash")


class DemoSessionState:
    def __init__(self) -> None:
        self.tmp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.runs: list[dict[str, Any]] = []  # Survives clear and reset; this is the run log.
        self.run_log_path: Path | None = None
        self.reset()

    def clear_inputs(self) -> None:
        """Clear current hunch/spec inputs and per-hunch trial meter while preserving the cumulative SHA-256 ledger and K_eff history."""
        self.current_spec = None
        self.last_loop = None
        self.kill_switch = False
        self.current_run = None
        self.run_committed = False
        self.hunch_trial_offset: int = self.ledger.trial_count()

    def reset(self) -> None:
        """Full session initialization (or hard session reset)."""
        if self.tmp_dir is not None:
            self.tmp_dir.cleanup()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.ledger = TrialLedger(Path(self.tmp_dir.name) / "session_ledger.jsonl", max_trials=12)
        self.train_cases = generate_market_windows(36, seed=808)
        self.holdout_cases = generate_market_windows(36, seed=10808)
        self.all_excess_vectors: list[list[int]] = []
        self.hunch_trial_offset = 0
        self.clear_inputs()

    def load_run_log(self, path: Path) -> None:
        self.run_log_path = path
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
            self.runs = [json.loads(line) for line in lines if line.strip()]

    def start_run(self, hunch: str, chart: str | None) -> dict[str, Any]:
        run: dict[str, Any] = {
            "id": uuid.uuid4().hex[:8],
            "started": datetime.now(timezone.utc).isoformat(),
            "hunch": hunch,
            "chart": chart,
            "status": "started",
        }
        self.runs.append(run)
        self.current_run = run
        return run

    def update_run(self, **fields: Any) -> None:
        """Snapshot the current session's hashes into the run log."""
        if self.current_run is None:
            self.start_run("(control test, no hunch translated)", None)
        run = self.current_run
        run.update(fields)
        entries = self.ledger.entries()
        run["ledger"] = [{k: e.get(k) for k in RUN_LOG_FIELDS} for e in entries]
        run["head_hash"] = self.ledger.head_hash()
        run["verified"] = self.ledger.verify_chain()
        run["trials_used"] = self.ledger.trial_count()
        if self.run_log_path is not None:
            text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in self.runs)
            self.run_log_path.write_text(text, encoding="utf-8")


STATE = DemoSessionState()


class PreregisterHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        # Static Routing
        if parsed.path == "/":
            index_path = ROOT / "app" / "static" / "index.html"
            if index_path.exists():
                raw = index_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return

        if parsed.path.startswith("/static/"):
            file_path = ROOT / "app" / parsed.path.lstrip("/")
            if file_path.exists() and file_path.is_file():
                ext = file_path.suffix
                ct = "text/plain"
                if ext == ".html":
                    ct = "text/html; charset=utf-8"
                elif ext == ".css":
                    ct = "text/css; charset=utf-8"
                elif ext == ".js":
                    ct = "application/javascript; charset=utf-8"
                elif ext == ".json":
                    ct = "application/json; charset=utf-8"
                elif ext == ".svg":
                    ct = "image/svg+xml; charset=utf-8"
                raw = file_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            else:
                self.send_response(HTTPStatus.NOT_FOUND)
                self.end_headers()
                return

        # API Routes
        if parsed.path == "/api/preset":
            key = parsed.query.split("key=")[-1] if "key=" in parsed.query else "cost_gated_reversion"
            preset = PRESET_HUNCHES.get(key, PRESET_HUNCHES["cost_gated_reversion"])
            self._send_json(preset)
            return
        if parsed.path == "/api/chart":
            name = parsed.query.split("name=")[-1] if "name=" in parsed.query else "chart_3_cost_gated_reversion.svg"
            chart_file = ROOT / "preregister" / "fixtures" / "charts" / Path(name).name
            if chart_file.exists():
                raw = chart_file.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            self._send_json({"error": "chart_not_found"}, HTTPStatus.NOT_FOUND)
            return
        if parsed.path == "/api/ledger":
            total_trials = STATE.ledger.trial_count()
            hunch_trials = max(0, total_trials - getattr(STATE, "hunch_trial_offset", 0))
            self._send_json({
                "verified": STATE.ledger.verify_chain(),
                "trials_used": hunch_trials,
                "session_trials_used": total_trials,
                "max_trials": 12,
                "head_hash": STATE.ledger.head_hash(),
                "entries": STATE.ledger.entries(),
            })
            return
        if parsed.path == "/api/runs":
            self._send_json({"runs": list(reversed(STATE.runs))})
            return
        if parsed.path == "/api/ablation":
            abl_path = ROOT / "eval" / "results" / "ablation_summary.json"
            grav_path = ROOT / "preregister" / "fixtures" / "graveyard.json"
            ablation = json.loads(abl_path.read_text(encoding="utf-8")) if abl_path.exists() else {"arms": {}}
            graveyard = json.loads(grav_path.read_text(encoding="utf-8")) if grav_path.exists() else []
            self._send_json({"ablation": ablation, "graveyard": graveyard})
            return
        self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self._read_body()

        if parsed.path == "/api/reset_trials":
            STATE.hunch_trial_offset = STATE.ledger.trial_count()
            STATE.ledger.max_trials = STATE.hunch_trial_offset + 12
            self._send_json({
                "status": "trials_reset",
                "trials_used": 0,
                "session_trials_used": STATE.ledger.trial_count(),
                "head_hash": STATE.ledger.head_hash(),
            })
            return

        if parsed.path == "/api/clear":
            STATE.clear_inputs()
            STATE.ledger.max_trials = STATE.hunch_trial_offset + 12
            self._send_json({
                "status": "cleared",
                "trials_used": 0,
                "session_trials_used": STATE.ledger.trial_count(),
                "head_hash": STATE.ledger.head_hash(),
            })
            return

        if parsed.path == "/api/reset":
            # Default to clearing inputs while preserving cumulative ledger tail, unless hard=True is explicitly requested
            if body.get("hard") is True:
                STATE.reset()
                self._send_json({"status": "reset", "hard": True})
            else:
                STATE.clear_inputs()
                STATE.ledger.max_trials = STATE.hunch_trial_offset + 12
                self._send_json({
                    "status": "cleared",
                    "hard": False,
                    "trials_used": 0,
                    "session_trials_used": STATE.ledger.trial_count(),
                    "head_hash": STATE.ledger.head_hash(),
                })
            return

        if parsed.path == "/api/translate":
            if STATE.run_committed:
                self._send_json(
                    {"error": "This hunch is locked to the ledger. Click 'Clear Inputs (Keep Ledger)' to test another hunch on the cumulative chain."},
                    HTTPStatus.CONFLICT,
                )
                return
            text = str(body.get("text", ""))
            chart_name = body.get("chart")
            img_path = ROOT / "preregister" / "fixtures" / "charts" / Path(str(chart_name)).name if chart_name else None
            result = translate_hunch(text, image_path=img_path)
            if result["status"] == "ok":
                sp_dict = result["spec"]
                STATE.current_spec = HunchSpec(
                    template=sp_dict["template"],
                    params=sp_dict["params"],
                    source_quotes=sp_dict["source_quotes"],
                    defaults_used=sp_dict["defaults_used"],
                    rationale=sp_dict.get("rationale", ""),
                )
            else:
                STATE.current_spec = None
            STATE.start_run(text, str(chart_name) if chart_name else None)
            STATE.update_run(
                status="translated" if result["status"] == "ok" else "refused",
                engine=result.get("engine"),
                reason=result.get("reason"),
                spec=result.get("spec"),
                spec_hash=STATE.current_spec.spec_hash() if STATE.current_spec else None,
            )
            self._send_json(result)
            return

        if parsed.path == "/api/lock":
            if STATE.current_spec is None:
                self._send_json({"error": "Translate a valid HunchSpec before locking."}, HTTPStatus.BAD_REQUEST)
                return
            entry = STATE.ledger.lock_spec(STATE.current_spec.spec_hash(), STATE.current_spec.to_dict())
            STATE.run_committed = True
            STATE.update_run(status="locked")
            self._send_json({"status": "locked", "entry": entry})
            return

        if parsed.path == "/api/research":
            if STATE.current_spec is None:
                self._send_json({"error": "Lock a valid HunchSpec before running research."}, HTTPStatus.BAD_REQUEST)
                return
            steps = int(body.get("steps", 4))
            try:
                loop_out = run_research_loop(
                    STATE.current_spec,
                    STATE.train_cases,
                    STATE.ledger,
                    max_steps=steps,
                    prior_excess_vectors=STATE.all_excess_vectors,
                )
                STATE.last_loop = loop_out
                STATE.run_committed = True
                STATE.all_excess_vectors.extend(loop_out["excess_vectors"])
                sel = loop_out["selected_spec"]
                STATE.current_spec = HunchSpec(
                    template=sel["template"],
                    params=sel["params"],
                    source_quotes=sel.get("source_quotes", {}),
                    defaults_used=sel.get("defaults_used", []),
                    rationale=sel.get("rationale", ""),
                )
                STATE.update_run(status="researched", selected_spec_hash=loop_out["selected_spec_hash"], selected_spec=sel)
                self._send_json(loop_out)
            except LedgerViolationError as err:
                STATE.update_run()
                self._send_json({"error": str(err)}, HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/force_denial":
            kind = str(body.get("kind", "budget"))
            sp = STATE.current_spec or HunchSpec(
                template="cost_gated_log_mean_reversion",
                params={"lookback_bars": 12, "entry_z": 1.65, "hold_bars": 8, "cost_hurdle_mult": 1.5, "trend_filter_bars": 24},
                source_quotes={"lookback_bars": "12-bar", "entry_z": "1.65 sigma", "hold_bars": "hold for 8 bars"},
            )
            shash = sp.spec_hash()
            if not STATE.ledger.is_locked(shash):
                STATE.ledger.lock_spec(shash, sp.to_dict())
            if kind == "budget":
                old_max = STATE.ledger.max_trials
                STATE.ledger.max_trials = STATE.ledger.trial_count()
                try:
                    STATE.ledger.charge_train_trial(shash, {"attempted": "over_budget"})
                except LedgerViolationError as err:
                    STATE.ledger.max_trials = old_max
                    STATE.update_run()
                    self._send_json({"status": "denied", "message": str(err)})
                    return
                STATE.ledger.max_trials = old_max
            else:
                try:
                    STATE.ledger.authorize_holdout_run(shash)
                except LedgerViolationError as err:
                    STATE.update_run()
                    self._send_json({"status": "denied", "message": str(err)})
                    return
            self._send_json({"status": "ok", "message": "No denial triggered"})
            return

        if parsed.path == "/api/verdict":
            if STATE.current_spec is None:
                self._send_json({"error": "No locked candidate selected."}, HTTPStatus.BAD_REQUEST)
                return
            shash = STATE.current_spec.spec_hash()
            if not STATE.ledger.is_locked(shash):
                STATE.ledger.lock_spec(shash, STATE.current_spec.to_dict())
            try:
                STATE.ledger.record_human_signoff(shash, reviewer="human_operator")
                STATE.ledger.authorize_holdout_run(shash)
                vecs = STATE.all_excess_vectors
                trials_run = max(1, STATE.ledger.trial_count())
                verdict = build_verdict(
                    STATE.current_spec,
                    STATE.holdout_cases,
                    total_trials_run=trials_run,
                    prior_excess_vectors=vecs,
                    ledger_head_hash=STATE.ledger.head_hash(),
                )
                memo = draft_verdict_memo(verdict)
                STATE.run_committed = True
                STATE.update_run(status="verdict", verdict=verdict.to_dict(), memo=memo)
                self._send_json({"verdict": verdict.to_dict(), "memo": memo})
            except LedgerViolationError as err:
                STATE.update_run()
                self._send_json({"error": str(err)}, HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/gate_test":
            mode = str(body.get("mode", "normal"))
            if mode == "kill_switch":
                STATE.kill_switch = not STATE.kill_switch

            # High Fee is 1100p to guarantee a breach of the 250bps hurdle
            fee = 1100 if mode == "high_fee" else 40
            bps = 35 if mode == "high_fee" else 10
            cash = 100000
            policy = RiskPolicy(kill_switch_engaged=STATE.kill_switch)
            act, reason = enforce_order_gate(
                "buy",
                price_pence=10000,
                cash_pence=cash,
                shares=0,
                fee_pence=fee,
                slippage_bps=bps,
                current_drawdown_bps=200,
                policy=policy,
            )
            rt_cost_bps = ((2 * fee * 10000) // cash) + 2 * bps
            self._send_json({"approved_action": act, "reason": reason, "rt_cost_bps": rt_cost_bps})
            return

        self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)


def load_windows_user_key() -> None:
    """Shells opened before the key was saved don't inherit it, so read it from the user's settings."""
    if os.name != "nt" or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env_key:
            value, _ = winreg.QueryValueEx(env_key, "GEMINI_API_KEY")
    except OSError:
        return
    if value:
        os.environ["GEMINI_API_KEY"] = str(value)


def run_server(host: str = "127.0.0.1", port: int | None = None) -> None:
    load_windows_user_key()
    has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    print(f"Gemini 4 Argon key: {'found' if has_key else 'MISSING, using offline parser'}", flush=True)
    actual_port = int(os.environ.get("PORT", str(port or 8765)))
    # On Windows, address reuse lets several servers share one port, so stale code keeps answering.
    HTTPServer.allow_reuse_address = os.name != "nt"
    STATE.load_run_log(ROOT / "ledger" / "run_log.jsonl")
    server = HTTPServer((host, actual_port), PreregisterHandler)
    print(f"Preregister Operate UI running on http://{host}:{actual_port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run_server()
