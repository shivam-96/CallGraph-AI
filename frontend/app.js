/**
 * CallGraph AI — Frontend Logic
 * Handles: WebSocket connection, push-to-talk audio capture, TTS playback
 */

// ─── DOM Elements ────────────────────────────────────────────────
const statusEl = document.getElementById("status");
const messagesEl = document.getElementById("messages");
const talkBtn = document.getElementById("talk-btn");
const btnIcon = document.getElementById("btn-icon");
const btnText = document.getElementById("btn-text");
const timingInfo = document.getElementById("timing-info");

// ─── State ───────────────────────────────────────────────────────
let ws = null;
let mediaRecorder = null;
let audioStream = null;
let isRecording = false;
let isProcessing = false;
let audioChunks = []; // TTS audio chunks from server

// ─── WebSocket Connection ────────────────────────────────────────
function connect() {
    setStatus("connecting", "Connecting...");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/voice`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        setStatus("connected", "Connected");
        talkBtn.disabled = false;
        addMessage("system", "Connected — hold the button to talk");
    };

    ws.onclose = () => {
        setStatus("disconnected", "Disconnected");
        talkBtn.disabled = true;
        setTimeout(connect, 3000); // Auto-reconnect
    };

    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        setStatus("disconnected", "Error");
    };

    ws.onmessage = (event) => {
        if (event.data instanceof Blob) {
            // Binary = TTS audio chunk
            audioChunks.push(event.data);
        } else {
            // Text = JSON control message
            const msg = JSON.parse(event.data);
            handleServerMessage(msg);
        }
    };
}

// ─── Server Message Handler ──────────────────────────────────────
function handleServerMessage(msg) {
    switch (msg.type) {
        case "transcript":
            if (msg.text) {
                addMessage("user", msg.text);
            }
            break;

        case "agent_text":
            addMessage("assistant", msg.text);
            break;

        case "audio_start":
            audioChunks = [];
            break;

        case "audio_end":
            playAudio(audioChunks);
            setProcessing(false);
            break;

        case "timing":
            timingInfo.textContent =
                `STT: ${msg.stt_ms}ms | Agent: ${msg.agent_ms}ms | TTS: ${msg.tts_ms}ms | Total: ${msg.total_ms}ms`;
            break;

        case "error":
            addMessage("system", `Error: ${msg.message}`);
            setProcessing(false);
            break;
    }
}

// ─── Audio Capture (Push-to-Talk) ────────────────────────────────
async function startRecording() {
    if (isProcessing) return;

    try {
        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
            },
        });

        mediaRecorder = new MediaRecorder(audioStream, {
            mimeType: "audio/webm;codecs=opus",
        });

        // Send audio chunks to server every 250ms
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                ws.send(event.data);
            }
        };

        mediaRecorder.start(250); // Chunk every 250ms
        isRecording = true;

        // Tell server we're starting
        ws.send(JSON.stringify({ type: "start" }));

        // Update UI
        talkBtn.classList.add("recording");
        btnIcon.textContent = "🔴";
        btnText.textContent = "Recording...";
        timingInfo.textContent = "";
    } catch (err) {
        console.error("Mic access error:", err);
        addMessage("system", "Microphone access denied");
    }
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;

    // Stop MediaRecorder
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }

    // Stop mic stream
    if (audioStream) {
        audioStream.getTracks().forEach((t) => t.stop());
        audioStream = null;
    }

    // Tell server we're done
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "stop" }));
    }

    setProcessing(true);
}

// ─── Audio Playback ──────────────────────────────────────────────
function playAudio(chunks) {
    if (chunks.length === 0) return;

    const blob = new Blob(chunks, { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);

    audio.onended = () => URL.revokeObjectURL(url);
    audio.play().catch((err) => console.error("Playback error:", err));
}

// ─── UI Helpers ──────────────────────────────────────────────────
function setStatus(state, text) {
    statusEl.className = `status ${state}`;
    statusEl.textContent = text;
}

function setProcessing(active) {
    isProcessing = active;
    if (active) {
        talkBtn.classList.remove("recording");
        talkBtn.classList.add("processing");
        btnIcon.textContent = "⏳";
        btnText.textContent = "Thinking...";
    } else {
        talkBtn.classList.remove("processing");
        btnIcon.textContent = "🎤";
        btnText.textContent = "Hold to Talk";
    }
}

function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.textContent = text;
    messagesEl.appendChild(div);

    // Auto-scroll to bottom
    const area = document.getElementById("transcript-area");
    area.scrollTop = area.scrollHeight;
}

// ─── Event Listeners ─────────────────────────────────────────────

// Mouse events
talkBtn.addEventListener("mousedown", (e) => {
    e.preventDefault();
    startRecording();
});
talkBtn.addEventListener("mouseup", stopRecording);
talkBtn.addEventListener("mouseleave", () => {
    if (isRecording) stopRecording();
});

// Touch events (mobile)
talkBtn.addEventListener("touchstart", (e) => {
    e.preventDefault();
    startRecording();
});
talkBtn.addEventListener("touchend", (e) => {
    e.preventDefault();
    stopRecording();
});

// ─── Initialize ──────────────────────────────────────────────────
connect();
