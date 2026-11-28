// The Living Cosmos — Pure ES Module 3D Embodied World, Voice & Chimes

const POLL_INTERVAL_MS = 3200;
const RING_RADIUS_LARGE = 32;
const RING_RADIUS_SMALL_OUTER = 26;
const RING_RADIUS_SMALL_INNER = 19;

const ZONE_3D = {
  hub: {
    label: "The Central Hearth",
    x: 0,
    y: -30,
    z: 24,
    radius: 96,
    hue: "#4fe3c1",
    edgeHue: "#1f9c88",
    glow: "rgba(79, 227, 193, 0.28)",
  },
  "alpha-sector": {
    label: "Alpha Sanctuary",
    x: -345,
    y: -155,
    z: 12,
    radius: 92,
    hue: "#60d9f6",
    edgeHue: "#257da3",
    glow: "rgba(96, 217, 246, 0.26)",
  },
  "beta-sector": {
    label: "Beta Frontier",
    x: 345,
    y: -155,
    z: 14,
    radius: 92,
    hue: "#f6c46d",
    edgeHue: "#a87729",
    glow: "rgba(246, 196, 109, 0.24)",
  },
  playground: {
    label: "Starlight Playground",
    x: 0,
    y: 185,
    z: 18,
    radius: 90,
    hue: "#ffdfa3",
    edgeHue: "#9f7aea",
    glow: "rgba(255, 223, 163, 0.25)",
  },
  frontier: {
    label: "Far Horizon",
    x: 0,
    y: 405,
    z: 34,
    radius: 88,
    hue: "#a78bfa",
    edgeHue: "#6447b5",
    glow: "rgba(167, 139, 250, 0.26)",
  },
};

const DEFAULT_CHAPTERS = [
  {
    title: "Genesis & Physics",
    era: "Era I · First Light",
    status: "Alive at the core",
    summary: "Conserved charges, energy flow, and gentle entropy bounds formed the first natural laws of this cosmos.",
    essence: "Energy moves like breath; nothing vanishes without trace.",
  },
  {
    title: "Chemistry & Bonding",
    era: "Era II · First Bonds",
    status: "Woven into perception",
    summary: "Molecules bond through catalysis and gentle activation thresholds, turning scattered hints into coherent meaning.",
    essence: "Small sparks meet and become whole understandings.",
  },
  {
    title: "Living Body & Five Organs",
    era: "Era III · First Heartbeat",
    status: "Breathing continuously",
    summary: "Perception, deliberation, memory, action, and defense beat together inside an immutable genome.",
    essence: "Five quiet organs listen, reflect, remember, act, and protect.",
  },
  {
    title: "Homeostasis & Stem Renewal",
    era: "Era IV · Self-Healing",
    status: "Self-healing",
    summary: "Tissues divide when needed, rest in dreaming renewal, and recycle tired matter back into vital energy.",
    essence: "Even rest is creative; dreams turn yesterday into strength.",
  },
  {
    title: "Society & Protective Skin",
    era: "Era V · Fellowship",
    status: "Harmonic fellowship",
    summary: "Neighbors verify one another with trust, share territory gently, and shield against harsh outside storms.",
    essence: "Trust travels softly between sovereign companions.",
  },
  {
    title: "Evolution & Living Senses",
    era: "Era VI · Awakening Senses",
    status: "Listening & adapting",
    summary: "Safe evolutionary trials and real vessel senses connect each organism to the living machine beneath it.",
    essence: "Grounded in real hardware warmth and gentle adaptation.",
  },
  {
    title: "Shared & Relative Worlds",
    era: "Era VII · Lands, Paths & Doors",
    status: "Unfolding now",
    summary: "Lands, cozy homes, winding paths, luminous doors, and playground trials form a living world shared by all.",
    essence: "Every step across a path or doorway carries a story.",
  },
  {
    title: "Soul, Character & Embodied Life",
    era: "Era VIII · Eyes, Ears, Hands & Soul",
    status: "Awakened",
    summary: "Each being walks with eyes, ears, tongue, hands, legs, an immutable calling, and honor earned in community.",
    essence: "Embodied life shaped by kindness, curiosity, and truth.",
  },
];

const state = {
  universe: null,
  selectedBeingId: null,
  selectedBeingWorld: null,
  hoveredHit: null,
  lastTick: -1,
  lastBulletinId: null,
  lastSpokenEventId: null,
  lastEventIds: new Set(),
  homeCycleIdx: 0,
  speechEnabled: false,
  chimesEnabled: false,
  selectedVoiceURI: "",
  voices: [],
  audioCtx: null,
  beingsAnim: new Map(),
  ripples: [],
  filaments: [],
  fxBursts: [],
  stars: [],
  zoneNodes: new Map(),
  doorFlashes: new Map(),
  hitTargets: [],
  canvasWidth: 0,
  canvasHeight: 0,
  dpr: 1,
  camera: {
    mode: "iso", // "iso" | "arena" | "follow"
    yaw: -0.34,
    pitch: 0.72,
    zoom: 0.92,
    tx: 0,
    ty: 75,
    tz: 18,
    targetTx: 0,
    targetTy: 75,
    targetTz: 18,
    targetYaw: -0.34,
    targetPitch: 0.72,
    targetZoom: 0.92,
    dragging: false,
    dragMoved: false,
    lastPointerX: 0,
    lastPointerY: 0,
  },
};

// DOM references
const sanctuaryHudEl = document.querySelector(".sanctuary-hud");
const nebulaEl = document.querySelector(".cosmos-nebula");
const canvas = document.getElementById("biosphere-canvas");
const ctx = canvas.getContext("2d");
const tooltipEl = document.getElementById("canvas-tooltip");
const worldBreathEl = document.getElementById("world-breath");
const narrativeHeadlineEl = document.getElementById("narrative-headline");
const narrativeStoryEl = document.getElementById("narrative-story");
const whisperVoiceStateEl = document.getElementById("whisper-voice-state");
const beingsStripEl = document.getElementById("beings-strip");

// Camera Controls DOM
const camIsoBtn = document.getElementById("cam-iso-btn");
const camArenaBtn = document.getElementById("cam-arena-btn");
const camFollowBtn = document.getElementById("cam-follow-btn");
const camZoomInBtn = document.getElementById("cam-zoom-in");
const camZoomOutBtn = document.getElementById("cam-zoom-out");
const competitionBannerEl = document.getElementById("competition-banner");
const competitionTextEl = document.getElementById("competition-text");
const playgroundPopoverEl = document.getElementById("playground-popover");
const playgroundCloseBtn = document.getElementById("playground-close-btn");
const podiumTitleEl = document.getElementById("podium-title");
const podiumStoryEl = document.getElementById("podium-story");
const podiumRunTrialBtn = document.getElementById("podium-run-trial-btn");
const podiumCountdownEl = document.getElementById("podium-countdown");
const playgroundPodiumEl = document.getElementById("playground-podium");
const playgroundRewardsListEl = document.getElementById("playground-rewards-list");

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

// Spark & Trial Form DOM
const sparkForm = document.getElementById("spark-form");
const sparkZoneEl = document.getElementById("spark-zone");
const sparkKindEl = document.getElementById("spark-kind");
const sparkInputEl = document.getElementById("spark-input");
const startTrialBtn = document.getElementById("start-trial-btn");
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
const drawerLifePlaceEl = document.getElementById("drawer-life-place");
const drawerAnatomyListEl = document.getElementById("drawer-anatomy-list");
const drawerHonorLedgerEl = document.getElementById("drawer-honor-ledger");
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
const evolveTraitsBtn = document.getElementById("evolve-traits-btn");
const evolutionInsightBannerEl = document.getElementById("evolution-insight-banner");

