import torch
import librosa
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import tempfile
import os
import numpy as np
import subprocess
import io
import soundfile as sf

# Load model dan processor (dilakukan sekali saat startup)
print("Loading STT model...")
processor = Wav2Vec2Processor.from_pretrained("indonesian-nlp/wav2vec2-large-xlsr-indonesian")
model = Wav2Vec2ForCTC.from_pretrained("indonesian-nlp/wav2vec2-large-xlsr-indonesian")

# Pindahkan model ke device (GPU jika ada)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
if device.type == "cuda":
    try:
        model.half()  # pakai FP16 jika GPU mendukung untuk mempercepat dan hemat memori
        print("Using FP16 precision for STT model.")
    except Exception:
        print("FP16 conversion failed, using default precision.")
        pass

print(f"STT model loaded successfully on {device}!")

def transcribe_audio(audio_bytes):
    """
    Melakukan transcription dari audio bytes
    - decode dengan ffmpeg langsung dari bytes ke WAV 16k mono (cepat)
    - split ke chunk ~8s untuk mengurangi latency
    """
    try:
        # Decode input bytes ke WAV 16k mono pakai ffmpeg (stdout)
        proc = subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-f", "wav", "-ar", "16000", "-ac", "1", "pipe:1", "-hide_banner", "-loglevel", "error"],
            input=audio_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        wav_bytes = proc.stdout

        # Baca audio dari bytes (menghasilkan float32 array)
        speech_array, sampling_rate = sf.read(io.BytesIO(wav_bytes), dtype='float32')
        if sampling_rate != 16000:
            # seharusnya ffmpeg sudah men-resample, tapi guard jika perlu
            import resampy
            speech_array = resampy.resample(speech_array, sampling_rate, 16000)
            sampling_rate = 16000

        # Chunking (mis. 8 detik per chunk)
        max_chunk_sec = 8
        max_samples = max_chunk_sec * sampling_rate
        texts = []
        for start in range(0, len(speech_array), max_samples):
            chunk = speech_array[start:start + max_samples]
            if len(chunk) == 0:
                continue

            inputs = processor(chunk, sampling_rate=16000, return_tensors="pt", padding=True)
            # pindahkan tensor ke device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                logits = model(inputs["input_values"], attention_mask=inputs.get("attention_mask")).logits

            predicted_ids = torch.argmax(logits, dim=-1)
            text = processor.batch_decode(predicted_ids)[0].strip()
            if text:
                texts.append(text)

        transcription = " ".join(texts).strip()
        return transcription

    except subprocess.CalledProcessError as e:
        print("ffmpeg decode error:", e.stderr.decode() if e.stderr else str(e))
        raise e

    except Exception as e:
        print(f"Error in transcription: {str(e)}")
        raise e