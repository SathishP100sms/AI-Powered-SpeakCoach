const API = "https://ai-powered-speakcoach.onrender.com";

let session_id = null;
let currentMode = "conversation";
let mediaRecorder = null;
let audioChunks = [];
let currentAudio = null;
let isRecording = false;
let sessionHistory = [];   // { id, label, session_id }

/* ─── INIT ───────────────────────────────────────── */
window.addEventListener("DOMContentLoaded", () => {
    renderHistory();
});

/* ─── UI HELPERS ─────────────────────────────────── */
function hideWelcome() {
    const w = document.getElementById("welcome");
    if (w) w.remove();
}

function getTimestamp() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function addMessage(text, sender) {
    hideWelcome();
    const chat = document.getElementById("chat");

    const wrapper = document.createElement("div");
    wrapper.className = `message ${sender}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.innerHTML = sender === "user"
        ? '<i class="ri-user-3-line"></i>'
        : '<i class="ri-robot-2-line"></i>';

    const inner = document.createElement("div");

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;   // textContent prevents XSS

    const meta = document.createElement("div");
    meta.className = "msg-meta";
    meta.textContent = getTimestamp();

    inner.appendChild(bubble);
    inner.appendChild(meta);

    wrapper.appendChild(avatar);
    wrapper.appendChild(inner);

    chat.appendChild(wrapper);
    chat.scrollTop = chat.scrollHeight;
}

function showTyping() {
    document.getElementById("typing").classList.remove("hidden");
    const chat = document.getElementById("chat");
    chat.scrollTop = chat.scrollHeight;
}

function hideTyping() {
    document.getElementById("typing").classList.add("hidden");
}

function showWave() {
    document.getElementById("wave").classList.remove("hidden");
}

function hideWave() {
    document.getElementById("wave").classList.add("hidden");
}

/* ─── SIDEBAR TOGGLE (mobile) ────────────────────── */
function toggleSidebar() {
    document.getElementById("sidebar").classList.toggle("open");
    document.getElementById("overlay").classList.toggle("open");
}

function closeSidebar() {
    document.getElementById("sidebar").classList.remove("open");
    document.getElementById("overlay").classList.remove("open");
}

/* ─── THEME ──────────────────────────────────────── */
function toggleTheme() {
    document.body.classList.toggle("light");
    const icon = document.getElementById("theme-icon");
    if (document.body.classList.contains("light")) {
        icon.className = "ri-moon-line";
    } else {
        icon.className = "ri-sun-line";
    }
}

/* ─── MODE ───────────────────────────────────────── */
function setMode(mode, btn) {
    currentMode = mode;
    document.querySelectorAll(".mode").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
}

/* ─── SESSION HISTORY ────────────────────────────── */
function saveSession(label) {
    if (!session_id) return;
    // Avoid duplicates
    const exists = sessionHistory.find(s => s.session_id === session_id);
    if (!exists) {
        sessionHistory.unshift({ id: Date.now(), label, session_id });
        renderHistory();
    }
}

function renderHistory() {
    const el = document.getElementById("history");
    el.innerHTML = "";

    if (sessionHistory.length === 0) {
        el.innerHTML = '<div style="font-size:12px;color:var(--muted);padding:6px 12px;">No sessions yet</div>';
        return;
    }

    sessionHistory.forEach(s => {
        const div = document.createElement("div");
        div.className = "history-item" + (s.session_id === session_id ? " active" : "");
        div.textContent = s.label;
        div.title = s.label;
        div.onclick = () => loadSession(s);
        el.appendChild(div);
    });
}

function loadSession(s) {
    // Just switch session_id; full message reload would need a backend endpoint
    session_id = s.session_id;
    renderHistory();
    closeSidebar();
}

/* ─── NEW CHAT ───────────────────────────────────── */
function newChat() {
    session_id = null;
    document.getElementById("chat").innerHTML = `
        <div class="welcome" id="welcome">
            <div class="welcome-icon"><i class="ri-mic-2-fill"></i></div>
            <h3>Start Practicing!</h3>
            <p>Type a message or tap the mic to begin your English coaching session.</p>
        </div>`;
    hideTyping();
    hideWave();
    closeSidebar();
}

/* ─── TEXT CHAT ──────────────────────────────────── */
async function sendMessage() {
    const input = document.getElementById("input");
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, "user");
    input.value = "";
    showTyping();

    try {
        const res = await fetch(`${API}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, mode: currentMode, session_id })
        });

        if (!res.ok) throw new Error(`Server error: ${res.status}`);

        const data = await res.json();
        session_id = data.session_id;

        hideTyping();
        addMessage(data.text, "ai");
        saveSession(text.slice(0, 36) + (text.length > 36 ? "…" : ""));
        playTTS(data.text);

    } catch (err) {
        hideTyping();
        addMessage("⚠️ Could not reach the server. Please check your connection.", "ai");
        console.error("sendMessage error:", err);
    }
}

/* ─── TTS ────────────────────────────────────────── */
async function playTTS(text) {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    try {
        const res = await fetch(`${API}/tts`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });

        if (!res.ok) return;   // silently skip if TTS fails

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        currentAudio = new Audio(url);
        currentAudio.play();
        currentAudio.onended = () => URL.revokeObjectURL(url);   // free memory

    } catch (err) {
        console.warn("TTS error:", err);
    }
}

/* ─── VOICE RECORDING ────────────────────────────── */
async function startRecording() {
    if (isRecording) {
        // Manual stop
        mediaRecorder?.stop();
        return;
    }

    let stream;
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
        addMessage("⚠️ Microphone access denied. Please allow mic access and try again.", "ai");
        return;
    }

    isRecording = true;
    audioChunks = [];

    const micBtn = document.getElementById("micBtn");
    const micIcon = document.getElementById("micIcon");
    micBtn.classList.add("recording");
    micIcon.className = "ri-stop-circle-line";
    showWave();

    // Try webm first, fallback to default
    const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});

    mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
        isRecording = false;
        micBtn.classList.remove("recording");
        micIcon.className = "ri-mic-line";
        hideWave();
        // Stop all tracks to release mic
        stream.getTracks().forEach(t => t.stop());
        sendAudio();
    };

    mediaRecorder.start(100);   // collect in 100ms chunks for reliability

    // Auto-stop after 10s
    setTimeout(() => {
        if (isRecording && mediaRecorder?.state !== "inactive") {
            mediaRecorder.stop();
        }
    }, 10000);
}

/* ─── SEND AUDIO ─────────────────────────────────── */
async function sendAudio() {
    if (audioChunks.length === 0) return;

    showTyping();

    const mimeType = audioChunks[0]?.type || "audio/webm";
    const blob = new Blob(audioChunks, { type: mimeType });
    const form = new FormData();
    form.append("file", blob, "recording.webm");

    try {
        const res = await fetch(`${API}/voice-chat`, {
            method: "POST",
            body: form
        });

        if (!res.ok) throw new Error(`Server error: ${res.status}`);

        const aiText = res.headers.get("X-AI-Text") || "(No response text)";

        hideTyping();
        addMessage(aiText, "ai");
        saveSession("🎙 Voice — " + aiText.slice(0, 28) + "…");

        const audioBlob = await res.blob();
        if (audioBlob.size > 0) {
            const url = URL.createObjectURL(audioBlob);
            if (currentAudio) currentAudio.pause();
            currentAudio = new Audio(url);
            currentAudio.play();
            currentAudio.onended = () => URL.revokeObjectURL(url);
        }

    } catch (err) {
        hideTyping();
        addMessage("⚠️ Voice processing failed. Please try again.", "ai");
        console.error("sendAudio error:", err);
    }
}
