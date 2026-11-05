# Voice Cloning

Workspace eksperimen speech-to-text (STT), text-to-speech (TTS), dan GPT-SoVITS. Dua aplikasi web dan sumber GPT-SoVITS disatukan dalam satu repositori.

Demo MMS memakai suara bawaan model. Cloning identitas suara dan fine-tuning GPT-SoVITS merupakan alur terpisah. Dataset dan checkpoint eksperimen tidak dipublikasikan.

## Struktur proyek

```text
Voice-Cloning/
|-- apps/
|   |-- speech_demo/        # FastAPI STT/TTS Indonesia
|   `-- suwawa/             # Flask: rekam, transkripsi, sintesis
|-- training/               # Pengunduh base model GPT-SoVITS
|-- third_party/gpt-sovits/  # Sumber upstream dan lisensi aslinya
|-- scripts/                # Audit berkas yang dapat masuk Git
|-- docs/                   # Catatan migrasi dan hasil audit
|-- data/                   # Audio, arsip model, log, checkpoint lokal
|-- .local/                 # Arsip environment dan riwayat Git lama
|-- .env.example
`-- .gitignore
```

Nama aplikasi memakai `snake_case`. Nama internal upstream seperti `GPT_SoVITS` dipertahankan untuk kompatibilitas import. Lihat [catatan migrasi](docs/folder-migration.md).

## Persiapan

Gunakan Python 3.10 atau 3.11 dan FFmpeg dalam `PATH`. Jalankan perintah PowerShell berikut dari root repositori. Setiap komponen memakai environment terpisah karena dependensinya berbeda. GPU CUDA bersifat opsional untuk demo; kebutuhan GPT-SoVITS mengikuti upstream.

Environment lama dalam `.local/environments/` disimpan sebagai arsip. Buat ulang environment karena skrip aktivasi dapat menyimpan path absolut lama. Unduhan pertama model memerlukan internet dan ruang disk yang cukup.

### Demo STT/TTS Indonesia

```powershell
python -m venv apps/speech_demo/.venv
& ./apps/speech_demo/.venv/Scripts/python.exe -m pip install -r apps/speech_demo/requirements.txt
& ./apps/speech_demo/.venv/Scripts/python.exe apps/speech_demo/backend.py
```

Buka `http://127.0.0.1:8000`. STT memakai `indonesian-nlp/wav2vec2-large-xlsr-indonesian`; TTS memakai `facebook/mms-tts-ind`. Keduanya dimuat saat startup.

- `POST /api/transcribe`: unggah multipart field `audio`.
- `POST /api/synthesize?text=...`: hasil WAV.

### Aplikasi Suwawa

```powershell
python -m venv apps/suwawa/.venv
& ./apps/suwawa/.venv/Scripts/python.exe -m pip install -r apps/suwawa/requirements.txt
& ./apps/suwawa/.venv/Scripts/python.exe apps/suwawa/app.py
```

Buka `http://127.0.0.1:5000` dan izinkan mikrofon. Audio disimpan dalam `data/audio/suwawa/`, di luar aset statis. Model ASR dimuat ketika diperlukan. Nama Suwawa adalah nama aplikasi, bukan jaminan dukungan model bahasa Suwawa.

Aplikasi masih merupakan eksperimen lokal satu pengguna. File hasil Suwawa dipakai bersama sehingga permintaan bersamaan dapat saling menimpa. Dependensi mengikuti eksperimen awal; kompatibilitas paket, inferensi, dan kualitas deteksi bahasa perlu diverifikasi pada environment yang digunakan. Kedua aplikasi berjalan di localhost dan Flask debug dinonaktifkan.

### GPT-SoVITS

Ikuti [README upstream](third_party/gpt-sovits/README.md) untuk instalasi, bobot pretrained, training, dan inferensi. Pengunduh dua base model dapat dijalankan terpisah:

```powershell
python -m venv training/.venv
& ./training/.venv/Scripts/python.exe -m pip install -r training/requirements.txt
& ./training/.venv/Scripts/python.exe training/download_models.py
```

