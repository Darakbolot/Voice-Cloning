# Publikasi dari PowerShell Windows

Sesi Codex ini masih dibatasi ACL sandbox dan tidak dapat terhubung ke GitHub. Jalankan langkah berikut dari PowerShell biasa sebagai pemilik workspace. Tidak perlu mereset ACL drive atau menghapus `.git`.

## Pemeriksaan akses lokal

```powershell
Set-Location -LiteralPath 'E:\Voice Cloning'
whoami
Get-Acl -LiteralPath '.git' | Format-List Owner,AccessToString
Get-Acl -LiteralPath '.git/config' | Format-List Owner,AccessToString
Get-Process git -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath '.git' -Force -Filter '*.lock'
git status --short
git remote -v
```

Audit menemukan ownership `MSI\GF63`, aturan Deny untuk identitas sandbox, dan tidak menemukan lock Git tertinggal. Jangan menghapus lock ketika proses Git masih aktif. Jangan menghapus aturan Deny sandbox atau mengubah keamanan Windows untuk mengatasi pembatasan sesi ini. Jika Git bekerja dari akun pemilik, lanjutkan langsung dari akun tersebut. Jika gagal juga, simpan keluaran ACL dan periksa hanya akses `.git` bersama administrator; jangan mereset permission seluruh drive.

## Remote kosong

Diperlukan Git, Python, Node.js, serta GitHub CLI yang sudah login ke akun dengan akses repositori. Jika GitHub CLI tersedia tetapi belum login, jalankan `gh auth login` secara interaktif. Jangan menuliskan token pada skrip atau command line.

```powershell
Set-Location -LiteralPath 'E:\Voice Cloning'
& .\scripts\publish.ps1
```

Script mengambil URL dari konfigurasi `origin`, memverifikasi repositori berstatus Private melalui GitHub CLI, dan memeriksa riwayat remote. Untuk remote kosong, script menjalankan seluruh pemeriksaan, melakukan staging pada path sumber yang ditentukan, memeriksa isi staging, membuat commit dengan pesan yang diminta, lalu menjalankan `git push -u origin main`. Hash `main` remote dibandingkan dengan hash lokal sebagai bukti keberhasilan. Setiap kegagalan menghentikan script. Tidak ada force push atau perubahan ACL.

## Remote memiliki riwayat

Script berhenti sebelum staging atau commit jika remote memiliki referensi. Periksa dahulu:

```powershell
git fetch origin
git log --oneline --graph --all -20
git remote show origin
```

Jika `origin/main` sudah ada, pertahankan riwayatnya. Setelah memahami isinya, tahap berikut dapat dilakukan dari root proyek. Setiap perintah dengan exit code bukan nol harus ditangani sebelum melanjutkan:

```powershell
python scripts/check_project.py
node --check apps/suwawa/static/app.js
python scripts/audit_repository.py
git add -- .env.example .gitattributes .gitignore README.md apps training third_party docs scripts tests data/README.md
python scripts/audit_repository.py
git diff --cached --name-only
git commit -m 'Initial commit: organize and secure Voice Cloning project'
git merge --allow-unrelated-histories --no-edit origin/main
```

Jika merge konflik, berhenti, tinjau file konflik, selesaikan tanpa membuang riwayat remote, lalu lakukan audit dan pengujian sebelum menyelesaikan merge. Jangan mengunggah konflik. Jika remote hanya memiliki branch selain `main`, periksa branch default yang ditunjukkan `git remote show origin` dan tentukan branch yang perlu digabungkan; jangan menebak nama branch atau melakukan force push.

Sesudah merge berhasil, periksa kode yang berasal dari remote dan ulangi audit. Auditor memeriksa file saat ini dan index, bukan seluruh riwayat commit remote. Pastikan riwayat remote tidak membawa rahasia yang pernah dipublikasikan.

```powershell
python scripts/check_project.py
node --check apps/suwawa/static/app.js
python scripts/audit_repository.py
gh repo view --json isPrivate --jq '.isPrivate'
git status --short
```

Lanjutkan hanya jika audit dan tes lolos, tidak ada konflik atau perubahan sumber yang belum di-commit, dan hasil pemeriksaan visibility adalah `true`:

```powershell
git push -u origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Push terverifikasi jika perintah push berhasil dan kedua hash identik. Jika push ditolak karena remote berubah lagi, fetch dan tinjau perubahan baru sebelum merge ulang. Jangan memakai `--force`.

Token Hugging Face lama dicabut sendiri oleh pemilik melalui akunnya. Prosedur ini tidak mengakses API pencabutan token.
