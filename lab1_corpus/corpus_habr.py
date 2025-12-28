import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Iterable, Optional

import orjson
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


DEFAULT_OUTPUT = "habr_corpus.jsonl"
DEFAULT_LIMIT = 50000
DEFAULT_DELAY = 0.5
USER_AGENT = "Mozilla/5.0 (compatible; MiniSearchBot/0.1; +https://example.com/contact)"


def sha1_hex(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", "ignore")).hexdigest()


def iter_article_urls(max_pages: int, session: requests.Session, delay: float) -> Iterable[str]:
    """
    Collect article URLs from the main articles feed.
    This is a trimmed version of the multi-strategy parser from examples/IR.
    """
    for page in range(1, max_pages + 1):
        url = f"https://habr.com/ru/articles/page{page}/"
        resp = session.get(url, timeout=20)
        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "lxml")
        links = soup.select("a.tm-title__link")
        if not links:
            break

        for link in links:
            href = link.get("href")
            if not href:
                continue
            yield f"https://habr.com{href}" if href.startswith("/") else href

        time.sleep(delay)


def extract_article(url: str, session: requests.Session) -> Optional[dict]:
    resp = session.get(url, timeout=20)
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    title_el = soup.find("h1")
    body_el = soup.find("div", class_="tm-article-presenter__body")
    if not body_el:
        body_el = soup.find("div", class_="article-formatted-body")

    title = title_el.get_text(strip=True) if title_el else ""

    paragraphs = []
    if body_el:
        for tag in body_el.find_all(["p", "li"]):
            text = tag.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)

    text = "\n".join(paragraphs).strip()
    tags = [a.get_text(strip=True) for a in soup.select("a.tm-article-snippet__hubs-item-link")]
    published_el = soup.find("time")
    published_iso = published_el.get("datetime") if published_el else None

    doc_id = f"habr:{sha1_hex(url)}"
    return {
        "id": doc_id,
        "source": "habr",
        "url": url,
        "title": title,
        "text": text,
        "meta": {
            "tags": tags or None,
            "date_iso": published_iso,
            "dataset": "habr_articles_feed",
        },
    }


def crawl_habr(output_path: str, limit: int, max_pages: int, delay: float):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    seen = set()
    written = 0
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("wb") as out:
        for url in tqdm(iter_article_urls(max_pages, session, delay), desc="collect urls"):
            if url in seen:
                continue
            seen.add(url)
            doc = extract_article(url, session)
            if not doc:
                continue
            out.write(orjson.dumps(doc) + b"\n")
            written += 1
            if written >= limit:
                break
    return written


def main():
    parser = argparse.ArgumentParser(description="Habr corpus collector (JSONL).")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSONL path.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Max articles to save.")
    parser.add_argument("--pages", type=int, default=300, help="Pages to scan in the feed.")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between list pages.")
    args = parser.parse_args()

    total = crawl_habr(args.output, args.limit, args.pages, args.delay)
    print(f"Saved {total} Habr articles to {args.output}")


if __name__ == "__main__":
    main()
