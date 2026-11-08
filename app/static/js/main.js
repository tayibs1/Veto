// Initialize Lenis for smooth scroll
const lenis = new Lenis();
lenis.on('scroll', ScrollTrigger.update);
gsap.ticker.add((time) => { lenis.raf(time * 1000); });
gsap.ticker.lagSmoothing(0);

// Global State
window.currentChartName = 'chart_3_cost_gated_reversion.svg';
window.activePreset = 'cost_gated_reversion';
const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const shortHash = (h) => (h && h.length > 16 ? h.slice(0, 8) + "…" + h.slice(-6) : (h || "—"));
let busyCount = 0;
let trialsUsed = 0;
function setBusy(delta) {
  busyCount = Math.max(0, busyCount + delta);
  $("btnReset").disabled = busyCount > 0;
  $("btnResearch").disabled = busyCount > 0 || trialsUsed >= 12;
}

// Hero Animations
function playHero() {
  const words = document.querySelectorAll('.rotator .word');
  let currentIndex = 0;
  gsap.fromTo('.hero-title', { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 1, ease: 'expo.out' });
  gsap.fromTo('.fact-row span', { opacity: 0 }, { opacity: 1, stagger: 0.1, duration: 0.8, delay: 0.5 });
  
  const rotate = () => {
    gsap.to(words[currentIndex], { opacity: 0, filter: 'blur(8px)', duration: 0.5 });
    currentIndex = (currentIndex + 1) % words.length;
    gsap.to(words[currentIndex], { opacity: 1, filter: 'blur(0px)', duration: 0.5 });
  };
  
  let cycles = 0;
  const interval = setInterval(() => {
    rotate();
    cycles++;
    if(cycles > 3) clearInterval(interval);
  }, 1000);
}

// Nav Theme Switcher
ScrollTrigger.create({
  trigger: "#evidence",
  start: "top center",
  end: "bottom center",
  onToggle: (self) => {
    if (self.isActive) document.body.setAttribute('data-theme', 'light');
    else document.body.removeAttribute('data-theme');
  }
});

// UI Logic
window.loadPreset = async (key) => {
  try {
    window.activePreset = key;
    // Safely update chips
    document.querySelectorAll('.scenario-chip').forEach(c => {
      c.classList.remove('active');
      if (c.getAttribute('onclick').includes(key)) {
        c.classList.add('active');
      }
    });
    
    const res = await fetch("/api/preset?key=" + encodeURIComponent(key));
    const data = await res.json();
    document.getElementById("hunchInput").value = data.text;
    
    window.currentChartName = data.chart;
    const chartRes = await fetch("/api/chart?name=" + encodeURIComponent(data.chart));
    if (chartRes.ok) document.getElementById("chartPreview").innerHTML = await chartRes.text();
    
    // Clear states for the new preset
    document.getElementById("specPreview").textContent = "{}";
    document.getElementById("argonStatus").textContent = "idle";
    document.getElementById("gateChecks").innerHTML = "";
    document.getElementById("lockNotice").innerHTML = "";
    document.getElementById("loopNotice").innerHTML = "";
    document.getElementById("gateResult").innerHTML = "";
    document.getElementById("holdoutVerdict").innerHTML = "";
    document.getElementById("holdoutVerdict").classList.add("hidden");
    document.getElementById("globalSignal").style.background = "var(--argon)";
  } catch (err) {
    console.error("Error loading preset:", err);
  }
};

window.translateHunch = async () => {
  setBusy(1);
  const text = document.getElementById("hunchInput").value;
  document.getElementById("argonStatus").textContent = "thinking...";
  document.getElementById("gateChecks").innerHTML = "";
  
  try {
    const res = await fetch("/api/translate", { 
      method: "POST", headers: {"Content-Type": "application/json"}, 
      body: JSON.stringify({text: text, chart: window.currentChartName}) 
    });
    const data = await res.json();
    
    document.getElementById("argonStatus").textContent = data.engine === "deterministic_fallback" ? "done · offline parser, Argon not reached" : "done · live Argon";
    
    if (data.error) {
      document.getElementById("argonStatus").textContent = "idle";
      document.getElementById("gateChecks").innerHTML = '<div class="notice error">' + esc(data.error) + '</div>';
    } else if (data.status === "refused") {
      document.getElementById("specPreview").textContent = JSON.stringify(data.partial_candidate, null, 2);
      document.getElementById("gateChecks").innerHTML = '<div class="notice error"><strong>Refused:</strong> ' + esc(data.reason) + '</div>';
      document.getElementById("globalSignal").style.background = "var(--veto)";
    } else {
      document.getElementById("specPreview").textContent = JSON.stringify(data.spec, null, 2);
      document.getElementById("gateChecks").innerHTML = '<div class="notice" style="color:var(--pass); border-color:var(--pass);">✓ Validated JSON Spec</div>';
      document.getElementById("globalSignal").style.background = "var(--pass)";
    }
    refreshLedger();
  } catch (err) {
    console.error("Error translating hunch:", err);
    document.getElementById("argonStatus").textContent = "error";
  } finally {
    setBusy(-1);
  }
};

