"""Download the selected Hugging Face dataset file to data/raw/."""
import sys
from pathlib import Path

import requests

URL = "https://huggingface.co/datasets/young-cc/korean-it-recruit-dataset/resolve/main/master_merged_v5.json"
DEST = Path(__file__).resolve().parents[1] / "data" / "raw" / "master_merged_v5.json"


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and DEST.stat().st_size > 100_000_000:
        print(f"[skip] already downloaded: {DEST} ({DEST.stat().st_size:,} bytes)")
        return 0
    print(f"[download] {URL}")
    with requests.get(URL, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(DEST, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {done:,}/{total:,} bytes ({done * 100 // total}%)", end="", flush=True)
                else:
                    print(f"\r  {done:,} bytes", end="", flush=True)
    print()
    print(f"[done] {DEST} ({DEST.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
