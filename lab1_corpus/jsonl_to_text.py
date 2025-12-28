import argparse
from pathlib import Path

import orjson
from tqdm import tqdm


DEFAULT_INPUT = "corpus.jsonl"
DEFAULT_OUTPUT = "plain_corpus.txt"


def stream_jsonl(path: str):
    with open(path, "rb") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                yield orjson.loads(line)
            except orjson.JSONDecodeError:
                continue


def dump_text(input_path: str, output_path: str, limit: int = 0):
    total = 0
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as out:
        for doc in tqdm(stream_jsonl(input_path), desc="export text"):
            text = doc.get("text") or ""
            out.write(text.replace("\r", " ").replace("\n", " ").strip() + "\n")
            total += 1
            if limit and total >= limit:
                break
    return total


def main():
    parser = argparse.ArgumentParser(description="Extract text field from JSONL corpus.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input corpus JSONL.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output plain text file.")
    parser.add_argument("--limit", type=int, default=0, help="Optional doc limit.")
    args = parser.parse_args()

    total = dump_text(args.input, args.output, args.limit)
    print(f"Exported {total} documents to {args.output}")


if __name__ == "__main__":
    main()
