import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
import xml.etree.ElementTree as ET

import orjson
from tqdm import tqdm


DEFAULT_OUTPUT = "ria_corpus.jsonl"
DEFAULT_INPUT = "ria_sitemap.xml"

DATE_PATTERNS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
]


def sha1_hex(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", "ignore")).hexdigest()


def strip_tz(raw: str) -> str:
    raw = raw.strip()
    for sep in ("Z", "+", "-"):
        if sep in raw[10:]:
            raw = raw.split(sep, 1)[0]
            break
    return raw.replace("T", " ")


def parse_date_to_iso(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    clean = strip_tz(raw)
    for pat in DATE_PATTERNS:
        try:
            dt = datetime.strptime(clean, pat)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return None


def ensure_plain_xml(path: str):
    low = path.lower()
    if any(low.endswith(ext) for ext in (".bz2", ".gz", ".xz", ".zip")):
        raise ValueError("Expected plain XML file, not archive: %s" % path)


def iter_ria_sitemap(path: str) -> Iterable[dict]:
    ensure_plain_xml(path)
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    for url_el in root.findall("sm:url", ns):
        loc_el = url_el.find("sm:loc", ns)
        if loc_el is None or not (loc_el.text and loc_el.text.strip()):
            continue
        url = loc_el.text.strip()

        lastmod_el = url_el.find("sm:lastmod", ns)
        lastmod_raw = lastmod_el.text.strip() if lastmod_el is not None and lastmod_el.text else None

        doc_id = f"ria:{sha1_hex(url)}"
        yield {
            "id": doc_id,
            "source": "ria",
            "url": url,
            "title": "",
            "text": "",
            "meta": {
                "topic": None,
                "tags": None,
                "date": lastmod_raw,
                "date_iso": parse_date_to_iso(lastmod_raw),
                "dataset": "ria_ru_sitemap_archive",
            },
        }


def main():
    parser = argparse.ArgumentParser(description="RIA sitemap parser to JSONL.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to ria sitemap XML.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSONL path.")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for debug.")
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with open(args.output, "wb") as out:
        for doc in tqdm(iter_ria_sitemap(args.input), desc="parse ria sitemap"):
            out.write(orjson.dumps(doc) + b"\n")
            total += 1
            if args.limit and total >= args.limit:
                break

    print(f"Saved {total} RIA records to {args.output}")


if __name__ == "__main__":
    main()
