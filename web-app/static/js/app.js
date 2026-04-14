const KEY_ROWS = [
  ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
  ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
  ["Z", "X", "C", "V", "B", "N", "M"],
];

const DWELL_MS = 900;
const GAZE_POLL_MS = 75;

const messageBox = document.getElementById("messageBox");
const keyboard = document.getElementById("keyboard");
const gazeCursor = document.getElementById("gazeCursor");
const speakBtn = document.getElementById("speakBtn");

let hoveredKey = null;
let hoverSince = 0;

function buildKeyboard() {
  KEY_ROWS.forEach((row) => {
    const rowEl = document.createElement("div");
    rowEl.className = "key-row";

    row.forEach((letter) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "key";
      btn.textContent = letter;
      btn.dataset.key = letter;
      rowEl.appendChild(btn);
    });

    keyboard.appendChild(rowEl);
  });
}

function appendText(value) {
  messageBox.value += value;
}

function backspace() {
  messageBox.value = messageBox.value.slice(0, -1);
}

function clearText() {
  messageBox.value = "";
}

function triggerAction(action) {
  if (action === "SPACE") {
    appendText(" ");
    return;
  }

  if (action === "BACKSPACE") {
    backspace();
    return;
  }

  if (action === "CLEAR") {
    clearText();
    return;
  }

  appendText(action);
}

function speakText() {
  const text = messageBox.value.trim();
  if (!text) {
    return;
  }

  if (!("speechSynthesis" in window)) {
    return;
  }

  const utterance = new SpeechSynthesisUtterance(text);
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function handleClick(event) {
  const keyTarget = event.target.closest(".key");
  if (keyTarget) {
    triggerAction(keyTarget.dataset.key);
    return;
  }

  const controlTarget = event.target.closest(".control[data-action]");
  if (controlTarget) {
    triggerAction(controlTarget.dataset.action);
    return;
  }

  const phraseTarget = event.target.closest(".phrase");
  if (phraseTarget) {
    appendText(`${phraseTarget.textContent} `);
  }
}

function moveCursor(x, y) {
  const clampedX = Math.max(0, Math.min(1, x));
  const clampedY = Math.max(0, Math.min(1, y));
  gazeCursor.style.left = `${clampedX * window.innerWidth}px`;
  gazeCursor.style.top = `${clampedY * window.innerHeight}px`;

  const element = document.elementFromPoint(
    clampedX * window.innerWidth,
    clampedY * window.innerHeight,
  );
  const key = element && element.closest(".key, .control[data-action], .phrase");

  if (!key) {
    if (hoveredKey) {
      hoveredKey.classList.remove("dwell");
    }
    hoveredKey = null;
    hoverSince = 0;
    return;
  }

  if (hoveredKey !== key) {
    if (hoveredKey) {
      hoveredKey.classList.remove("dwell");
    }
    hoveredKey = key;
    hoverSince = performance.now();
    hoveredKey.classList.add("dwell");
    return;
  }

  if (performance.now() - hoverSince >= DWELL_MS) {
    hoveredKey.classList.remove("dwell");
    hoveredKey.click();
    hoveredKey = null;
    hoverSince = 0;
  }
}

async function pollGaze() {
  try {
    const response = await fetch("/api/gaze", { cache: "no-store" });
    if (!response.ok) {
      return;
    }

    const gaze = await response.json();
    moveCursor(Number(gaze.x ?? 0.5), Number(gaze.y ?? 0.5));
  } catch (error) {
    // Ignore intermittent fetch failures while tracker is starting.
  }
}

buildKeyboard();
document.addEventListener("click", handleClick);
speakBtn.addEventListener("click", speakText);
window.setInterval(pollGaze, GAZE_POLL_MS);
const keyboardRoot = document.getElementById("keyboard");
const messageBox = document.getElementById("messageBox");
const gazeCursor = document.getElementById("gazeCursor");
const speakBtn = document.getElementById("speakBtn");

const KEYS = [
  ..."ABCDEFGHIJKLMNOPQRSTUVWXYZ".split(""),
  "SPACE",
  "BACKSPACE",
];

const DWELL_MS = 900;
const GAZE_POLL_MS = 65;

let currentTarget = null;
let targetStart = 0;
let committedOnCurrent = false;

function createKeyboard() {
  KEYS.forEach((label) => {
    const btn = document.createElement("button");
    btn.className = "key";
    btn.dataset.key = label;
    btn.textContent = label === "SPACE" ? "Space" : label === "BACKSPACE" ? "Bksp" : label;
    if (label === "SPACE") {
      btn.classList.add("wide");
    }
    keyboardRoot.appendChild(btn);
  });
}

function typeKey(label) {
  if (label === "BACKSPACE") {
    messageBox.value = messageBox.value.slice(0, -1);
    return;
  }
  if (label === "SPACE") {
    messageBox.value += " ";
    return;
  }
  messageBox.value += label;
}

function applyAction(action) {
  if (action === "SPACE") {
    messageBox.value += " ";
  } else if (action === "BACKSPACE") {
    messageBox.value = messageBox.value.slice(0, -1);
  } else if (action === "CLEAR") {
    messageBox.value = "";
  }
}

function speakText() {
  const text = messageBox.value.trim();
  if (!text || !("speechSynthesis" in window)) {
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95;
  utterance.pitch = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

async function fetchGaze() {
  try {
    const res = await fetch("/api/gaze", { cache: "no-store" });
    if (!res.ok) {
      return null;
    }
    return await res.json();
  } catch {
    return null;
  }
}

function updateCursor(normalized) {
  const x = Math.max(0, Math.min(1, normalized.x));
  const y = Math.max(0, Math.min(1, normalized.y));
  const px = x * window.innerWidth;
  const py = y * window.innerHeight;

  gazeCursor.style.left = `${px}px`;
  gazeCursor.style.top = `${py}px`;
}

function clearHighlights() {
  document.querySelectorAll(".key.active-gaze, .key.commit").forEach((node) => {
    node.classList.remove("active-gaze", "commit");
  });
}

function processDwellTarget(targetNode) {
  const now = performance.now();

  if (targetNode !== currentTarget) {
    committedOnCurrent = false;
    currentTarget = targetNode;
    targetStart = now;
    clearHighlights();
    if (targetNode) {
      targetNode.classList.add("active-gaze");
    }
    return;
  }

  if (!targetNode || committedOnCurrent) {
    return;
  }

  const elapsed = now - targetStart;
  if (elapsed >= DWELL_MS) {
    committedOnCurrent = true;
    targetNode.classList.add("commit");
    const label = targetNode.dataset.key;
    typeKey(label);
    setTimeout(() => targetNode.classList.remove("commit"), 260);
  }
}

async function gazeLoop() {
  const gaze = await fetchGaze();
  if (!gaze) {
    return;
  }

  updateCursor(gaze);
  const px = gaze.x * window.innerWidth;
  const py = gaze.y * window.innerHeight;
  const hovered = document.elementFromPoint(px, py);
  const keyNode = hovered && hovered.classList.contains("key") ? hovered : null;
  processDwellTarget(keyNode);
}

function wireControls() {
  document.querySelectorAll(".control[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      applyAction(button.dataset.action);
    });
  });

  document.querySelectorAll(".phrase").forEach((button) => {
    button.addEventListener("click", () => {
      if (messageBox.value && !messageBox.value.endsWith(" ")) {
        messageBox.value += " ";
      }
      messageBox.value += button.textContent;
    });
  });

  speakBtn.addEventListener("click", speakText);
}

createKeyboard();
wireControls();
setInterval(gazeLoop, GAZE_POLL_MS);
