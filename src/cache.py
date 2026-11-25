import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing
from typing import Any, Optional

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_DIR, ".cache")
DB_PATH = os.path.join(CACHE_DIR, "fast_cache.db")

try:
    from stealth import is_usable_content
except ImportError:
    try:
        from src.stealth import is_usable_content
    except ImportError:
        def is_usable_content(text, min_words=20):
            return bool(text) and len(text.strip()) >= 40

#: Bump whenever the shape of cached Markdown changes so old-format entries
#: are never served to a client expecting the new layout. Bumped to 3 to
#: invalidate challenge/thin pages cached by earlier versions.
MARKDOWN_CACHE_VERSION = 3


def make_markdown_cache_key(url: str) -> str:
    """Namespace a URL's Markdown cache entry by output format version."""
    return f"mdv{MARKDOWN_CACHE_VERSION}:{url}"


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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS search_last_good (
            query_key TEXT PRIMARY KEY,
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
        with closing(_get_db()) as conn:
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
    """Store scraped markdown in local cache.

    Wall and empty-shell results are refused so a transient bot challenge can
    never poison the cache for the next two hours.
    """
    if not content or len(content.strip()) < 40:
        return
    if not is_usable_content(content, min_words=5 if url.startswith("html:") else 20):
        return
    try:
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        with closing(_get_db()) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scrapes (url_hash, url, content, timestamp) VALUES (?, ?, ?, ?)",
                (url_hash, url, content, time.time()),
            )
            conn.commit()
    except Exception:
        pass


def get_cached_html(url: str, ttl: float = 900) -> Optional[str]:
    """Retrieve cached raw HTML for a URL if younger than ttl seconds.

    Raw HTML and Markdown share the same cache table, so HTML uses a prefixed
    key. This keeps a property-page render reusable without letting the
    Markdown cache hand an HTML shell back to ``scrape_single``. The default
    TTL is deliberately short (15 minutes) because these pages carry prices.
    """
    return get_cached_scrape("html:" + url, ttl=ttl)


def set_cached_html(url: str, content: str) -> None:
    """Store rendered raw HTML in the local cache."""
    set_cached_scrape("html:" + url, content)


def make_search_key(query: str, search_type: str, max_results: int, region: str = None, backend: str = "fast", timelimit: str = None, recent: bool = False) -> str:
    # Time-filtered and recency-ranked searches must never reuse an unfiltered
    # cache entry (or vice versa) — otherwise -t w / --recent silently change.
    raw = f"{query.strip().lower()}|{search_type}|{max_results}|{region or ''}|{backend}|{timelimit or ''}|{bool(recent)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_search(key: str, ttl: float = 1800) -> Optional[list[dict[str, Any]]]:
    """Retrieve cached search results if younger than ttl seconds (default 30 mins)."""
    try:
        with closing(_get_db()) as conn:
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
        with closing(_get_db()) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO searches (query_hash, results, timestamp) VALUES (?, ?, ?)",
                (key, results_json, time.time()),
            )
            conn.commit()
    except Exception:
        pass


def make_last_good_key(query: str, search_type: str = "text") -> str:
    """Key for the last successful search of a query, independent of backend/options.

    Used as the "always a response" fallback when every live engine is down.
    """
    raw = f"{query.strip().lower()}|{search_type}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_last_good_search(query: str, search_type: str = "text") -> Optional[list[dict[str, Any]]]:
    """Return the last successful results for a query, regardless of age."""
    try:
        key = make_last_good_key(query, search_type)
        with closing(_get_db()) as conn:
            cur = conn.execute(
                "SELECT results FROM search_last_good WHERE query_key = ?", (key,)
            )
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
    except Exception:
        pass
    return None


def set_last_good_search(query: str, results: list[dict[str, Any]], search_type: str = "text") -> None:
    """Remember the last successful results for a query (no expiry)."""
    if not results:
        return
    try:
        key = make_last_good_key(query, search_type)
        with closing(_get_db()) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO search_last_good (query_key, results, timestamp) VALUES (?, ?, ?)",
                (key, json.dumps(results, ensure_ascii=False), time.time()),
            )
            conn.commit()
    except Exception:
        pass
