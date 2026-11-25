let audioCtx = null;
let webcamStream = null;
let currentScenarioId = "hallway_nav";

function playEarcon(type) {
  if (!document.getElementById("chk-audio").checked || type === "none") return;
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const now = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    if (type === "chime") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(660, now);
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.14);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
      osc.start(now); osc.stop(now + 0.24);
    } else if (type === "sonar") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(520, now);
      gain.gain.setValueAtTime(0.10, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc.start(now); osc.stop(now + 0.26);
    } else if (type === "urgent_double") {
      osc.type = "triangle";
      osc.frequency.setValueAtTime(920, now);
      osc.frequency.setValueAtTime(1120, now + 0.12);
      gain.gain.setValueAtTime(0.16, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
      osc.start(now); osc.stop(now + 0.30);
    } else if (type === "uncertainty_low") {
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(240, now);
      osc.frequency.linearRampToValueAtTime(180, now + 0.26);
      gain.gain.setValueAtTime(0.10, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.30);
      osc.start(now); osc.stop(now + 0.32);
    }
  } catch (e) {
    console.warn("AudioContext unavailable:", e);
  }
}

function speakText(text, tier) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  if (!document.getElementById("chk-audio").checked) return;
  if (tier === 0) return; // Tier 0 is Earcon-only to minimise auditory overload
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.08;
  window.speechSynthesis.speak(utter);
}

async function apiPost(url, payload = {}) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const state = await res.json();
  renderState(state, true);
}

function renderState(state, triggerAudio = false) {
  // Scenario buttons
  const bar = document.getElementById("scenario-buttons");
  if (bar.children.length === 0 && state.scenarios) {
    state.scenarios.forEach(sc => {
      const btn = document.createElement("button");
      btn.className = "scenario-btn";
      btn.dataset.id = sc.id;
      btn.innerHTML = `<strong>${sc.title}</strong><small>${sc.summary}</small>`;
      btn.addEventListener("click", () => {
        currentScenarioId = sc.id;
        apiPost("/api/scenario", { scenario_id: sc.id, sync_mode: true });
      });
      bar.appendChild(btn);
    });
  }

  // Highlight active scenario
  if (state.last_frame) {
    currentScenarioId = state.last_frame.scenario_id;
    document.querySelectorAll(".scenario-btn").forEach(b => {
      b.classList.toggle("active", b.dataset.id === currentScenarioId);
    });
    document.getElementById("scene-title").textContent = state.last_frame.scene_title;
    document.getElementById("scene-source").textContent =
      state.last_frame.source === "live_webcam_metrics" ? "Live Webcam Quality + Sim CV" : "Simulated Vision Stream";

    const bEl = document.getElementById("metric-brightness");
    bEl.textContent = `${Math.round(state.last_frame.brightness * 100)}%`;
    bEl.className = "metric-value " + (state.last_frame.brightness < 0.30 ? "low" : "good");

    const sEl = document.getElementById("metric-sharpness");
    sEl.textContent = `${Math.round(state.last_frame.sharpness * 100)}%`;
    sEl.className = "metric-value " + (state.last_frame.sharpness < 0.35 ? "low" : "good");

    const topConf = state.last_response ? state.last_response.confidence_shown : 0;
    const cEl = document.getElementById("metric-confidence");
    cEl.textContent = `${Math.round(topConf * 100)}%`;
    cEl.className = "metric-value " + (topConf < state.confidence_threshold ? "low" : "good");

    const detList = document.getElementById("detections-list");
    detList.innerHTML = "";
    state.last_frame.detections.forEach(d => {
      const div = document.createElement("div");
      const cls = d.confidence < state.confidence_threshold ? "low-conf" : (d.hazard ? "hazard" : "");
      div.className = `det-item ${cls}`;
      div.innerHTML = `<span><strong>${d.label}</strong> — ${d.distance_m.toFixed(1)}m (${d.clock_direction})${d.hazard ? " [HAZARD]" : ""}</span>
                       <span>${Math.round(d.confidence * 100)}% conf</span>`;
      detList.appendChild(div);
    });
  }

  // Mode buttons
  document.getElementById("btn-mode-nav").classList.toggle("active-mode", state.mode === "navigation");
  document.getElementById("btn-mode-find").classList.toggle("active-mode", state.mode === "object_finding");
  if (state.target_query) {
    document.getElementById("target-input").value = state.target_query;
  }

  // Response panel
  const r = state.last_response;
  if (r) {
    const panel = document.getElementById("response-panel");
    panel.className = `response-panel status-${r.status}`;
    const tierNames = { 0: "Tier 0: Earcon Only", 1: "Tier 1: Concise Cue", 2: "Tier 2: Detailed View" };
    document.getElementById("resp-tier").textContent = tierNames[r.tier] || `Tier ${r.tier}`;
    document.getElementById("resp-earcon").textContent = `Earcon: ${r.earcon}`;
    const hapEl = document.getElementById("resp-haptic");
    hapEl.textContent = `Haptic (Simulated): ${r.haptic_pattern}`;
    hapEl.classList.remove("pulse");
    if (r.haptic_pattern !== "none") {
      void hapEl.offsetWidth;
      hapEl.classList.add("pulse");
    }

    document.getElementById("resp-speech").textContent = r.speech_text;
    const hintEl = document.getElementById("resp-hint");
    if (r.guidance_hint) {
      hintEl.textContent = `Guidance: ${r.guidance_hint}`;
      hintEl.classList.remove("hidden");
    } else {
      hintEl.classList.add("hidden");
    }

    document.getElementById("resp-explanation").textContent = r.explanation;
    document.getElementById("suppressed-badge").textContent = `Suppressed Items: ${r.suppressed_count}`;

    if (triggerAudio) {
      if (r.status === "interrupted") {
        if ("speechSynthesis" in window) window.speechSynthesis.cancel();
      } else {
        playEarcon(r.earcon);
        speakText(r.speech_text, r.tier);
      }
    }
  }

  // Event log
  document.getElementById("correction-counter").textContent = `User Corrections Logged: ${state.corrections_count}`;
  const logUl = document.getElementById("event-log");
  logUl.innerHTML = "";
  (state.event_log || []).forEach(item => {
    const li = document.createElement("li");
    li.innerHTML = `[${item.timestamp}] <strong>${item.event}</strong>: ${item.detail}`;
    logUl.appendChild(li);
  });
}

