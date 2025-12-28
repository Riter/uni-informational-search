import argparse
import os
import sys
from pathlib import Path

import orjson
from tqdm import tqdm


DEFAULT_INPUT = "corpus.jsonl"
DEFAULT_REPORT = "corpus_stats.json"


def collect_stats(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    file_size = os.path.getsize(path)
    total_docs = 0
    total_text_chars = 0
    total_raw_bytes = 0
    sample_raw_sizes = []

    with open(path, "rb") as f:
        for line in tqdm(f, desc=f"scan {Path(path).name}"):
            if not line.strip():
                continue
            total_raw_bytes += len(line.rstrip(b"\r\n"))
            if len(sample_raw_sizes) < 10:
                sample_raw_sizes.append(len(line.rstrip(b"\r\n")))
            try:
                doc = orjson.loads(line)
            except orjson.JSONDecodeError:
                continue

            text = doc.get("text") or ""
            total_text_chars += len(text)
            total_docs += 1

    if total_docs == 0:
        return {"file": path, "error": "no_documents"}

    avg_raw_size = total_raw_bytes / total_docs
    avg_text_len = total_text_chars / total_docs

    return {
        "file": path,
        "file_size_bytes": file_size,
        "file_size_mb": file_size / 1024 / 1024,
        "total_docs": total_docs,
        "sample_raw_doc_sizes_bytes": sample_raw_sizes,
        "total_text_chars": total_text_chars,
        "avg_raw_doc_size_bytes": avg_raw_size,
        "avg_text_len_chars": avg_text_len,
    }


def main():
    parser = argparse.ArgumentParser(description="Corpus size statistics.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input JSONL file.")
    parser.add_argument("--report", default=DEFAULT_REPORT, help="Output JSON report.")
    args = parser.parse_args()

    report = collect_stats(args.input)
    with open(args.report, "wb") as out:
        out.write(orjson.dumps(report, option=orjson.OPT_INDENT_2))
    print(f"Report saved to {args.report}")


if __name__ == "__main__":
    main()