function setupHoldButton(id, callback) {
  const btn = document.getElementById(id);
  if(!btn) return;
  let timer;
  let progress = 0;
  const reset = () => { clearInterval(timer); progress = 0; btn.style.setProperty('--after-width', '0%'); };

  btn.addEventListener('pointerdown', () => {
    if (btn.disabled) return;
    reset();
    timer = setInterval(() => {
      progress += 5;
      btn.style.setProperty('--after-width', progress + '%');
      if (progress >= 100) {
        reset();
        callback();
      }
    }, 50);
  });

  btn.addEventListener('pointerup', reset);
  btn.addEventListener('pointerleave', reset);
  btn.addEventListener('pointercancel', reset);
}

setupHoldButton('btnLock', async () => {
  try {
    const res = await fetch("/api/lock", {method: "POST"});
    const data = await res.json();
    const notice = document.getElementById("lockNotice");
    if (data.error) {
      notice.innerHTML = '<div class="notice error">' + data.error + '</div>';
    } else {
      notice.innerHTML = '<div class="notice" style="color:var(--pass); border-color:var(--pass);">✓ Locked cleanly to ledger:<br><span class="mono" style="color:var(--text-secondary);">' + data.entry.entry_hash + '</span></div>';
    }
    refreshLedger();
  } catch (err) { console.error(err); }
});

window.runResearch = async (steps) => {
  setBusy(1);
  $("btnResearch").disabled = true;
  try {
    document.getElementById("loopNotice").innerHTML = '<div class="notice" style="color:var(--argon); border-color:var(--argon);">gemini-4-argon is running ' + steps + ' trials. This takes about a minute…</div>';
    const res = await fetch("/api/research", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({steps}) });
    const data = await res.json();
    const notice = document.getElementById("loopNotice");
    if (data.error) {
      notice.innerHTML = '<div class="notice error">' + data.error + '</div>';
    } else {
      notice.innerHTML = '<div class="notice" style="color:var(--argon); border-color:var(--argon);">✓ Generated ' + data.trials.length + ' trials. Selected Hash: <span class="mono">' + data.selected_spec_hash.slice(0,8) + '</span></div>';
    }
  } catch (err) {
    console.error(err);
    $("loopNotice").innerHTML = '<div class="notice error">The trial run did not finish. Check the server and try again.</div>';
  } finally {
    setBusy(-1);
    refreshLedger();
  }
};

window.forceBudgetDenial = async () => {
  try {
    const res = await fetch("/api/force_denial", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({kind: "budget"}) });
    const data = await res.json();
    document.getElementById("loopNotice").innerHTML = '<div class="notice error"><strong>BLOCKED:</strong> ' + data.message + '</div>';
    refreshLedger();
  } catch (err) { console.error(err); }
};

window.forceEarlyHoldoutDenial = async () => {
  try {
    const res = await fetch("/api/force_denial", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({kind: "holdout"}) });
    const data = await res.json();
    document.getElementById("loopNotice").innerHTML = '<div class="notice error"><strong>BLOCKED:</strong> ' + data.message + '</div>';
    refreshLedger();
  } catch (err) { console.error(err); }
};

const VERDICT_MEANING = {
  SURVIVES: "The idea held up on data it had never seen, even after every trial was counted against it.",
  DOES_NOT_SURVIVE: "On data it had never seen, the idea did not beat buy-and-hold by enough once every trial was counted against it. Veto says no.",
  UNDERPOWERED: "There were too few signals on unseen data to tell whether this idea works, so Veto will not approve it.",
};

