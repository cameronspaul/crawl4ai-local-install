"""Shared helpers for the retailer listing parsers.

Every site module in :mod:`src.listings` exposes the same four things::

    SITE_NAME                       e.g. "Scan"
    DOMAINS                         tuple of hostnames it can handle
    build_search_url(query) -> str
    parse(html, page_url) -> list[dict]

Each returned listing dict uses these keys (all strings)::

    title   product name
    price   human-readable price, e.g. "£109.99" ("" when not shown)
    url     absolute product URL ("" when it cannot be resolved)
    note    short extra info: stock, delivery, seller, rating ... ("" if none)

Keep parsers defensive: real retailer HTML changes constantly, so never raise
on a missing field — return an empty string for it instead.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urljoin

_WHITESPACE = re.compile(r"\s+")

#: Notes that mean a product cannot actually be bought. Kept deliberately
#: narrow so ordinary text like "4.6 out of 5 stars" is never matched.
OUT_OF_STOCK = re.compile(
    r"out\s+of\s+stock|sold\s+out|unavailable|not\s+available|"
    r"currently\s+unavailable|temporarily\s+out|zero\s+stock|0\s+in\s+stock",
    re.IGNORECASE,
)


def clean_text(value) -> str:
    """Collapse whitespace and strip. Accepts strings, lxml elements or None."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = " ".join(value.itertext())
    return _WHITESPACE.sub(" ", value).strip()


def absolute_url(base_url: str, href: str | None) -> str:
    """Resolve a possibly-relative href against the page URL."""
    href = clean_text(href)
    if not href or href.startswith(("javascript:", "#", "mailto:")):
        return ""
    return urljoin(base_url, href)


def normalise_price(value) -> str:
    """Tidy a price string without inventing a currency symbol.

    "£1,099.00" stays "£1,099.00"; " 109.99 " becomes "109.99".
    Prices split across elements ("£" + "109.99") should be joined by the
    parser before calling this.
    """
    text = clean_text(value)
    if not text:
        return ""
    # Drop common decorative separators used between currency and amount.
    text = re.sub(r"(?<=\S)\s*[\u00a0\u202f]\s*", " ", text)
    return text.strip()


def first_text(node, *xpaths: str) -> str:
    """Return the first non-empty text matched by any of the XPath expressions."""
    for xpath in xpaths:
        try:
            found = node.xpath(xpath)
        except Exception:
            continue
        for item in found:
            text = clean_text(item)
            if text:
                return text
    return ""


def first_attr(node, attr: str, *xpaths: str) -> str:
    """Return the first non-empty attribute value matched by the XPaths."""
    for xpath in xpaths:
        try:
            found = node.xpath(xpath)
        except Exception:
            continue
        for item in found:
            if isinstance(item, str):
                value = item.strip()
            else:
                value = clean_text(item.get(attr))
            if value:
                return value
    return ""


def dedupe(listings: list[dict]) -> list[dict]:
    """Remove listings with the same (title, price), keeping first occurrence."""
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for item in listings:
        key = (item.get("title", "").lower(), item.get("price", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def parse_jsonld(html: str) -> list[dict]:
    """Flatten all JSON-LD blocks on a page into a list of dictionaries."""
    try:
        from lxml import html as lxml_html

        tree = lxml_html.fromstring(html)
    except Exception:
        return []
    out: list[dict] = []
    for raw in tree.xpath("//script[@type='application/ld+json']/text()"):
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if isinstance(data, dict):
            data = data.get("@graph", [data])
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    out.append(entry)
    return out


#: Retailers use absurd values as "no price" placeholders. Scan, for example,
#: renders 999999.00 for items it cannot quote, often with no stock note at all.
_PLACEHOLDER_PRICE = re.compile(r"^9{5,}(?:\.0+)?$")


def has_real_price(price: str) -> bool:
    """True when *price* contains a plausible, non-placeholder amount.

    Rejects empty/"POA" text, zero, and sentinel values such as 99999 / 999999
    (with or without .00). A plain numeric check is not enough: Scan cards with
    `data-price="999999.00"` show no out-of-stock note.
    """
    text = price or ""
    match = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    if not match:
        return False
    amount = match.group().replace(",", "")
    if _PLACEHOLDER_PRICE.fullmatch(amount):
        return False
    try:
        value = float(amount)
    except ValueError:
        return False
    return 0 < value < 99999


def is_available(listing: dict) -> bool:
    """True only for listings that show a real price and are not out of stock.

    Stock status is read from the note field; product names and ratings are
    never used for that decision. Prices are checked separately because some
    sites encode "unavailable" purely as an implausible price.
    """
    if not has_real_price(listing.get("price") or ""):
        return False
    if OUT_OF_STOCK.search(listing.get("note") or ""):
        return False
    return True


def make_listing(title: str = "", price: str = "", url: str = "", note: str = "") -> dict:
    """Build a listing dict with all four guaranteed keys."""
    return {
        "title": clean_text(title),
        "price": normalise_price(price),
        "url": url,
        "note": clean_text(note),
    }
