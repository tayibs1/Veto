#!/usr/bin/env python3
"""Preregister Operate Web UI Server (Python 3.11+ stdlib only, zero build step).

Provides:
- Panel 1: Multimodal Hunch Intake (Annotated Chart SVG + Text -> HunchSpec JSON) + Ambiguity Refusal Gate
- Panel 2: Bounded 12-Trial Gemini 4 Argon Diagnostic Research Loop + Budget/Lock Denial Controls
- Panel 3: Cryptographic SHA-256 Hash-Chained Ledger Inspector (Live Verification)
- Panel 4: Human Sign-Off, One-Shot Unseen Holdout Verdict, Paper-Order Risk Gate, and 3-Way Ablation & Graveyard
"""

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
from preregister.agent import (
    PRESET_HUNCHES,
    draft_verdict_memo,
    run_research_loop,
    translate_hunch,
)
from preregister.backtest import build_verdict
from preregister.gate import RiskPolicy, enforce_order_gate
from preregister.ledger import LedgerViolationError, TrialLedger
from preregister.schemas import HunchSpec


class DemoSessionState:
    """In-memory + ledger-backed interactive state for the Operate UI."""

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

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Hunch. | Deterministic AI Referee</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #000000;
    --surface: rgba(255, 255, 255, 0.03);
    --surface-hover: rgba(255, 255, 255, 0.08);
    --border: rgba(255, 255, 255, 0.1);
    --text-primary: #FFFFFF;
    --text-secondary: #888888;
    --accent: #FFFFFF;
    --success: #34C759;
    --danger: #FF3B30;
    --argon: #0A84FF;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  
  body { 
    background-color: var(--bg); 
    color: var(--text-primary); 
    font-family: 'Inter', -apple-system, sans-serif; 
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
  }

  /* Typography */
  h1 { font-size: 2.5rem; font-weight: 300; letter-spacing: -0.04em; margin-bottom: 0.2rem; }
  h2 { font-size: 1.1rem; font-weight: 500; letter-spacing: -0.01em; margin-bottom: 1.5rem; color: var(--text-secondary); }
  h3 { font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-secondary); margin-bottom: 1rem; }
  
  .mono { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-variant-numeric: tabular-nums; }

  /* Layout */
  .container { max-width: 800px; margin: 0 auto; padding: 4rem 2rem; }
  
  header { margin-bottom: 4rem; text-align: center; }
  .status-bar { 
    display: inline-flex; gap: 1rem; align-items: center; justify-content: center;
    padding: 0.5rem 1rem; border-radius: 99px; background: var(--surface); border: 1px solid var(--border);
    margin-top: 2rem; backdrop-filter: blur(10px);
  }
  
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
  .dot.argon { background: var(--argon); box-shadow: 0 0 10px var(--argon); }
  .dot.secure { background: var(--success); box-shadow: 0 0 10px var(--success); }

  /* Section Styling (Apple-like Cards) */
  section { 
    background: var(--surface); border: 1px solid var(--border); 
    border-radius: 24px; padding: 2.5rem; margin-bottom: 2rem;
    backdrop-filter: blur(20px);
    opacity: 0; transform: translateY(20px);
    animation: fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  
  @keyframes fadeUp {
    to { opacity: 1; transform: translateY(0); }
  }

  section:nth-child(1) { animation-delay: 0.1s; }
  section:nth-child(2) { animation-delay: 0.2s; }
  section:nth-child(3) { animation-delay: 0.3s; }
  section:nth-child(4) { animation-delay: 0.4s; }

  /* Inputs & Controls */
  input[type="text"] {
    width: 100%; background: transparent; color: var(--text-primary);
    border: none; border-bottom: 1px solid var(--border);
    padding: 1rem 0; font-size: 1.1rem; font-family: 'Inter', sans-serif;
    margin-bottom: 2rem; outline: none; transition: border-color 0.3s;
  }
  input[type="text"]:focus { border-bottom-color: var(--accent); }

  .btn-row { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 2rem; }
  
  button {
    background: var(--surface); color: var(--text-primary);
    border: 1px solid var(--border); border-radius: 99px;
    padding: 0.75rem 1.5rem; font-size: 0.9rem; font-weight: 500;
    cursor: pointer; transition: all 0.2s ease;
    backdrop-filter: blur(10px);
  }
  button:hover { background: var(--surface-hover); transform: scale(1.02); }
  button.primary { background: var(--text-primary); color: var(--bg); border: none; }
  button.primary:hover { background: #E0E0E0; }
  button.danger { color: var(--danger); border-color: rgba(255,59,48,0.3); }
  button.danger:hover { background: rgba(255,59,48,0.1); }
  button.success { color: var(--success); border-color: rgba(52,199,89,0.3); }
  button.success:hover { background: rgba(52,199,89,0.1); }

  /* Visual Elements */
  #chartPreview { 
    margin-bottom: 2rem; border-radius: 12px; overflow: hidden; 
    border: 1px solid var(--border); background: #050505;
  }
  #chartPreview svg { width: 100%; height: auto; display: block; }
  
  pre { 
    background: #050505; border: 1px solid var(--border); border-radius: 12px; 
    padding: 1.5rem; overflow-x: auto; color: #A0A0A0; 
  }

  /* Minimalist Data Rows */
  .data-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 1rem 0; border-bottom: 1px solid var(--border);
  }
  .data-row:last-child { border-bottom: none; }
  .data-label { color: var(--text-secondary); font-size: 0.9rem; }
  .data-value { font-weight: 500; }

  /* Tags & Badges */
  .tag { 
    font-size: 0.75rem; padding: 0.25rem 0.75rem; border-radius: 99px; 
    border: 1px solid var(--border); display: inline-flex; align-items: center; gap: 6px;
  }
  .tag.red { color: var(--danger); border-color: rgba(255,59,48,0.3); background: rgba(255,59,48,0.1); }
  .tag.green { color: var(--success); border-color: rgba(52,199,89,0.3); background: rgba(52,199,89,0.1); }
  .tag.blue { color: var(--argon); border-color: rgba(10,132,255,0.3); background: rgba(10,132,255,0.1); }

  .notice { padding: 1rem; border-radius: 12px; margin-bottom: 1rem; font-size: 0.9rem; border: 1px solid var(--border); }
  .notice.error { border-color: var(--danger); color: var(--danger); background: rgba(255,59,48,0.05); }

