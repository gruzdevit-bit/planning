import os
import threading
import time
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime

import requests
from flask import Blueprint, jsonify

bp = Blueprint("news_api", __name__)

NEWS_ERROR = "Не удалось загрузить новости"
LIMIT = 10

_cache = {"ts": 0.0, "items": None}
_lock = threading.Lock()


class NewsError(Exception):
    pass


def reset_cache():
    with _lock:
        _cache["ts"] = 0.0
        _cache["items"] = None


def parse_rss(content):
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise NewsError(str(exc))
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if not title or not link.startswith("http"):
            continue
        published = None
        if pub:
            try:
                dt = parsedate_to_datetime(pub)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                published = dt.isoformat()
            except (TypeError, ValueError):
                published = None
        items.append({"title": title, "url": link, "published": published})
        if len(items) >= LIMIT:
            break
    if not items:
        raise NewsError("empty feed")
    return items


def fetch_news():
    url = os.environ.get("NEWS_URL", "https://lenta.ru/rss/news")
    ttl = float(os.environ.get("NEWS_TTL", "300"))
    timeout = float(os.environ.get("NEWS_TIMEOUT", "5"))
    with _lock:
        if _cache["items"] is not None and time.time() - _cache["ts"] < ttl:
            return _cache["items"]
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Daily planner)"},
            )
            resp.raise_for_status()
            items = parse_rss(resp.content)
        except (requests.RequestException, NewsError) as exc:
            raise NewsError(str(exc))
        _cache["items"] = items
        _cache["ts"] = time.time()
        return items


@bp.get("/api/news")
def get_news():
    try:
        return jsonify(fetch_news())
    except NewsError:
        return jsonify({"error": NEWS_ERROR}), 502
