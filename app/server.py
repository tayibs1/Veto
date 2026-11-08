#!/usr/bin/env python3
"""Preregister Operate Web UI Server (Python 3.11+ stdlib only, zero build step)."""

from __future__ import annotations
import json
import os
import sys
import tempfile
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

class DemoSessionState:
    def __init__(self) -> None:
        self.tmp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.reset()

    def reset(self) -> None:
        if self.tmp_dir is not None:
            self.tmp_dir.cleanup()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.ledger = TrialLedger(Path(self.tmp_dir.name) / "session_ledger.jsonl", max_trials=12)
        self.train_cases = generate_market_windows(36, seed=808)
        self.holdout_cases = generate_market_windows(36, seed=10808)
        self.current_spec: HunchSpec | None = None
        self.last_loop: dict[str, Any] | None = None
        self.kill_switch: bool = False

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
                if ext == ".html": ct = "text/html; charset=utf-8"
                elif ext == ".css": ct = "text/css; charset=utf-8"
                elif ext == ".js": ct = "application/javascript; charset=utf-8"
                elif ext == ".json": ct = "application/json; charset=utf-8"
                elif ext == ".svg": ct = "image/svg+xml; charset=utf-8"
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
            self._send_json({
                "verified": STATE.ledger.verify_chain(),
                "trials_used": STATE.ledger.trial_count(),
                "max_trials": STATE.ledger.max_trials,
                "head_hash": STATE.ledger.head_hash(),
                "entries": STATE.ledger.entries(),
            })
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
        
        if parsed.path == "/api/reset":
            STATE.reset()
            self._send_json({"status": "reset"})
            return
        
        if parsed.path == "/api/translate":
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
            self._send_json(result)
            return
            
        if parsed.path == "/api/lock":
            if STATE.current_spec is None:
                self._send_json({"error": "Translate a valid HunchSpec before locking."}, HTTPStatus.BAD_REQUEST)
                return
            entry = STATE.ledger.lock_spec(STATE.current_spec.spec_hash(), STATE.current_spec.to_dict())
            self._send_json({"status": "locked", "entry": entry})
            return
            
        if parsed.path == "/api/research":
            if STATE.current_spec is None:
                self._send_json({"error": "Lock a valid HunchSpec before running research."}, HTTPStatus.BAD_REQUEST)
                return
            steps = int(body.get("steps", 4))
            try:
                loop_out = run_research_loop(STATE.current_spec, STATE.train_cases, STATE.ledger, max_steps=steps)
                STATE.last_loop = loop_out
                sel = loop_out["selected_spec"]
                STATE.current_spec = HunchSpec(
                    template=sel["template"],
                    params=sel["params"],
                    source_quotes=sel.get("source_quotes", {}),
                    defaults_used=sel.get("defaults_used", []),
                    rationale=sel.get("rationale", ""),
                )
                self._send_json(loop_out)
            except LedgerViolationError as err:
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
                    self._send_json({"status": "denied", "message": str(err)})
                    return
                STATE.ledger.max_trials = old_max
            else:
                try:
                    STATE.ledger.authorize_holdout_run(shash)
                except LedgerViolationError as err:
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
                vecs = STATE.last_loop["excess_vectors"] if STATE.last_loop else []
                trials_run = max(1, STATE.ledger.trial_count())
                verdict = build_verdict(
                    STATE.current_spec,
                    STATE.holdout_cases,
                    total_trials_run=trials_run,
                    prior_excess_vectors=vecs,
                    ledger_head_hash=STATE.ledger.head_hash(),
                )
                memo = draft_verdict_memo(verdict)
                self._send_json({"verdict": verdict.to_dict(), "memo": memo})
            except LedgerViolationError as err:
                self._send_json({"error": str(err)}, HTTPStatus.BAD_REQUEST)
            return
            
        if parsed.path == "/api/gate_test":
            mode = str(body.get("mode", "normal"))
            if mode == "kill_switch":
                STATE.kill_switch = not STATE.kill_switch
            
            # TRUTH FIX 1: High Fee is 1100p to guarantee a breach of the 250bps hurdle
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

def run_server(host: str = "127.0.0.1", port: int | None = None) -> None:
    actual_port = int(os.environ.get("PORT", str(port or 8765)))
    server = HTTPServer((host, actual_port), PreregisterHandler)
    print(f"Preregister Operate UI running on http://{host}:{actual_port}", flush=True)
    server.serve_forever()

if __name__ == "__main__":
    run_server()
