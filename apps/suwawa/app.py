# app.py
import os
import traceback
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from pydub import AudioSegment
import soundfile as sf
import torch

from asr_engine import Wav2Vec2ASR  # ganti dari WhisperASR
from tts_engine import MMSTTS

# Paths
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parents[1]
AUDIO_DIR = ROOT_DIR / "data" / "audio" / "suwawa"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
TMP_WEBM = AUDIO_DIR / "tmp.webm"
INPUT_WAV = AUDIO_DIR / "input.wav"
OUTPUT_WAV = AUDIO_DIR / "output.wav"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

# ======================================================
# Hugging Face Token
# ======================================================
# Konfigurasikan sendiri token melalui environment variable HF_TOKEN untuk model privat/gated.
# Jangan menuliskan token langsung di source code.
HF_TOKEN = os.getenv("HF_TOKEN") or None

# ======================================================
# Initialize engines
# ======================================================
asr = Wav2Vec2ASR(hf_token=HF_TOKEN)  # Wav2Vec2 multi-bahasa
tts = MMSTTS()                        # MMS-TTS


@app.route("/")
def index():
    return render_template("index.html")


# ======================================================
# PROCESS AUDIO (RECORD → ASR → TTS)
# ======================================================
@app.route("/process_audio", methods=["POST"])
def process_audio():
    try:
        if "audio" not in request.files:
            return jsonify({"ok": False, "error": "No audio file sent"}), 400

        f = request.files["audio"]
        f.save(TMP_WEBM)

        # --------------------------------------------------
        # Convert to WAV 16k mono (ASR requirement)
        # --------------------------------------------------
        audio = AudioSegment.from_file(TMP_WEBM)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(INPUT_WAV, format="wav")

        # --------------------------------------------------
        # ASR — transcribe speech
        # --------------------------------------------------
        # bisa tambahkan hint_text untuk auto deteksi bahasa
        hint_text = None
        transcript = asr.transcribe(INPUT_WAV, hint_text=hint_text)

        if transcript is None or transcript.strip() == "":
            return jsonify({
                "ok": False,
                "error": "ASR returned empty transcript"
            }), 500

        # --------------------------------------------------
        # TTS — generate waveform from text
        # --------------------------------------------------
        waveform = tts.synthesize(transcript)

        # Ensure numpy array float32
        if isinstance(waveform, torch.Tensor):
            arr = waveform.detach().cpu().numpy()
        else:
            arr = waveform

        # Normalize
        maxv = max(abs(arr.max()), abs(arr.min()), 1e-6)
        if maxv > 1.0:
            arr = arr / maxv

        # Save WAV (16k)
        sf.write(OUTPUT_WAV, arr, 16000, subtype="PCM_16")

        return jsonify({
            "ok": True,
            "transcript": transcript,
            "audio_url": "/output_audio"
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# ======================================================
# Download endpoint
# ======================================================
@app.route("/output_audio")
def output_audio():
    if OUTPUT_WAV.exists():
        response = send_file(OUTPUT_WAV, mimetype="audio/wav")
        response.headers["Cache-Control"] = "no-store"
        return response
    return "No output file", 404


@app.route("/download_output")
def download_output():
    if os.path.exists(OUTPUT_WAV):
        return send_file(OUTPUT_WAV, as_attachment=True)
    return "No output file", 404


# ======================================================
# MAIN
# ======================================================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