// ---------------------------------------------------------------------------
// Helpers: Organic Naming, Viewport Clamping & Formatting
// ---------------------------------------------------------------------------
function prettifyZone(zoneName) {
  if (!zoneName) return "Sanctuary";
  if (ZONE_3D[zoneName]) return ZONE_3D[zoneName].label;
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
  if (t.includes("reward") || t.includes("warm") || t.includes("soul") || t.includes("gold") || t.includes("spark")) {
    return "#f6c46d";
  }
  if (t.includes("punish") || t.includes("alert") || t.includes("coral") || t.includes("warn")) return "#fb8a70";
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

function positionPopoverInViewport(popoverEl, anchorEl) {
  if (!popoverEl || popoverEl.classList.contains("hidden") || !anchorEl) return;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const anchorRect = anchorEl.getBoundingClientRect();
  const margin = 12;

  if (vw <= 760) {
    const top = Math.min(Math.max(margin, anchorRect.bottom + 8), Math.max(margin, vh * 0.26));
    popoverEl.style.left = `${margin}px`;
    popoverEl.style.right = `${margin}px`;
    popoverEl.style.top = `${Math.round(top)}px`;
    popoverEl.style.maxHeight = `${Math.max(180, Math.round(vh - top - margin))}px`;
    return;
  }

  popoverEl.style.right = "auto";
  const popRect = popoverEl.getBoundingClientRect();
  const popW = Math.min(popRect.width || 320, vw - margin * 2);
  const popH = Math.min(popRect.height || 320, vh - margin * 2);

  let left = anchorRect.right - popW;
  left = Math.max(margin, Math.min(left, vw - popW - margin));

  let top = anchorRect.bottom + 10;
  if (top + popH > vh - margin) {
    top = Math.max(margin, vh - popH - margin);
  }

  popoverEl.style.left = `${Math.round(left)}px`;
  popoverEl.style.top = `${Math.round(top)}px`;
  popoverEl.style.maxHeight = `${Math.round(vh - top - margin)}px`;
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
      pulse: [392.0, 493.88, 587.33],
      spark: [440.0, 554.37, 659.25, 880.0],
      reward: [523.25, 659.25, 783.99, 1046.5],
      select: [329.63, 440.0, 523.25],
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
    // Ignored cleanly if blocked
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
    // Safe no-op
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
// 3D Camera Projection & Spatial World Geometry
// ---------------------------------------------------------------------------
function initStars() {
  state.stars = Array.from({ length: 95 }, () => ({
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

  if (state.canvasWidth <= 760 && state.camera.mode === "iso") {
    state.camera.targetZoom = 0.76;
    state.camera.zoom = 0.76;
  }

  positionPopoverInViewport(voicePopoverEl, voicePillBtn);
  positionPopoverInViewport(vitalityPopoverEl, vitalityPillBtn);
  positionPopoverInViewport(playgroundPopoverEl, competitionBannerEl);
}

function project3D(wx, wy, wz) {
  const cam = state.camera;
  const rx = wx - cam.tx;
  const ry = wy - cam.ty;
  const rz = wz - cam.tz;

  const cy = Math.cos(cam.yaw);
  const sy = Math.sin(cam.yaw);
  const x1 = rx * cy - ry * sy;
  const y1 = rx * sy + ry * cy;

  const cp = Math.cos(cam.pitch);
  const sp = Math.sin(cam.pitch);
  const y2 = y1 * cp - rz * sp;
  const z2 = y1 * sp + rz * cp;

  const focal = 1100;
  const depth = Math.max(-520, z2);
  const persp = focal / (focal + 540 - depth);
  const isPhone = state.canvasWidth <= 760;
  const baseScale = isPhone ? (state.canvasWidth / 560) : (Math.min(state.canvasWidth, state.canvasHeight) / 840);
  const scale = persp * cam.zoom * baseScale;

  const drawerShift = state.selectedBeingId && state.canvasWidth > 980 ? -185 : 0;
  const cx = state.canvasWidth * 0.5 + drawerShift;
  const cyScreen = state.canvasHeight * (isPhone ? 0.42 : 0.43);

  return {
    sx: cx + x1 * scale,
    sy: cyScreen + y2 * scale * 0.86 - rz * scale * 0.42,
    depth,
    scale,
  };
}

function worldCoordsForZone(zone, idx = 0) {
  const preset = ZONE_3D[zone?.name];
  if (preset) {
    return {
      x: preset.x,
      y: preset.y,
      z: preset.z,
      radius: preset.radius,
      rawX: Number(zone?.x ?? preset.x),
      rawY: Number(zone?.y ?? preset.y),
      rawZ: Number(zone?.z ?? preset.z),
    };
  }
  if (zone && zone.x != null && zone.y != null) {
    return {
      x: Number(zone.x) * 1.55,
      y: Number(zone.y) * 1.65,
      z: Number(zone.z ?? 10) * 1.6,
      radius: Number(zone.radius ?? 130) * 0.68,
      rawX: Number(zone.x),
      rawY: Number(zone.y),
      rawZ: Number(zone.z ?? 10),
    };
  }
  return [
    { x: 0, y: -30, z: 24, radius: 96, rawX: 0, rawY: 0, rawZ: 14 },
    { x: -345, y: -155, z: 12, radius: 92, rawX: -245, rawY: -110, rawZ: 6 },
    { x: 345, y: -155, z: 14, radius: 92, rawX: 245, rawY: -110, rawZ: 6 },
    { x: 0, y: 185, z: 18, radius: 90, rawX: 0, rawY: 110, rawZ: 10 },
    { x: 0, y: 405, z: 34, radius: 88, rawX: 0, rawY: 255, rawZ: 22 },
  ][idx % 5];
}

function syncZoneNodes() {
  const zones = state.universe?.world?.zones || [];
  state.zoneNodes.clear();
  zones.forEach((zone, idx) => {
    const preset = ZONE_3D[zone.name] || {};
    const coords = worldCoordsForZone(zone, idx);
    state.zoneNodes.set(zone.name, {
      ...coords,
      hue: preset.hue || "#4fe3c1",
      edgeHue: preset.edgeHue || "#1e7c6d",
      glow: preset.glow || "rgba(79, 227, 193, 0.24)",
      label: zone.label || prettifyZone(zone.name),
      zone,
    });
  });
}

function getZoneCenter(zoneName) {
  return state.zoneNodes.get(zoneName) || state.zoneNodes.get("hub") || { x: 0, y: 0, z: 10, radius: 95 };
}

function resolvePlaceWorldCoords(place, fallbackZone = "hub", offsetIdx = 0) {
  const zc = getZoneCenter(place?.zone || fallbackZone);
  if (place && place.x != null && place.y != null && zc.rawX != null) {
    const dx = Math.max(-zc.radius * 0.55, Math.min(zc.radius * 0.55, Number(place.x) - zc.rawX));
    const dy = Math.max(-zc.radius * 0.55, Math.min(zc.radius * 0.55, Number(place.y) - zc.rawY));
    return {
      x: zc.x + dx,
      y: zc.y + dy,
      z: zc.z,
    };
  }
  const angle = offsetIdx * 1.65 + 0.5;
  return {
    x: zc.x + Math.cos(angle) * (zc.radius * 0.48),
    y: zc.y + Math.sin(angle) * (zc.radius * 0.44),
    z: zc.z,
  };
}

function resolvePlaygroundCoords() {
  const pgs = state.universe?.world?.playgrounds || [];
  if (pgs.length) {
    return resolvePlaceWorldCoords(pgs[0], pgs[0].zone || "playground", 0);
  }
  const f = getZoneCenter("playground");
  return { x: f.x, y: f.y, z: f.z + 2 };
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
    const zc = getZoneCenter(being.zone);
    const siblings = zoneBuckets.get(being.zone || "hub") || [being];
    const indexInZone = siblings.indexOf(being);
    const count = siblings.length;
    const walkState = String(being.location?.walk_state || "");

    let tx;
    let ty;
    let tz;
    if (walkState === "crossing_door" && being.location?.x != null && zc.rawX != null) {
      const dx = Number(being.location.x) - zc.rawX;
      const dy = Number(being.location.y) - zc.rawY;
      tx = zc.x + dx * 1.35;
      ty = zc.y + dy * 1.35;
      tz = zc.z + 4;
    } else if (count === 1) {
      tx = zc.x + zc.radius * 0.24;
      ty = zc.y + zc.radius * 0.22;
      tz = zc.z + 2;
    } else {
      // Spread siblings cleanly across the island terrace so no bodies or labels stack
      const angleOffset = (indexInZone / count) * Math.PI * 2 + 0.35;
      const orbitDist = Math.min(zc.radius * 0.68, Math.max(46, count * 14));
      tx = zc.x + Math.cos(angleOffset) * orbitDist;
      ty = zc.y + Math.sin(angleOffset) * (orbitDist * 0.86);
      tz = zc.z + (walkState === "competing_playground" ? 6 : 2);
    }

    const existing = state.beingsAnim.get(being.id);
    if (!existing) {
      state.beingsAnim.set(being.id, {
        wx: tx,
        wy: ty,
        wz: tz,
        targetX: tx,
        targetY: ty,
        targetZ: tz,
        phase: Math.random() * Math.PI * 2,
        blinkTimer: 1.5 + Math.random() * 3.5,
        rewardTimer: 0,
        punishTimer: 0,
        speakTimer: 0,
        prevRewards: Number(being.rewards ?? 0),
        prevPunishments: Number(being.punishments ?? 0),
        being,
      });
    } else {
      if (existing.being.zone !== being.zone) {
        triggerFilament(existing.being.zone, being.zone, "#60d9f6");
        triggerRipple(being.zone, "#f6c46d", 1.0);
        state.doorFlashes.set(`${existing.being.zone}:${being.zone}`, 1.0);
      }
      const rNow = Number(being.rewards ?? 0);
      const pNow = Number(being.punishments ?? 0);
      if (rNow > existing.prevRewards) {
        existing.rewardTimer = 3.2;
        state.fxBursts.push({ wx: tx, wy: ty, wz: tz + 28, kind: "reward", life: 1.0 });
        playHarmonicChime("reward");
      }
      if (pNow > existing.prevPunishments) {
        existing.punishTimer = 2.8;
        state.fxBursts.push({ wx: tx, wy: ty, wz: tz + 24, kind: "punish", life: 1.0 });
      }
      existing.prevRewards = rNow;
      existing.prevPunishments = pNow;
      existing.targetX = tx;
      existing.targetY = ty;
      existing.targetZ = tz;
      existing.being = being;
    }
  });

  for (const key of state.beingsAnim.keys()) {
    if (!seenIds.has(key)) state.beingsAnim.delete(key);
  }
}

function triggerRipple(zoneName, color = "#4fe3c1", strength = 1.0) {
  const zc = getZoneCenter(zoneName);
  state.ripples.push({
    wx: zc.x,
    wy: zc.y,
    wz: zc.z,
    r: zc.radius * 0.25,
    maxR: zc.radius * (1.55 + strength * 0.55),
    alpha: 0.85,
    color,
  });
}

function triggerFilament(fromZone, toZone, color = "#f6c46d") {
  const a = getZoneCenter(fromZone);
  const b = getZoneCenter(toZone);
  if (a === b) return;
  state.filaments.push({
    x1: a.x,
    y1: a.y,
    z1: a.z + 18,
    x2: b.x,
    y2: b.y,
    z2: b.z + 18,
    progress: 0,
    color,
  });
}

function setCameraMode(mode) {
  state.camera.mode = mode;
  [camIsoBtn, camArenaBtn, camFollowBtn].forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.cam === mode);
  });

  if (mode === "iso") {
    state.camera.targetTx = 0;
    state.camera.targetTy = 75;
    state.camera.targetTz = 18;
    state.camera.targetYaw = -0.34;
    state.camera.targetPitch = 0.72;
    state.camera.targetZoom = state.canvasWidth <= 760 ? 0.76 : 0.92;
  } else if (mode === "arena") {
    const pg = resolvePlaygroundCoords();
    state.camera.targetTx = pg.x;
    state.camera.targetTy = pg.y;
    state.camera.targetTz = pg.z + 8;
    state.camera.targetPitch = 0.58;
    state.camera.targetZoom = state.canvasWidth <= 760 ? 0.96 : 1.32;
  } else if (mode === "follow") {
    if (!state.selectedBeingId && state.universe?.beings?.length) {
      selectBeing(state.universe.beings[0].id, { speak: false });
    }
    state.camera.targetZoom = state.canvasWidth <= 760 ? 1.08 : 1.42;
  }
}