window.runHoldoutVerdict = async () => {
  const box = $("holdoutVerdict");
  const btn = $("btnHoldout");
  btn.disabled = true;
  setBusy(1);
  box.classList.remove("hidden");
  box.innerHTML = '<div class="shimmer-text" style="margin-left:0; font-size:15px;">Signed off. Testing once on unseen paths, then Argon writes the audit memo. This can take about 20 seconds…</div>';
  box.scrollIntoView({ behavior: "smooth", block: "center" });
  try {
    const res = await fetch("/api/verdict", {method: "POST"});
    const data = await res.json();
    if (data.error) {
      box.innerHTML = '<div class="notice error" style="margin-top:0;">' + esc(data.error) + '</div>';
      if (!data.error.includes("already consumed")) btn.disabled = false;
      return;
    }
    const v = data.verdict;
    const color = v.verdict === "SURVIVES" ? "var(--pass)" : v.verdict === "UNDERPOWERED" ? "var(--amber)" : "var(--veto)";
    const stat = (k, val, hint) => '<div><div class="k">' + k + '</div><div class="v mono">' + val + '</div><div class="h">' + hint + '</div></div>';
    box.innerHTML =
      '<h3 class="verdict-title" style="color:' + color + ';">' + esc(v.verdict.replaceAll("_", " ")) + '</h3>' +
      '<p class="verdict-meaning">' + esc(VERDICT_MEANING[v.verdict] || "") + '</p>' +
      '<div class="verdict-stats">' +
        stat("Unseen paths", v.paths_tested, "Tested once, after sign-off") +
        stat("vs buy-and-hold", v.wins_vs_buy_and_hold + "W / " + v.losses_vs_buy_and_hold + "L", "Wins and losses") +
        stat("Median excess", (v.median_excess_bps >= 0 ? "+" : "") + v.median_excess_bps + " bps", "Above buy-and-hold") +
        stat("p-value", v.raw_sign_p_value.toFixed(4) + " → " + v.trial_adjusted_p_value.toFixed(4), "Raw → after " + v.effective_trials_k_eff.toFixed(2) + " effective trials") +
        stat("Deflated Sharpe", v.deflated_sharpe_prob.toFixed(4), "Chance the result is not luck") +
      '</div>' +
      '<p class="verdict-memo-label">Audit memo, written from these numbers only</p>' +
      '<pre class="verdict-memo">' + esc(data.memo) + '</pre>' +
      '<div class="verdict-next"><button class="action-btn" onclick="window.clearInputs()">Clear Inputs (Keep Ledger)</button><button class="action-btn" onclick="window.openLog()">View hashes in Log</button></div>';
    $("globalSignal").style.background = color;
    btn.textContent = "Unseen data used for this spec. Clear inputs to test another hunch.";
  } catch (err) {
    console.error(err);
    box.innerHTML = '<div class="notice error" style="margin-top:0;">The verdict did not come back. Check the server and try again.</div>';
    btn.disabled = false;
  } finally {
    setBusy(-1);
    refreshLedger();
  }
};

setupHoldButton('btnHoldout', window.runHoldoutVerdict);

window.testGate = async (mode) => {
  try {
    const res = await fetch("/api/gate_test", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({mode}) });
    const data = await res.json();
    const killOn = data.reason.startsWith("kill_switch");
    $("btnKill").classList.toggle("is-on", killOn);
    $("btnKill").textContent = killOn ? "Kill Switch On: Turn Off" : "Toggle Kill Switch";
    let title, detail, color;
    if (killOn) {
      title = "HALTED"; color = "var(--veto)";
      detail = "The kill switch is on, so no new orders can go through until it's turned off.";
    } else if (mode === "kill_switch") {
      title = "KILL SWITCH OFF"; color = "var(--pass)";
      detail = "Orders can go through the gate again.";
    } else if (data.approved_action === "buy") {
      title = "APPROVED"; color = "var(--pass)";
      detail = "Round-trip cost is " + data.rt_cost_bps + " bps, within the 250 bps limit.";
    } else {
      title = "BLOCKED"; color = "var(--veto)";
      detail = "Round-trip cost is " + data.rt_cost_bps + " bps, over the 250 bps limit.";
    }
    $("gateResult").innerHTML = '<div class="notice gate-outcome" style="border-color:' + color + ';"><strong style="color:' + color + ';">' + title + '</strong><span>' + detail + '</span> <span class="mono">' + esc(data.reason) + '</span></div>';
    $("globalSignal").style.background = color;
  } catch (err) { console.error(err); }
};

