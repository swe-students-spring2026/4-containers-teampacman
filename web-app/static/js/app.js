const messageBox = document.getElementById("messageBox");
const gazeCursor = document.getElementById("gazeCursor");
const canvas = document.getElementById("captureCanvas");
const video = document.getElementById("video");
const ctx = canvas.getContext("2d");


// approx 10 fps sent to the backend
const SEND_INTERVAL_MS = 100;
const DWELL_MS = 900;
const GAZE_POLL_MS = 65;

let currentTarget = null;
let targetStart = 0;
let committedOnCurrent = false;

const CALIBRATION_ORDER = ["center", "top_left", "top_right", "bottom_left", "bottom_right"];

function renderKeyboard() {
  keys.forEach((key) => {
    const button = document.createElement("button");
    button.className = "key";
    button.dataset.key = key;
    button.textContent = key;

    if (key === "SPACE") {
      button.classList.add("wide");
    }

    keyboardRoot.appendChild(button);
  });
}

const TARGETS = {
    "center": { left: "50%", top: "50%" },
    "top_left": { left: "8%", top: "10%" },
    "top_right": { left: "92%", top: "10%" },
    "bottom_left": { left: "8%", top: "90%" },
    "bottom_right": { left: "92%", top: "90%" }
};

let calibStep = 0;
let isCalibrating = false;
let samplesCollected = 0;



document.getElementById("btn-calibrate")?.addEventListener("click", () => {
  isCalibrating = true;
  samplesCollected = 0;
  calibStep = 0;
  document.getElementById("calibration-overlay").style.display = "block";
  updateCalibrationUI();
});

function updateCalibrationUI(){
  // Check if completed like the previous calibration version
  if(calibStep >= CALIBRATION_ORDER.length){
    document.getElementById("calibration-overlay").style.display = "none";
    isCalibrating = false;
    alert("Calibration complete!");
    return;

  }

  const stepName = CALIBRATION_ORDER[calibStep];
  const dot = document.getElementById("calib-dot")

  dot.style.left = TARGETS[stepName].left;
  dot.style.top = TARGETS[stepName].top;

  document.getElementById("calib-text").innerText = `Look at the yellow dot: ${stepName}. Press SPACE to sample.}`;
  document.getElementById("calib-progress").innerText = `Samples: ${samplesCollected} / 8`
}

window.addEventListener("keydown", async (e) => {
  if (isCalibrating && e.code === "Space") {
    e.preventDefault();
    await sendCalibrationSample();
  }

});

async function sendCalibrationSample(){
  if (!video.videoWidth) return;
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  // reducing the file size for faster processing
  const img = canvas.toDataURL("image/jpeg", 0.6).split(",")[1];
  const targetName = CALIBRATION_ORDER[calibStep]

  try {
    const res = await fetch("/api/calibrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: img, target: targetName })
    });

    if(res.ok) {
      const data = await res.json();
      if (data.status === "success"){
        samplesCollected = data.sample_count || data.samples;

        if (samplesCollected >= 8){
          calibStep ++;
          samplesCollected = 0;
        }
        updateCalibrationUI()
      }
    } else {
      const errData = await res.json();
      console.warn("Calibration sample rejected:", errData.error);
    }
  } catch (err){
    console.error("error sending calibration frame:", err);
  }


}

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: {width: 1280, height: 720},
      audio: false
    });

    video.srcObject = stream;
  } catch (err) {
    console.error("Error accessing camera:", err);
    alert("Camera access is required for tracking.");
  }
}



function updateCursor(x, y) {
  const px = Math.max(0, Math.min(1, x)) * window.innerWidth;
  const py = Math.max(0, Math.min(1, y)) * window.innerHeight;
  
  gazeCursor.style.left = `${px}px`;
  gazeCursor.style.top = `${py}px`;
}

function processDwellTarget(targetNode) {
  const now = performance.now();

  if (targetNode !== currentTarget) {
    committedOnCurrent = false;

    if (currentTarget) {
        currentTarget.classList.remove("active-gaze");
    }

    currentTarget = targetNode;
    targetStart = now;
    
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
    const label = targetNode.textContent
    messageBox.value = label;
    setTimeout(() => targetNode.classList.remove("commit"), 260);
  }
}


async function gazeLoop() {
  if (!video.videoWidth) {
    setTimeout(gazeLoop, SEND_INTERVAL_MS);
    return;
  }

  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

  const dataUrl = canvas.toDataURL();
  const img = canvas.toDataURL("image/jpeg", 0.6).split(",")[1]; // Changed from default (PNG) to JPEG

  try {
    const res = await fetch("/api/process_frame", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: img })
    });

    if (res.ok) {
      const data = await res.json();
      if (data.x !== undefined && data.y !== undefined) {
        updateCursor(data.x, data.y);
        const element = document.elementFromPoint(
            data.x * window.innerWidth, 
            data.y * window.innerHeight
        );
        processDwellTarget(element?.closest(".phrase"));
      }
    }
  } catch (err) {
    console.error("Error sending frame:", err);
  }

  setTimeout(gazeLoop, SEND_INTERVAL_MS);



}


startCamera(); 
gazeLoop();
