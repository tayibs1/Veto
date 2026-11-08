// Initialize Lenis for smooth scroll
const lenis = new Lenis();
lenis.on('scroll', ScrollTrigger.update);
gsap.ticker.add((time) => { lenis.raf(time * 1000); });
gsap.ticker.lagSmoothing(0);

// Global State
window.currentChartName = 'chart_3_cost_gated_reversion.svg';

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
    document.getElementById("holdoutVerdict").classList.add("hidden");
    document.getElementById("globalSignal").style.background = "var(--argon)";
  } catch (err) {
    console.error("Error loading preset:", err);
  }
};

window.translateHunch = async () => {
  const text = document.getElementById("hunchInput").value;
  document.getElementById("argonStatus").textContent = "thinking...";
  document.getElementById("gateChecks").innerHTML = "";
  
  try {
    const res = await fetch("/api/translate", { 
      method: "POST", headers: {"Content-Type": "application/json"}, 
      body: JSON.stringify({text: text, chart: window.currentChartName}) 
    });
    const data = await res.json();
    
    document.getElementById("argonStatus").textContent = "done";
    
    if (data.status === "refused") {
      document.getElementById("specPreview").textContent = JSON.stringify(data.partial_candidate, null, 2);
      document.getElementById("gateChecks").innerHTML = '<div class="notice error"><strong>Refused:</strong> ' + data.reason + '</div>';
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
  }
};

function setupHoldButton(id, callback) {
  const btn = document.getElementById(id);
  if(!btn) return;
  let timer;
  let progress = 0;
  
  btn.addEventListener('mousedown', () => {
    timer = setInterval(() => {
      progress += 5;
      btn.style.setProperty('--after-width', progress + '%');
      if (progress >= 100) {
        clearInterval(timer);
        btn.style.setProperty('--after-width', '0%');
        callback();
      }
    }, 50);
  });
  
  const reset = () => { clearInterval(timer); progress = 0; btn.style.setProperty('--after-width', '0%'); };
  btn.addEventListener('mouseup', reset);
  btn.addEventListener('mouseleave', reset);
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
  try {
    const res = await fetch("/api/research", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({steps}) });
    const data = await res.json();
    const notice = document.getElementById("loopNotice");
    if (data.error) {
      notice.innerHTML = '<div class="notice error">' + data.error + '</div>';
    } else {
      notice.innerHTML = '<div class="notice" style="color:var(--argon); border-color:var(--argon);">✓ Generated ' + data.trials.length + ' trials. Selected Hash: <span class="mono">' + data.selected_spec_hash.slice(0,8) + '</span></div>';
    }
    refreshLedger();
  } catch (err) { console.error(err); }
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

window.runHoldoutVerdict = async () => {
  try {
    const res = await fetch("/api/verdict", {method: "POST"});
    const data = await res.json();
    const box = document.getElementById("holdoutVerdict");
    box.classList.remove("hidden");
    if (data.error) {
      box.innerHTML = '<div class="notice error">' + data.error + '</div>';
    } else {
      const v = data.verdict;
      const color = v.verdict === "SURVIVES" ? "var(--pass)" : "var(--veto)";
      box.innerHTML = '<h3 style="color:' + color + '; margin:0 0 16px 0; font-size:24px;">VERDICT: ' + v.verdict + '</h3>' +
        '<table><tr><th>Paths</th><th class="num">W/L</th><th class="num">Excess</th><th class="num">p_adj</th><th class="num">DSR</th></tr>' +
        '<tr><td>' + v.paths_tested + '</td><td class="num">' + v.wins_vs_buy_and_hold + 'W / ' + v.losses_vs_buy_and_hold + 'L</td><td class="num">' + (v.median_excess_bps >= 0 ? "+" : "") + v.median_excess_bps + ' bps</td><td class="num">' + v.trial_adjusted_p_value.toFixed(4) + '</td><td class="num" style="color:var(--pass); font-weight:bold;">' + v.deflated_sharpe_prob.toFixed(4) + '</td></tr></table>' +
        '<pre>' + data.memo + '</pre>';
    }
    refreshLedger();
  } catch (err) { console.error(err); }
};

setupHoldButton('btnHoldout', window.runHoldoutVerdict);

window.testGate = async (mode) => {
  try {
    const res = await fetch("/api/gate_test", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({mode}) });
    const data = await res.json();
    const color = data.approved_action === "buy" ? "var(--pass)" : "var(--veto)";
    document.getElementById("gateResult").innerHTML = '<div class="notice" style="color:' + color + '; border-color:' + color + ';">Gate Action: <strong>' + data.approved_action.toUpperCase() + '</strong><br><span style="color:var(--text-secondary); font-size:13px;">Cost: ' + data.rt_cost_bps + ' bps | ' + data.reason + '</span></div>';
    document.getElementById("globalSignal").style.background = color;
  } catch (err) { console.error(err); }
};

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