</style>
</head>
<body>

<div class="container">
  <header>
    <h1>Hunch.</h1>
    <h2>The Deterministic Referee for AI Quants</h2>
    <div class="status-bar mono">
      <span><span class="dot argon"></span> Gemini 4 Argon</span>
      <span id="budgetBadge"><span class="dot secure"></span> 0/12 Trials</span>
      <span id="chainBadge"><span class="dot secure"></span> SHA-256 Ledger Locked</span>
    </div>
  </header>

  <!-- Step 1 -->
  <section>
    <h3>01 &middot; Multimodal Intake</h3>
    <div class="btn-row">
      <button onclick="loadPreset('ambiguous_dip')">Missing Specs (Fail)</button>
      <button onclick="loadPreset('naive_churn')">High-Fee Churn</button>
      <button onclick="loadPreset('cost_gated_reversion')" class="primary">Cost-Gated Reversion</button>
    </div>
    
    <div id="chartPreview"></div>
    <input type="text" id="hunchInput" placeholder="Describe the strategy logic..." />
    
    <div class="btn-row">
      <button onclick="translateHunch()">Translate (Gemini 4)</button>
      <button onclick="lockCurrentSpec()" class="success">Human Sign-off & Lock</button>
    </div>
    
    <div id="intakeStatus"></div>
    <pre class="mono" id="specPreview">// Awaiting translation...</pre>
  </section>

  <!-- Step 2 -->
  <section>
    <h3>02 &middot; 12-Trial Diagnostic Loop</h3>
    <div class="btn-row">
      <button onclick="runResearch(4)" class="primary">Run Argon Loop</button>
      <button onclick="forceBudgetDenial()" class="danger">Force Over-Budget Refusal</button>
      <button onclick="forceEarlyHoldoutDenial()" class="danger">Attempt Unseen Read Refusal</button>
    </div>
    <div id="loopNotice"></div>
    <div id="trialsList">
      <div class="data-row"><span class="data-label">Awaiting diagnostic execution...</span></div>
    </div>
  </section>

  <!-- Step 3 -->
  <section>
    <h3>03 &middot; Immutable Ledger</h3>
    <div id="ledgerList" class="mono">
      <div class="data-row"><span class="data-label">GENESIS</span></div>
    </div>
  </section>

  <!-- Step 4 -->
  <section>
    <h3>04 &middot; The Unseen Verdict</h3>
    <div class="btn-row">
      <button onclick="runHoldoutVerdict()" class="success">Unlock One-Shot Verdict</button>
      <button onclick="testOrderGate('high_fee')" class="danger">Test Paper-Order Circuit Breaker</button>
    </div>
    <div id="gateBox" style="margin-bottom: 1rem;"></div>
    <div id="verdictBox">
      <div class="data-row"><span class="data-label">Waiting for human sign-off on a locked candidate...</span></div>
    </div>
  </section>