window.clearInputs = async () => {
  if (busyCount > 0) return;
  setBusy(1);
  try {
    await fetch("/api/clear", { method: "POST", headers: {"Content-Type": "application/json"}, body: "{}" });
    $("btnHoldout").disabled = false;
    $("btnHoldout").textContent = "Hold to Sign Off & Unlock Unseen Data";
    $("btnKill").classList.remove("is-on");
    $("btnKill").textContent = "Toggle Kill Switch";
    $("hunchInput").value = "";
    $("specPreview").textContent = "{}";
    $("argonStatus").textContent = "idle";
    $("gateChecks").innerHTML = "";
    $("lockNotice").innerHTML = "";
    $("loopNotice").innerHTML = '<div class="notice" style="color:var(--argon); border-color:var(--argon);">✓ Inputs &amp; 0/12 trial meter reset for next hunch. Cumulative SHA-256 ledger and K_eff history remain active.</div>';
    $("gateResult").innerHTML = "";
    $("holdoutVerdict").innerHTML = "";
    $("holdoutVerdict").classList.add("hidden");
    $("globalSignal").style.background = "var(--argon)";
    document.querySelectorAll('.scenario-chip').forEach(c => c.classList.remove('active'));
    await refreshLedger();
    window.closeLog();
    $("demo").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    console.error(err);
  } finally {
    setBusy(-1);
  }
};

window.resetRun = window.clearInputs;

window.resetTrialMeter = async () => {
  if (busyCount > 0) return;
  try {
    await fetch("/api/reset_trials", { method: "POST", headers: {"Content-Type": "application/json"}, body: "{}" });
    $("trialCount").textContent = "0";
    $("navTrials").textContent = "0 / 12 trials";
    trialsUsed = 0;
    const bars = $("meterBars");
    if (bars) {
      bars.innerHTML = Array.from({length: 12}, () => '<div class="bar"></div>').join("") + '<div class="bar locked"></div>';
    }
    $("btnResearch").disabled = false;
    $("btnResearch").textContent = "Run Next 4 Trials";
    $("loopNotice").innerHTML = '<div class="notice" style="color:var(--argon); border-color:var(--argon);">✓ 0/12 trial counter reset for this hunch. Cumulative SHA-256 ledger and K_eff history remain active.</div>';
    await refreshLedger();
  } catch (err) {
    console.error(err);
  }
};

