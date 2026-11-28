// The Living Cosmos — Pure ES Module Biosphere Canvas, Voice & Chimes

const POLL_INTERVAL_MS = 3500;
const RING_RADIUS_LARGE = 32;
const RING_CIRC_LARGE = 2 * Math.PI * RING_RADIUS_LARGE;
const RING_RADIUS_SMALL_OUTER = 26;
const RING_RADIUS_SMALL_INNER = 19;

const ZONE_STYLE = {
  hub: {
    label: "The Central Hearth",
    rx: 0.50,
    ry: 0.33,
    radiusFactor: 0.132,
    hue: "#4fe3c1",
    glow: "rgba(79, 227, 193, 0.28)",
  },
  "alpha-sector": {
    label: "Alpha Sanctuary",
    rx: 0.30,
    ry: 0.25,
    radiusFactor: 0.112,
    hue: "#60d9f6",
    glow: "rgba(96, 217, 246, 0.24)",
  },
  "beta-sector": {
    label: "Beta Frontier",
    rx: 0.70,
    ry: 0.25,
    radiusFactor: 0.112,
    hue: "#f6c46d",
    glow: "rgba(246, 196, 109, 0.22)",
  },
  frontier: {
    label: "Far Horizon",
    rx: 0.50,
    ry: 0.53,
    radiusFactor: 0.105,
    hue: "#a78bfa",
    glow: "rgba(167, 139, 250, 0.25)",
  },
};

const DEFAULT_CHAPTERS = [
  {
    title: "Genesis & Physics",
    status: "Alive at the core",
    story: "Conserved charges, energy flow, and gentle entropy bounds formed the first natural laws of this cosmos.",
  },
  {
    title: "Chemistry & Bonding",
    status: "Woven into perception",
    story: "Molecules bond through catalysis and gentle activation thresholds, turning scattered hints into coherent meaning.",
  },
  {
    title: "Living Body & Five Organs",
    status: "Breathing continuously",
    story: "Perception, deliberation, memory, action, and defense beat together inside an immutable genome.",
  },
  {
    title: "Homeostasis & Stem Renewal",
    status: "Self-healing",
    story: "Tissues divide when needed, rest in dreaming renewal, and recycle tired matter back into vital energy.",
  },
  {
    title: "Society & Protective Skin",
    status: "Harmonic fellowship",
    story: "Neighbors verify one another with trust, share territory gently, and shield against harsh outside storms.",
  },
  {
    title: "Evolution & Living Senses",
    status: "Listening & adapting",
    story: "Safe evolutionary trials and real vessel senses connect each organism to the living machine beneath it.",
  },
  {
    title: "Shared & Relative Worlds",
    status: "Unfolding now",
    story: "Habitats pulse with finite warmth and rivers of light while every creature experiences its own personal horizon.",
  },
  {
    title: "Soul, Character & Beliefs",
    status: "Awakened",
    story: "Each being carries an unshakeable calling, a temperament constellation, and evolving beliefs shaped by lived experience.",
  },
];

const state = {
  universe: null,
  selectedBeingId: null,
  selectedBeingWorld: null,
  hoveredBeingId: null,
  lastTick: -1,
  lastBulletinId: null,
  lastEventIds: new Set(),
  speechEnabled: false,
  chimesEnabled: false,
  selectedVoiceURI: "",
  voices: [],
  audioCtx: null,
  beingsAnim: new Map(),
  ripples: [],
  filaments: [],
  stars: [],
  zonePositions: new Map(),
  canvasWidth: 0,
  canvasHeight: 0,
  dpr: 1,
};

// DOM references
const sanctuaryHudEl = document.querySelector(".sanctuary-hud");
const canvas = document.getElementById("biosphere-canvas");
const ctx = canvas.getContext("2d");
const tooltipEl = document.getElementById("canvas-tooltip");
const worldBreathEl = document.getElementById("world-breath");
const narrativeHeadlineEl = document.getElementById("narrative-headline");
const narrativeStoryEl = document.getElementById("narrative-story");
const whisperVoiceStateEl = document.getElementById("whisper-voice-state");
const beingsStripEl = document.getElementById("beings-strip");

// Voice & Sound DOM
const voicePillBtn = document.getElementById("voice-sound-btn");
const voicePopoverEl = document.getElementById("voice-popover");
const voiceCloseBtn = document.getElementById("voice-close-btn");
const toggleSpeechBtn = document.getElementById("toggle-speech-btn");
const toggleSpeechText = document.getElementById("toggle-speech-text");
const toggleChimesBtn = document.getElementById("toggle-chimes-btn");
const toggleChimesText = document.getElementById("toggle-chimes-text");
const speakNowBtn = document.getElementById("speak-now-btn");
const muteAllBtn = document.getElementById("mute-all-btn");
const voiceSelectEl = document.getElementById("voice-select");

// Vitality DOM
const vitalityPillBtn = document.getElementById("vitality-pill-btn");
const vitalityPopoverEl = document.getElementById("vitality-popover");
const vitalityCloseBtn = document.getElementById("vitality-close-btn");
const vitalityPhraseEl = document.getElementById("vitality-phrase");
const hostNameHeadingEl = document.getElementById("host-name-heading");
const hostVitalityStoryEl = document.getElementById("host-vitality-story");
const ringMemSmall = document.getElementById("ring-mem");
const ringCpuSmall = document.getElementById("ring-cpu");
const detailRingCpu = document.getElementById("detail-ring-cpu");
const detailRingMem = document.getElementById("detail-ring-mem");
const detailRingDisk = document.getElementById("detail-ring-disk");
const metricCpuEl = document.getElementById("metric-cpu");
const metricMemEl = document.getElementById("metric-mem");
const metricDiskEl = document.getElementById("metric-disk");
const metricUptimeEl = document.getElementById("metric-uptime");

// Spark Form DOM
const sparkForm = document.getElementById("spark-form");
const sparkZoneEl = document.getElementById("spark-zone");
const sparkKindEl = document.getElementById("spark-kind");
const sparkInputEl = document.getElementById("spark-input");
const sparkFeedbackEl = document.getElementById("spark-feedback");

// Being Drawer DOM
const beingDrawerEl = document.getElementById("being-drawer");
const drawerCloseBtn = document.getElementById("drawer-close-btn");
const drawerMoodAuraEl = document.getElementById("drawer-mood-aura");
const drawerZoneRoleEl = document.getElementById("drawer-zone-role");
const drawerBeingNameEl = document.getElementById("drawer-being-name");
const drawerMoodPhraseEl = document.getElementById("drawer-mood-phrase");
const hearBeingBtn = document.getElementById("hear-being-btn");
const drawerKarmaPillEl = document.getElementById("drawer-karma-pill");
const drawerSoulCallingEl = document.getElementById("drawer-soul-calling");
const drawerConscienceEl = document.getElementById("drawer-conscience");
const constellationSvg = document.getElementById("character-constellation");
const traitsLegendEl = document.getElementById("character-traits-legend");
const drawerVitalityWhisperEl = document.getElementById("drawer-vitality-whisper");
const drawerOrgansEl = document.getElementById("drawer-organs");
const drawerWorldHorizonEl = document.getElementById("drawer-world-horizon");
const drawerBeliefsEl = document.getElementById("drawer-beliefs");
const drawerObservablesEl = document.getElementById("drawer-observables");

