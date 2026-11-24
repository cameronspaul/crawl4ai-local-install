"""Listing parser for WeBuy / CeX search result pages.

The captured ``research/webuy.html`` is a Nuxt application shell (results are
loaded client side), so the selectors below were derived from the component
class names present in the real CSS bundle shipped in that page:
``.xcardproduct`` cards with ``.xcardproduct-title``, ``.xcardproduct-main-price``
/ ``.cash-price`` and ``.xcardproduct-subtitle``, plus the older
``.cx-card-product`` / ``.search-product-card`` card markup.  The parser also
handles JSON-LD ``Product`` entries when a server-rendered page provides them.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from lxml import html as lxml_html

from .base import (
    absolute_url,
    dedupe,
    first_attr,
    first_text,
    make_listing,
    normalise_price,
    parse_jsonld,
)

SITE_NAME = "WeBuy"
DOMAINS = ("uk.webuy.com", "webuy.com")

#: Search results are rendered client-side, so the fast HTTP tier only returns
#: an empty Nuxt shell. Ask the CLI to go straight to the stealth browser.
FORCE_STEALTH = True


def build_search_url(query: str) -> str:
    """Return the WeBuy search URL for *query*."""
    return "https://uk.webuy.com/search?stext=" + quote_plus(query)


# Class-token aware so ".xcardproduct-container" does not match ".xcardproduct".
_CARD_XPATHS = (
    '//div[contains(concat(" ", normalize-space(@class), " "), " xcardproduct ")]',
    '//div[contains(concat(" ", normalize-space(@class), " "), " cx-card-product ")]',
    '//div[contains(concat(" ", normalize-space(@class), " "), " search-product-card ")]',
)

_TITLE_XPATHS = (
    './/*[contains(concat(" ", normalize-space(@class), " "), " xcardproduct-title ")]',
    './/*[contains(concat(" ", normalize-space(@class), " "), " card-title ")]',
    ".//h2",
    ".//h3",
    './/a[contains(@href, "product-detail")]',
)

_LINK_XPATHS = (
    './/a[contains(concat(" ", normalize-space(@class), " "), " xcardproduct-title-link ")]/@href',
    './/a[ancestor::*[contains(concat(" ", normalize-space(@class), " "), " xcardproduct-title ")]]/@href',
    './/a[ancestor::*[contains(concat(" ", normalize-space(@class), " "), " card-title ")]]/@href',
    './/a[contains(@href, "product-detail")]/@href',
    './/a[contains(@href, "/product")]/@href',
)

_PRICE_XPATHS = (
    './/*[contains(concat(" ", normalize-space(@class), " "), " xcardproduct-main-price ")]',
    './/*[contains(concat(" ", normalize-space(@class), " "), " cash-price ")]',
    './/*[contains(concat(" ", normalize-space(@class), " "), " price-tag ")]',
    './/*[contains(concat(" ", normalize-space(@class), " "), " product-prices ")]',
)

_NOTE_XPATHS = (
    './/*[contains(concat(" ", normalize-space(@class), " "), " cx-out-of-stock ")]',
    './/*[contains(concat(" ", normalize-space(@class), " "), " xcardproduct-subtitle ")]',
    './/*[contains(concat(" ", normalize-space(@class), " "), " card-subtitle ")]',
)


#: Sections that hold "trending"/"recommended" products rather than the actual
#: search results. On a no-match search, WeBuy still renders a full carousel of
#: unrelated products; those must never be reported as listings for the query.
_NON_RESULT_SECTIONS = (
    "trending-product",
    "card-carousel",
    "carousel-navigation",
    "recommend",
    "related-product",
    "recently-viewed",
    "popular-product",
    "wishlist",
)

_NO_RESULTS_PHRASES = (
    "couldn't find",
    "could not find",
    "no results",
    "no products found",
    "nothing found",
    "0 results",
)


def _is_recommendation(card) -> bool:
    """True when a card lives inside a carousel/recommendation section."""
    for node in card.xpath("ancestor::*"):
        classes = (node.get("class") or "").lower().split()
        if any(marker in token for token in classes for marker in _NON_RESULT_SECTIONS):
            return True
    return False


def _no_results(tree) -> bool:
    """Detect WeBuy's friendly 'we couldn't find X' heading."""
    text = " ".join(tree.xpath("//h1//text() | //h2//text()")).lower()
    return any(phrase in text for phrase in _NO_RESULTS_PHRASES)


def _from_jsonld(page_html: str, page_url: str) -> list[dict]:
    """Fallback for pages that expose products only as JSON-LD."""
    out: list[dict] = []
    for entry in parse_jsonld(page_html):
        if str(entry.get("@type", "")).lower() != "product":
            continue
        title = first_text(entry.get("name"))
        offers = entry.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers and isinstance(offers[0], dict) else {}
        price = normalise_price(offers.get("price")) if isinstance(offers, dict) else ""
        url = absolute_url(page_url, entry.get("url") if isinstance(entry, dict) else "")
        if title or price or url:
            out.append(make_listing(title=title, price=price, url=url))
    return out


def parse(html: str, page_url: str) -> list[dict]:
    """Return product listings found in WeBuy search HTML.

    Missing fields become empty strings; the function never raises on malformed
    or unexpected markup.
    """
    if not html:
        return []
    try:
        tree = lxml_html.fromstring(html)
    except Exception:
        return []

    if _no_results(tree):
        return []

    listings: list[dict] = []
    try:
        cards: list = []
        for xpath in _CARD_XPATHS:
            cards.extend(tree.xpath(xpath))
        for card in cards:
            if _is_recommendation(card):
                continue
            try:
                title = first_text(card, *_TITLE_XPATHS)
                href = first_attr(card, "href", *_LINK_XPATHS)
                price = first_text(card, *_PRICE_XPATHS)
                note = first_text(card, *_NOTE_XPATHS)
                if not (title or price or href):
                    continue
                listings.append(
                    make_listing(
                        title=title,
                        price=price,
                        url=absolute_url(page_url, href),
                        note=note,
                    )
                )
            except Exception:
                continue
    except Exception:
        listings = []

    if not listings:
        try:
            listings = _from_jsonld(html, page_url)
        except Exception:
            listings = []
    return dedupe(listings)
