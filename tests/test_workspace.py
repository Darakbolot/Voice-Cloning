"""Routing and migration checks with model inference replaced by local fakes."""

import asyncio
import importlib.util
import io
import os
from pathlib import Path
import sys
import contextlib
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AuditTests(unittest.TestCase):
    def test_cookie_exports_are_private_paths(self):
        audit = load("audit_cookie_test", "scripts/audit_repository.py")
        for name in ["cookies.txt", "apps/suwawa/cookies-browser.json", "Cookies", "Cookies-journal", ".auth/session.json", "requests.har"]:
            self.assertTrue(audit.private_path(name), name)
        self.assertFalse(audit.private_path("apps/suwawa/app.py"))

    def test_staged_secret_is_detected_even_after_working_file_is_cleaned(self):
        audit = load("audit_test", "scripts/audit_repository.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text(".env\n", encoding="utf-8")
            secret = "hf_" + "a" * 30
            source = root / "example.py"
            source.write_text("value = " + repr(secret), encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "example.py"], check=True)
            source.write_text("value = None\n", encoding="utf-8")
            output = io.StringIO()
            with patch.object(audit, "ROOT", root), patch.object(audit, "PROBES", [".env"]), patch.object(audit, "REQUIRED", []), contextlib.redirect_stdout(output):
                result = audit.main()
            self.assertEqual(result, 1)
            self.assertIn("index: hugging-face-token: example.py", output.getvalue())
            self.assertNotIn(secret, output.getvalue())


class DownloaderTests(unittest.TestCase):
    def test_download_destinations_and_no_download_at_import(self):
        calls = []
        hub = types.SimpleNamespace(snapshot_download=lambda **kw: calls.append(kw))
        with patch.dict(sys.modules, {"huggingface_hub": hub}):
            module = load("download_models_test", "training/download_models.py")
            self.assertEqual(calls, [])
            self.assertEqual(module.DEFAULT_MODEL_DIR, ROOT / "third_party/gpt-sovits/GPT_SoVITS/pretrained_models")
            with tempfile.TemporaryDirectory() as tmp:
                with patch.object(sys, "argv", ["download_models.py", "--output-dir", tmp]):
                    module.main()
                self.assertEqual({c["repo_id"] for c in calls}, set(module.MODELS.values()))
                self.assertEqual({Path(c["local_dir"]).parent for c in calls}, {Path(tmp).resolve()})


@unittest.skipUnless(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx") and importlib.util.find_spec("multipart"), "FastAPI/httpx/multipart not available")
class FastAPITests(unittest.TestCase):
    def test_routes_from_different_working_directory(self):
        import httpx
        mocks = {
            "stt_service": types.SimpleNamespace(transcribe_audio=lambda audio: "uji suara"),
            "tts_service": types.SimpleNamespace(generate_speech=lambda text: b"RIFF-test-wave"),
        }
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, mocks):
            try:
                os.chdir(tmp)
                module = load("speech_backend_test", "apps/speech_demo/backend.py")
                async def check():
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=module.app), base_url="http://test") as client:
                        page = await client.get("/")
                        self.assertEqual(page.status_code, 200)
                        self.assertIn("<html", page.text.lower())
                        response = await client.post("/api/transcribe", files={"audio": ("test.webm", b"fake-audio", "audio/webm")})
                        self.assertEqual(response.json(), {"transcription": "uji suara", "success": True})
                        audio = await client.post("/api/synthesize", params={"text": "uji suara"})
                        self.assertEqual(audio.status_code, 200)
                        self.assertEqual(audio.content, b"RIFF-test-wave")
                        self.assertIn("audio/wav", audio.headers["content-type"])
                asyncio.run(check())
            finally:
                os.chdir(previous)


@unittest.skipUnless(importlib.util.find_spec("flask"), "Flask not available")
class FlaskTests(unittest.TestCase):
    def test_pages_audio_routes_and_private_storage(self):
        class FakeArray:
            def max(self):
                return 0.5
            def min(self):
                return -0.5
        class FakeASR:
            def __init__(self, **kw):
                pass
            def transcribe(self, path, **kw):
                self_test.assertTrue(Path(path).exists())
                return "uji suara"
        class FakeTTS:
            def synthesize(self, text):
                return FakeArray()
        class FakeSegment:
            def set_frame_rate(self, rate):
                return self
            def set_channels(self, channels):
                return self
            def export(self, path, **kw):
                Path(path).write_bytes(b"RIFF-input")
        self_test = self
        mocks = {
            "asr_engine": types.SimpleNamespace(Wav2Vec2ASR=FakeASR),
            "tts_engine": types.SimpleNamespace(MMSTTS=FakeTTS),
            "torch": types.SimpleNamespace(Tensor=type("FakeTensor", (), {})),
            "pydub": types.SimpleNamespace(AudioSegment=types.SimpleNamespace(from_file=lambda p: FakeSegment())),
            "soundfile": types.SimpleNamespace(write=lambda p, *a, **kw: Path(p).write_bytes(b"RIFF-output")),
        }
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, mocks):
            try:
                os.chdir(tmp)
                module = load("suwawa_app_test", "apps/suwawa/app.py")
                self.assertEqual(module.AUDIO_DIR, ROOT / "data/audio/suwawa")
                self.assertFalse(module.AUDIO_DIR.is_relative_to(ROOT / "apps/suwawa/static"))
                module.TMP_WEBM = Path(tmp) / "test.webm"
                module.INPUT_WAV = Path(tmp) / "input.wav"
                module.OUTPUT_WAV = Path(tmp) / "output.wav"
                client = module.app.test_client()
                for route in ["/", "/static/style.css", "/static/app.js"]:
                    with client.get(route) as response:
                        self.assertEqual(response.status_code, 200, route)
                self.assertEqual(client.get("/output_audio").status_code, 404)
                self.assertEqual(client.get("/download_output").status_code, 404)
                self.assertEqual(client.post("/process_audio").status_code, 400)
                response = client.post("/process_audio", data={"audio": (io.BytesIO(b"fake-audio"), "test.webm")})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["transcript"], "uji suara")
                self.assertEqual(response.json["audio_url"], "/output_audio")
                with client.get("/output_audio") as audio:
                    self.assertEqual(audio.data, b"RIFF-output")
                    self.assertEqual(audio.headers["Cache-Control"], "no-store")
                with client.get("/download_output") as audio:
                    self.assertEqual(audio.status_code, 200)
                    self.assertIn("attachment", audio.headers["Content-Disposition"])
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main(verbosity=2)
