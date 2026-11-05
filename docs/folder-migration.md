# Migrasi folder

| Lokasi lama | Lokasi saat ini |
| --- | --- |
| `speech-tts-stt-testing/` | `apps/speech_demo/` |
| `Suwawa/` | `apps/suwawa/` |
| `Fine-Tuning-GPTSoVITS/GPT-SoVITS/` | `third_party/gpt-sovits/` |
| `Fine-Tuning-GPTSoVITS/app.py` | `training/download_models.py` |
| `Fine-Tuning-GPTSoVITS/GPT_SoVITS/pretrained_models/` | `data/models/gpt-sovits/pretrained_models/` |
| `Fine-Tuning-GPTSoVITS/logs_s1_indonesia/` | `data/training/indonesia/stage-1/` |
| `Fine-Tuning-GPTSoVITS/logs_s2_indonesia/` | `data/training/indonesia/stage-2/` |
| `Suwawa/static/input.wav`, `tmp.webm` | `data/audio/suwawa/` |
| `env/` masing-masing komponen | `.local/environments/` |
| Git lama demo dan upstream | `.local/repositories/` |

Pemindahan sudah dilakukan sebelumnya dan tidak diulang saat audit lanjutan. Model juga tersedia pada folder runtime upstream dan dipertahankan di tempatnya. Riwayat Git lama disimpan sebagai arsip lokal terpisah. Environment perlu dibuat ulang setelah migrasi.
