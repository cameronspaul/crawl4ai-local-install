"""Retailer-specific listing parsers.

Each module exposes ``SITE_NAME``, ``DOMAINS``, ``build_search_url(query)`` and
``parse(html, page_url)``. See :mod:`src.listings.base` for the contract.
"""
from __future__ import annotations

from urllib.parse import urlparse

from . import amazon, ccl, ebuyer, gpused, overclockers, scan, webuy  # noqa: F401

MODULES = (scan, overclockers, ebuyer, amazon, webuy, gpused, ccl)
SITES = {module.SITE_NAME: module for module in MODULES}

# Friendly aliases so users can type "scan", "scan.co.uk" or "Scan Computers".
_ALIASES: dict[str, object] = {}
for _module in MODULES:
    _ALIASES[_module.SITE_NAME.lower()] = _module
    for _domain in _module.DOMAINS:
        _ALIASES[_domain.lower()] = _module
        _ALIASES[_domain.lower().removeprefix("www.")] = _module


def detect_site(value: str):
    """Resolve a site name, domain, or full search URL to a parser module.

    Returns ``None`` when nothing matches.
    """
    key = value.strip().lower()
    if key in _ALIASES:
        return _ALIASES[key]
    try:
        host = (urlparse(value if "://" in value else "https://" + value).hostname or "").lower()
    except Exception:
        return None
    if host in _ALIASES:
        return _ALIASES[host]
    host = host.removeprefix("www.")
    return _ALIASES.get(host)


def parse_listings(module, html: str, page_url: str) -> list[dict]:
    """Run a site's parser and guarantee the standard listing keys."""
    from .base import is_available, make_listing

    try:
        raw = module.parse(html, page_url) or []
    except Exception:
        raw = []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        listing = make_listing(
            title=item.get("title", ""),
            price=item.get("price", ""),
            url=item.get("url", ""),
            note=item.get("note", ""),
        )
        # Only show things the user can actually buy: a real price and no
        # out-of-stock marker. Applied here so every retailer behaves the same.
        if not is_available(listing):
            continue
        out.append(listing)
    return out


__all__ = ["SITES", "MODULES", "detect_site", "parse_listings"]