</div>

<script>
let currentChartName = "chart_3_cost_gated_reversion.svg";

async function loadChart(name) {
  currentChartName = name;
  const res = await fetch("/api/chart?name=" + encodeURIComponent(name));
  if (res.ok) document.getElementById("chartPreview").innerHTML = await res.text();
}

async function loadPreset(key) {
  const res = await fetch("/api/preset?key=" + encodeURIComponent(key));
  const data = await res.json();
  document.getElementById("hunchInput").value = data.text;
  await loadChart(data.chart);
  await translateHunch(key);
}

async function translateHunch(presetKey) {
  const text = document.getElementById("hunchInput").value;
  const res = await fetch("/api/translate", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({text: presetKey || text, chart: currentChartName}) });
  const data = await res.json();
  const statusEl = document.getElementById("intakeStatus");
  const preEl = document.getElementById("specPreview");
  
  if (data.status === "refused") {
    statusEl.innerHTML = '<div class="notice error"><strong>Grammar Refusal:</strong> ' + data.reason + '</div>';
    preEl.textContent = JSON.stringify(data.partial_candidate, null, 2);
  } else {
    statusEl.innerHTML = '<div style="margin-bottom:1rem;"><span class="tag green"><span class="dot secure"></span> Validated Spec</span> <span class="mono" style="margin-left:10px; color:var(--text-secondary);">Hash: ' + data.spec.spec_hash.slice(0,16) + '...</span></div>';
    preEl.textContent = JSON.stringify(data.spec, null, 2);
  }
  await refreshLedger();
}

async function lockCurrentSpec() {
  const res = await fetch("/api/lock", {method: "POST"});
  const data = await res.json();
  const statusEl = document.getElementById("intakeStatus");
  if (data.error) {
    statusEl.innerHTML = '<div class="notice error">' + data.error + '</div>';
  } else {
    statusEl.innerHTML = '<div style="margin-bottom:1rem;"><span class="tag green"><span class="dot secure"></span> Locked to Ledger</span> <span class="mono" style="margin-left:10px; color:var(--text-secondary);">Entry: ' + data.entry.entry_hash.slice(0, 16) + '...</span></div>';
  }
  await refreshLedger();
}

async function runResearch(steps) {
  const res = await fetch("/api/research", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({steps: steps}) });
  const data = await res.json();
  const notice = document.getElementById("loopNotice");
  if (data.error) {
    notice.innerHTML = '<div class="notice error">' + data.error + '</div>';
  } else {
    notice.innerHTML = '<div style="margin-bottom:1rem;"><span class="tag blue">Selected: ' + data.selected_spec_hash.slice(0, 8) + '</span></div>';
    const list = document.getElementById("trialsList");
    list.innerHTML = data.trials.map(t => {
      const d = t.diagnostics;
      return '<div class="data-row" style="flex-direction:column; align-items:flex-start; gap:8px;">' +
             '<div style="width:100%; display:flex; justify-content:space-between;"><strong class="mono">Trial ' + t.trial_number + '</strong><span class="tag">K_eff: ' + d.effective_trials_k_eff.toFixed(2) + '</span></div>' +
             '<div style="color:var(--text-secondary); font-size:0.9rem;">' + t.hypothesis + '</div>' +
             '<div class="mono" style="width:100%; display:flex; justify-content:space-between; color:var(--text-secondary);"><span>Excess: ' + (d.median_excess_bps >= 0 ? "+" : "") + d.median_excess_bps + ' bps</span><span>p_adj: ' + d.trial_adjusted_p_value.toFixed(4) + '</span></div>' +
             '</div>';
    }).join("");
  }
  await refreshLedger();
}

