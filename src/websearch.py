import argparse
import difflib
import io
import json
import os
import queue
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote, urlencode, urlparse

import primp
from ddgs import DDGS

# Persistent micro-daemon client
try:
    from daemon_client import is_daemon_alive, daemon_search
except ImportError:
    try:
        from src.daemon_client import is_daemon_alive, daemon_search
    except ImportError:
        is_daemon_alive = lambda: False
        daemon_search = lambda *args, **kwargs: None

# Fast local cross-agent cache
try:
    from cache import (
        get_cached_search,
        set_cached_search,
        make_search_key,
        get_last_good_search,
        set_last_good_search,
    )
except ImportError:
    try:
        from src.cache import (
            get_cached_search,
            set_cached_search,
            make_search_key,
            get_last_good_search,
            set_last_good_search,
        )
    except ImportError:
        get_cached_search = lambda key, ttl=1800: None
        set_cached_search = lambda key, results: None
        make_search_key = lambda *args: ""
        get_last_good_search = lambda query, search_type="text": None
        set_last_good_search = lambda query, results, search_type="text": None

# Ensure UTF-8 output for Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# Each engine is called on its own (see _race_backends), so this list is only
# the preferred first wave. Engines unavailable in the installed DDGS version
# are skipped automatically.
FAST_TEXT_BACKENDS = ("yahoo", "duckduckgo", "brave", "startpage", "mojeek")
FAST_NEWS_BACKENDS = ("bing", "yahoo", "duckduckgo")

# DDGS 9.16.1 marks the Bing text engine as disabled, so it is absent from the
# registry. Its class still works, however, and it is the fastest text provider
# here (~0.25 s). Call it directly (as "direct:bing") before the registry ones.
DIRECT_TEXT_ENGINES = ("bing",)

SEARCH_TIMEOUT = 5       # per-engine HTTP timeout passed to DDGS
FIRST_WAVE_WAIT = 2.6    # seconds before giving up on the preferred engines
SECOND_WAVE_WAIT = 3.0   # seconds for the remaining engines / auto
MERGE_GRACE = 0.4        # short window to merge extra engines after a winner

# Query understanding (what Google does implicitly): site hints, typo fixes and
# relevance reranking of results merged from several engines.
SITE_HINTS = {
    "reddit": "reddit.com", "youtube": "youtube.com", "github": "github.com",
    "wikipedia": "wikipedia.org", "steam": "steampowered.com", "amazon": "amazon.",
    "stackoverflow": "stackoverflow.com", "quora": "quora.com", "tiktok": "tiktok.com",
    "facebook": "facebook.com", "x": "x.com", "medium": "medium.com",
}
QUERY_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "at", "is",
    "are", "was", "with", "my", "me", "how", "do", "does", "what", "why", "best",
}
_SPELL_CACHE = {}

# Regex to capture leading dates in search snippets (e.g. "Aug 3, 2026 ·", "2 days ago ·", "2024-05-12 ·")
DATE_PREFIX_REGEX = re.compile(
    r'^((?:\d{1,2}\s+(?:secs?|seconds?|mins?|minutes?|hours?|days?|weeks?|months?|years?)\s+ago)|'
    r'(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})|'
    r'(?:\d{4}-\d{2}-\d{2}))\s*[·•\-\uFFFD\u00B7\s]\s*',
    re.IGNORECASE,
)


def extract_date_and_clean_body(body: str, raw_date: str = None) -> tuple[str, str]:
    """Extract published date if present and clean it from the body snippet."""
    date = raw_date or ""
    clean_body = body or ""

    if date:
        # If ISO format from news API (e.g., 2026-08-16T12:00:00+00:00)
        date = date.split("T")[0] if "T" in date else date
    elif clean_body:
        match = DATE_PREFIX_REGEX.search(clean_body)
        if match:
            date = match.group(1).strip()
            clean_body = DATE_PREFIX_REGEX.sub("", clean_body).strip()

    return date, clean_body


