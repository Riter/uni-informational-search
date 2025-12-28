from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set

import yaml


@dataclass
class DbConfig:
    uri: str
    database: str
    collection: str = "documents"


@dataclass
class LogicConfig:
    urls_jsonl: Optional[str] = None
    start_urls: List[str] = field(default_factory=list)
    allowed_domains: Set[str] = field(default_factory=set)
    request_delay_sec: float = 1.0
    recrawl_interval_sec: int = 86400
    max_pages: Optional[int] = None
    worker_count: int = 4
    user_agent: str = "MiniSearchBot/0.1"
    respect_robots: bool = True
    follow_links: bool = False


@dataclass
class AppConfig:
    db: DbConfig
    logic: LogicConfig


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    db_raw = raw.get("db") or {}
    logic_raw = raw.get("logic") or {}

    allowed_domains = {str(d).lower() for d in (logic_raw.get("allowed_domains") or [])}

    db_cfg = DbConfig(
        uri=db_raw["uri"],
        database=db_raw["database"],
        collection=db_raw.get("collection", "documents"),
    )
    logic_cfg = LogicConfig(
        urls_jsonl=logic_raw.get("urls_jsonl"),
        start_urls=list(logic_raw.get("start_urls") or []),
        allowed_domains=allowed_domains,
        request_delay_sec=float(logic_raw.get("request_delay_sec", 1.0)),
        recrawl_interval_sec=int(logic_raw.get("recrawl_interval_sec", 86400)),
        max_pages=int(logic_raw["max_pages"]) if logic_raw.get("max_pages") is not None else None,
        worker_count=int(logic_raw.get("worker_count", 4)),
        user_agent=logic_raw.get("user_agent", "MiniSearchBot/0.1"),
        respect_robots=bool(logic_raw.get("respect_robots", True)),
        follow_links=bool(logic_raw.get("follow_links", False)),
    )
    return AppConfig(db=db_cfg, logic=logic_cfg)