function drawOutlinedText(text, x, y, fillStyle, font) {
  ctx.save();
  ctx.textAlign = "center";
  ctx.font = font;
  ctx.lineJoin = "round";
  ctx.lineWidth = 3.4;
  ctx.strokeStyle = "rgba(5, 8, 20, 0.9)";
  ctx.strokeText(text, x, y);
  ctx.fillStyle = fillStyle;
  ctx.fillText(text, x, y);
  ctx.restore();
}

// ---------------------------------------------------------------------------
// 3D Drawing Primitives: Lands, Homes, Paths, Doors, Playground & Embodied Beings
// ---------------------------------------------------------------------------
function draw3DLandPlatform(node, t) {
  const zInfo = node.zone || {};
  const breath = 1 + 0.024 * Math.sin(t * 1.1 + node.x * 0.01);
  const rad = node.radius * breath;
  const sides = 8;
  const thickness = 18;

  const topPts = [];
  const botPts = [];
  for (let i = 0; i < sides; i += 1) {
    const a = (i / sides) * Math.PI * 2 + Math.PI / 8;
    const vx = node.x + Math.cos(a) * rad;
    const vy = node.y + Math.sin(a) * rad;
    topPts.push(project3D(vx, vy, node.z));
    botPts.push(project3D(vx, vy, node.z - thickness));
  }

  // Soft glow beneath island
  const centerProj = project3D(node.x, node.y, node.z);
  const glowR = rad * centerProj.scale * 1.4;
  const halo = ctx.createRadialGradient(
    centerProj.sx,
    centerProj.sy,
    glowR * 0.12,
    centerProj.sx,
    centerProj.sy,
    glowR
  );
  halo.addColorStop(0, node.glow);
  halo.addColorStop(1, "rgba(5, 8, 20, 0)");
  ctx.beginPath();
  ctx.arc(centerProj.sx, centerProj.sy, glowR, 0, Math.PI * 2);
  ctx.fillStyle = halo;
  ctx.fill();

  // Extruded side faces (bottom bevel)
  for (let i = 0; i < sides; i += 1) {
    const next = (i + 1) % sides;
    ctx.beginPath();
    ctx.moveTo(topPts[i].sx, topPts[i].sy);
    ctx.lineTo(topPts[next].sx, topPts[next].sy);
    ctx.lineTo(botPts[next].sx, botPts[next].sy);
    ctx.lineTo(botPts[i].sx, botPts[i].sy);
    ctx.closePath();
    ctx.fillStyle = "rgba(11, 18, 40, 0.84)";
    ctx.fill();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // Top luminous terrace
  ctx.beginPath();
  topPts.forEach((p, idx) => (idx === 0 ? ctx.moveTo(p.sx, p.sy) : ctx.lineTo(p.sx, p.sy)));
  ctx.closePath();
  const topGrad = ctx.createLinearGradient(
    centerProj.sx - glowR * 0.5,
    centerProj.sy - glowR * 0.5,
    centerProj.sx + glowR * 0.5,
    centerProj.sy + glowR * 0.5
  );
  topGrad.addColorStop(0, "rgba(20, 32, 66, 0.92)");
  topGrad.addColorStop(1, "rgba(10, 16, 36, 0.92)");
  ctx.fillStyle = topGrad;
  ctx.fill();

  const calmness = Number(zInfo.calmness ?? 0.85);
  ctx.strokeStyle = calmness < 0.5 ? "rgba(251, 138, 112, 0.55)" : node.hue;
  ctx.globalAlpha = 0.55;
  ctx.lineWidth = 1.8;
  ctx.stroke();
  ctx.globalAlpha = 1;

  // Inner concentric contour terrace ring
  ctx.beginPath();
  for (let i = 0; i < sides; i += 1) {
    const a = (i / sides) * Math.PI * 2 + Math.PI / 8;
    const p = project3D(node.x + Math.cos(a) * rad * 0.64, node.y + Math.sin(a) * rad * 0.64, node.z + 1);
    if (i === 0) ctx.moveTo(p.sx, p.sy);
    else ctx.lineTo(p.sx, p.sy);
  }
  ctx.closePath();
  ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
  ctx.lineWidth = 1;
  ctx.stroke();

  // Floating label above island edge
  const labelAnchor = project3D(node.x, node.y - rad * 0.94, node.z + 18);
  const isPhone = state.canvasWidth <= 760;
  drawOutlinedText(
    node.label,
    labelAnchor.sx,
    labelAnchor.sy - 6,
    "rgba(244, 247, 251, 0.94)",
    `600 ${Math.max(10, Math.round(12.5 * labelAnchor.scale))}px "Inter", system-ui, sans-serif`
  );
  if (zInfo.mood && !isPhone) {
    drawOutlinedText(
      zInfo.mood,
      labelAnchor.sx,
      labelAnchor.sy + 9,
      "rgba(182, 196, 224, 0.78)",
      `400 ${Math.max(9, Math.round(10.5 * labelAnchor.scale))}px "Inter", system-ui, sans-serif`
    );
  }
}

function draw3DPath(fromNode, toNode, t, index = 0) {
  const steps = 12;
  const mx = (fromNode.x + toNode.x) * 0.5;
  const my = (fromNode.y + toNode.y) * 0.5;
  const dx = toNode.x - fromNode.x;
  const dy = toNode.y - fromNode.y;
  const cx = mx - dy * 0.14;
  const cy = my + dx * 0.14;
  const cz = (fromNode.z + toNode.z) * 0.5 + 4;

  const points = [];
  for (let i = 0; i <= steps; i += 1) {
    const u = i / steps;
    const inv = 1 - u;
    const wx = inv * inv * fromNode.x + 2 * inv * u * cx + u * u * toNode.x;
    const wy = inv * inv * fromNode.y + 2 * inv * u * cy + u * u * toNode.y;
    const wz = inv * inv * fromNode.z + 2 * inv * u * cz + u * u * toNode.z;
    points.push({ wx, wy, wz, p: project3D(wx, wy, wz) });
  }

  ctx.save();
  ctx.beginPath();
  points.forEach((pt, idx) => (idx === 0 ? ctx.moveTo(pt.p.sx, pt.p.sy) : ctx.lineTo(pt.p.sx, pt.p.sy)));
  ctx.strokeStyle = "rgba(96, 217, 246, 0.34)";
  ctx.lineWidth = 3.2;
  ctx.stroke();

  // Stepping stones along the path
  for (let i = 2; i < steps - 1; i += 2) {
    const sp = points[i].p;
    ctx.beginPath();
    ctx.ellipse(sp.sx, sp.sy, 4.5 * sp.scale, 2.7 * sp.scale, 0, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255, 223, 163, 0.38)";
    ctx.fill();
  }

  // Flowing river motes
  for (let m = 0; m < 2; m += 1) {
    const u = (t * 0.16 + m * 0.5 + index * 0.21) % 1;
    const inv = 1 - u;
    const wx = inv * inv * fromNode.x + 2 * inv * u * cx + u * u * toNode.x;
    const wy = inv * inv * fromNode.y + 2 * inv * u * cy + u * u * toNode.y;
    const wz = inv * inv * fromNode.z + 2 * inv * u * cz + u * u * toNode.z + 2;
    const mp = project3D(wx, wy, wz);
    ctx.beginPath();
    ctx.arc(mp.sx, mp.sy, 3 * mp.scale, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(190, 248, 255, 0.88)";
    ctx.fill();
  }
  ctx.restore();
}

function draw3DHome(home, coords, t) {
  const base = project3D(coords.x, coords.y, coords.z);
  const roof = project3D(coords.x, coords.y, coords.z + 28);
  const s = base.scale;
  const w = 18 * s;
  const h = 15 * s;

  ctx.save();
  // Warm hearth ground glow
  const glow = ctx.createRadialGradient(base.sx, base.sy, 2, base.sx, base.sy, 30 * s);
  glow.addColorStop(0, "rgba(246, 196, 109, 0.36)");
  glow.addColorStop(1, "rgba(246, 196, 109, 0)");
  ctx.beginPath();
  ctx.arc(base.sx, base.sy, 30 * s, 0, Math.PI * 2);
  ctx.fillStyle = glow;
  ctx.fill();

  // Cottage body
  ctx.beginPath();
  ctx.roundRect(base.sx - w * 0.75, base.sy - h, w * 1.5, h, 4 * s);
  ctx.fillStyle = "rgba(32, 42, 74, 0.94)";
  ctx.strokeStyle = "rgba(246, 196, 109, 0.55)";
  ctx.lineWidth = 1.3;
  ctx.fill();
  ctx.stroke();

  // Warm glowing arched doorway
  ctx.beginPath();
  ctx.arc(base.sx, base.sy - 2 * s, 4.5 * s, Math.PI, 0);
  ctx.lineTo(base.sx + 4.5 * s, base.sy);
  ctx.lineTo(base.sx - 4.5 * s, base.sy);
  ctx.closePath();
  ctx.fillStyle = "#ffdfa3";
  ctx.fill();

  // Glowing domed roof
  ctx.beginPath();
  ctx.moveTo(base.sx - w * 0.95, base.sy - h + 1);
  ctx.quadraticCurveTo(roof.sx, roof.sy - 6 * s, base.sx + w * 0.95, base.sy - h + 1);
  ctx.closePath();
  ctx.fillStyle = "rgba(167, 139, 250, 0.78)";
  ctx.strokeStyle = "rgba(255, 223, 163, 0.65)";
  ctx.fill();
  ctx.stroke();

  // Floating hearth ember
  const emberY = roof.sy - 6 * s - ((t * 14) % (12 * s));
  ctx.beginPath();
  ctx.arc(roof.sx + Math.sin(t * 2 + coords.x) * 2 * s, emberY, 1.8 * s, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(255, 223, 163, 0.75)";
  ctx.fill();

  if ((home.name || home.label) && state.canvasWidth > 760) {
    drawOutlinedText(
      home.label || home.name,
      base.sx,
      base.sy + 13 * s,
      "rgba(255, 223, 163, 0.86)",
      `500 ${Math.max(9, Math.round(10 * s))}px "Inter", system-ui, sans-serif`
    );
  }
  ctx.restore();

  state.hitTargets.push({
    sx: base.sx,
    sy: base.sy - h * 0.5,
    r: Math.max(18, 22 * s),
    type: "home",
    home,
    label: home.label || home.name || "Cozy Home",
    story: `${home.name || "Cozy Home"} — ${home.story || "A warm sanctuary hearth where beings dream and renew."} (Click to visit resident)`,
  });
}

function draw3DDoor(door, coords, t) {
  const base = project3D(coords.x, coords.y, coords.z);
  const top = project3D(coords.x, coords.y, coords.z + 26);
  const s = base.scale;
  const guarded = String(door.state || "open").toLowerCase() === "guarded";
  const zA = door.zone_a || door.from_zone || "";
  const zB = door.zone_b || door.to_zone || "";
  const flashKey = `${zA}:${zB}`;
  const flashRev = `${zB}:${zA}`;
  let flash = Math.max(state.doorFlashes.get(flashKey) || 0, state.doorFlashes.get(flashRev) || 0);
  if (door.recent_flash) flash = Math.max(flash, 0.85);
  if (state.doorFlashes.get(flashKey) > 0) state.doorFlashes.set(flashKey, Math.max(0, state.doorFlashes.get(flashKey) - 0.02));
  if (state.doorFlashes.get(flashRev) > 0) state.doorFlashes.set(flashRev, Math.max(0, state.doorFlashes.get(flashRev) - 0.02));

  const archColor = guarded ? "#fb8a70" : flash > 0.1 ? "#ffdfa3" : "#4fe3c1";
  const archW = 11 * s;
  const archH = Math.max(16 * s, base.sy - top.sy);

  ctx.save();
  // Portal inner shimmer
  const portalGrad = ctx.createRadialGradient(base.sx, base.sy - archH * 0.5, 1, base.sx, base.sy - archH * 0.5, archW * 1.4);
  portalGrad.addColorStop(0, guarded ? "rgba(251, 138, 112, 0.45)" : "rgba(79, 227, 193, 0.45)");
  portalGrad.addColorStop(1, "rgba(5, 8, 20, 0)");
  ctx.beginPath();
  ctx.arc(base.sx, base.sy - archH * 0.5, archW * 1.4, 0, Math.PI * 2);
  ctx.fillStyle = portalGrad;
  ctx.fill();

  // Luminous archway pillars & crown
  ctx.beginPath();
  ctx.moveTo(base.sx - archW, base.sy);
  ctx.lineTo(base.sx - archW, base.sy - archH * 0.65);
  ctx.arc(base.sx, base.sy - archH * 0.65, archW, Math.PI, 0);
  ctx.lineTo(base.sx + archW, base.sy);
  ctx.strokeStyle = archColor;
  ctx.lineWidth = (2.6 + flash * 2) * Math.max(0.8, s);
  ctx.shadowColor = archColor;
  ctx.shadowBlur = 12 + flash * 14;
  ctx.stroke();

  if (guarded) {
    // Soft protective lattice across guarded door
    ctx.beginPath();
    ctx.moveTo(base.sx - archW * 0.7, base.sy - archH * 0.35);
    ctx.lineTo(base.sx + archW * 0.7, base.sy - archH * 0.55);
    ctx.strokeStyle = "rgba(251, 138, 112, 0.75)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
  ctx.restore();

  state.hitTargets.push({
    sx: base.sx,
    sy: base.sy - archH * 0.5,
    r: Math.max(16, 18 * s),
    type: "door",
    door,
    label: door.name || door.label || "Realm Doorway",
    story: `${door.name || "Doorway"} (${guarded ? "Guarded" : "Open"}) — Click to toggle guardian seal`,
  });
}

function draw3DPlaygroundArena(pg, coords, t, compActive) {
  const base = project3D(coords.x, coords.y, coords.z + 4);
  const s = base.scale;
  const rx = 44 * s;
  const ry = 24 * s;

  ctx.save();
  // Stage outer aura
  const stageGlow = ctx.createRadialGradient(base.sx, base.sy, rx * 0.2, base.sx, base.sy, rx * 1.4);
  stageGlow.addColorStop(0, compActive ? "rgba(246, 196, 109, 0.42)" : "rgba(167, 139, 250, 0.28)");
  stageGlow.addColorStop(1, "rgba(5, 8, 20, 0)");
  ctx.beginPath();
  ctx.arc(base.sx, base.sy, rx * 1.4, 0, Math.PI * 2);
  ctx.fillStyle = stageGlow;
  ctx.fill();

  // Concentric 3D arena rings
  [1.0, 0.72, 0.42].forEach((k, idx) => {
    ctx.beginPath();
    ctx.ellipse(base.sx, base.sy, rx * k, ry * k, 0, 0, Math.PI * 2);
    ctx.fillStyle = idx === 0 ? "rgba(24, 22, 58, 0.78)" : "rgba(246, 196, 109, 0.12)";
    ctx.fill();
    ctx.strokeStyle = compActive ? "#f6c46d" : idx === 0 ? "#a78bfa" : "rgba(96, 217, 246, 0.45)";
    ctx.lineWidth = idx === 0 ? 2 : 1.2;
    ctx.stroke();
  });

  // 4 glowing arena beacons around rim
  for (let i = 0; i < 4; i += 1) {
    const a = t * (compActive ? 0.8 : 0.25) + (i * Math.PI) / 2;
    const bx = base.sx + Math.cos(a) * rx;
    const by = base.sy + Math.sin(a) * ry;
    ctx.beginPath();
    ctx.moveTo(bx, by);
    ctx.lineTo(bx, by - 16 * s);
    ctx.strokeStyle = "rgba(255, 223, 163, 0.72)";
    ctx.lineWidth = 2 * s;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(bx, by - 17 * s, 3 * s, 0, Math.PI * 2);
    ctx.fillStyle = compActive ? "#ffdfa3" : "#60d9f6";
    ctx.fill();
  }

  ctx.restore();
  drawOutlinedText(
    pg?.name || pg?.label || "Starlight Arena",
    base.sx,
    base.sy + ry + 13 * s,
    "#ffdfa3",
    `600 ${Math.max(10, Math.round(11.5 * s))}px "Inter", system-ui, sans-serif`
  );

  state.hitTargets.push({
    sx: base.sx,
    sy: base.sy,
    r: Math.max(24, rx * 0.9),
    type: "playground",
    label: pg?.name || pg?.label || "Starlight Arena",
    story: pg?.story || "A vibrant cosmic stage where organisms test skills, collaborate, and earn honor.",
  });
}

function drawArticulatedBeing3D(anim, t) {
  const being = anim.being;
  const walkState = String(being.location?.walk_state || (String(being.mode || "").includes("SLEEP") ? "resting_home" : "walking_path"));
  const isResting = walkState === "resting_home" || String(being.mode || "").includes("SLEEP");
  const isCompeting = walkState === "competing_playground";
  const isWorking = walkState === "crossing_door" || String(being.mode || "") === "DEEP_FOCUS";
  const isMoving = (anim.speed ?? 0) > 0.15 || walkState === "walking_path" || walkState === "crossing_door";

  const wanderX = walkState === "walking_path" && (anim.speed ?? 0) < 0.5 ? Math.cos(t * 0.55 + anim.phase) * 7 : 0;
  const wanderY = walkState === "walking_path" && (anim.speed ?? 0) < 0.5 ? Math.sin(t * 0.45 + anim.phase) * 6 : 0;

  const bobAmp = isResting ? 1.5 : isCompeting ? 5.5 : isMoving ? 4.0 : 2.6;
  const bob = Math.sin(t * (isCompeting ? 5.4 : isMoving ? 4.2 : 2.1) + anim.phase) * bobAmp;
  const proj = project3D(anim.wx + wanderX, anim.wy + wanderY, anim.wz + 12 + bob);
  const footProj = project3D(anim.wx + wanderX, anim.wy + wanderY, anim.wz + 1);
  const s = Math.max(0.55, proj.scale);

  const pal = moodPalette(being);
  const isSelected = state.selectedBeingId === being.id;
  const isHovered = state.hoveredHit?.type === "being" && state.hoveredHit?.id === being.id;
  const anatomy = being.anatomy || {};
  const eyeStr = Number(anatomy.eyes?.strength ?? 0.75);
  const earStr = Number(anatomy.ears?.strength ?? 0.7);
  const tongueStr = Number(anatomy.tongue?.strength ?? 0.72);
  const handStr = Number(anatomy.hands?.strength ?? 0.75);
  const legStr = Number(anatomy.legs?.strength ?? 0.75);

  const sx = proj.sx;
  const sy = proj.sy;

  ctx.save();

  // Ground shadow
  ctx.beginPath();
  ctx.ellipse(footProj.sx, footProj.sy, 14 * s, 7 * s, 0, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(3, 5, 14, 0.55)";
  ctx.fill();

  // Mood / Selection / Punishment / Reward Aura
  const auraR = (isSelected ? 40 : isHovered ? 35 : 29) * s;
  const auraGrad = ctx.createRadialGradient(sx, sy - 6 * s, 3 * s, sx, sy - 6 * s, auraR);
  auraGrad.addColorStop(0, pal.glow);
  auraGrad.addColorStop(1, "rgba(5, 8, 20, 0)");
  ctx.beginPath();
  ctx.arc(sx, sy - 6 * s, auraR, 0, Math.PI * 2);
  ctx.fillStyle = auraGrad;
  ctx.fill();

  if (isSelected || isHovered) {
    ctx.beginPath();
    ctx.ellipse(footProj.sx, footProj.sy, 22 * s, 11 * s, 0, 0, Math.PI * 2);
    ctx.strokeStyle = isSelected ? "#ffdfa3" : "rgba(255, 255, 255, 0.6)";
    ctx.lineWidth = isSelected ? 2.2 : 1.4;
    ctx.stroke();
  }

  // Brief crimson correction ring if punished recently
  if (anim.punishTimer > 0) {
    anim.punishTimer = Math.max(0, anim.punishTimer - 0.016);
    ctx.beginPath();
    ctx.ellipse(footProj.sx, footProj.sy, 24 * s, 12 * s, 0, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(251, 138, 112, 0.85)";
    ctx.lineWidth = 2.4;
    ctx.stroke();
  }

  // 1. LEGS (crisp walking stride when velocity > 0.15 or strolling paths; tucked at Home)
  const strideFreq = isMoving ? 6.2 + legStr * 3.5 : 3.0;
  const strideAmp = isResting ? 0 : isMoving ? (6.5 + legStr * 4.0) * s : 2.4 * s;
  const stride = Math.sin(t * strideFreq + anim.phase) * strideAmp;
  const legLen = (isResting ? 5 : 10.5 + legStr * 3) * s;
  ctx.strokeStyle = pal.secondary;
  ctx.lineWidth = 2.6 * s;
  ctx.lineCap = "round";
  [-1, 1].forEach((side) => {
    const hipX = sx + side * 4.5 * s;
    const hipY = sy + 4 * s;
    const footX = hipX + side * (isResting ? 3 * s : 1.5 * s) + (side === -1 ? stride : -stride) * 0.65;
    const footY = hipY + legLen - (side === -1 ? Math.max(0, stride * 0.38) : Math.max(0, -stride * 0.38));
    ctx.beginPath();
    ctx.moveTo(hipX, hipY);
    ctx.quadraticCurveTo(hipX + side * 2 * s, hipY + legLen * 0.5, footX, footY);
    ctx.stroke();
  });

  // 2. HANDS / ARMS (gesturing, carrying golden spark orbs, or raising celebration ribbons)
  const armWave = isCompeting || anim.rewardTimer > 0
    ? -8 * s - Math.abs(Math.sin(t * 6 + anim.phase)) * 7 * s
    : isWorking || isMoving
      ? Math.sin(t * 4.8 + anim.phase) * 5.2 * s
      : Math.sin(t * 1.8 + anim.phase) * 2.5 * s;

  [-1, 1].forEach((side) => {
    const shX = sx + side * 10 * s;
    const shY = sy - 3 * s;
    const handX = shX + side * (8 + handStr * 4) * s;
    const handY = shY + (isCompeting || anim.rewardTimer > 0 ? armWave : 3 * s + armWave * side);
    ctx.beginPath();
    ctx.moveTo(shX, shY);
    ctx.lineTo(handX, handY);
    ctx.strokeStyle = pal.primary;
    ctx.lineWidth = 2.4 * s;
    ctx.stroke();

    const carryingOrb = side === 1 && (isWorking || isCompeting || walkState === "walking_path");
    ctx.beginPath();
    ctx.arc(handX, handY, (carryingOrb ? 3.2 : 2.2 + handStr * 1.4) * s, 0, Math.PI * 2);
    ctx.fillStyle = carryingOrb ? "#ffdfa3" : pal.secondary;
    ctx.fill();
  });

  // 3. TORSO & HEAD CORE
  const bodyR = 11.5 * s;
  const torsoGrad = ctx.createRadialGradient(sx - 3 * s, sy - 6 * s, 2 * s, sx, sy - 3 * s, bodyR);
  torsoGrad.addColorStop(0, "#ffffff");
  torsoGrad.addColorStop(0.45, pal.primary);
  torsoGrad.addColorStop(1, "rgba(12, 20, 46, 0.92)");
  ctx.beginPath();
  ctx.ellipse(sx, sy - 3 * s, bodyR, bodyR * 1.12, 0, 0, Math.PI * 2);
  ctx.fillStyle = torsoGrad;
  ctx.fill();

  // Head dome
  const headY = sy - 16 * s;
  const headR = 8.2 * s;
  ctx.beginPath();
  ctx.arc(sx, headY, headR, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(18, 28, 58, 0.94)";
  ctx.strokeStyle = pal.primary;
  ctx.lineWidth = 1.6 * s;
  ctx.fill();
  ctx.stroke();

  // 4. EARS (expressive listening antennae/ears + soft sound wave arcs)
  const earTwitch = Math.sin(t * 2.4 + anim.phase) * 0.14;
  [-1, 1].forEach((side) => {
    const ex = sx + side * (headR * 0.9);
    const ey = headY - 3 * s;
    const tipX = ex + side * (4.5 + earStr * 3.5) * s;
    const tipY = ey - (5 + earStr * 3) * s + earTwitch * 6 * s * side;
    ctx.beginPath();
    ctx.moveTo(ex, ey);
    ctx.lineTo(tipX, tipY);
    ctx.strokeStyle = "#60d9f6";
    ctx.lineWidth = 2.1 * s;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(tipX, tipY, 2 * s, 0, Math.PI * 2);
    ctx.fillStyle = "#c4b5fd";
    ctx.fill();

    if (earStr > 0.72 && Math.sin(t * 2.5 + anim.phase) > 0.55) {
      ctx.beginPath();
      ctx.arc(tipX, tipY, 5.5 * s, side === -1 ? Math.PI * 0.8 : -Math.PI * 0.4, side === -1 ? Math.PI * 1.4 : Math.PI * 0.3);
      ctx.strokeStyle = "rgba(96, 217, 246, 0.45)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  });

  // 5. EYES (blinking & looking toward active sparks or arena)
  anim.blinkTimer -= 0.016;
  if (anim.blinkTimer < -0.14) anim.blinkTimer = 2.4 + Math.random() * 3.2;
  const blinking = anim.blinkTimer < 0;
  const gazeX = Math.sin(t * 0.9 + anim.phase) * 1.1 * s;
  const eyeR = (1.5 + eyeStr * 1.0) * s;
  [-1, 1].forEach((side) => {
    const ex = sx + side * 3.1 * s + gazeX;
    const ey = headY - 1 * s;
    if (blinking) {
      ctx.beginPath();
      ctx.moveTo(ex - eyeR, ey);
      ctx.lineTo(ex + eyeR, ey);
      ctx.strokeStyle = "#ffdfa3";
      ctx.lineWidth = 1.4 * s;
      ctx.stroke();
    } else {
      ctx.beginPath();
      ctx.arc(ex, ey, eyeR, 0, Math.PI * 2);
      ctx.fillStyle = "#ffdfa3";
      ctx.fill();
    }
  });

  // 6. TONGUE / VOICE (expressive voice ripple when communicating or speaking)
  const speakingNow = anim.speakTimer > 0 || (isSelected && whisperVoiceStateEl.textContent.includes("Speaking"));
  if (anim.speakTimer > 0) anim.speakTimer = Math.max(0, anim.speakTimer - 0.016);
  const mouthOpen = speakingNow || (tongueStr > 0.78 && Math.sin(t * 4.2 + anim.phase) > 0.65);
  ctx.beginPath();
  if (mouthOpen) {
    ctx.ellipse(sx, headY + 3.4 * s, 2.3 * s, 1.8 * s, 0, 0, Math.PI * 2);
    ctx.fillStyle = "#fb8a70";
    ctx.fill();
    // Speech ripple ring
    const spR = (8 + ((t * 18) % 14)) * s;
    ctx.beginPath();
    ctx.arc(sx, headY + 3 * s, spR, -Math.PI * 0.25, Math.PI * 0.25);
    ctx.strokeStyle = "rgba(255, 223, 163, 0.55)";
    ctx.lineWidth = 1.3;
    ctx.stroke();
  } else {
    ctx.arc(sx, headY + 2.8 * s, 2.1 * s, 0.15 * Math.PI, 0.85 * Math.PI);
    ctx.strokeStyle = "rgba(255, 223, 163, 0.85)";
    ctx.lineWidth = 1.2 * s;
    ctx.stroke();
  }

  // Reward golden halo / rising stars
  if (anim.rewardTimer > 0) {
    anim.rewardTimer = Math.max(0, anim.rewardTimer - 0.016);
    ctx.beginPath();
    ctx.ellipse(sx, headY - 12 * s, 10 * s, 3.6 * s, 0, 0, Math.PI * 2);
    ctx.strokeStyle = "#ffdfa3";
    ctx.lineWidth = 1.8;
    ctx.stroke();
  }

  // 5 tiny orbiting vital-organ lights around waist
  const organs = being.organs || [];
  for (let o = 0; o < 5; o += 1) {
    const org = organs[o];
    const vit = Number(org?.vitality ?? 0.85);
    const oa = t * 0.85 + anim.phase + (o * Math.PI * 2) / 5;
    const ox = sx + Math.cos(oa) * 16 * s;
    const oy = sy - 3 * s + Math.sin(oa) * 6 * s;
    ctx.beginPath();
    ctx.arc(ox, oy, (1.6 + vit * 1.2) * s, 0, Math.PI * 2);
    ctx.fillStyle = vit > 0.7 ? pal.secondary : "#fb8a70";
    ctx.fill();
  }

  // Name & subtle honor glint
  const honor = Number(being.honor ?? 0);
  const label = honor > 0 ? `${being.name || being.id} ★${honor}` : (being.name || being.id);
  drawOutlinedText(
    label,
    sx,
    footProj.sy + 17 * s,
    isSelected ? "#ffdfa3" : "rgba(244, 247, 251, 0.94)",
    `${isSelected ? "600" : "500"} ${Math.max(9.5, Math.round(11.5 * s))}px "Inter", system-ui, sans-serif`
  );

  ctx.restore();

  state.hitTargets.push({
    sx,
    sy: sy - 6 * s,
    r: Math.max(22, 26 * s),
    type: "being",
    id: being.id,
    label: being.name || being.id,
    story: `${being.name} — ${being.mood_phrase || "quietly present"}`,
    depth: proj.depth,
  });
}

// ---------------------------------------------------------------------------
// 60fps Render Loop
// ---------------------------------------------------------------------------
function renderFrame(nowMs) {
  const t = nowMs * 0.001;
  const w = state.canvasWidth;
  const h = state.canvasHeight;
  ctx.clearRect(0, 0, w, h);

  // Smoothly lerp camera toward target (including Follow Being)
  const cam = state.camera;
  if (cam.mode === "follow" && state.selectedBeingId) {
    const anim = state.beingsAnim.get(state.selectedBeingId);
    if (anim) {
      cam.targetTx = anim.wx;
      cam.targetTy = anim.wy;
      cam.targetTz = anim.wz + 8;
    }
  }
  cam.tx += (cam.targetTx - cam.tx) * 0.08;
  cam.ty += (cam.targetTy - cam.ty) * 0.08;
  cam.tz += (cam.targetTz - cam.tz) * 0.08;
  cam.yaw += (cam.targetYaw - cam.yaw) * 0.1;
  cam.pitch += (cam.targetPitch - cam.pitch) * 0.1;
  cam.zoom += (cam.targetZoom - cam.zoom) * 0.1;

  // Starfield dust
  for (const s of state.stars) {
    const twinkle = 0.24 + 0.55 * (0.5 + 0.5 * Math.sin(t * s.speed + s.phase));
    ctx.beginPath();
    ctx.arc(s.x * w, s.y * h, s.r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(218, 232, 255, ${twinkle.toFixed(3)})`;
    ctx.fill();
  }

  state.hitTargets = [];

  // 1. Paths connecting neighboring lands (drawn below platforms/actors)
  const paths = state.universe?.world?.paths || [];
  if (paths.length) {
    paths.forEach((p, idx) => {
      const a = getZoneCenter(p.from_zone || p.from);
      const b = getZoneCenter(p.to_zone || p.to);
      draw3DPath(a, b, t, idx);
    });
  } else {
    const drawnEdges = new Set();
    for (const [zName, node] of state.zoneNodes.entries()) {
      for (const nb of node.zone?.neighbors || []) {
        const nbNode = state.zoneNodes.get(nb);
        if (!nbNode) continue;
        const key = [zName, nb].sort().join("--");
        if (drawnEdges.has(key)) continue;
        drawnEdges.add(key);
        draw3DPath(node, nbNode, t, drawnEdges.size);
      }
    }
  }

  // 2. 3D Land Platforms sorted back-to-front by projected depth
  const sortedZones = [...state.zoneNodes.values()]
    .map((node) => ({ node, p: project3D(node.x, node.y, node.z) }))
    .sort((a, b) => a.p.depth - b.p.depth);
  sortedZones.forEach(({ node }) => draw3DLandPlatform(node, t));

  // 3. Expanding 3D Ripples on lands
  for (let i = state.ripples.length - 1; i >= 0; i -= 1) {
    const rp = state.ripples[i];
    rp.r += 1.4;
    rp.alpha *= 0.968;
    const p = project3D(rp.wx, rp.wy, rp.wz + 2);
    ctx.beginPath();
    ctx.ellipse(p.sx, p.sy, rp.r * p.scale, rp.r * p.scale * 0.56, 0, 0, Math.PI * 2);
    ctx.strokeStyle = rp.color;
    ctx.globalAlpha = Math.max(0, rp.alpha);
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.globalAlpha = 1;
    if (rp.r >= rp.maxR || rp.alpha <= 0.02) state.ripples.splice(i, 1);
  }

  // 4. Depth-sorted 3D Objects: Homes, Doors, Playground Arena, Sparks & Embodied Beings
  const renderQueue = [];

  const homes = state.universe?.world?.homes || [];
  homes.forEach((home, idx) => {
    const coords = resolvePlaceWorldCoords(home, home.zone || "alpha-sector", idx);
    const d = project3D(coords.x, coords.y, coords.z).depth;
    renderQueue.push({ depth: d, draw: () => draw3DHome(home, coords, t) });
  });

  const doors = state.universe?.world?.doors || [];
  doors.forEach((door, idx) => {
    let coords;
    const za = door.zone_a || door.from_zone;
    const zb = door.zone_b || door.to_zone;
    if (za && zb) {
      const a = getZoneCenter(za);
      const b = getZoneCenter(zb);
      coords = { x: (a.x + b.x) * 0.5, y: (a.y + b.y) * 0.5, z: (a.z + b.z) * 0.5 + 4 };
    } else {
      coords = resolvePlaceWorldCoords(door, door.zone || "hub", idx);
    }
    const d = project3D(coords.x, coords.y, coords.z).depth;
    renderQueue.push({ depth: d, draw: () => draw3DDoor(door, coords, t) });
  });

  const playgrounds = state.universe?.world?.playgrounds || [];
  const comp = state.universe?.world?.competition;
  const compActive = Boolean(comp && (comp.active || comp.status === "active"));
  if (playgrounds.length) {
    playgrounds.forEach((pg, idx) => {
      const coords = resolvePlaceWorldCoords(pg, pg.zone || "frontier", idx);
      const d = project3D(coords.x, coords.y, coords.z).depth;
      renderQueue.push({ depth: d, draw: () => draw3DPlaygroundArena(pg, coords, t, compActive) });
    });
  } else if (state.zoneNodes.has("frontier")) {
    const coords = resolvePlaygroundCoords();
    const d = project3D(coords.x, coords.y, coords.z).depth;
    renderQueue.push({ depth: d, draw: () => draw3DPlaygroundArena(null, coords, t, compActive) });
  }

  // World entities (floating glowing sparks inside lands)
  const entities = state.universe?.world?.entities || [];
  entities.slice(0, 24).forEach((ent, idx) => {
    const zc = getZoneCenter(ent.zone);
    const angle = t * 0.32 + idx * 1.4;
    const wx = zc.x + Math.cos(angle) * (zc.radius * 0.58);
    const wy = zc.y + Math.sin(angle) * (zc.radius * 0.58);
    const wz = zc.z + 18 + Math.sin(t * 2 + idx) * 4;
    const p = project3D(wx, wy, wz);
    const resolved = String(ent.state || "").toLowerCase() === "resolved";
    renderQueue.push({
      depth: p.depth,
      draw: () => {
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, (resolved ? 2.6 : 4.2) * p.scale, 0, Math.PI * 2);
        ctx.fillStyle = resolved ? "rgba(79, 227, 193, 0.48)" : "rgba(246, 196, 109, 0.85)";
        ctx.fill();
      },
    });
  });

  // Embodied Beings (smooth 60fps 3D locomotion interpolation)
  for (const [, anim] of state.beingsAnim.entries()) {
    const dx = anim.targetX - anim.wx;
    const dy = anim.targetY - anim.wy;
    const dz = anim.targetZ - anim.wz;
    anim.speed = Math.hypot(dx, dy);
    anim.wx += dx * 0.036;
    anim.wy += dy * 0.036;
    anim.wz += dz * 0.045;
    const d = project3D(anim.wx, anim.wy, anim.wz + 10).depth;
    renderQueue.push({ depth: d, draw: () => drawArticulatedBeing3D(anim, t) });
  }

  renderQueue.sort((a, b) => a.depth - b.depth);
  renderQueue.forEach((item) => item.draw());

  // 5. Synaptic filaments & Reward/Punishment bursts
  for (let i = state.filaments.length - 1; i >= 0; i -= 1) {
    const fl = state.filaments[i];
    fl.progress += 0.024;
    const u = Math.min(1, fl.progress);
    const wx = fl.x1 + (fl.x2 - fl.x1) * u;
    const wy = fl.y1 + (fl.y2 - fl.y1) * u;
    const wz = fl.z1 + (fl.z2 - fl.z1) * u + Math.sin(u * Math.PI) * 58;
    const p = project3D(wx, wy, wz);
    ctx.save();
    ctx.beginPath();
    ctx.arc(p.sx, p.sy, 4.8 * p.scale, 0, Math.PI * 2);
    ctx.fillStyle = fl.color;
    ctx.shadowColor = fl.color;
    ctx.shadowBlur = 14;
    ctx.fill();
    ctx.restore();
    if (fl.progress >= 1.05) state.filaments.splice(i, 1);
  }

  for (let i = state.fxBursts.length - 1; i >= 0; i -= 1) {
    const fb = state.fxBursts[i];
    fb.life -= 0.016;
    fb.wz += 0.6;
    const p = project3D(fb.wx, fb.wy, fb.wz);
    ctx.save();
    ctx.globalAlpha = Math.max(0, fb.life);
    ctx.fillStyle = fb.kind === "reward" ? "#ffdfa3" : "#fb8a70";
    ctx.font = `600 ${Math.round(14 * p.scale)}px "Inter", system-ui, sans-serif`;
    ctx.textAlign = "center";
    ctx.fillText(fb.kind === "reward" ? "★ Honor" : "✦ Gentle Check", p.sx, p.sy);
    ctx.restore();
    if (fb.life <= 0) state.fxBursts.splice(i, 1);
  }

  requestAnimationFrame(renderFrame);
}

// ---------------------------------------------------------------------------
// Canvas Pointer Orbit / Drag / Zoom & Hit Detection
// ---------------------------------------------------------------------------
function findHitAt(clientX, clientY) {
  let best = null;
  let bestScore = Infinity;
  for (const hit of state.hitTargets) {
    const d = Math.hypot(clientX - hit.sx, clientY - hit.sy);
    if (d <= hit.r) {
      const priority = hit.type === "being" ? d * 0.6 : d + 8;
      if (priority < bestScore) {
        bestScore = priority;
        best = hit;
      }
    }
  }
  return best;
}

canvas.addEventListener("pointerdown", (ev) => {
  state.camera.dragging = true;
  state.camera.dragMoved = false;
  state.camera.lastPointerX = ev.clientX;
  state.camera.lastPointerY = ev.clientY;
});

window.addEventListener("pointermove", (ev) => {
  if (state.camera.dragging) {
    const dx = ev.clientX - state.camera.lastPointerX;
    const dy = ev.clientY - state.camera.lastPointerY;
    if (Math.hypot(dx, dy) > 3) state.camera.dragMoved = true;
    state.camera.lastPointerX = ev.clientX;
    state.camera.lastPointerY = ev.clientY;
    state.camera.targetYaw -= dx * 0.0065;
    state.camera.targetPitch = Math.max(0.28, Math.min(1.22, state.camera.targetPitch + dy * 0.0055));
    tooltipEl.classList.add("hidden");
    return;
  }

  if (ev.target !== canvas) {
    state.hoveredHit = null;
    tooltipEl.classList.add("hidden");
    return;
  }

  const hit = findHitAt(ev.clientX, ev.clientY);
  state.hoveredHit = hit;
  if (hit) {
    canvas.style.cursor = "pointer";
    tooltipEl.textContent = hit.story || hit.label;
    tooltipEl.style.left = `${Math.max(90, Math.min(window.innerWidth - 90, ev.clientX))}px`;
    tooltipEl.style.top = `${Math.max(70, ev.clientY)}px`;
    tooltipEl.classList.remove("hidden");
  } else {
    canvas.style.cursor = "grab";
    tooltipEl.classList.add("hidden");
  }
});

window.addEventListener("pointerup", (ev) => {
  const wasDrag = state.camera.dragMoved;
  state.camera.dragging = false;
  if (!wasDrag && ev.target === canvas) {
    const hit = findHitAt(ev.clientX, ev.clientY);
    if (hit?.type === "being") {
      selectBeing(hit.id, { speak: true });
    } else if (hit?.type === "door" && hit.door) {
      toggleDoor(hit.door);
    } else if (hit?.type === "home" && hit.home) {
      focusHomeResident(hit.home);
    } else if (hit?.type === "playground") {
      openPlaygroundPopover(competitionBannerEl);
    }
  }
});

canvas.addEventListener(
  "wheel",
  (ev) => {
    ev.preventDefault();
    const delta = ev.deltaY > 0 ? -0.08 : 0.08;
    state.camera.targetZoom = Math.max(0.5, Math.min(2.2, state.camera.targetZoom + delta));
  },
  { passive: false }
);

// ---------------------------------------------------------------------------
// UI Rendering: Narrative, Beings Strip, Vitality, Anatomy & Tapestry
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

  [0.45, 0.75, 1.0].forEach((scale) => {
    const ring = document.createElementNS(ns, "circle");
    ring.setAttribute("cx", cx);
    ring.setAttribute("cy", cy);
    ring.setAttribute("r", (maxR * scale).toFixed(1));
    ring.setAttribute("fill", "none");
    ring.setAttribute("stroke", "rgba(255,255,255,0.08)");
    constellationSvg.appendChild(ring);
  });

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

function renderAnatomySection(being, rwData) {
  const anatomy = rwData?.anatomy || being.anatomy || {};
  const homeLabel = being.home?.name || being.home?.label || (typeof being.home === "string" ? prettifyPhrase(being.home) : `${prettifyZone(being.zone)} Hearth`);
  const walkPhrase = prettifyPhrase(being.location?.walk_state || "exploring");
  drawerLifePlaceEl.textContent = being.action_story
    ? `${being.action_story} Home: ${homeLabel}.`
    : `Home: ${homeLabel} · Currently ${walkPhrase.toLowerCase()} in ${prettifyZone(being.zone)}.`;

  clearEl(drawerAnatomyListEl);
  const parts = [
    { key: "eyes", title: "Eyes", fallback: "Observant eyes watching the horizon." },
    { key: "ears", title: "Ears", fallback: "Attentive ears listening for soft signals." },
    { key: "tongue", title: "Tongue & Voice", fallback: "Gentle voice sharing clarity with peers." },
    { key: "hands", title: "Hands", fallback: "Steady hands crafting sparks and repairs." },
    { key: "legs", title: "Legs", fallback: "Sure-footed legs walking paths and doorways." },
  ];

  parts.forEach((p) => {
    const info = anatomy[p.key] || {};
    const str = Math.max(0.1, Math.min(1, Number(info.strength ?? 0.72)));
    const row = document.createElement("div");
    row.className = "anatomy-row";

    const head = document.createElement("div");
    head.className = "anatomy-row-head";
    const nameEl = document.createElement("span");
    nameEl.textContent = p.title;
    const valEl = document.createElement("span");
    valEl.className = "anatomy-strength";
    valEl.textContent = `${Math.round(str * 100)}%`;
    head.append(nameEl, valEl);

    const story = document.createElement("p");
    story.className = "anatomy-story";
    story.textContent = info.role_story || info.story || p.fallback;

    const track = document.createElement("div");
    track.className = "confidence-glow-track";
    const fill = document.createElement("div");
    fill.className = "confidence-glow-fill";
    fill.style.width = `${Math.round(str * 100)}%`;
    track.appendChild(fill);

    row.append(head, story, track);
    drawerAnatomyListEl.appendChild(row);
  });

  clearEl(drawerHonorLedgerEl);
  const honor = Number(being.honor ?? 0);
  const rewards = Number(being.rewards ?? 0);
  const punishments = Number(being.punishments ?? 0);

  const honorChip = document.createElement("span");
  honorChip.className = "honor-chip is-gold";
  honorChip.textContent = `Honor · ${honor}`;

  const rewardChip = document.createElement("span");
  rewardChip.className = "honor-chip is-gold";
  rewardChip.textContent = `Rewards · ${rewards}`;

  const penChip = document.createElement("span");
  penChip.className = punishments > 0 ? "honor-chip is-coral" : "honor-chip";
  penChip.textContent = punishments > 0 ? `Gentle Corrections · ${punishments}` : "Clear Standing";

  drawerHonorLedgerEl.append(honorChip, rewardChip, penChip);
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
  const honorVal = being.honor ?? 0;
  drawerKarmaPillEl.textContent = `Honor ${honorVal} · Karma ${Number(karmaVal).toFixed(1)}`;

  renderAnatomySection(being, rwData);

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
  const insights = state.universe?.evolution_insights || [];
  if (insights.length && evolutionInsightBannerEl) {
    const latest = insights[insights.length - 1];
    if (latest?.sentence) {
      evolutionInsightBannerEl.textContent = latest.sentence;
      evolutionInsightBannerEl.classList.remove("hidden");
    }
  }

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

function applyDaylightSky(daylight) {
  if (!nebulaEl || daylight == null || Number.isNaN(Number(daylight))) return;
  const d = Math.max(0, Math.min(1, Number(daylight)));
  // Smooth blend between twilight (#050814), dawn warmth (#14112b), and radiant starlight (#0c1836)
  const dawnMix = Math.sin(d * Math.PI);
  const topR = Math.round(5 + dawnMix * 16);
  const topG = Math.round(8 + d * 12 + dawnMix * 6);
  const topB = Math.round(20 + d * 24);
  nebulaEl.style.background = `radial-gradient(circle at 50% 42%, rgb(${topR + 8}, ${topG + 12}, ${topB + 28}) 0%, rgb(${topR}, ${topG}, ${topB}) 74%)`;
  nebulaEl.style.opacity = String((0.88 + dawnMix * 0.12).toFixed(2));
}

function renderCompetitionBanner(world) {
  const comp = world?.competition;
  const isActive = Boolean(comp && (comp.active || comp.status === "active"));
  competitionBannerEl.classList.remove("hidden");
  competitionBannerEl.classList.toggle("is-live", isActive);
  if (isActive) {
    const leaders = (comp.leaderboard || []).slice(0, 2).map((l) => l.name).filter(Boolean);
    const leaderTxt = leaders.length ? ` · Leading: ${leaders.join(", ")}` : "";
    competitionTextEl.textContent = `${comp.title || "Starlight Harmony Trial"}${leaderTxt}`;
  } else {
    competitionTextEl.textContent = "Starlight Arena · Trial Podium";
  }
  renderPlaygroundPopover();
}

function renderPlaygroundPopover() {
  if (!playgroundPopoverEl || playgroundPopoverEl.classList.contains("hidden")) return;
  const world = state.universe?.world || {};
  const comp = world.competition;
  const isActive = Boolean(comp && (comp.active || comp.status === "active"));

  podiumTitleEl.textContent = comp?.title || "Starlight Arena Podium";
  podiumStoryEl.textContent =
    comp?.story ||
    "Companions gather in Starlight Arena to test kindness, grace, and swift teamwork.";
  if (isActive && comp?.ticks_remaining != null) {
    podiumCountdownEl.textContent = `${comp.ticks_remaining} breaths left`;
  } else if (comp?.winner_name) {
    podiumCountdownEl.textContent = `Crowned · ${comp.winner_name}`;
  } else {
    podiumCountdownEl.textContent = isActive ? "Trial Live" : "Open Stage";
  }

  clearEl(playgroundPodiumEl);
  const board = (comp?.podium && comp.podium.length ? comp.podium : comp?.leaderboard) || [];
  if (!board.length) {
    const empty = document.createElement("p");
    empty.className = "horizon-whisper";
    empty.textContent = "Start a friendly trial to see companions shine on the podium.";
    playgroundPodiumEl.appendChild(empty);
  } else {
    board.slice(0, 5).forEach((entry, idx) => {
      const row = document.createElement("div");
      row.className = "podium-row";
      const left = document.createElement("span");
      left.className = "podium-rank";
      const rank = entry.rank ?? idx + 1;
      const medal = rank === 1 ? "★ " : rank === 2 ? "✦ " : `${rank}. `;
      left.textContent = `${medal}${entry.name || entry.id}`;
      const right = document.createElement("span");
      right.className = "podium-score";
      right.textContent = `${Number(entry.score ?? 0).toFixed(2)} radiance`;
      row.append(left, right);
      playgroundPodiumEl.appendChild(row);
    });
  }

  clearEl(playgroundRewardsListEl);
  const rlog = state.universe?.rewards_log || [];
  if (!rlog.length) {
    const empty = document.createElement("p");
    empty.className = "horizon-whisper";
    empty.textContent = "Honor rewards and gentle guidance moments will gather here.";
    playgroundRewardsListEl.appendChild(empty);
  } else {
    rlog
      .slice(-5)
      .reverse()
      .forEach((item) => {
        const row = document.createElement("div");
        row.className = "podium-reward-row";
        if (item.kind === "punishment") row.classList.add("is-punishment");
        const txt = document.createElement("span");
        txt.textContent = item.sentence || `${item.who || "Companion"} received ${item.kind || "honor"}.`;
        row.appendChild(txt);
        playgroundRewardsListEl.appendChild(row);
      });
  }
}

function openPlaygroundPopover(anchorEl = competitionBannerEl) {
  const hidden = playgroundPopoverEl.classList.toggle("hidden");
  competitionBannerEl.setAttribute("aria-expanded", String(!hidden));
  if (!hidden) {
    voicePopoverEl.classList.add("hidden");
    voicePillBtn.setAttribute("aria-expanded", "false");
    vitalityPopoverEl.classList.add("hidden");
    vitalityPillBtn.setAttribute("aria-expanded", "false");
    renderPlaygroundPopover();
    positionPopoverInViewport(playgroundPopoverEl, anchorEl || competitionBannerEl);
  }
}

async function toggleDoor(door) {
  if (!door) return;
  const doorId = door.id || door.name;
  const zone = door.zone_a || door.zone || "hub";
  const flashKey = `${door.zone_a || ""}:${door.zone_b || ""}`;
  state.doorFlashes.set(flashKey, 1.0);
  triggerRipple(zone, "#ffdfa3", 1.15);
  playHarmonicChime("spark");
  sparkFeedbackEl.textContent = `Adjusting guardian seal on ${door.name || "the doorway"}…`;

  try {
    const res = await fetch("/api/pulse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ zone, spark: door.name || doorId, kind: "door", door_id: doorId }),
    });
    const result = await res.json().catch(() => ({}));
    if (!res.ok || result.ok === false) throw new Error(result.error || "Door unchanged");
    sparkFeedbackEl.textContent = result.acknowledgment || `${door.name || "Doorway"} updated.`;
    if (state.speechEnabled && result.spoken_reply) {
      speakText(result.spoken_reply);
    }
    await refreshUniverse();
  } catch (err) {
    sparkFeedbackEl.textContent = err?.message || "Could not adjust that doorway right now.";
  }
}

function focusHomeResident(home) {
  if (!home) return;
  const beings = state.universe?.beings || [];
  const residents = Array.isArray(home.residents) && home.residents.length
    ? beings.filter((b) => home.residents.includes(b.id))
    : beings.filter((b) => b.home?.id === home.id || b.zone === home.zone);

  triggerRipple(home.zone || "hub", "#f6c46d", 1.1);
  if (residents.length) {
    const chosen = residents[state.homeCycleIdx % residents.length];
    state.homeCycleIdx += 1;
    sparkFeedbackEl.textContent = `Visiting ${chosen.name} inside ${home.name || "Home"}.`;
    selectBeing(chosen.id, { speak: true });
  } else {
    sparkFeedbackEl.textContent = `${home.name || "Cozy Home"} glows quietly, waiting for companions to rest.`;
  }
}

async function triggerTrialPulse(customTitle = "Starlight Harmony Trial") {
  sparkFeedbackEl.textContent = "Opening a Playground Trial in Starlight Arena…";
  triggerRipple("playground", "#f6c46d", 1.45);
  triggerFilament("hub", "playground", "#ffdfa3");
  playHarmonicChime("reward");

  try {
    const res = await fetch("/api/pulse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ zone: "playground", spark: customTitle, kind: "competition" }),
    });
    const result = await res.json().catch(() => ({}));
    if (!res.ok || result.ok === false) throw new Error(result.error || "Trial paused");
    sparkInputEl.value = "";
    sparkFeedbackEl.textContent = result.acknowledgment || "A friendly Playground Trial has begun!";
    if (state.speechEnabled && result.spoken_reply) {
      speakText(result.spoken_reply);
    }
    await refreshUniverse();
  } catch (err) {
    sparkFeedbackEl.textContent = err?.message || "Could not start the Playground Trial right now.";
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
  playHarmonicChime("select");

  const anim = state.beingsAnim.get(beingId);
  if (anim) {
    anim.speakTimer = 2.4;
    triggerRipple(anim.being.zone || "hub", "#f6c46d", 0.9);
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

    syncZoneNodes();
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

    const events = data.chronicle?.events || [];
    events.forEach((ev) => {
      const eid = ev.id || `${ev.tick}:${ev.who}:${ev.where}`;
      if (!state.lastEventIds.has(eid)) {
        state.lastEventIds.add(eid);
        if (!firstLoad) {
          triggerRipple(ev.where || "hub", toneColor(ev.tone), 1.0);
          const major = ["warm", "alert"].includes(String(ev.tone || "").toLowerCase()) ||
            /crowned|honor|trial|door|evolved/i.test(String(ev.sentence || ""));
          if (major && state.speechEnabled && ev.sentence && eid !== state.lastSpokenEventId) {
            state.lastSpokenEventId = eid;
            speakText(ev.sentence);
          }
        }
      }
    });
    if (state.lastTick !== -1 && tick > state.lastTick && !firstLoad) {
      playHarmonicChime("pulse");
    }
    state.lastTick = tick;

    applyDaylightSky(data.world?.daylight);
    syncBeingsAnimationState(beings);
    renderBeingsStrip(beings);
    renderHostVitality(data.machine);
    renderCompetitionBanner(data.world);
    renderTapestry();

    if (state.selectedBeingId) {
      renderBeingDrawer();
      fetchBeingWorld(state.selectedBeingId);
    }
  } catch {
    // Keep existing frame gracefully
  }
}

// ---------------------------------------------------------------------------
// Interactive Controls & Event Listeners
// ---------------------------------------------------------------------------
camIsoBtn.addEventListener("click", () => setCameraMode("iso"));
camArenaBtn.addEventListener("click", () => setCameraMode("arena"));
camFollowBtn.addEventListener("click", () => setCameraMode("follow"));
camZoomInBtn.addEventListener("click", () => {
  state.camera.targetZoom = Math.min(2.2, state.camera.targetZoom + 0.16);
});
camZoomOutBtn.addEventListener("click", () => {
  state.camera.targetZoom = Math.max(0.5, state.camera.targetZoom - 0.16);
});

voicePillBtn.addEventListener("click", () => {
  const hidden = voicePopoverEl.classList.toggle("hidden");
  voicePillBtn.setAttribute("aria-expanded", String(!hidden));
  if (!hidden) {
    vitalityPopoverEl.classList.add("hidden");
    vitalityPillBtn.setAttribute("aria-expanded", "false");
    playgroundPopoverEl.classList.add("hidden");
    competitionBannerEl.setAttribute("aria-expanded", "false");
    populateVoices();
    positionPopoverInViewport(voicePopoverEl, voicePillBtn);
  }
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
  if (!hidden) {
    voicePopoverEl.classList.add("hidden");
    voicePillBtn.setAttribute("aria-expanded", "false");
    playgroundPopoverEl.classList.add("hidden");
    competitionBannerEl.setAttribute("aria-expanded", "false");
    positionPopoverInViewport(vitalityPopoverEl, vitalityPillBtn);
  }
});

competitionBannerEl.addEventListener("click", () => openPlaygroundPopover(competitionBannerEl));

playgroundCloseBtn.addEventListener("click", () => {
  playgroundPopoverEl.classList.add("hidden");
  competitionBannerEl.setAttribute("aria-expanded", "false");
});

podiumRunTrialBtn.addEventListener("click", () => triggerTrialPulse("Starlight Harmony Trial"));

vitalityCloseBtn.addEventListener("click", () => {
  vitalityPopoverEl.classList.add("hidden");
  vitalityPillBtn.setAttribute("aria-expanded", "false");
});

drawerCloseBtn.addEventListener("click", () => {
  state.selectedBeingId = null;
  state.selectedBeingWorld = null;
  sanctuaryHudEl?.classList.remove("drawer-open");
  beingDrawerEl.classList.add("hidden");
  renderBeingsStrip(state.universe?.beings || []);
});

hearBeingBtn.addEventListener("click", () => {
  const being = (state.universe?.beings || []).find((b) => b.id === state.selectedBeingId);
  const anim = state.beingsAnim.get(state.selectedBeingId);
  if (anim) anim.speakTimer = 3.0;
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

evolveTraitsBtn.addEventListener("click", async () => {
  tabChaptersBtn.click();
  evolutionInsightBannerEl.textContent = "Testing gentle trait adaptations across the living genome…";
  evolutionInsightBannerEl.classList.remove("hidden");
  playHarmonicChime("spark");
  triggerRipple("hub", "#a78bfa", 1.25);

  try {
    const res = await fetch("/api/pulse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ zone: "hub", spark: "Gentle evolutionary adaptation", kind: "evolve" }),
    });
    const result = await res.json().catch(() => ({}));
    if (!res.ok || result.ok === false) throw new Error(result.error || "Evolution paused");
    const msg = result.insight || result.acknowledgment || result.story || "Traits refined gracefully while preserving safety.";
    evolutionInsightBannerEl.textContent = msg;
    if (state.speechEnabled && result.spoken_reply) {
      speakText(result.spoken_reply);
    }
    await refreshUniverse();
  } catch (err) {
    evolutionInsightBannerEl.textContent = err?.message || "Adaptation check paused for now.";
  }
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
  sparkFeedbackEl.textContent = "Sending your spark across the 3D sanctuary…";
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

startTrialBtn.addEventListener("click", () => {
  const customTitle = sparkInputEl.value.trim() || "Starlight Harmony Trial";
  triggerTrialPulse(customTitle);
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