// Button bindings
document.getElementById("btn-mode-nav").addEventListener("click", () => apiPost("/api/mode", { mode: "navigation" }));
document.getElementById("btn-mode-find").addEventListener("click", () => {
  const target = document.getElementById("target-input").value;
  apiPost("/api/mode", { mode: "object_finding", target_query: target });
});
document.getElementById("btn-set-target").addEventListener("click", () => {
  const target = document.getElementById("target-input").value;
  apiPost("/api/mode", { mode: "object_finding", target_query: target });
});
document.getElementById("btn-detail").addEventListener("click", () => apiPost("/api/detail"));
document.getElementById("btn-bargein").addEventListener("click", () => {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  apiPost("/api/barge_in");
});
document.getElementById("btn-why").addEventListener("click", () => {
  const txt = document.getElementById("resp-explanation").textContent;
  playEarcon("chime");
  speakText("Explanation: " + txt, 1);
});
document.getElementById("btn-correct").addEventListener("click", () => {
  apiPost("/api/correct", { note: "User flagged inaccurate or unnecessary alert" });
});

// Optional live webcam lighting/blur sensor
document.getElementById("btn-webcam").addEventListener("click", async () => {
  const video = document.getElementById("webcam-video");
  const sampleBtn = document.getElementById("btn-sample-webcam");
  if (webcamStream) {
    webcamStream.getTracks().forEach(t => t.stop());
    webcamStream = null;
    video.classList.add("hidden");
    sampleBtn.classList.add("hidden");
    document.getElementById("btn-webcam").textContent = "Enable Live Webcam Quality Sensor (Optional)";
    return;
  }
  try {
    webcamStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = webcamStream;
    video.classList.remove("hidden");
    video.style.width = "100%";
    video.style.maxHeight = "150px";
    video.style.objectFit = "cover";
    video.style.borderRadius = "8px";
    video.style.marginBottom = "10px";
    sampleBtn.classList.remove("hidden");
    document.getElementById("btn-webcam").textContent = "Stop Live Webcam";
  } catch (err) {
    alert("Webcam unavailable or permission denied. Simulated scenarios remain fully functional.");
  }
});

document.getElementById("btn-sample-webcam").addEventListener("click", () => {
  const video = document.getElementById("webcam-video");
  const canvas = document.getElementById("webcam-canvas");
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  let lumSum = 0;
  let edgeSum = 0;
  const w = canvas.width;
  const grays = new Float32Array(w * canvas.height);
  for (let i = 0, p = 0; i < data.length; i += 4, p++) {
    const g = (0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]) / 255.0;
    grays[p] = g;
    lumSum += g;
  }
  for (let y = 1; y < canvas.height - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const idx = y * w + x;
      const diff = Math.abs(grays[idx] - grays[idx - 1]) + Math.abs(grays[idx] - grays[idx - w]);
      edgeSum += diff;
    }
  }
  const brightness = lumSum / grays.length;
  const sharpness = Math.min(1.0, (edgeSum / grays.length) * 6.5);
  apiPost("/api/scenario", {
    scenario_id: currentScenarioId,
    sync_mode: false,
    live_brightness: Number(brightness.toFixed(2)),
    live_sharpness: Number(sharpness.toFixed(2))
  });
});

// Keyboard shortcuts for eyes-free / accessible interaction
document.addEventListener("keydown", (e) => {
  if (document.activeElement.tagName === "INPUT") return;
  if (e.code === "Space") {
    e.preventDefault();
    document.getElementById("btn-bargein").click();
  } else if (e.key === "1") {
    document.getElementById("btn-mode-nav").click();
  } else if (e.key === "2") {
    document.getElementById("btn-mode-find").click();
  } else if (e.key.toLowerCase() === "d") {
    document.getElementById("btn-detail").click();
  } else if (e.key.toLowerCase() === "r") {
    document.getElementById("btn-why").click();
  } else if (e.key.toLowerCase() === "c") {
    document.getElementById("btn-correct").click();
  }
});

// Initial load
fetch("/api/state").then(r => r.json()).then(state => renderState(state, false));
