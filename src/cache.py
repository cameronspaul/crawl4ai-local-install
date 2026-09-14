import hashlib
import json
import os
import sqlite3
import time
from typing import Any, Optional

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_DIR, ".cache")
DB_PATH = os.path.join(CACHE_DIR, "fast_cache.db")


def _get_db():
    os.makedirs(CACHE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scrapes (
            url_hash TEXT PRIMARY KEY,
            url TEXT,
            content TEXT,
            timestamp REAL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS searches (
            query_hash TEXT PRIMARY KEY,
            results TEXT,
            timestamp REAL
        );
        """
    )
    return conn


def get_cached_scrape(url: str, ttl: float = 7200) -> Optional[str]:
    """Retrieve cached markdown for a URL if younger than ttl seconds (default 2 hours)."""
    try:
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        with _get_db() as conn:
            cur = conn.execute(
                "SELECT content, timestamp FROM scrapes WHERE url_hash = ?", (url_hash,)
            )
            row = cur.fetchone()
            if row:
                content, ts = row
                if time.time() - ts < ttl:
                    return content
    except Exception:
        pass
    return None


def set_cached_scrape(url: str, content: str) -> None:
    """Store scraped markdown in local cache."""
    if not content or len(content.strip()) < 40:
        return
    try:
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        with _get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scrapes (url_hash, url, content, timestamp) VALUES (?, ?, ?, ?)",
                (url_hash, url, content, time.time()),
            )
            conn.commit()
    except Exception:
        pass


def make_search_key(query: str, search_type: str, max_results: int, region: str = None, backend: str = "fast") -> str:
    raw = f"{query.strip().lower()}|{search_type}|{max_results}|{region or ''}|{backend}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_search(key: str, ttl: float = 1800) -> Optional[list[dict[str, Any]]]:
    """Retrieve cached search results if younger than ttl seconds (default 30 mins)."""
    try:
        with _get_db() as conn:
            cur = conn.execute(
                "SELECT results, timestamp FROM searches WHERE query_hash = ?", (key,)
            )
            row = cur.fetchone()
            if row:
                results_json, ts = row
                if time.time() - ts < ttl:
                    return json.loads(results_json)
    except Exception:
        pass
    return None


def set_cached_search(key: str, results: list[dict[str, Any]]) -> None:
    """Store search results in local cache."""
    if not results:
        return
    try:
        results_json = json.dumps(results, ensure_ascii=False)
        with _get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO searches (query_hash, results, timestamp) VALUES (?, ?, ?)",
                (key, results_json, time.time()),
            )
            conn.commit()
    except Exception:
        pass
