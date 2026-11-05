# asr_engine.py
import torch
import torchaudio
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
from langdetect import detect

class Wav2Vec2ASR:
    def __init__(self, hf_token: str = None):
        """
        hf_token : str | Optional Hugging Face token untuk akses model private/gated
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.hf_token = hf_token

        # mapping bahasa → model
        # gunakan model publik jika private model tidak tersedia
        self.models = {
            "id": ["indonesian-nlp/wav2vec2-large-xlsr-indonesian"],  # fallback ke publik
            "en": ["facebook/wav2vec2-large-960h"],
            "jv": ["jonathansj/javanese-wav2vec2"],  # jika private, harus token valid
            "su": ["jonathansj/sundanese-wav2vec2"], # jika private, harus token valid
        }

        self.default_lang = "id"
        self.cache = {}  # cache processor + model per bahasa

    def _load_model(self, lang):
        lang = lang if lang in self.models else self.default_lang
        if lang in self.cache:
            return self.cache[lang]

        for repo in self.models[lang]:
            try:
                print(f"Loading Wav2Vec2 model: {repo} for language '{lang}'")
                processor = Wav2Vec2Processor.from_pretrained(repo, token=self.hf_token)
                dtype = torch.float16 if self.device.type == "cuda" else torch.float32
                model = Wav2Vec2ForCTC.from_pretrained(
                    repo,
                    torch_dtype=dtype,
                    token=self.hf_token
                ).to(self.device)
                model.eval()
                self.cache[lang] = {"processor": processor, "model": model, "dtype": dtype}
                return self.cache[lang]
            except Exception as e:
                print(f"Failed to load {repo}: {e}")
                continue

        raise RuntimeError(f"Failed to load any model for language '{lang}'")

    def _detect_language(self, text):
        try:
            lang = detect(text)
            if lang.startswith("id"):
                return "id"
            if lang.startswith("en"):
                return "en"
            if lang.startswith("jv"):
                return "jv"
            if lang.startswith("su"):
                return "su"
            return self.default_lang
        except:
            return self.default_lang

    def transcribe(self, wav_path, hint_text: str = None):
        # load waveform
        speech, sr = torchaudio.load(wav_path)
        if speech.ndim > 1 and speech.shape[0] > 1:
            speech = torch.mean(speech, dim=0, keepdim=True)

        if sr != 16000:
            speech = torchaudio.functional.resample(speech, sr, 16000)

        # detect language from hint_text if tersedia
        lang = self._detect_language(hint_text) if hint_text else self.default_lang
        entry = self._load_model(lang)

        processor = entry["processor"]
        model = entry["model"]
        dtype = entry["dtype"]

        # prepare inputs
        proc_out = processor(speech.squeeze(0), sampling_rate=16000, return_tensors="pt")
        inputs = {}
        for k, v in proc_out.items():
            if torch.is_tensor(v):
                inputs[k] = v.to(self.device, dtype=dtype)
            else:
                inputs[k] = v

        # forward
        with torch.no_grad():
            input_values = inputs.get("input_values", inputs.get("input_features"))
            if input_values is None:
                raise RuntimeError("Processor output missing input_values or input_features")

            logits = model(input_values).logits
            predicted_ids = torch.argmax(logits, dim=-1)

        # decode
        text = processor.batch_decode(predicted_ids)[0]
        return text
