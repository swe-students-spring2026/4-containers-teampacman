const keyboardRoot = document.getElementById("keyboard");
const messageBox = document.getElementById("messageBox");
const gazeCursor = document.getElementById("gazeCursor");

const keys = [
  ..."ABCDEFGHIJKLMNOPQRSTUVWXYZ".split(""),
  "SPACE",
  "BACKSPACE",
];

const DWELL_MS = 900;
const GAZE_POLL_MS = 65;

let currentTarget = null;
let targetStart = 0;
let committedOnCurrent = false;

function renderKeyboard() {
  keys.forEach((key)=> {
    const button = document.createElement('button');
    button.className = 'key';
    button.dataset.key = label;
    button.textContent = label;
    if(label === "Space") {
      button.classList.add('wide');
    }
    keyboardRoot.appendChild(button);
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
}

renderKeyboard();
wireControls();
setInterval(gazeLoop, GAZE_POLL_MS);