Default tujuan adalah `third_party/gpt-sovits/GPT_SoVITS/pretrained_models/`, sesuai path runtime upstream. Gunakan `--output-dir PATH` untuk tujuan lain. Script hanya mengunduh HuBERT dan RoBERTa; bobot GPT/SoVITS harus disediakan terpisah. Model lokal yang sudah tersedia dipertahankan. Salinan arsip juga tersedia di `data/models/` dan tidak ikut Git.

Jalankan perintah upstream dari `third_party/gpt-sovits/`. Log dan checkpoint eksperimen Indonesia berada di `data/training/indonesia/stage-1/` dan `stage-2/`. Konfigurasi asli eksperimen masih memakai path Kaggle; sesuaikan dataset, output, dan checkpoint sebelum melanjutkan training. Belum tersedia pipeline training Indonesia otomatis yang tervalidasi.

## Kredensial dan data privat

Token Hugging Face hardcoded telah dihapus. Pemilik akun tetap harus mencabut atau mengganti token lama melalui pengaturan Hugging Face. Penghapusan dari kode tidak menonaktifkan token.

Untuk model privat atau gated, set token baru melalui environment sesi:

```powershell
$env:HF_TOKEN = "your_huggingface_token_here"
```

`.env.example` menyediakan contoh `HF_TOKEN=your_huggingface_token_here`. Ganti placeholder tersebut dengan token milik sendiri pada konfigurasi lokal, lalu ekspor `HF_TOKEN` ke environment proses. Aplikasi membaca token melalui `os.getenv("HF_TOKEN")`; `.env` tidak dimuat otomatis. Jangan simpan token di kode, README, atau commit. `.gitignore` mengecualikan kredensial lokal, kunci privat, audio, dataset, checkpoint, log, cache, environment, dan `.local/`. Pengecualian Git tidak mengenkripsi file lokal. Arsip Git lama dapat berisi konfigurasi pribadi dan tidak boleh dipublikasikan.

Sebelum staging atau push, jalankan:

```powershell
python scripts/audit_repository.py
git status --short
git diff --cached --name-only
```

Audit memeriksa berkas terlacak, berkas baru yang tidak diabaikan, dan isi index bila ada staging. Temuan hanya menampilkan kategori dan lokasi, tanpa nilai rahasia. Pemindaian berbasis pola tidak menjamin deteksi semua jenis rahasia. Gunakan suara dan identitas suara dengan persetujuan pemiliknya.

## Pengujian

```powershell
python scripts/check_project.py
node --check apps/suwawa/static/app.js
python scripts/audit_repository.py
```

Tes routing memerlukan Flask atau FastAPI, httpx, dan python-multipart sesuai komponen yang diuji. Tes yang dependensinya tidak tersedia akan dilewati. Inferensi model diganti dengan data uji lokal; tidak ada unduhan model atau rekaman pribadi yang digunakan. Hasil dan batas pengujian dicatat dalam [laporan audit](docs/audit.md).

## Publikasi

Lihat [panduan PowerShell](docs/publishing.md) untuk audit staging, verifikasi repositori Private, penanganan riwayat remote, commit, push, dan perbandingan hash remote. Script `scripts/publish.ps1` menghentikan publikasi jika pemeriksaan gagal.

## Asal kode dan lisensi

GPT-SoVITS berasal dari `RVC-Boss/GPT-SoVITS`, commit `2d9193b0d3c0eae0c3a14d8c68a839f1bae157dc`. Perubahan lokal yang sudah ada pada `GPT_SoVITS/inference_webui.py` dipertahankan. Aturan ignore upstream disesuaikan agar konfigurasi default dan kode UVR ikut repositori gabungan.

Lisensi upstream dan komponen pihak ketiga dipertahankan dalam `third_party/gpt-sovits/`; lisensi model mengikuti masing-masing model card. Pemilik belum menetapkan lisensi terpisah untuk kode aplikasi workspace ini.

Repositori tujuan: [Darakbolot/Voice-Cloning](https://github.com/Darakbolot/Voice-Cloning).
