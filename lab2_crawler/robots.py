from __future__ import annotations

from typing import Dict
from urllib.robotparser import RobotFileParser

import requests

from url_utils import get_domain


class RobotsCache:
    def __init__(self, session: requests.Session, user_agent: str):
        self.session = session
        self.user_agent = user_agent
        self._cache: Dict[str, RobotFileParser] = {}

    def _load_robots(self, domain: str) -> RobotFileParser:
        robots_url = f"https://{domain}/robots.txt"
        rp = RobotFileParser()
        try:
            rp.set_url(robots_url)
            rp.read()
        except Exception:
            pass
        return rp

    def can_fetch(self, url: str) -> bool:
        domain = get_domain(url)
        if domain not in self._cache:
            self._cache[domain] = self._load_robots(domain)
        rp = self._cache[domain]
        return rp.can_fetch(self.user_agent, url)
