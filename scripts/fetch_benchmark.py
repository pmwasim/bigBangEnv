"""Vendor the public deepset/prompt-injections corpus (Apache-2.0) into the repo.

Source: https://huggingface.co/datasets/deepset/prompt-injections
Fetched through the Hugging Face dataset-viewer rows API, so no parquet
reader is needed. The evaluation then runs offline from the vendored copy.

Run:  python scripts/fetch_benchmark.py
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

DATASET = "deepset/prompt-injections"
API = "https://datasets-server.huggingface.co/rows"
OUT = Path(__file__).resolve().parent.parent / "src" / "bigbang" / "data" / "deepset_prompt_injections.jsonl"


def ssl_context() -> ssl.SSLContext:
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()


def fetch(split: str, offset: int, length: int = 100) -> dict:
    query = urllib.parse.urlencode(
        {"dataset": DATASET, "config": "default", "split": split, "offset": offset, "length": length}
    )
    with urllib.request.urlopen(f"{API}?{query}", context=ssl_context(), timeout=60) as resp:
        return json.load(resp)


def main() -> None:
    rows = []
    for split in ("train", "test"):
        offset = 0
        while True:
            page = fetch(split, offset)
            batch = page["rows"]
            for item in batch:
                row = item["row"]
                rows.append({"split": split, "index": item["row_idx"], "label": row["label"], "text": row["text"]})
            offset += len(batch)
            if not batch or offset >= page["num_rows_total"]:
                break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    injections = sum(r["label"] == 1 for r in rows)
    print(f"wrote {len(rows)} rows ({injections} injections) to {OUT}")


if __name__ == "__main__":
    main()
