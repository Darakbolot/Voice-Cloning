let recorder;
let chunks = [];
const recordBtn = document.getElementById("recordBtn");
const statusEl = document.getElementById("status");
const transcriptEl = document.getElementById("transcript");
const audioPlayer = document.getElementById("audioPlayer");
const errorMsg = document.getElementById("errorMsg");

async function startRecording() {
    errorMsg.textContent = "";
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);

    recorder.ondataavailable = e => chunks.push(e.data);
    recorder.onstop = onStop;
    recorder.start();
    recordBtn.classList.add("recording");
    recordBtn.textContent = "Stop";
    statusEl.innerHTML = "";
}

async function stopRecording() {
    if (recorder && recorder.state !== "inactive") recorder.stop();
    recordBtn.classList.remove("recording");
    recordBtn.textContent = "Rekam";
}

async function onStop() {
    statusEl.innerHTML = '<div class="spinner"></div><div class="mt-2">Mengunggah & memproses...</div>';
    const blob = new Blob(chunks, { type: "audio/webm" });
    chunks = [];

    const fd = new FormData();
    fd.append("audio", blob, "audio.webm");

    try {
        const res = await fetch("/process_audio", { method: "POST", body: fd });
        const data = await res.json();
        if (!data.ok) {
            throw new Error(data.error || "Unknown error");
        }

        transcriptEl.value = data.transcript;
        audioPlayer.src = data.audio_url + "?t=" + Date.now();
        statusEl.innerHTML = "<div class='text-success'>Selesai</div>";
    } catch (err) {
        console.error(err);
        errorMsg.textContent = "Error: " + err.message;
        statusEl.innerHTML = "";
    }
}

recordBtn.onclick = async () => {
    if (!recorder || recorder.state === "inactive") {
        try {
            await startRecording();
        } catch (e) {
            errorMsg.textContent = "Tidak bisa mengakses mikrofon: " + e.message;
        }
    } else {
        await stopRecording();
    }
};