function renderRun(run) {
  const v = run.verdict && run.verdict.verdict;
  const label = v ? v.replaceAll("_", " ")
    : run.status === "refused" ? "REFUSED"
    : run.status === "translated" ? "NOT LOCKED"
    : run.status === "locked" ? "LOCKED"
    : run.status === "researched" ? "NO VERDICT YET"
    : String(run.status || "").toUpperCase();
  const dot = v === "SURVIVES" ? "pass" : v === "UNDERPOWERED" ? "amber" : (v || run.status === "refused") ? "veto" : "argon";
  const time = run.started ? new Date(run.started).toLocaleString([], { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" }) : "";
  const copy = (h) => h ? '<button class="copy-pill" data-copy="' + esc(h) + '" title="Copy full hash">' + esc(shortHash(h)) + '</button>' : "—";
  const row = (k, val) => '<dt>' + k + '</dt><dd>' + val + '</dd>';
  const finalSpec = run.selected_spec || run.spec;
  let kv = row("Run ID", '<span class="mono">' + esc(run.id) + '</span>');
  if (run.engine) kv += row("Read by", '<span class="mono">' + esc(run.engine) + '</span>');
  if (run.reason) kv += row("Reason", esc(run.reason));
  if (finalSpec) kv += row("Template", '<span class="mono">' + esc(finalSpec.template) + '</span>') + row("Parameters", '<span class="mono">' + esc(JSON.stringify(finalSpec.params)) + '</span>');
  if (run.spec_hash) kv += row("Spec hash", copy(run.spec_hash));
  if (run.selected_spec_hash) kv += row("Tested hash", copy(run.selected_spec_hash));
  if (run.ledger && run.ledger.length) {
    kv += row("Head hash", copy(run.head_hash)) + row("Chain", run.verified ? '<span class="pass-green">Verified</span>' : '<span class="veto-red">Broken</span>') + row("Trials used", '<span class="mono">' + run.trials_used + ' of 12</span>');
  }
  if (run.verdict) kv += row("Result", '<span class="mono">' + run.verdict.wins_vs_buy_and_hold + 'W / ' + run.verdict.losses_vs_buy_and_hold + 'L, p_adj ' + run.verdict.trial_adjusted_p_value.toFixed(4) + '</span>');
  const chain = (run.ledger || []).map((e) =>
    '<div class="log-chain-row mono ' + (e.event.includes("denied") ? "red" : "") + '"><span>' + e.seq + '</span><span>' + esc(e.event) + '</span>' + copy(e.entry_hash) + '</div>').join("");
  return '<details class="log-run"><summary><span class="log-dot ' + dot + '"></span><span class="log-hunch">' + esc(run.hunch) + '</span>' +
    '<span class="log-meta mono">' + esc(label) + ' · ' + esc(time) + '</span></summary>' +
    '<div class="log-body"><dl class="log-kv">' + kv + '</dl>' +
    (chain ? '<p class="log-sub">Ledger, oldest first</p>' + chain : '<p class="log-sub">Nothing was locked, so no ledger hashes were written.</p>') +
    '</div></details>';
}

async function refreshRuns() {
  try {
    const res = await fetch("/api/runs");
    const data = await res.json();
    $("logCount").textContent = data.runs.length;
    const list = $("logList");
    const open = new Set([...list.querySelectorAll("details[open]")].map((d) => d.dataset.run));
    list.innerHTML = data.runs.length
      ? data.runs.map(renderRun).join("")
      : '<div class="log-empty">No runs yet. Translate a hunch and it will appear here.</div>';
    list.querySelectorAll("details").forEach((d, i) => {
      d.dataset.run = data.runs[i].id;
      d.open = open.has(d.dataset.run);
    });
  } catch (err) { console.error(err); }
}

window.openLog = async () => {
  await refreshRuns();
  $("logBackdrop").classList.remove("hidden");
  $("logPanel").classList.add("open");
  $("logPanel").setAttribute("aria-hidden", "false");
  lenis.stop();
};
window.closeLog = () => {
  $("logBackdrop").classList.add("hidden");
  $("logPanel").classList.remove("open");
  $("logPanel").setAttribute("aria-hidden", "true");
  lenis.start();
};
document.addEventListener("keydown", (e) => { if (e.key === "Escape") window.closeLog(); });
$("logList").addEventListener("click", async (e) => {
  const pill = e.target.closest(".copy-pill");
  if (!pill) return;
  e.preventDefault();
  const original = pill.textContent;
  try {
    await navigator.clipboard.writeText(pill.dataset.copy);
    pill.textContent = "copied ✓";
  } catch {
    pill.textContent = "copy failed";
  }
  setTimeout(() => { pill.textContent = original; }, 1200);
});

async function refreshLedger() {
  try {
    const res = await fetch("/api/ledger");
    const data = await res.json();
    
    const bars = document.getElementById("meterBars");
    bars.innerHTML = '';
    for(let i=0; i<12; i++) {
      bars.innerHTML += '<div class="bar ' + (i < data.trials_used ? 'filled' : '') + '"></div>';
    }
    bars.innerHTML += '<div class="bar locked"></div>';
    document.getElementById("trialCount").textContent = data.trials_used;
    const sessNote = document.getElementById("sessionTrialNote");
    if (sessNote) {
      sessNote.textContent = (data.session_trials_used > data.trials_used)
        ? "(Session cumulative: " + data.session_trials_used + ")"
        : "";
    }
    $("navTrials").textContent = data.trials_used + " / 12 trials";
    trialsUsed = data.trials_used;
    $("btnResearch").disabled = busyCount > 0 || data.trials_used >= 12;
    $("btnResearch").textContent = data.trials_used >= 12 ? "All 12 Trials Used" : "Run Next 4 Trials";
    refreshRuns();
    
    const list = document.getElementById("ledgerList");
    if (!data.entries.length) {
      list.innerHTML = '<div class="ledger-row"><span>GENESIS</span></div>';
      return;
    }
    list.innerHTML = data.entries.slice().reverse().map(e => {
      const isErr = e.event.includes("denied");
      return '<div class="ledger-row ' + (isErr ? 'red' : '') + '"><span>[' + e.seq + '] ' + e.event + '</span><span>' + e.entry_hash.slice(0, 16) + '...</span></div>';
    }).join("");
  } catch (err) { console.error(err); }
}

// Init
playHero();
window.loadPreset("cost_gated_reversion");
refreshLedger();
