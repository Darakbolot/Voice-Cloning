# tts_engine.py
import os
os.environ["DISABLE_TORCHCODEC"] = "1"   # disable torchcodec on Windows if present

import torch
from transformers import AutoProcessor, VitsModel
from langdetect import detect

class MMSTTS:
    def __init__(self):
        print("Initializing MMSTTS (lazy load, FP32 enforced)...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # model repo mapping (change repos if you prefer smaller models)
        self.model_repos = {
            "id": "facebook/mms-tts-ind",
            "en": "facebook/mms-tts-eng",
            "jv": "facebook/mms-tts-jav",
            "su": "facebook/mms-tts-sun"
        }

        self.cache = {}
        self.default = "id"

    def _load(self, lang):
        if lang in self.cache:
            return self.cache[lang]

        repo = self.model_repos.get(lang, self.model_repos[self.default])
        print(f"[MMSTTS] Loading {repo} ... (this may take time)")

        processor = AutoProcessor.from_pretrained(repo)
        model = VitsModel.from_pretrained(repo)

        # FORCE model to float32 to avoid mixed-precision bias/input mismatch
        model = model.to(dtype=torch.float32)
        model.eval()
        model.to(self.device)

        self.cache[lang] = {"p": processor, "m": model}
        return self.cache[lang]

    def _detect(self, word):
        try:
            d = detect(word)
            if d.startswith("id"): return "id"
            if d.startswith("en"): return "en"
            if d.startswith("jv"): return "jv"
            if d.startswith("su"): return "su"
            return self.default
        except Exception:
            return self.default

    def synthesize(self, text):
        """
        - Split text into language-homogeneous segments to reduce number of model calls
        - For each segment, run TTS and concatenate waveforms
        """
        # quick guard
        if text is None:
            return torch.zeros(16000 // 2)

        words = text.strip().split()
        if not words:
            return torch.zeros(16000 // 2)

        # group contiguous words by detected language
        segments = []
        cur_lang = None
        cur_tokens = []
        for w in words:
            lang = self._detect(w)
            if cur_lang is None:
                cur_lang = lang
                cur_tokens = [w]
            elif lang == cur_lang:
                cur_tokens.append(w)
            else:
                segments.append((cur_lang, " ".join(cur_tokens)))
                cur_lang = lang
                cur_tokens = [w]
        if cur_tokens:
            segments.append((cur_lang, " ".join(cur_tokens)))

        audio_parts = []
        for (lang, seg_text) in segments:
            entry = self._load(lang)
            proc = entry["p"]
            model = entry["m"]

            # prepare inputs
            inputs = proc(text=seg_text, return_tensors="pt")

            # ensure inputs are float32 and moved to device
            inputs = {k: (v.to(self.device).to(dtype=torch.float32) if torch.is_tensor(v) else v) for k, v in inputs.items()}

            with torch.no_grad():
                out = model(**inputs)

                # Extract waveform: depending on model output attribute name
                if hasattr(out, "audio"):
                    wav = out.audio
                elif hasattr(out, "waveform"):
                    wav = out.waveform
                else:
                    # defensive: find first tensor attr
                    found = None
                    for val in out.__dict__.values():
                        if torch.is_tensor(val):
                            found = val
                            break
                    if found is None:
                        raise RuntimeError("Unable to extract audio tensor from TTS model output.")
                    wav = found

                # ensure 1D cpu tensor float32
                wav = wav.squeeze().cpu().to(dtype=torch.float32)

            audio_parts.append(wav)

        if not audio_parts:
            return torch.zeros(16000 // 2)

        return torch.cat(audio_parts)