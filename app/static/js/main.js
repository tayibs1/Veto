
// Initialize Lenis for smooth scroll
const lenis = new Lenis();
lenis.on('scroll', ScrollTrigger.update);
gsap.ticker.add((time) => { lenis.raf(time * 1000); });
gsap.ticker.lagSmoothing(0);

// Global State
let currentChartName = "chart_3_cost_gated_reversion.svg";

// Hero Animations
function playHero() {
  const words = document.querySelectorAll('.rotator .word');
  let currentIndex = 0;
  
  // Stagger title
  gsap.fromTo('.hero-title', { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 1, ease: 'expo.out' });
  gsap.fromTo('.fact-row span', { opacity: 0 }, { opacity: 1, stagger: 0.1, duration: 0.8, delay: 0.5 });
  
  // Word rotator
  const rotate = () => {
    gsap.to(words[currentIndex], { opacity: 0, filter: 'blur(8px)', duration: 0.5 });
    currentIndex = (currentIndex + 1) % words.length;
    gsap.to(words[currentIndex], { opacity: 1, filter: 'blur(0px)', duration: 0.5 });
  };
  
  let cycles = 0;
  const interval = setInterval(() => {
    rotate();
    cycles++;
    if(cycles > 3) clearInterval(interval); // Stop on 'propose'
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
  document.querySelectorAll('.scenario-chip').forEach(c => c.classList.remove('active'));
  event.target.classList.add('active');
  
  const res = await fetch("/api/preset?key=" + encodeURIComponent(key));
  const data = await res.json();
  document.getElementById("hunchInput").value = data.text;
  
  currentChartName = data.chart;
  const chartRes = await fetch("/api/chart?name=" + encodeURIComponent(data.chart));
  if (chartRes.ok) document.getElementById("chartPreview").innerHTML = await chartRes.text();
  
  // Reset UI
  document.getElementById("specPreview").textContent = "{}";
  document.getElementById("argonStatus").textContent = "thinking...";
  
  setTimeout(() => window.translateHunch(key), 800);
};

window.translateHunch = async (presetKey) => {
  const text = document.getElementById("hunchInput").value;
  const res = await fetch("/api/translate", { 
    method: "POST", headers: {"Content-Type": "application/json"}, 
    body: JSON.stringify({text: presetKey || text, chart: currentChartName}) 
  });
  const data = await res.json();
  
  document.getElementById("argonStatus").textContent = "done";
  
  if (data.status === "refused") {
    document.getElementById("specPreview").textContent = JSON.stringify(data.partial_candidate, null, 2);
    document.getElementById("gateChecks").innerHTML = '<div style="color:var(--veto); font-size:12px; margin-top:8px;">❌ REFUSED: ' + data.reason + '</div>';
    document.getElementById("globalSignal").style.background = "var(--veto)";
  } else {
    document.getElementById("specPreview").textContent = JSON.stringify(data.spec, null, 2);
    document.getElementById("gateChecks").innerHTML = '<div style="color:var(--pass); font-size:12px; margin-top:8px;">✓ VALIDATED SPEC</div>';
    document.getElementById("globalSignal").style.background = "var(--pass)";
  }
  refreshLedger();
};

// Press-and-hold logic for buttons
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
        callback();
      }
    }, 50);
  });
  
  const reset = () => { clearInterval(timer); progress = 0; btn.style.setProperty('--after-width', '0%'); };
  btn.addEventListener('mouseup', reset);
  btn.addEventListener('mouseleave', reset);
}

setupHoldButton('btnLock', async () => {
  await fetch("/api/lock", {method: "POST"});
  refreshLedger();
});

window.testGate = async (mode) => {
  const res = await fetch("/api/gate_test", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({mode}) });
  const data = await res.json();
  const color = data.approved_action === "buy" ? "var(--pass)" : "var(--veto)";
  document.getElementById("gateResult").innerHTML = '<div style="color:' + color + ';">Gate: ' + data.approved_action.toUpperCase() + ' (Cost: ' + data.rt_cost_bps + ' bps)</div>';
  document.getElementById("globalSignal").style.background = color;
};

async function refreshLedger() {
  const res = await fetch("/api/ledger");
  const data = await res.json();
  
  // Update meter
  const bars = document.getElementById("meterBars");
  bars.innerHTML = '';
  for(let i=0; i<12; i++) {
    bars.innerHTML += '<div class="bar ' + (i < data.trials_used ? 'filled' : '') + '"></div>';
  }
  bars.innerHTML += '<div class="bar locked"></div>'; // 13th
  document.getElementById("trialCount").textContent = data.trials_used;
  
  // Update ledger list
  const list = document.getElementById("ledgerList");
  list.innerHTML = data.entries.slice().reverse().map(e => {
    const isErr = e.event.includes("denied");
    return '<div class="ledger-row ' + (isErr ? 'red' : '') + '"><span>[' + e.seq + '] ' + e.event + '</span><span>' + e.entry_hash.slice(0, 8) + '</span></div>';
  }).join("");
}

// Init
playHero();
window.loadPreset("cost_gated_reversion");
