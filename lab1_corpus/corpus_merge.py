import argparse
import hashlib
from pathlib import Path
from typing import Iterable, List

import orjson
from tqdm import tqdm


DEFAULT_OUTPUT = "corpus.jsonl"
DEFAULT_INPUTS: List[str] = ["habr_corpus.jsonl", "ria_corpus.jsonl"]


def sha1_hex(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", "ignore")).hexdigest()


def stream_jsonl(path: str) -> Iterable[dict]:
    with open(path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield orjson.loads(line)


def merge(inputs: List[str], output: str):
    seen_urls = set()
    total = 0
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    with open(output, "wb") as out:
        for path in inputs:
            for doc in tqdm(stream_jsonl(path), desc=f"merge {path}"):
                url = (doc.get("url") or "").strip()
                dedup_key = url or doc.get("id") or sha1_hex(orjson.dumps(doc).decode("utf-8", "ignore"))
                if dedup_key in seen_urls:
                    continue
                seen_urls.add(dedup_key)
                out.write(orjson.dumps(doc) + b"\n")
                total += 1
    return total


def main():
    parser = argparse.ArgumentParser(description="Merge Habr + RIA JSONL corpora.")
    parser.add_argument("--inputs", nargs="+", default=DEFAULT_INPUTS, help="Input JSONL files.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSONL path.")
    args = parser.parse_args()

    total = merge(args.inputs, args.output)
    print(f"Merged {total} documents into {args.output}")


if __name__ == "__main__":
    main()
