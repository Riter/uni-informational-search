from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

import orjson
import requests
from bs4 import BeautifulSoup
from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from config import AppConfig, load_config
from db import create_mongo, get_documents_collection, get_frontier_collection
from logging_conf import setup_logging
from robots import RobotsCache
from url_utils import get_domain, normalize_url

log = logging.getLogger("crawler")


def read_jsonl(path: str):
    with open(path, "rb") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                yield orjson.loads(line)
            except orjson.JSONDecodeError:
                continue


@dataclass
class FrontierItem:
    url: str
    source: str


class SearchBot:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": cfg.logic.user_agent})

        self.db = create_mongo(cfg.db)
        self.docs: Collection = get_documents_collection(self.db, cfg.db)
        self.frontier: Collection = get_frontier_collection(self.db)

        self._indexes_ready()

        self.allowed_domains = set(cfg.logic.allowed_domains)
        self.follow_links = cfg.logic.follow_links
        self.respect_robots = cfg.logic.respect_robots
        self.delay = cfg.logic.request_delay_sec
        self.revisit_after = cfg.logic.recrawl_interval_sec
        self.max_pages = cfg.logic.max_pages
        self.workers = cfg.logic.worker_count

        self.pages_done = 0
        self._stop = threading.Event()
        self._count_lock = threading.Lock()
        self.robots_cache = RobotsCache(self.session, cfg.logic.user_agent)

    # --- helpers ---
    def _indexes_ready(self):
        self.docs.create_index([("url", ASCENDING)], unique=True)
        self.docs.create_index([("source", ASCENDING)])
        self.docs.create_index([("crawled_at", ASCENDING)])
        self.frontier.create_index([("url", ASCENDING)], unique=True)
        self.frontier.create_index([("status", ASCENDING), ("next_crawl_at", ASCENDING)])

    def seed_frontier(self):
        if self.frontier.estimated_document_count() > 0:
            log.info("Frontier already has data, skip seeding")
            return
        now = time.time()
        if self.cfg.logic.urls_jsonl:
            for doc in read_jsonl(self.cfg.logic.urls_jsonl):
                raw_url = (doc.get("url") or "").strip()
                if not raw_url:
                    continue
                url = normalize_url(raw_url)
                dom = get_domain(url)
                if self.allowed_domains and dom not in self.allowed_domains:
                    continue
                self._upsert_frontier(url, dom, now)
        else:
            for raw in self.cfg.logic.start_urls:
                url = normalize_url(raw)
                dom = get_domain(url)
                if self.allowed_domains and dom not in self.allowed_domains:
                    continue
                self._upsert_frontier(url, dom, now)

    def _upsert_frontier(self, url: str, source: str, ts: float):
        try:
            self.frontier.update_one(
                {"url": url},
                {
                    "$setOnInsert": {
                        "url": url,
                        "source": source,
                        "status": "pending",
                        "next_crawl_at": ts,
                        "discovered_at": ts,
                    }
                },
                upsert=True,
            )
        except PyMongoError as e:
            log.warning("Frontier upsert failed for %s: %s", url, e)

    def _claim_next(self) -> Optional[FrontierItem]:
        now = time.time()
        doc = self.frontier.find_one_and_update(
            {"status": "pending", "next_crawl_at": {"$lte": now}},
            {"$set": {"status": "processing"}},
            sort=[("discovered_at", ASCENDING)],
        )
        if not doc:
            return None
        return FrontierItem(url=doc["url"], source=doc.get("source") or get_domain(doc["url"]))

    def _store_done(self, url: str, status: str, delay: float, error: Optional[str] = None):
        next_time = time.time() + delay
        update = {"status": status, "next_crawl_at": next_time}
        if error:
            update["last_error"] = error
        self.frontier.update_one({"url": url}, {"$set": update})

    # --- crawling ---
    def run(self):
        self.seed_frontier()
        threads: list[threading.Thread] = []
        for i in range(self.workers):
            t = threading.Thread(target=self._worker, args=(i,), daemon=True)
            t.start()
            threads.append(t)
        try:
            while not self._stop.is_set():
                with self._count_lock:
                    if self.max_pages is not None and self.pages_done >= self.max_pages:
                        self._stop.set()
                time.sleep(0.5)
        except KeyboardInterrupt:
            self._stop.set()
        for t in threads:
            t.join()
        log.info("Crawler finished, pages=%d", self.pages_done)

    def _worker(self, wid: int):
        while not self._stop.is_set():
            if self.max_pages is not None:
                with self._count_lock:
                    if self.pages_done >= self.max_pages:
                        break
            item = self._claim_next()
            if not item:
                time.sleep(1.0)
                continue
            try:
                self._process(item)
                with self._count_lock:
                    self.pages_done += 1
                self._store_done(item.url, "pending", self.revisit_after)  # back to queue for recrawl
            except Exception as e:
                log.exception("[worker %d] error on %s: %s", wid, item.url, e)
                self._store_done(item.url, "error", self.revisit_after, str(e))
            time.sleep(self.delay)

    def _process(self, item: FrontierItem):
        if self.respect_robots and not self.robots_cache.can_fetch(item.url):
            log.info("robots.txt forbids %s", item.url)
            return

        resp = self.session.get(item.url, timeout=15)
        if resp.status_code != 200:
            log.warning("HTTP %s for %s", resp.status_code, item.url)
            return
        if "text/html" not in (resp.headers.get("Content-Type") or ""):
            log.info("skip non-html %s", item.url)
            return

        html = resp.text
        content_hash = hashlib.sha1(html.encode("utf-8", "ignore")).hexdigest()
        crawled_at = int(time.time())

        norm_url = normalize_url(item.url)
        existing = self.docs.find_one({"url": norm_url})
        if existing and existing.get("content_hash") == content_hash:
            self.docs.update_one({"_id": existing["_id"]}, {"$set": {"crawled_at": crawled_at}})
        else:
            doc = {
                "url": norm_url,
                "raw_html": html,
                "source": item.source,
                "crawled_at": crawled_at,
                "content_hash": content_hash,
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
            }
            try:
                if existing:
                    self.docs.update_one({"_id": existing["_id"]}, {"$set": doc})
                else:
                    self.docs.insert_one(doc)
            except DuplicateKeyError:
                log.warning("doc already exists: %s", norm_url)

        if self.follow_links:
            self._enqueue_links(item.url, html)

    def _enqueue_links(self, base_url: str, html: str):
        soup = BeautifulSoup(html, "html.parser")
        now = time.time()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full_url = requests.compat.urljoin(base_url, href)
            norm = normalize_url(full_url)
            if not norm.startswith("http"):
                continue
            dom = get_domain(norm)
            if self.allowed_domains and dom not in self.allowed_domains:
                continue
            self._upsert_frontier(norm, dom, now)


def main():
    import sys

    if len(sys.argv) != 2:
        print("Usage: python crawler.py <config.yaml>")
        raise SystemExit(1)
    cfg = load_config(sys.argv[1])
    setup_logging()
    bot = SearchBot(cfg)
    bot.run()


if __name__ == "__main__":
    main()