// Tapestry Modal DOM
const openTapestryBtn = document.getElementById("open-tapestry-btn");
const tapestryBackdropEl = document.getElementById("tapestry-backdrop");
const closeTapestryBtn = document.getElementById("close-tapestry-btn");
const tabChaptersBtn = document.getElementById("tab-chapters");
const tabEventsBtn = document.getElementById("tab-events");
const panelChaptersEl = document.getElementById("panel-chapters");
const panelEventsEl = document.getElementById("panel-events");
const chaptersTimelineEl = document.getElementById("chapters-timeline");
const eventsChronicleEl = document.getElementById("events-chronicle");

// ---------------------------------------------------------------------------
// Helpers: Organic Naming, Colors & Formatting (No dry dev phrasing)
// ---------------------------------------------------------------------------
function prettifyZone(zoneName) {
  if (!zoneName) return "Sanctuary";
  if (ZONE_STYLE[zoneName]) return ZONE_STYLE[zoneName].label;
  return String(zoneName)
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function prettifyPhrase(raw) {
  return String(raw || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDurationNatural(seconds) {
  if (seconds == null || Number.isNaN(Number(seconds))) {
    return "Steady quiet wakefulness";
  }
  const s = Math.max(0, Math.floor(Number(seconds)));
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const mins = Math.floor((s % 3600) / 60);
  if (days > 0) return `Awake for ${days}d ${hours}h of continuous harmony`;
  if (hours > 0) return `Awake for ${hours}h ${mins}m of steady flow`;
  return `Awake for ${mins}m of fresh genesis`;
}

function moodPalette(being) {
  const mode = String(being?.mode || "").toUpperCase();
  const stress = Number(being?.stress ?? 0);
  const moodPhrase = String(being?.mood_phrase || "").toLowerCase();
  if (mode === "LOCKDOWN" || stress >= 0.65 || moodPhrase.includes("turbul") || moodPhrase.includes("guard")) {
    return { primary: "#fb8a70", secondary: "#f6c46d", cadence: 2.8, glow: "rgba(251, 138, 112, 0.45)" };
  }
  if (mode.includes("SLEEP") || mode.includes("REM") || moodPhrase.includes("dream")) {
    return { primary: "#a78bfa", secondary: "#c4b5fd", cadence: 0.9, glow: "rgba(167, 139, 250, 0.45)" };
  }
  if (mode === "DORMANT" || moodPhrase.includes("still")) {
    return { primary: "#818cf8", secondary: "#a5b4fc", cadence: 0.7, glow: "rgba(129, 140, 248, 0.36)" };
  }
  if (mode === "DEEP_FOCUS" || moodPhrase.includes("focus") || moodPhrase.includes("deep")) {
    return { primary: "#f6c46d", secondary: "#4fe3c1", cadence: 1.9, glow: "rgba(246, 196, 109, 0.42)" };
  }
  return { primary: "#4fe3c1", secondary: "#60d9f6", cadence: 1.4, glow: "rgba(79, 227, 193, 0.42)" };
}

function toneColor(tone) {
  const t = String(tone || "").toLowerCase();
  if (t.includes("dream") || t.includes("violet") || t.includes("rem")) return "#a78bfa";
  if (t.includes("curious") || t.includes("cyan")) return "#60d9f6";
  if (t.includes("warm") || t.includes("soul") || t.includes("gold") || t.includes("spark")) return "#f6c46d";
  if (t.includes("alert") || t.includes("coral") || t.includes("warn")) return "#fb8a70";
  return "#4fe3c1";
}

function setRingFraction(circleEl, radius, fraction) {
  if (!circleEl) return;
  const circ = 2 * Math.PI * radius;
  const clamped = Math.max(0.04, Math.min(1, Number.isFinite(fraction) ? fraction : 0.25));
  circleEl.style.strokeDasharray = `${circ.toFixed(2)}`;
  circleEl.style.strokeDashoffset = `${(circ * (1 - clamped)).toFixed(2)}`;
}

function clearEl(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
}

// ---------------------------------------------------------------------------
// Generative Web Audio Chimes + Web Speech Narrator
// ---------------------------------------------------------------------------
function ensureAudioContext() {
  if (!state.chimesEnabled) return null;
  if (!state.audioCtx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;
    state.audioCtx = new AudioCtx();
  }
  if (state.audioCtx.state === "suspended") {
    state.audioCtx.resume().catch(() => {});
  }
  return state.audioCtx;
}

function playHarmonicChime(kind = "pulse") {
  if (!state.chimesEnabled) return;
  const ac = ensureAudioContext();
  if (!ac) return;
  try {
    const now = ac.currentTime;
    const scales = {
      pulse: [392.0, 493.88, 587.33], // G4, B4, D5
      spark: [440.0, 554.37, 659.25, 880.0], // A major ethereal
      select: [329.63, 440.0, 523.25], // soft triad
    };
    const notes = scales[kind] || scales.pulse;
    notes.forEach((freq, idx) => {
      const osc = ac.createOscillator();
      const gain = ac.createGain();
      osc.type = idx === 0 ? "sine" : "triangle";
      osc.frequency.setValueAtTime(freq, now + idx * 0.08);
      gain.gain.setValueAtTime(0.0001, now + idx * 0.08);
      gain.gain.exponentialRampToValueAtTime(0.032, now + idx * 0.08 + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.08 + 1.45);
      osc.connect(gain);
      gain.connect(ac.destination);
      osc.start(now + idx * 0.08);
      osc.stop(now + idx * 0.08 + 1.5);
    });
  } catch {
    // Audio playback cleanly ignored if blocked by browser policy
  }
}

function populateVoices() {
  if (!("speechSynthesis" in window)) return;
  try {
    const voices = window.speechSynthesis.getVoices() || [];
    state.voices = voices;
    const previous = state.selectedVoiceURI;
    clearEl(voiceSelectEl);
    const defaultOpt = document.createElement("option");
    defaultOpt.value = "";
    defaultOpt.textContent = voices.length ? "Natural Default Voice" : "Browser Voice Unavailable";
    voiceSelectEl.appendChild(defaultOpt);

    voices.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v.voiceURI;
      opt.textContent = `${v.name} (${v.lang})`;
      voiceSelectEl.appendChild(opt);
    });
    if (previous) voiceSelectEl.value = previous;
  } catch {
    // Safe fallback in headless environments
  }
}

function speakText(text, { force = false, rate = 0.96, pitch = 1.0 } = {}) {
  if (!text || (!state.speechEnabled && !force)) return;
  if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") return;
  try {
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(String(text));
    utter.rate = rate;
    utter.pitch = pitch;
    utter.volume = 0.9;
    if (state.selectedVoiceURI && state.voices.length) {
      const match = state.voices.find((v) => v.voiceURI === state.selectedVoiceURI);
      if (match) utter.voice = match;
    } else if (state.voices.length) {
      const english = state.voices.find((v) => /^en/i.test(v.lang));
      if (english) utter.voice = english;
    }
    utter.onstart = () => {
      whisperVoiceStateEl.textContent = "Speaking gently…";
    };
    utter.onend = () => {
      whisperVoiceStateEl.textContent = state.speechEnabled ? "Voice attuned" : "Quietly listening";
    };
    utter.onerror = () => {
      whisperVoiceStateEl.textContent = "Quietly listening";
    };
    window.speechSynthesis.speak(utter);
  } catch {
    // Graceful no-op if speech synthesis unavailable
  }
}

function syncVoiceUI() {
  toggleSpeechBtn.setAttribute("aria-pressed", String(state.speechEnabled));
  toggleSpeechText.textContent = state.speechEnabled ? "Spoken Story: Listening & Speaking" : "Spoken Story: Quiet";
  toggleChimesBtn.setAttribute("aria-pressed", String(state.chimesEnabled));
  toggleChimesText.textContent = state.chimesEnabled ? "Harmonic Chimes: Flowing" : "Harmonic Chimes: Quiet";

  const active = state.speechEnabled || state.chimesEnabled;
  voicePillBtn.classList.toggle("is-active", active);
  whisperVoiceStateEl.textContent = state.speechEnabled ? "Voice attuned" : "Quietly listening";
}

// ---------------------------------------------------------------------------
// Canvas Geometry, Bioluminescent Habitats & Organisms
// ---------------------------------------------------------------------------
function initStars() {
  state.stars = Array.from({ length: 85 }, () => ({
    x: Math.random(),
    y: Math.random(),
    r: 0.5 + Math.random() * 1.5,
    phase: Math.random() * Math.PI * 2,
    speed: 0.4 + Math.random() * 0.9,
  }));
}

function resizeCanvas() {
  state.dpr = Math.min(window.devicePixelRatio || 1, 2);
  state.canvasWidth = window.innerWidth;
  state.canvasHeight = window.innerHeight;
  canvas.width = Math.floor(state.canvasWidth * state.dpr);
  canvas.height = Math.floor(state.canvasHeight * state.dpr);
  ctx.setTransform(state.dpr, 0, 0, state.dpr, 0, 0);
  computeZonePositions();
}

function computeZonePositions() {
  const zones = state.universe?.world?.zones || [];
  const rawW = state.canvasWidth || window.innerWidth;
  const h = state.canvasHeight || window.innerHeight;
  const drawerActive = Boolean(state.selectedBeingId) && rawW > 980;
  const w = drawerActive ? Math.max(540, rawW - 410) : rawW;
  const minDim = Math.min(w, h);
  state.zonePositions.clear();

  const fallbackOrder = [
    { rx: 0.50, ry: 0.33, radiusFactor: 0.132 },
    { rx: 0.30, ry: 0.25, radiusFactor: 0.112 },
    { rx: 0.70, ry: 0.25, radiusFactor: 0.112 },
    { rx: 0.50, ry: 0.53, radiusFactor: 0.105 },
    { rx: 0.29, ry: 0.49, radiusFactor: 0.10 },
    { rx: 0.71, ry: 0.49, radiusFactor: 0.10 },
  ];

  zones.forEach((zone, idx) => {
    const preset = ZONE_STYLE[zone.name] || fallbackOrder[idx % fallbackOrder.length];
    state.zonePositions.set(zone.name, {
      x: w * preset.rx,
      y: h * preset.ry,
      r: Math.max(60, minDim * (preset.radiusFactor || 0.112)),
      hue: preset.hue || "#4fe3c1",
      glow: preset.glow || "rgba(79, 227, 193, 0.24)",
      label: zone.label || prettifyZone(zone.name),
      zone,
    });
  });
}

function triggerRipple(zoneName, color = "#4fe3c1", strength = 1.0) {
  const pos = state.zonePositions.get(zoneName) || [...state.zonePositions.values()][0];
  if (!pos) return;
  state.ripples.push({
    x: pos.x,
    y: pos.y,
    r: pos.r * 0.25,
    maxR: pos.r * (1.7 + strength * 0.6),
    alpha: 0.75,
    color,
  });
}

function triggerFilament(fromZone, toZone, color = "#f6c46d") {
  const a = state.zonePositions.get(fromZone);
  const b = state.zonePositions.get(toZone);
  if (!a || !b || a === b) return;
  state.filaments.push({
    x1: a.x,
    y1: a.y,
    x2: b.x,
    y2: b.y,
    progress: 0,
    color,
  });
}

function syncBeingsAnimationState(beings) {
  const seenIds = new Set();
  const zoneBuckets = new Map();
  beings.forEach((b) => {
    const z = b.zone || "hub";
    if (!zoneBuckets.has(z)) zoneBuckets.set(z, []);
    zoneBuckets.get(z).push(b);
  });

  beings.forEach((being) => {
    seenIds.add(being.id);
    const zPos = state.zonePositions.get(being.zone) || state.zonePositions.get("hub") || {
      x: state.canvasWidth * 0.5,
      y: state.canvasHeight * 0.45,
      r: 110,
    };
    const siblings = zoneBuckets.get(being.zone || "hub") || [being];
    const indexInZone = siblings.indexOf(being);
    const angleOffset = (indexInZone / Math.max(1, siblings.length)) * Math.PI * 2;
    const orbitDist = siblings.length === 1 ? zPos.r * 0.22 : zPos.r * 0.48;
    const anchorX = zPos.x + Math.cos(angleOffset) * orbitDist;
    const anchorY = zPos.y + Math.sin(angleOffset) * orbitDist;

    const existing = state.beingsAnim.get(being.id);
    if (!existing) {
      state.beingsAnim.set(being.id, {
        x: anchorX,
        y: anchorY,
        targetX: anchorX,
        targetY: anchorY,
        phase: Math.random() * Math.PI * 2,
        radius: 21,
        being,
      });
    } else {
      if (existing.being.zone !== being.zone) {
        triggerFilament(existing.being.zone, being.zone, "#60d9f6");
        triggerRipple(being.zone, "#60d9f6", 0.9);
      }
      existing.targetX = anchorX;
      existing.targetY = anchorY;
      existing.being = being;
    }
  });

  for (const key of state.beingsAnim.keys()) {
    if (!seenIds.has(key)) state.beingsAnim.delete(key);
  }
}

function drawCurvedRiver(a, b, timeSec) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const cx = mx - dy * 0.14;
  const cy = my + dx * 0.14;

  const grad = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
  grad.addColorStop(0, "rgba(79, 227, 193, 0.20)");
  grad.addColorStop(0.5, "rgba(96, 217, 246, 0.34)");
  grad.addColorStop(1, "rgba(167, 139, 250, 0.22)");

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.quadraticCurveTo(cx, cy, b.x, b.y);
  ctx.strokeStyle = grad;
  ctx.lineWidth = 2.2;
  ctx.stroke();

  // Flowing bioluminescent motes along the river
  for (let i = 0; i < 3; i += 1) {
    const t = (timeSec * 0.14 + i / 3) % 1;
    const inv = 1 - t;
    const px = inv * inv * a.x + 2 * inv * t * cx + t * t * b.x;
    const py = inv * inv * a.y + 2 * inv * t * cy + t * t * b.y;
    ctx.beginPath();
    ctx.arc(px, py, 2.6, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(190, 248, 255, 0.78)";
    ctx.fill();
  }
  ctx.restore();
}

function renderFrame(nowMs) {
  const t = nowMs * 0.001;
  const w = state.canvasWidth;
  const h = state.canvasHeight;
  ctx.clearRect(0, 0, w, h);

  // Subtle ambient drifting starlight dust
  for (const s of state.stars) {
    const twinkle = 0.25 + 0.55 * (0.5 + 0.5 * Math.sin(t * s.speed + s.phase));
    ctx.beginPath();
    ctx.arc(s.x * w, s.y * h, s.r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(218, 232, 255, ${twinkle.toFixed(3)})`;
    ctx.fill();
  }

  // Flowing Rivers of Light between neighboring zones
  const drawnEdges = new Set();
  for (const [zName, pos] of state.zonePositions.entries()) {
    const neighbors = pos.zone?.neighbors || [];
    for (const nb of neighbors) {
      const nbPos = state.zonePositions.get(nb);
      if (!nbPos) continue;
      const edgeKey = [zName, nb].sort().join("--");
      if (drawnEdges.has(edgeKey)) continue;
      drawnEdges.add(edgeKey);
      drawCurvedRiver(pos, nbPos, t);
    }
  }

  // Breathing Bioluminescent Habitat Zones
  for (const [, pos] of state.zonePositions.entries()) {
    const zone = pos.zone || {};
    const breath = 1 + 0.038 * Math.sin(t * 1.1 + pos.x * 0.01);
    const radius = pos.r * breath;
    const calmness = Number(zone.calmness ?? 0.85);

    const outerGrad = ctx.createRadialGradient(pos.x, pos.y, radius * 0.15, pos.x, pos.y, radius * 1.38);
    outerGrad.addColorStop(0, pos.glow);
    outerGrad.addColorStop(0.65, "rgba(16, 26, 56, 0.20)");
    outerGrad.addColorStop(1, "rgba(5, 8, 20, 0)");

    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius * 1.38, 0, Math.PI * 2);
    ctx.fillStyle = outerGrad;
    ctx.fill();

    // Soft membrane ring
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
    ctx.strokeStyle = calmness < 0.5 ? "rgba(251, 138, 112, 0.34)" : "rgba(255, 255, 255, 0.12)";
    ctx.lineWidth = 1.4;
    ctx.stroke();

    // Zone poetic label
    ctx.save();
    ctx.textAlign = "center";
    ctx.fillStyle = "rgba(244, 247, 251, 0.86)";
    ctx.font = '600 13px "Inter", system-ui, sans-serif';
    ctx.fillText(pos.label, pos.x, pos.y - radius - 14);
    if (zone.mood) {
      ctx.fillStyle = "rgba(182, 196, 224, 0.65)";
      ctx.font = '400 11px "Inter", system-ui, sans-serif';
      ctx.fillText(zone.mood, pos.x, pos.y - radius + 1);
    }
    ctx.restore();
  }

  // World entities floating gently inside their zones (subtle embers/sparks)
  const entities = state.universe?.world?.entities || [];
  entities.slice(0, 24).forEach((ent, idx) => {
    const zPos = state.zonePositions.get(ent.zone);
    if (!zPos) return;
    const angle = t * 0.25 + idx * 1.3;
    const dist = zPos.r * (0.62 + (idx % 3) * 0.12);
    const ex = zPos.x + Math.cos(angle) * dist;
    const ey = zPos.y + Math.sin(angle) * dist;
    const resolved = String(ent.state || "").toLowerCase() === "resolved";
    ctx.beginPath();
    ctx.arc(ex, ey, resolved ? 2.8 : 4.1, 0, Math.PI * 2);
    ctx.fillStyle = resolved ? "rgba(79, 227, 193, 0.45)" : "rgba(246, 196, 109, 0.78)";
    ctx.fill();
  });

  // Expanding ripple waves
  for (let i = state.ripples.length - 1; i >= 0; i -= 1) {
    const rp = state.ripples[i];
    rp.r += 1.45;
    rp.alpha *= 0.972;
    ctx.beginPath();
    ctx.arc(rp.x, rp.y, rp.r, 0, Math.PI * 2);
    ctx.strokeStyle = rp.color;
    ctx.globalAlpha = Math.max(0, rp.alpha);
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.globalAlpha = 1;
    if (rp.r >= rp.maxR || rp.alpha <= 0.02) state.ripples.splice(i, 1);
  }

  // Synaptic light filaments arcing across zones
  for (let i = state.filaments.length - 1; i >= 0; i -= 1) {
    const fl = state.filaments[i];
    fl.progress += 0.024;
    const p = Math.min(1, fl.progress);
    const px = fl.x1 + (fl.x2 - fl.x1) * p;
    const py = fl.y1 + (fl.y2 - fl.y1) * p - Math.sin(p * Math.PI) * 42;
    ctx.save();
    ctx.beginPath();
    ctx.arc(px, py, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = fl.color;
    ctx.shadowColor = fl.color;
    ctx.shadowBlur = 14;
    ctx.fill();
    ctx.restore();
    if (fl.progress >= 1.05) state.filaments.splice(i, 1);
  }

  // Living Multi-Ring Organisms (Beings)
  for (const [, anim] of state.beingsAnim.entries()) {
    anim.x += (anim.targetX - anim.x) * 0.045;
    anim.y += (anim.targetY - anim.y) * 0.045;

    const driftX = anim.x + Math.cos(t * 0.8 + anim.phase) * 7;
    const driftY = anim.y + Math.sin(t * 1.05 + anim.phase) * 7;
    anim.renderX = driftX;
    anim.renderY = driftY;

    const palette = moodPalette(anim.being);
    const isSelected = state.selectedBeingId === anim.being.id;
    const isHovered = state.hoveredBeingId === anim.being.id;
    const pulse = 1 + 0.09 * Math.sin(t * palette.cadence + anim.phase);
    const coreR = (isSelected ? 15 : 12.5) * pulse;

    // Outer mood aura
    const auraR = (isSelected ? 48 : isHovered ? 40 : 34) * pulse;
    const auraGrad = ctx.createRadialGradient(driftX, driftY, coreR * 0.4, driftX, driftY, auraR);
    auraGrad.addColorStop(0, palette.glow);
    auraGrad.addColorStop(1, "rgba(5, 8, 20, 0)");
    ctx.beginPath();
    ctx.arc(driftX, driftY, auraR, 0, Math.PI * 2);
    ctx.fillStyle = auraGrad;
    ctx.fill();

    // Selection or Hover Halo Ring
    if (isSelected || isHovered) {
      ctx.beginPath();
      ctx.arc(driftX, driftY, 32 * pulse, 0, Math.PI * 2);
      ctx.strokeStyle = isSelected ? "rgba(255, 223, 163, 0.85)" : "rgba(255, 255, 255, 0.45)";
      ctx.lineWidth = isSelected ? 2 : 1.2;
      ctx.stroke();
    }

    // 5 Orbiting Inner Lights (5 Vital Organs)
    const organs = anim.being.organs || [];
    const organCount = 5;
    for (let o = 0; o < organCount; o += 1) {
      const organ = organs[o];
      const vitality = Number(organ?.vitality ?? organ?.health ?? 0.85);
      const orbitAngle = t * (0.7 + o * 0.07) + anim.phase + (o * Math.PI * 2) / organCount;
      const orbitR = 22.5;
      const ox = driftX + Math.cos(orbitAngle) * orbitR;
      const oy = driftY + Math.sin(orbitAngle) * orbitR;
      ctx.beginPath();
      ctx.arc(ox, oy, 2.2 + vitality * 1.8, 0, Math.PI * 2);
      ctx.fillStyle = vitality > 0.7 ? palette.secondary : "#fb8a70";
      ctx.fill();
    }

    // Inner luminous core
    const coreGrad = ctx.createRadialGradient(driftX - 3, driftY - 3, 2, driftX, driftY, coreR);
    coreGrad.addColorStop(0, "#ffffff");
    coreGrad.addColorStop(0.45, palette.primary);
    coreGrad.addColorStop(1, "rgba(10, 16, 36, 0.8)");
    ctx.beginPath();
    ctx.arc(driftX, driftY, coreR, 0, Math.PI * 2);
    ctx.fillStyle = coreGrad;
    ctx.fill();

    // Gentle Name Label
    ctx.save();
    ctx.textAlign = "center";
    ctx.fillStyle = isSelected ? "#ffdfa3" : "rgba(244, 247, 251, 0.9)";
    ctx.font = `${isSelected ? "600" : "500"} 12px "Inter", system-ui, sans-serif`;
    ctx.fillText(anim.being.name || anim.being.id, driftX, driftY + 38);
    ctx.restore();
  }

  requestAnimationFrame(renderFrame);
}

// Canvas Pointer Interaction
function findBeingAt(clientX, clientY) {
  let closest = null;
  let minDist = 36;
  for (const [, anim] of state.beingsAnim.entries()) {
    const dx = clientX - (anim.renderX ?? anim.x);
    const dy = clientY - (anim.renderY ?? anim.y);
    const d = Math.hypot(dx, dy);
    if (d < minDist) {
      minDist = d;
      closest = anim;
    }
  }
  return closest;
}

function findZoneAt(clientX, clientY) {
  for (const [, pos] of state.zonePositions.entries()) {
    const d = Math.hypot(clientX - pos.x, clientY - pos.y);
    if (d <= pos.r * 0.95) return pos;
  }
  return null;
}

canvas.addEventListener("mousemove", (ev) => {
  const hit = findBeingAt(ev.clientX, ev.clientY);
  if (hit) {
    state.hoveredBeingId = hit.being.id;
    canvas.style.cursor = "pointer";
    tooltipEl.textContent = `${hit.being.name} — ${hit.being.mood_phrase || "quietly present"}`;
    tooltipEl.style.left = `${ev.clientX}px`;
    tooltipEl.style.top = `${ev.clientY}px`;
    tooltipEl.classList.remove("hidden");
    return;
  }
  state.hoveredBeingId = null;
  canvas.style.cursor = "default";
  const zoneHit = findZoneAt(ev.clientX, ev.clientY);
  if (zoneHit?.zone) {
    tooltipEl.textContent = zoneHit.zone.story || `${zoneHit.label} — ${zoneHit.zone.mood || "peaceful"}`;
    tooltipEl.style.left = `${ev.clientX}px`;
    tooltipEl.style.top = `${ev.clientY}px`;
    tooltipEl.classList.remove("hidden");
  } else {
    tooltipEl.classList.add("hidden");
  }
});

canvas.addEventListener("click", (ev) => {
  const hit = findBeingAt(ev.clientX, ev.clientY);
  if (hit) {
    selectBeing(hit.being.id, { speak: true });
  }
});

// ---------------------------------------------------------------------------
// UI Rendering: Narrative, Beings Strip, Host Vitality, Drawer & Tapestry
// ---------------------------------------------------------------------------
function renderBeingsStrip(beings) {
  clearEl(beingsStripEl);
  beings.forEach((b) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "being-chip";
    if (state.selectedBeingId === b.id) btn.classList.add("is-selected");

    const orb = document.createElement("span");
    orb.className = "being-chip-orb";
    const pal = moodPalette(b);
    orb.style.background = pal.primary;
    orb.style.boxShadow = `0 0 12px ${pal.primary}`;

    const meta = document.createElement("span");
    meta.className = "being-chip-meta";
    const nameSpan = document.createElement("span");
    nameSpan.className = "being-chip-name";
    nameSpan.textContent = b.name || b.id;
    const moodSpan = document.createElement("span");
    moodSpan.className = "being-chip-mood";
    moodSpan.textContent = b.mood_phrase || "Awake";

    meta.append(nameSpan, moodSpan);
    btn.append(orb, meta);
    btn.addEventListener("click", () => selectBeing(b.id, { speak: true }));
    beingsStripEl.appendChild(btn);
  });
}

function renderHostVitality(machine) {
  if (!machine) return;
  const hostName = machine.host || "Sanctuary Vessel";
  const vitalityPhrase = machine.vitality_phrase || "Steady & calm";
  vitalityPhraseEl.textContent = vitalityPhrase;
  hostNameHeadingEl.textContent = `${hostName}`;

  const hasMem = machine.mem_used_pct != null && !Number.isNaN(Number(machine.mem_used_pct));
  const memPct = hasMem ? Number(machine.mem_used_pct) : 38;
  const cpuRatio = Number(machine.load_ratio ?? 0.25);
  const cpuPct = Math.min(100, Math.round(cpuRatio * 100));
  const diskPct = Number(machine.disk_used_pct ?? 35);

  setRingFraction(ringMemSmall, RING_RADIUS_SMALL_OUTER, memPct / 100);
  setRingFraction(ringCpuSmall, RING_RADIUS_SMALL_INNER, Math.max(0.08, Math.min(1, cpuRatio)));
  setRingFraction(detailRingCpu, RING_RADIUS_LARGE, Math.max(0.08, Math.min(1, cpuRatio)));
  setRingFraction(detailRingMem, RING_RADIUS_LARGE, memPct / 100);
  setRingFraction(detailRingDisk, RING_RADIUS_LARGE, diskPct / 100);

  metricCpuEl.textContent = `${cpuPct}%`;
  if (machine.mem_used_gb != null && machine.mem_total_gb != null) {
    metricMemEl.textContent = `${Number(machine.mem_used_gb).toFixed(1)} / ${Number(machine.mem_total_gb).toFixed(0)} GB`;
  } else if (hasMem) {
    metricMemEl.textContent = `${Math.round(memPct)}%`;
  } else {
    metricMemEl.textContent = "Clear";
  }

  metricDiskEl.textContent = machine.disk_free_gb != null
    ? `${Number(machine.disk_free_gb).toFixed(0)} GB free`
    : `${Math.round(diskPct)}% used`;

  hostVitalityStoryEl.textContent =
    `${hostName} sustains the biosphere with ${machine.cpu_count || 1} breathing cores — ${vitalityPhrase}.`;
  metricUptimeEl.textContent = formatDurationNatural(machine.uptime_s);
}

function renderCharacterConstellation(character) {
  clearEl(constellationSvg);
  clearEl(traitsLegendEl);
  const c = {
    caution: Number(character?.caution ?? 0.65),
    curiosity: Number(character?.curiosity ?? 0.6),
    diligence: Number(character?.diligence ?? 0.8),
    altruism: Number(character?.altruism ?? 0.75),
  };

  const cx = 130;
  const cy = 110;
  const maxR = 72;
  const axes = [
    { key: "curiosity", label: "Curiosity", angle: -Math.PI / 2 },
    { key: "altruism", label: "Altruism", angle: 0 },
    { key: "diligence", label: "Diligence", angle: Math.PI / 2 },
    { key: "caution", label: "Caution", angle: Math.PI },
  ];

  const ns = "http://www.w3.org/2000/svg";

  // Concentric guide rings
  [0.45, 0.75, 1.0].forEach((scale) => {
    const ring = document.createElementNS(ns, "circle");
    ring.setAttribute("cx", cx);
    ring.setAttribute("cy", cy);
    ring.setAttribute("r", (maxR * scale).toFixed(1));
    ring.setAttribute("fill", "none");
    ring.setAttribute("stroke", "rgba(255,255,255,0.08)");
    constellationSvg.appendChild(ring);
  });

  // Axes & Star points
  const pts = [];
  axes.forEach((ax) => {
    const val = Math.max(0.1, Math.min(1, c[ax.key]));
    const endX = cx + Math.cos(ax.angle) * maxR;
    const endY = cy + Math.sin(ax.angle) * maxR;
    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", cx);
    line.setAttribute("y1", cy);
    line.setAttribute("x2", endX.toFixed(1));
    line.setAttribute("y2", endY.toFixed(1));
    line.setAttribute("stroke", "rgba(255,255,255,0.1)");
    constellationSvg.appendChild(line);

    const px = cx + Math.cos(ax.angle) * (maxR * val);
    const py = cy + Math.sin(ax.angle) * (maxR * val);
    pts.push({ px, py, ax, val });

    const lx = cx + Math.cos(ax.angle) * (maxR + 19);
    const ly = cy + Math.sin(ax.angle) * (maxR + 14) + 4;
    const txt = document.createElementNS(ns, "text");
    txt.setAttribute("x", lx.toFixed(1));
    txt.setAttribute("y", ly.toFixed(1));
    txt.setAttribute("text-anchor", "middle");
    txt.setAttribute("fill", "rgba(226, 234, 248, 0.75)");
    txt.setAttribute("font-size", "10.5");
    txt.textContent = ax.label;
    constellationSvg.appendChild(txt);
  });

  const poly = document.createElementNS(ns, "polygon");
  poly.setAttribute("points", pts.map((p) => `${p.px.toFixed(1)},${p.py.toFixed(1)}`).join(" "));
  poly.setAttribute("fill", "rgba(246, 196, 109, 0.22)");
  poly.setAttribute("stroke", "#f6c46d");
  poly.setAttribute("stroke-width", "1.8");
  constellationSvg.appendChild(poly);

  pts.forEach((p) => {
    const star = document.createElementNS(ns, "circle");
    star.setAttribute("cx", p.px.toFixed(1));
    star.setAttribute("cy", p.py.toFixed(1));
    star.setAttribute("r", "4");
    star.setAttribute("fill", "#ffdfa3");
    constellationSvg.appendChild(star);

    const chip = document.createElement("div");
    chip.className = "trait-chip";
    const span = document.createElement("span");
    span.textContent = p.ax.label;
    const strong = document.createElement("strong");
    strong.textContent = `${Math.round(p.val * 100)}%`;
    chip.append(span, strong);
    traitsLegendEl.appendChild(chip);
  });
}

function renderBeingDrawer() {
  const beings = state.universe?.beings || [];
  const being = beings.find((b) => b.id === state.selectedBeingId);
  if (!being) {
    sanctuaryHudEl?.classList.remove("drawer-open");
    beingDrawerEl.classList.add("hidden");
    return;
  }

  beingDrawerEl.classList.remove("hidden");
  const pal = moodPalette(being);
  drawerMoodAuraEl.style.background = `radial-gradient(circle, ${pal.secondary}, ${pal.primary})`;
  drawerMoodAuraEl.style.boxShadow = `0 0 22px ${pal.primary}`;

  drawerZoneRoleEl.textContent = `${prettifyZone(being.zone)} · ${prettifyPhrase(being.role || "Steward")}`;
  drawerBeingNameEl.textContent = being.name || being.id;
  drawerMoodPhraseEl.textContent = being.mood_phrase || "Quietly attentive";

  const rwData = state.selectedBeingWorld;
  const activeSoul = rwData?.soul || being.soul || {};
  const activeChar = rwData?.character || being.character;
  const activeOrgans = rwData?.organs || being.organs;
  const activeBeliefs = rwData?.beliefs || being.beliefs || [];

  const karmaVal = activeSoul.karma ?? 1.0;
  drawerKarmaPillEl.textContent = `Karma Radiance · ${Number(karmaVal).toFixed(1)}`;

  const callingRaw = String(activeSoul.calling || "steward").replace(/_/g, " ").trim();
  const callingSentence = callingRaw.includes(" ")
    ? callingRaw
    : `to care for this sanctuary as ${callingRaw}`;
  drawerSoulCallingEl.textContent = `"My calling is ${callingSentence} — keeping harmony across the living habitats."`;

  clearEl(drawerConscienceEl);
  const conscienceList =
    activeSoul.conscience_phrases && activeSoul.conscience_phrases.length
      ? activeSoul.conscience_phrases
      : (activeSoul.conscience || ["do_no_harm", "preserve_owner_sovereignty", "truth_before_action"]).map(prettifyPhrase);
  conscienceList.forEach((item) => {
    const seal = document.createElement("span");
    seal.className = "conscience-seal";
    seal.textContent = String(item);
    drawerConscienceEl.appendChild(seal);
  });

  renderCharacterConstellation(activeChar);

  // Five Inner Organs
  const fuelPct = being.fuel_pct != null ? Math.round(Number(being.fuel_pct)) : 90;
  drawerVitalityWhisperEl.textContent = being.memory_mb != null
    ? `Vital reserve at ${fuelPct}% · Vessel memory aura ${Number(being.memory_mb).toFixed(0)} MB`
    : `Vital reserve at ${fuelPct}% across five living organs`;

  clearEl(drawerOrgansEl);
  const fallbackOrgans = [
    { name: "perception", label: "Perception", vitality: 0.92 },
    { name: "deliberation", label: "Deliberation", vitality: 0.88 },
    { name: "memory", label: "Memory", vitality: 0.9 },
    { name: "action", label: "Action", vitality: 0.86 },
    { name: "defense", label: "Defense", vitality: 0.95 },
  ];
  const organs = (activeOrgans && activeOrgans.length ? activeOrgans : fallbackOrgans).slice(0, 5);
  organs.forEach((org) => {
    const rawVit = Number(org.vitality ?? org.health ?? 0.88);
    const vit = Math.max(0.05, Math.min(1, rawVit > 1 ? rawVit / 100 : rawVit));
    const petal = document.createElement("div");
    petal.className = "organ-petal";
    if (org.story) petal.title = org.story;

    const orb = document.createElement("span");
    orb.className = "organ-orb";
    const color = vit > 0.7 ? "#4fe3c1" : vit > 0.4 ? "#f6c46d" : "#fb8a70";
    orb.style.background = `radial-gradient(circle, #ffffff, ${color})`;
    orb.style.boxShadow = `0 0 ${Math.round(8 + vit * 12)}px ${color}`;

    const name = document.createElement("span");
    name.className = "organ-name";
    name.textContent = org.label || org.name || "organ";
    const pct = document.createElement("span");
    pct.className = "organ-vitality";
    pct.textContent = `${Math.round(vit * 100)}%`;

    petal.append(orb, name, pct);
    drawerOrgansEl.appendChild(petal);
  });

  // Beliefs
  clearEl(drawerBeliefsEl);
  if (!activeBeliefs.length) {
    const empty = document.createElement("p");
    empty.className = "horizon-whisper";
    empty.textContent = "Still forming gentle impressions from its surroundings.";
    drawerBeliefsEl.appendChild(empty);
  } else {
    activeBeliefs.slice(0, 6).forEach((bl) => {
      const card = document.createElement("div");
      card.className = "belief-card";
      const story = document.createElement("p");
      story.className = "belief-story";
      story.textContent = bl.story || prettifyPhrase(bl.proposition);
      const track = document.createElement("div");
      track.className = "confidence-glow-track";
      const fill = document.createElement("div");
      fill.className = "confidence-glow-fill";
      const conf = Math.max(0.05, Math.min(1, Number(bl.confidence ?? 0.6)));
      fill.style.width = `${Math.round(conf * 100)}%`;
      track.appendChild(fill);
      card.append(story, track);
      drawerBeliefsEl.appendChild(card);
    });
  }

  // Relative World
  clearEl(drawerObservablesEl);
  const bw = rwData?.body_world || rwData;
  if (bw) {
    drawerWorldHorizonEl.textContent =
      bw.story ||
      `Looking out from ${prettifyZone(bw.frame_origin || being.zone)}, sensing ${(bw.observables || []).length} quiet ripples nearby.`;
    (bw.observables || []).slice(0, 5).forEach((obs) => {
      const item = document.createElement("div");
      item.className = "observable-card";
      item.textContent =
        obs.story ||
        obs.title ||
        `Noticing ${prettifyPhrase(obs.kind || "presence")} in ${prettifyZone(obs.zone || being.zone)}`;
      drawerObservablesEl.appendChild(item);
    });
  } else {
    drawerWorldHorizonEl.textContent = `Attuning to ${being.name}'s local horizon…`;
  }
}

function renderTapestry() {
  const chapters = state.universe?.chronicle?.chapters;
  const list = chapters && chapters.length ? chapters : DEFAULT_CHAPTERS;

  clearEl(chaptersTimelineEl);
  list.forEach((ch) => {
    const card = document.createElement("article");
    card.className = "chapter-card";
    if (ch.era) {
      const era = document.createElement("span");
      era.className = "chapter-era";
      era.textContent = ch.era;
      card.appendChild(era);
    }
    const head = document.createElement("div");
    head.className = "chapter-head";
    const h3 = document.createElement("h3");
    h3.className = "chapter-title";
    h3.textContent = ch.title || ch.name;
    const status = document.createElement("span");
    status.className = "chapter-status";
    status.textContent = ch.status || "Woven & alive";
    head.append(h3, status);

    const p = document.createElement("p");
    p.className = "chapter-story";
    p.textContent = ch.summary || ch.story || ch.description || "";
    card.append(head, p);

    if (ch.essence) {
      const essence = document.createElement("p");
      essence.className = "chapter-essence";
      essence.textContent = ch.essence;
      card.appendChild(essence);
    }
    chaptersTimelineEl.appendChild(card);
  });

  const events = state.universe?.chronicle?.events || [];
  clearEl(eventsChronicleEl);
  if (!events.length) {
    const empty = document.createElement("p");
    empty.className = "tapestry-intro";
    empty.textContent = "The sanctuary rests in quiet stillness; new story moments will appear here as they happen.";
    eventsChronicleEl.appendChild(empty);
    return;
  }

  events
    .slice()
    .reverse()
    .forEach((ev) => {
      const beat = document.createElement("div");
      beat.className = "event-beat";
      const dot = document.createElement("span");
      dot.className = "event-tone-dot";
      const color = toneColor(ev.tone);
      dot.style.background = color;
      dot.style.boxShadow = `0 0 12px ${color}`;

      const copy = document.createElement("div");
      const sentence = document.createElement("p");
      sentence.className = "event-sentence";
      sentence.textContent = ev.sentence || ev.story || "A gentle ripple passed through the sanctuary.";
      const meta = document.createElement("span");
      meta.className = "event-meta";
      const who = ev.who ? `${ev.who} · ` : "";
      const where = ev.where ? `${prettifyZone(ev.where)} · ` : "";
      meta.textContent = `${who}${where}Breath ${ev.tick ?? 0}`;

      copy.append(sentence, meta);
      beat.append(dot, copy);
      eventsChronicleEl.appendChild(beat);
    });
}

function updateZoneDropdown(zones) {
  if (!zones || !zones.length) return;
  const current = sparkZoneEl.value;
  clearEl(sparkZoneEl);
  zones.forEach((z) => {
    const opt = document.createElement("option");
    opt.value = z.name;
    opt.textContent = z.label || prettifyZone(z.name);
    sparkZoneEl.appendChild(opt);
  });
  if (zones.some((z) => z.name === current)) {
    sparkZoneEl.value = current;
  }
}

// ---------------------------------------------------------------------------
// API Synchronization
// ---------------------------------------------------------------------------
async function fetchBeingWorld(beingId) {
  try {
    const res = await fetch(`/api/beings/${encodeURIComponent(beingId)}/world`, { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    if (state.selectedBeingId === beingId) {
      state.selectedBeingWorld = data;
      renderBeingDrawer();
    }
  } catch {
    // Non-fatal network pause
  }
}

async function selectBeing(beingId, { speak = false } = {}) {
  state.selectedBeingId = beingId;
  state.selectedBeingWorld = null;
  sanctuaryHudEl?.classList.add("drawer-open");
  computeZonePositions();
  syncBeingsAnimationState(state.universe?.beings || []);
  playHarmonicChime("select");

  const being = (state.universe?.beings || []).find((b) => b.id === beingId);
  if (being) {
    triggerRipple(being.zone || "hub", "#f6c46d", 0.9);
  }
  renderBeingsStrip(state.universe?.beings || []);
  renderBeingDrawer();
  await fetchBeingWorld(beingId);

  if (speak && state.speechEnabled && state.selectedBeingWorld?.voice_intro) {
    speakText(state.selectedBeingWorld.voice_intro, { force: true });
  }
}

async function refreshUniverse() {
  try {
    const res = await fetch("/api/universe", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    const firstLoad = !state.universe;
    state.universe = data;

    computeZonePositions();
    if (firstLoad) {
      updateZoneDropdown(data.world?.zones || []);
    }

    const tick = data.world?.tick ?? 0;
    const beings = data.beings || [];
    worldBreathEl.textContent = `Breath ${tick} · ${beings.length} living ${beings.length === 1 ? "being" : "beings"}`;

    if (data.narrative) {
      narrativeHeadlineEl.textContent = data.narrative.headline || "The sanctuary breathes together.";
      narrativeStoryEl.textContent = data.narrative.story || "";

      const bId = data.narrative.bulletin_id;
      if (bId && bId !== state.lastBulletinId) {
        state.lastBulletinId = bId;
        if (state.speechEnabled && data.narrative.spoken_bulletin) {
          speakText(data.narrative.spoken_bulletin);
        }
      }
    }

    // Visual ripples when new live events or ticks happen
    const events = data.chronicle?.events || [];
    events.forEach((ev) => {
      const eid = ev.id || `${ev.tick}:${ev.who}:${ev.where}`;
      if (!state.lastEventIds.has(eid)) {
        state.lastEventIds.add(eid);
        if (!firstLoad) {
          triggerRipple(ev.where || "hub", toneColor(ev.tone), 1.0);
        }
      }
    });
    if (state.lastTick !== -1 && tick > state.lastTick && !firstLoad) {
      playHarmonicChime("pulse");
    }
    state.lastTick = tick;

    syncBeingsAnimationState(beings);
    renderBeingsStrip(beings);
    renderHostVitality(data.machine);
    renderTapestry();

    if (state.selectedBeingId) {
      renderBeingDrawer();
      fetchBeingWorld(state.selectedBeingId);
    }
  } catch {
    // Keep existing frame gracefully if server briefly restarts
  }
}

// ---------------------------------------------------------------------------
// Interactive Controls & Event Listeners
// ---------------------------------------------------------------------------
voicePillBtn.addEventListener("click", () => {
  const open = voicePopoverEl.classList.toggle("hidden");
  voicePillBtn.setAttribute("aria-expanded", String(!open));
  populateVoices();
});

voiceCloseBtn.addEventListener("click", () => {
  voicePopoverEl.classList.add("hidden");
  voicePillBtn.setAttribute("aria-expanded", "false");
});

toggleSpeechBtn.addEventListener("click", () => {
  state.speechEnabled = !state.speechEnabled;
  syncVoiceUI();
  if (state.speechEnabled && state.universe?.narrative?.spoken_bulletin) {
    speakText(state.universe.narrative.spoken_bulletin, { force: true });
  } else if (!state.speechEnabled && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
});

toggleChimesBtn.addEventListener("click", () => {
  state.chimesEnabled = !state.chimesEnabled;
  syncVoiceUI();
  if (state.chimesEnabled) {
    ensureAudioContext();
    playHarmonicChime("spark");
  }
});

speakNowBtn.addEventListener("click", () => {
  const text =
    state.universe?.narrative?.spoken_bulletin ||
    `${narrativeHeadlineEl.textContent}. ${narrativeStoryEl.textContent}`;
  speakText(text, { force: true });
});

muteAllBtn.addEventListener("click", () => {
  state.speechEnabled = false;
  state.chimesEnabled = false;
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  syncVoiceUI();
});

voiceSelectEl.addEventListener("change", () => {
  state.selectedVoiceURI = voiceSelectEl.value;
});

vitalityPillBtn.addEventListener("click", () => {
  const hidden = vitalityPopoverEl.classList.toggle("hidden");
  vitalityPillBtn.setAttribute("aria-expanded", String(!hidden));
});

vitalityCloseBtn.addEventListener("click", () => {
  vitalityPopoverEl.classList.add("hidden");
  vitalityPillBtn.setAttribute("aria-expanded", "false");
});

drawerCloseBtn.addEventListener("click", () => {
  state.selectedBeingId = null;
  state.selectedBeingWorld = null;
  sanctuaryHudEl?.classList.remove("drawer-open");
  beingDrawerEl.classList.add("hidden");
  computeZonePositions();
  syncBeingsAnimationState(state.universe?.beings || []);
  renderBeingsStrip(state.universe?.beings || []);
});

hearBeingBtn.addEventListener("click", () => {
  const being = (state.universe?.beings || []).find((b) => b.id === state.selectedBeingId);
  const fallback = being
    ? `I am ${being.name}, ${being.mood_phrase || "keeping quiet watch"} in ${prettifyZone(being.zone)}. My calling is ${being.soul?.calling || "steward"}.`
    : "I am listening within the sanctuary.";
  const spoken = state.selectedBeingWorld?.voice_intro || fallback;
  speakText(spoken, { force: true });
});

openTapestryBtn.addEventListener("click", () => {
  renderTapestry();
  tapestryBackdropEl.classList.remove("hidden");
});

closeTapestryBtn.addEventListener("click", () => {
  tapestryBackdropEl.classList.add("hidden");
});

tapestryBackdropEl.addEventListener("click", (ev) => {
  if (ev.target === tapestryBackdropEl) {
    tapestryBackdropEl.classList.add("hidden");
  }
});

tabChaptersBtn.addEventListener("click", () => {
  tabChaptersBtn.classList.add("active");
  tabEventsBtn.classList.remove("active");
  panelChaptersEl.classList.remove("hidden");
  panelEventsEl.classList.add("hidden");
});

tabEventsBtn.addEventListener("click", () => {
  tabEventsBtn.classList.add("active");
  tabChaptersBtn.classList.remove("active");
  panelEventsEl.classList.remove("hidden");
  panelChaptersEl.classList.add("hidden");
});

sparkForm.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const message = sparkInputEl.value.trim();
  const zone = sparkZoneEl.value || "hub";
  const kind = sparkKindEl?.value || "curiosity";
  if (!message) {
    sparkFeedbackEl.textContent = "Whisper a few words first to send a spark.";
    return;
  }
  sparkFeedbackEl.textContent = "Sending your spark across the sanctuary…";
  triggerRipple(zone, kind === "incident" ? "#fb8a70" : "#f6c46d", 1.35);
  triggerFilament("hub", zone, "#ffdfa3");
  playHarmonicChime("spark");

  try {
    const res = await fetch("/api/pulse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ zone, spark: message, kind }),
    });
    const result = await res.json().catch(() => ({}));
    if (!res.ok || result.ok === false) {
      throw new Error(result.error || "Pulse paused");
    }
    sparkInputEl.value = "";
    sparkFeedbackEl.textContent =
      result.acknowledgment || result.story || `Your spark now glows inside ${prettifyZone(zone)}.`;
    if (state.speechEnabled && (result.spoken_reply || result.spoken)) {
      speakText(result.spoken_reply || result.spoken);
    }
    await refreshUniverse();
  } catch (err) {
    sparkFeedbackEl.textContent = err?.message || "The sanctuary could not catch that spark right now.";
  }
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
initStars();
resizeCanvas();
window.addEventListener("resize", resizeCanvas);
if ("speechSynthesis" in window) {
  populateVoices();
  window.speechSynthesis.onvoiceschanged = populateVoices;
}
syncVoiceUI();
refreshUniverse();
setInterval(refreshUniverse, POLL_INTERVAL_MS);
requestAnimationFrame(renderFrame);