async function forceBudgetDenial() {
  const res = await fetch("/api/force_denial", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({kind: "budget"}) });
  const data = await res.json();
  document.getElementById("loopNotice").innerHTML = '<div class="notice error"><strong>BLOCKED:</strong> ' + data.message + '</div>';
  await refreshLedger();
}

async function forceEarlyHoldoutDenial() {
  const res = await fetch("/api/force_denial", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({kind: "holdout"}) });
  const data = await res.json();
  document.getElementById("loopNotice").innerHTML = '<div class="notice error"><strong>BLOCKED:</strong> ' + data.message + '</div>';
  await refreshLedger();
}

async function runHoldoutVerdict() {
  const res = await fetch("/api/verdict", {method: "POST"});
  const data = await res.json();
  const box = document.getElementById("verdictBox");
  if (data.error) {
    box.innerHTML = '<div class="notice error">' + data.error + '</div>';
  } else {
    const v = data.verdict;
    const tag = v.verdict === "SURVIVES" ? "tag green" : (v.verdict === "UNDERPOWERED" ? "tag" : "tag red");
    box.innerHTML = '<div style="margin-bottom:1.5rem;"><span class="' + tag + '" style="font-size:1rem; padding:0.5rem 1rem;">VERDICT: ' + v.verdict + '</span></div>' +
      '<div class="data-row"><span class="data-label">Paths Evaluated</span><span class="data-value mono">' + v.paths_tested + '</span></div>' +
      '<div class="data-row"><span class="data-label">Win/Loss Ratio</span><span class="data-value mono">' + v.wins_vs_buy_and_hold + 'W / ' + v.losses_vs_buy_and_hold + 'L</span></div>' +
      '<div class="data-row"><span class="data-label">Median Excess</span><span class="data-value mono">' + (v.median_excess_bps >= 0 ? "+" : "") + v.median_excess_bps + ' bps</span></div>' +
      '<div class="data-row"><span class="data-label">Trial-Adjusted p-value</span><span class="data-value mono">' + v.trial_adjusted_p_value.toFixed(4) + '</span></div>' +
      '<div class="data-row"><span class="data-label">Deflated Sharpe (DSR)</span><span class="data-value mono" style="color:var(--success);">' + v.deflated_sharpe_prob.toFixed(4) + '</span></div>' +
      '<pre style="margin-top:1.5rem;">' + data.memo + '</pre>';
  }
  await refreshLedger();
}

async function testOrderGate(mode) {
  const res = await fetch("/api/gate_test", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({mode: mode}) });
  const data = await res.json();
  const tag = data.approved_action === "buy" ? "tag green" : "tag red";
  document.getElementById("gateBox").innerHTML = '<div class="notice" style="display:flex; justify-content:space-between; align-items:center;"><span>Gate Action: <span class="' + tag + '">' + data.approved_action.toUpperCase() + '</span></span><span class="mono">Cost: ' + data.rt_cost_bps + ' bps</span></div>';
}

async function refreshLedger() {
  const res = await fetch("/api/ledger");
  const data = await res.json();
  
  document.getElementById("budgetBadge").innerHTML = '<span class="dot ' + (data.trials_used < data.max_trials ? 'secure' : 'danger') + '"></span>' + data.trials_used + '/' + data.max_trials + ' Trials';
  
  const ledgerList = document.getElementById("ledgerList");
  if (!data.entries.length) {
    ledgerList.innerHTML = '<div class="data-row"><span class="data-label">GENESIS</span></div>';
    return;
  }
  ledgerList.innerHTML = data.entries.slice().reverse().map(e => {
    const isDenial = e.event.indexOf("denied") !== -1;
    const color = isDenial ? "var(--danger)" : "var(--text-primary)";
    return '<div class="data-row" style="color:' + color + ';">' +
           '<span>[' + e.seq + '] ' + e.event + '</span>' +
           '<span style="color:var(--text-secondary);">' + e.entry_hash.slice(0, 16) + '</span>' +
           '</div>';
  }).join("");
}

window.addEventListener("DOMContentLoaded", async () => { 
  await loadPreset("cost_gated_reversion"); 
});
</script>
</body>
</html>"""


class PreregisterHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

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
        if parsed.path == "/":
            raw = HTML_PAGE.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
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
            fee = 220 if mode == "high_fee" else 40
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
