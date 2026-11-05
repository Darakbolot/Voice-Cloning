"""Audit publishable working files and Git index without printing secret values."""

import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "hugging-face-token": re.compile(rb"hf_[A-Za-z0-9]{20,}"),
    "github-token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "aws-access-key": re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "credential-url": re.compile(rb"https?://[^\s/:@]+:[^\s/@]+@"),
    "assigned-secret": re.compile(
        rb"(?im)^\s*[\"']?[A-Za-z_]*(?:token|api_key|secret|password)[A-Za-z_]*[\"']?\s*[:=]\s*[\"']([^\"'\r\n]{12,})[\"']"
    ),
}
PRIVATE_SUFFIXES = {
    ".pem", ".key", ".p12", ".pfx", ".wav", ".webm", ".mp3", ".flac", ".ogg",
    ".m4a", ".mp4", ".pth", ".pt", ".ckpt", ".bin", ".safetensors", ".onnx",
    ".h5", ".msgpack", ".pickle", ".pkl", ".db", ".sqlite", ".jsonl", ".tsv", ".har", ".session",
}
PROBES = [
    ".env", ".env.production", "apps/suwawa/.env", "credentials.json", "secrets.yaml",
    "private.pem", ".netrc", ".pypirc", ".huggingface/token",
    ".local/repositories/old.git/config", ".local/environments/demo/Scripts/python.exe",
    "data/audio/suwawa/input.wav", "data/training/indonesia/stage-1/weights/model.pth",
    "data/models/gpt-sovits/pretrained_models/config.json", "data/private/transcript.txt",
    "apps/suwawa/.venv/pyvenv.cfg", "apps/suwawa/__pycache__/app.pyc",
    "third_party/gpt-sovits/GPT_SoVITS/pretrained_models/private/config.json",
    "third_party/gpt-sovits/weight.json",
    "cookies.txt", "cookies-browser.json", "apps/suwawa/cookies.txt",
    "Cookies", "Cookies-journal", ".cookies/session.txt", ".auth/session.json", "requests.har",
]
REQUIRED = [
    "README.md", ".env.example", "data/README.md", "apps/suwawa/static/app.js",
    "third_party/gpt-sovits/LICENSE", "third_party/gpt-sovits/GPT_SoVITS/configs/s1longer-v2.yaml",
    "third_party/gpt-sovits/GPT_SoVITS/configs/tts_infer.yaml",
    "third_party/gpt-sovits/tools/uvr5/lib/lib_v5/spec_utils.py",
    "third_party/gpt-sovits/GPT_SoVITS/text/ja_userdic/userdict.csv",
]


def git(*args, input=None):
    return subprocess.check_output(["git", *args], cwd=ROOT, input=input)


def private_path(name):
    path = PurePosixPath(name)
    if name.startswith("data/") and name != "data/README.md":
        return True
    if any(p in {".local", ".git", ".aws", ".ssh", ".huggingface", "env", "venv", ".venv", "__pycache__", ".cookies", ".auth"} for p in path.parts):
        return True
    if "pretrained_models" in path.parts and path.name != ".gitignore":
        return True
    if path.name.startswith(".env") and path.name != ".env.example":
        return True
    if path.name.startswith(("credentials.", "secrets.")) or path.name in {".netrc", ".npmrc", ".pypirc", "weight.json"}:
        return True
    if path.name in {"Cookies", "Cookies-journal"} or (path.name.lower().startswith("cookie") and path.suffix.lower() in {".txt", ".json"}):
        return True
    return path.suffix.lower() in PRIVATE_SUFFIXES


def inspect(label, name, data, findings):
    if private_path(name):
        findings.append(f"{label}: private path: {name}")
    if len(data) >= 100 * 1024 * 1024:
        findings.append(f"{label}: exceeds GitHub file limit: {name}")
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(data):
            if kind == "assigned-secret" and match.group(1) in {b"TOKEN_BARU_ANDA", b"YOUR_TOKEN_HERE"}:
                continue
            line = data.count(b"\n", 0, match.start()) + 1
            findings.append(f"{label}: {kind}: {name}:{line}")


def main():
    findings = []
    index = []
    for record in git("ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        mode, oid, stage = meta.decode().split()
        name = name.decode("utf-8")
        if mode == "160000" or stage != "0":
            findings.append(f"index: unresolved entry or nested repository: {name}")
            continue
        index.append((name, oid))
    names = {name for name, oid in index}
    names.update(p.decode("utf-8") for p in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if p)
    for name in sorted(names):
        path = ROOT / name
        if path.is_file():
            inspect("working-tree", name, path.read_bytes(), findings)
    for name, oid in index:
        inspect("index", name, git("cat-file", "blob", oid), findings)
    ignored = set(git("check-ignore", "--no-index", "--stdin", "-z", input=("\0".join(PROBES) + "\0").encode()).decode().strip("\0").split("\0"))
    for name in PROBES:
        if name not in ignored:
            findings.append(f"ignore rule missing: {name}")
    for name in REQUIRED:
        if name not in names or not (ROOT / name).is_file():
            findings.append(f"required source missing or ignored: {name}")
    for base in ("apps", "training", "third_party"):
        for path in (ROOT / base).rglob(".git"):
            findings.append(f"nested repository: {path.relative_to(ROOT)}")
    print(f"Audited {len(names)} working-tree candidates and {len(index)} index blobs.")
    print(f"Checked {len(PROBES)} private-path exclusions and {len(REQUIRED)} required source paths.")
    for finding in findings:
        print(finding)
    print("FAIL" if findings else "PASS: no matching secrets or private artifacts found in publishable files.")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
