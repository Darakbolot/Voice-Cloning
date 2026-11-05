"""Download GPT-SoVITS base models to the vendored runtime directory."""

import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT_DIR / "third_party" / "gpt-sovits" / "GPT_SoVITS" / "pretrained_models"
MODELS = {
    "chinese-roberta-wwm-ext-large": "hfl/chinese-roberta-wwm-ext-large",
    "chinese-hubert-base": "TencentGameMate/chinese-hubert-base",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()

    from huggingface_hub import snapshot_download

    for name, repo_id in MODELS.items():
        destination = args.output_dir.resolve() / name
        destination.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {repo_id} to {destination}")
        snapshot_download(repo_id=repo_id, local_dir=str(destination))
    print("Base models ready. Training/inference weights must be supplied separately.")


if __name__ == "__main__":
    main()