_DATE_UNITS = {
    "sec": 1, "second": 1,
    "min": 60, "minute": 60,
    "hr": 3600, "hour": 3600,
    "day": 86400, "week": 604800,
    "month": 2592000, "year": 31536000,
}
_RELATIVE_DATE_RE = re.compile(
    r'(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?)\s+ago',
    re.IGNORECASE,
)
_MONTH_DATE_RE = re.compile(
    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b',
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(r'\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2})?')


def date_to_timestamp(value):
    """Turn a result date ('35 minutes ago', 'Nov 24, 2026', ISO) into an epoch."""
    if not value:
        return None
    text = str(value).strip()
    now = time.time()

    match = _RELATIVE_DATE_RE.search(text)
    if match:
        unit = match.group(2).lower().rstrip("s")
        if unit == "sec":
            unit = "second"
        elif unit == "min":
            unit = "minute"
        elif unit == "hr":
            unit = "hour"
        multiplier = _DATE_UNITS.get(unit)
        if multiplier:
            return now - int(match.group(1)) * multiplier

    if re.search(r"\byesterday\b", text, re.IGNORECASE):
        return now - 86400
    if re.search(r"\btoday\b", text, re.IGNORECASE):
        return now

    match = _ISO_DATE_RE.search(text)
    if match:
        try:
            return datetime.fromisoformat(
                match.group(0).replace(" ", "T")[:19]
            ).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            pass

    match = _MONTH_DATE_RE.search(text)
    if match:
        raw = match.group(0).replace(",", "")
        for fmt in ("%b %d %Y", "%B %d %Y"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                pass
    return None


def sort_by_date(results):
    """Newest first; results without a parseable date stay at the end."""
    def key(result):
        ts = date_to_timestamp(result.get("date"))
        return (ts is not None, ts or 0)
    return sorted(results, key=key, reverse=True)


def _suggest_spelling(token):
    """Ask autocomplete for a likely correction of a single misspelled word."""
    if token in _SPELL_CACHE:
        return _SPELL_CACHE[token]
    endpoints = (
        "https://duckduckgo.com/ac/?q=" + quote(token) + "&type=list",
        "https://suggestqueries.google.com/complete/search?client=chrome&q=" + quote(token),
    )
    found = ""
    for url in endpoints:
        suggestions = []
        try:
            data = json.loads(primp.Client(impersonate="chrome", timeout=3).get(url).text)
            suggestions = data[1] if isinstance(data, list) and len(data) > 1 else []
        except Exception:
            continue
        for suggestion in suggestions:
            words = re.findall(r"\w+", str(suggestion).lower())
            if not words:
                continue
            candidate = words[0]
            ratio = difflib.SequenceMatcher(None, token, candidate).ratio()
            if candidate != token and ratio >= 0.75 and abs(len(candidate) - len(token)) <= 3:
                found = candidate
                break
        if found or suggestions:
            break
    _SPELL_CACHE[token] = found
    return found


def corrected_queries(query):
    """Return reformulations of a query, e.g. a misspelling fixed via autocomplete."""
    tokens = re.findall(r"\w+", query)
    if not tokens:
        return []
    fixes = {}
    candidates = sorted(
        (t for t in set(tokens) if len(t) >= 6 and t.isalpha()
         and t.lower() not in QUERY_STOPWORDS and t.lower() not in SITE_HINTS),
        key=len, reverse=True,
    )[:2]
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [(token, executor.submit(_suggest_spelling, token.lower())) for token in candidates]
        for token, future in futures:
            suggestion = future.result()
            if suggestion:
                fixes[token] = suggestion
    if not fixes:
        return []
    fixed = " ".join(fixes.get(token, token) for token in tokens)
    return [fixed] if fixed.lower() != query.lower() else []


def detect_site_hint(query):
    """'reddit' in a query behaves like site:reddit.com to users."""
    explicit = re.search(r"\bsite:([^\s]+)", query, re.IGNORECASE)
    if explicit:
        return explicit.group(1).lower()
    lowered = query.lower()
    for word, domain in SITE_HINTS.items():
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return domain
    return None


def query_tokens(query):
    """Content tokens only: site words (`reddit`, `github`, ...) are handled
    separately as a site hint and must not let any page on that site win."""
    cleaned = re.sub(r"\bsite:\S+", " ", query.lower())
    return {
        token for token in re.findall(r"\w+", cleaned)
        if len(token) > 1 and token not in QUERY_STOPWORDS
        and token not in SITE_HINTS and token != "site"
    }


def build_query_variants(query, corrected=None, site_hint=None):
    """Google-style query facets: typo fix, site-scoped search and a quoted
    distinctive-phrase search. They race in parallel and their results are
    merged, so one query can answer several intents at once."""
    base = corrected or query
    variants = []
    if corrected and corrected.lower() != query.lower():
        variants.append(corrected)
    if site_hint and not re.search(r"\bsite:", base, re.IGNORECASE):
        site_base = " ".join(
            token for token in re.findall(r"\w+", base)
            if token.lower() not in SITE_HINTS
        ) or base
        variants.append(f"{site_base} site:{site_hint}")
    tokens = [
        token for token in re.findall(r"\w+", base.lower())
        if len(token) > 1 and token not in QUERY_STOPWORDS and token not in SITE_HINTS
    ]
    if len(tokens) >= 3:
        phrase = " ".join(tokens[-3:])
        remainder = " ".join(tokens[:-3])
        variant = f'"{phrase}" {remainder}'.strip()
        if variant.lower() != base.lower():
            variants.append(variant)

    seen = {query.lower()}
    unique = []
    for variant in variants:
        if variant.lower() not in seen:
            seen.add(variant.lower())
            unique.append(variant)
    return unique[:3]


def _domain_key(url: str) -> str:
    """Group www.reddit.com and old.reddit.com into one domain for diversity."""
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return ""
    parts = [part for part in host.split(".") if part]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _token_weights(rows, query):
    """Rarer query terms are more informative: 'unofficial' should count far
    more than 'gta', which appears in nearly every result."""
    tokens = query_tokens(query)
    total = max(1, len(rows))
    counts = {token: 0 for token in tokens}
    for row in rows:
        text = " ".join(str(row.get(key) or "") for key in ("title", "body", "snippet", "href", "url")).lower()
        for token in tokens:
            if token in text:
                counts[token] += 1
    return {token: 1.0 + 2.0 * (1.0 - counts[token] / total) for token in tokens}


def relevance_score(row, query, site_hint=None, recency=False, weights=None):
    """Score a result against the query that produced it, weighting specific
    terms, coverage and freshness instead of raw keyword presence alone."""
    source_query = row.get("_query") or query
    tokens = query_tokens(source_query)
    title = str(row.get("title") or "").lower()
    snippet = str(row.get("body") or row.get("snippet") or "").lower()
    url = str(row.get("href") or row.get("url") or "").lower()

    score = 0.0
    phrase = " ".join(
        token for token in re.findall(r"\w+", source_query.lower()) if token in tokens
    )
    if phrase and phrase in re.sub(r"\W+", " ", title + " " + snippet):
        score += 6
    for token in tokens:
        weight = weights.get(token, 1.0) if weights else 1.0
        if token in title:
            score += 3 * weight
        if token in snippet:
            score += weight
        if token in url:
            score += 0.5 * weight
    if tokens:
        coverage = sum(1 for t in tokens if t in title or t in snippet) / len(tokens)
        score += coverage * 8
        if coverage < 0.5:
            score -= (0.5 - coverage) * 10
    if weights and tokens:
        rarest = max(tokens, key=lambda t: weights.get(t, 1.0))
        if rarest not in title and rarest not in snippet and rarest not in url:
            score -= 3
    if site_hint:
        domain = urlparse(url).netloc.lower() if url else ""
        if site_hint in domain:
            score += 3  # a tiebreaker, not a blanket pass like the old +14
        elif site_hint in title or site_hint in snippet:
            score += 1
    timestamp = date_to_timestamp(row.get("date") or "")
    if timestamp is not None:
        age_days = max(0.0, (time.time() - timestamp) / 86400)
        # Freshness breaks ties between equally relevant results; it must not
        # outrank a result that actually matches the distinctive query terms.
        score += max(0.0, 6 - age_days / 30) * (2.0 if recency else 0.35)
    return score


def rank_and_dedupe(rows, query, site_hint=None, recency=False, per_domain_cap=3):
    """Sort merged results by relevance, dropping duplicate URLs and capping
    how many results one domain may occupy."""
    weights = _token_weights(rows, query)
    scored = [
        (relevance_score(row, query, site_hint, recency, weights), index, row)
        for index, row in enumerate(rows)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    seen = set()
    domains = {}
    ranked = []
    for _, _, row in scored:
        key = row.get("href") or row.get("url") or row.get("title", "")
        if key in seen:
            continue
        domain = _domain_key(key)
        if domain:
            cap = 4 if site_hint and site_hint in domain else per_domain_cap
            if domains.get(domain, 0) >= cap:
                continue
            domains[domain] = domains.get(domain, 0) + 1
        seen.add(key)
        ranked.append(row)
    return ranked


def available_backends(category: str = "text") -> list[str]:
    """Backends actually enabled in the installed DDGS version."""
    try:
        from ddgs.engines import ENGINES
        return [
            name for name in ENGINES.get(category, {})
            if name not in ("wikipedia", "grokipedia")
        ]
    except Exception:
        return list(FAST_NEWS_BACKENDS if category == "news" else FAST_TEXT_BACKENDS)


def _result_to_dict(row):
    """Convert a DDGS result (dict or dataclass) to a plain dict."""
    if isinstance(row, dict):
        return row
    if hasattr(row, "_asdict"):
        return row._asdict()
    return {
        key: getattr(row, key, "")
        for key in ("title", "href", "url", "body", "date", "source")
    }


def _direct_engine_rows(engine_name, query, kwargs, timeout):
    """Call a disabled-but-working DDGS engine class directly."""
    if engine_name == "bing":
        from ddgs.engines.bing import Bing

        rows = Bing(
            proxy=None, timeout=timeout, verify=True
        ).search(
            query,
            region=kwargs.get("region", "us-en"),
            safesearch="moderate",
            timelimit=kwargs.get("timelimit"),
            page=1,
        )
        out = []
        for row in rows:
            item = _result_to_dict(row)
            # Bing mixes in ad rows with no destination; drop those.
            if item.get("href") or item.get("url"):
                out.append(item)
        return out
    return []


def _race_backends(query, category, backends, kwargs, timeout, wait_seconds, want, extra_queries=()):
    """Race independent single-backend DDGS calls and keep what succeeds.

    DDGS's own multi-backend call can silently discard good results when one
    engine raises first (deedy5/ddgs#427), and any one engine may be
    rate-limited at a given moment. Calling engines separately and taking the
    first successful responses makes both failures harmless: a single bad
    engine can never blank out the others, and the response stays fast because
    we stop as soon as enough results have arrived.
    """
    out = queue.Queue()
    # Reformulated queries (e.g. a typo fix) race on the two fastest engines.
    # They need a slightly longer window so a fast original query cannot fill
    # the quota before the corrected results arrive.
    grace = 0.8 if extra_queries else MERGE_GRACE
    if extra_queries:
        wait_seconds = min(wait_seconds, 1.2)
    tasks = [(query, backend) for backend in backends]
    for extra in extra_queries:
        tasks.extend((extra, backend) for backend in backends[:2])

    def worker(task):
        task_query, backend = task
        try:
            if backend.startswith("direct:"):
                rows = _direct_engine_rows(backend.split(":", 1)[1], task_query, kwargs, timeout)
            else:
                ddgs = DDGS(timeout=timeout)
                if category == "news":
                    rows = list(ddgs.news(task_query, backend=backend, **kwargs))
                    for row in rows:
                        if "url" in row and "href" not in row:
                            row["href"] = row["url"]
                else:
                    rows = list(ddgs.text(task_query, backend=backend, **kwargs))
        except Exception:
            rows = []
        out.put((task_query, rows))

    for task in tasks:
        threading.Thread(target=worker, args=(task,), daemon=True).start()

    deadline = time.monotonic() + wait_seconds
    seen = set()
    collected = []
    pending = len(tasks)
    while pending and time.monotonic() < deadline:
        try:
            task_query, rows = out.get(timeout=max(0.01, deadline - time.monotonic()))
        except queue.Empty:
            break
        pending -= 1
        if not rows:
            continue
        # A winner arrived: give the other engines a brief chance to add more
        # results, but never stretch the response beyond the grace window.
        deadline = min(deadline, time.monotonic() + grace)
        for row in rows:
            if not isinstance(row, dict):
                row = _result_to_dict(row)
            key = row.get("href") or row.get("url") or row.get("title", "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            row["_query"] = task_query
            collected.append(row)
        if len(collected) >= want and not extra_queries:
            break

    return collected


def _live_search(query, max_results, search_type, region, timelimit, backend, recent=False):
    """Fetch raw results using two fast waves of racing engines."""
    kwargs = {"max_results": max_results}
    # Only pass region if non-default to prevent unnecessary DDGS region-routing delay
    if region and region != "wt-wt":
        kwargs["region"] = region
    if timelimit:
        kwargs["timelimit"] = timelimit

    category = "news" if search_type == "news" else "text"
    available = available_backends(category)
    preferred = FAST_NEWS_BACKENDS if category == "news" else FAST_TEXT_BACKENDS

    if backend and backend not in ("fast", "auto", "all"):
        requested = [b.strip() for b in backend.split(",") if b.strip()]
        # An explicit "bing" text request uses the direct engine class, since
        # DDGS 9.16.1 no longer lists it in the text registry.
        primary = [
            f"direct:{b}" if category == "text" and b == "bing" else b
            for b in requested
        ]
        primary = [b for b in primary if b.startswith("direct:") or b in available] or requested
    else:
        direct = [f"direct:{name}" for name in DIRECT_TEXT_ENGINES] if category == "text" else []
        primary = direct + [b for b in preferred if b in available] or available[:3] or ["auto"]

    secondary = [b for b in available if b not in primary]
    if category == "text":
        if not any(b.startswith("direct:") for b in primary):
            secondary.insert(0, f"direct:{DIRECT_TEXT_ENGINES[0]}")
        secondary.append("auto")

    site_hint = detect_site_hint(query)
    extra = []
    if category == "text":
        fixes = corrected_queries(query)
        extra = build_query_variants(query, fixes[0] if fixes else None, site_hint)
    rows = _race_backends(
        query, category, primary, kwargs, SEARCH_TIMEOUT, FIRST_WAVE_WAIT, max_results,
        extra_queries=extra,
    )
    if not rows and secondary:
        rows = _race_backends(
            query, category, secondary, kwargs, SEARCH_TIMEOUT + 2, SECOND_WAVE_WAIT, max_results,
            extra_queries=extra,
        )
    ranked = rank_and_dedupe(
        rows, query, site_hint, recency=recent or bool(timelimit)
    )
    return ranked[:max_results]


def _process_results(raw_results):
    """Normalize DDGS rows into the CLI's result shape."""
    processed_results = []
    for r in raw_results:
        url = r.get("href", "").strip()
        body = r.get("body", "").strip()
        raw_date = r.get("date", "")
        date, clean_body = extract_date_and_clean_body(body, raw_date)

        domain = ""
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "")
            except Exception:
                domain = ""

        processed_results.append({
            "title": r.get("title", "").strip(),
            "url": url,
            "site": domain,
            "date": date if date else None,
            "source": r.get("source", ""),
            "snippet": clean_body,
        })
    return processed_results


def _fallback_results(query):
    """Last-resort direct search links, so a query never returns nothing."""
    encoded = urlencode({"q": query})
    links = (
        ("Google", "https://www.google.com/search?" + encoded, "google.com"),
        ("Bing", "https://www.bing.com/search?" + encoded, "bing.com"),
        ("DuckDuckGo", "https://duckduckgo.com/?" + encoded, "duckduckgo.com"),
    )
    return [
        {
            "title": f'{name} search for "{query}"',
            "url": url,
            "site": site,
            "date": None,
            "source": "search-fallback",
            "snippet": "Live search is temporarily unavailable. Open this link to run the search directly.",
            "fallback": True,
        }
        for name, url, site in links
    ]


def search(
    query: str,
    max_results: int = 10,
    search_type: str = "text",
    region: str = None,
    timelimit: str = None,
    backend: str = "fast",
    no_cache: bool = False,
    recent: bool = False,
):
    def finish(results):
        return sort_by_date(results) if recent else results

    cache_key = make_search_key(query, search_type, max_results, region, backend, timelimit, recent)
    if not no_cache:
        cached = get_cached_search(cache_key)
        if cached:
            return finish(cached)

    # Persistent micro-daemon path (warm pooled HTTP client). Only accept a
    # non-empty result: an empty daemon result must fall through to the local
    # resilient search instead of ending the query with no content. Recency
    # sorting is done here, so bypass the daemon for those requests.
    if not os.environ.get("INSIDE_DAEMON") and is_daemon_alive() and not timelimit and not recent:
        daemon_res = daemon_search(
            query=query,
            max_results=max_results,
            search_type=search_type,
            region=region,
            backend=backend,
            no_cache=no_cache,
        )
        if daemon_res:
            return finish(daemon_res)

    try:
        raw_results = _live_search(
            query, max_results, search_type, region, timelimit, backend, recent
        )
    except Exception:
        raw_results = []

    processed_results = _process_results(raw_results)
    if processed_results:
        if not no_cache:
            set_cached_search(cache_key, processed_results)
            set_last_good_search(query, processed_results, search_type)
        return finish(processed_results)

    # Every live engine failed. Serve the last successful results for this
    # query (any age) before resorting to direct search links.
    if not no_cache:
        stale = get_last_good_search(query, search_type)
        if stale:
            for result in stale:
                result["stale"] = True
            return finish(stale[:max_results])

    return finish(_fallback_results(query)[:max_results])


def _output_notice(results):
    if any(r.get("fallback") for r in results):
        print("* Live search is unavailable right now — showing direct search links instead. *\n")
    elif any(r.get("stale") for r in results):
        print("* Live search is unavailable right now — showing the last successful results for this query. *\n")


def print_clean_list(results, query: str):
    if not results:
        print(f"\nNo results found for: \"{query}\"\n")
        return

    _output_notice(results)
    print(f"\nSearch results for \"{query}\" ({len(results)} results):\n")

    for idx, r in enumerate(results, 1):
        print(f"[{idx}]")
        print(f"Title:   {r['title']}")
        print(f"URL:     {r['url']}")
        if r.get("site"):
            print(f"Site:    {r['site']}")
        if r.get("source"):
            print(f"Source:  {r['source']}")
        if r.get("date"):
            print(f"Date:    {r['date']}")
        if r.get("snippet"):
            print(f"Snippet: {r['snippet']}")
        print()  # Blank line separator between items


def print_markdown_results(results, query: str):
    _output_notice(results)
    print(f"# Search Results: {query}\n")
    for idx, r in enumerate(results, 1):
        print(f"### {idx}. [{r['title']}]({r['url']})")
        if r.get("date") or r.get("site"):
            meta = []
            if r.get("site"):
                meta.append(f"**Site:** {r['site']}")
            if r.get("date"):
                meta.append(f"**Date:** {r['date']}")
            print(f"- {' | '.join(meta)}")
        if r.get("snippet"):
            print(f"> {r['snippet']}\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Search the web with clean, structured formatted results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  websearch "python asyncio tutorial"
  websearch "python web scraping" 5
  websearch "ai technology" --news
  websearch "ai technology" --news --recent
  websearch "fastapi" --json
"""
    )
    parser.add_argument("queries", nargs="*", help="Search query string(s) (supports multiple for parallel batch search)")
    parser.add_argument(
        "-n", "--num",
        dest="max_results",
        type=int,
        default=10,
        help="Maximum number of results to fetch (default: 10)",
    )
    parser.add_argument(
        "--news",
        action="store_true",
        help="Search news specifically (includes date and news source)",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["list", "markdown", "json"],
        default="list",
        help="Output format: list (default), markdown, json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Shortcut for JSON output format",
    )
    parser.add_argument(
        "--markdown", "--md",
        action="store_true",
        dest="markdown",
        help="Shortcut for Markdown output format",
    )
    parser.add_argument(
        "-r", "--region",
        default=None,
        help="Search region (e.g. us-en, uk-en, wt-wt; default: wt-wt)",
    )
    parser.add_argument(
        "-t", "--time",
        choices=["d", "w", "m", "y"],
        default=None,
        help="Time filter (d=day, w=week, m=month, y=year)",
    )
    parser.add_argument(
        "-b", "--backend",
        default="fast",
        help="Search backend: 'fast' (default, optimized web engines), 'auto', or comma-separated engine names",
    )
    parser.add_argument(
        "--no-cache", "--fresh",
        dest="no_cache",
        action="store_true",
        help="Bypass local cache and perform live search",
    )
    parser.add_argument(
        "--recent",
        action="store_true",
        help="Prefer the newest results: ask engines for the last week (unless -t is given) and sort by date, newest first",
    )

    args = parser.parse_args()

    raw_queries = args.queries
    if not raw_queries:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    # Check if the last positional argument is an integer max_results (e.g. websearch "foo bar" 5)
    if len(raw_queries) > 1 and raw_queries[-1].isdigit() and args.max_results == 10:
        args.max_results = int(raw_queries[-1])
        queries = raw_queries[:-1]
    else:
        queries = raw_queries

    args.queries = queries

    if args.recent and args.time is None:
        args.time = "w"

    if args.json:
        args.format = "json"
    elif args.markdown:
        args.format = "markdown"

    return args


def main():
    args = parse_args()
    search_type = "news" if args.news else "text"

    if len(args.queries) == 1:
        query = args.queries[0]
        try:
            results = search(
                query=query,
                max_results=args.max_results,
                search_type=search_type,
                region=args.region,
                timelimit=args.time,
                backend=args.backend,
                no_cache=args.no_cache,
                recent=args.recent,
            )
        except Exception as e:
            print(f"Search failed: {e}", file=sys.stderr)
            sys.exit(1)

        # Standard console output
        if args.format == "json":
            print(json.dumps(results, indent=2, ensure_ascii=False))
        elif args.format == "markdown":
            print_markdown_results(results, query)
        else:
            print_clean_list(results, query)
        return

    # Multi-query batch parallel execution (Option D)
    def run_one(q):
        try:
            return q, search(
                query=q,
                max_results=args.max_results,
                search_type=search_type,
                region=args.region,
                timelimit=args.time,
                backend=args.backend,
                no_cache=args.no_cache,
                recent=args.recent,
            ), None
        except Exception as err:
            return q, [], str(err)

    max_workers = min(len(args.queries), 6)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        batch_results = list(executor.map(run_one, args.queries))

    if args.format == "json":
        out = {q: res for q, res, err in batch_results}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.format == "markdown":
        for idx, (q, res, err) in enumerate(batch_results):
            if idx > 0:
                print("\n---\n")
            if err:
                print(f"# Search Results: {q}\n\n*Failed: {err}*\n")
            else:
                print_markdown_results(res, q)
    else:
        for idx, (q, res, err) in enumerate(batch_results):
            if idx > 0:
                print("\n" + "=" * 80 + "\n")
            if err:
                print(f"\nSearch failed for \"{q}\": {err}\n")
            else:
                print_clean_list(res, q)


if __name__ == "__main__":
    main()
