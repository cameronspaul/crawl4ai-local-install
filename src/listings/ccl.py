"""Listing parser for CCL Computers search result pages."""
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
)

SITE_NAME = "CCL"
DOMAINS = ("www.cclonline.com", "cclonline.com")


def build_search_url(query: str) -> str:
    """Return the CCL search URL for *query*."""
    return "https://www.cclonline.com/search?query=" + quote_plus(query)


# Verified against research/ccl.html: repeated div.col.product-preview-card
# cards (and the equivalent div.col.product-preview-row list view).
_CARD_XPATHS = (
    '//div[contains(concat(" ", normalize-space(@class), " "), " product-preview-card ")]',
    '//div[contains(concat(" ", normalize-space(@class), " "), " product-preview-row ")]',
    '//div[@data-productid][.//a[contains(@href, "/")]]',
)

_TITLE_XPATHS = (
    './/a[contains(concat(" ", normalize-space(@class), " "), " h5 ")]',
    './/a[contains(concat(" ", normalize-space(@class), " "), " text-white ")]',
    './/h5',
    './/h3',
)

_LINK_XPATHS = (
    './/a[contains(concat(" ", normalize-space(@class), " "), " h5 ")]/@href',
    './/a[contains(concat(" ", normalize-space(@class), " "), " text-white ")]/@href',
    './/a[contains(@href, "/")]/@href',
)

# The price is split across a parent span ("£423.") and a small child span
# ("99"), so use string() to join descendant text without adding spaces.
_PRICE_XPATHS = (
    # List view: span.fw-bold.h3 -> "£423." + nested span.fw-bold.h5 -> "99".
    'string(.//span[contains(concat(" ", normalize-space(@class), " "), " fw-bold ")]'
    '[contains(concat(" ", normalize-space(@class), " "), " h3 ")])',
    # Grid view: span.fw-bold.h5 -> "£423." + nested span.fw-bold.h6 -> "99".
    'string(.//span[contains(concat(" ", normalize-space(@class), " "), " fw-bold ")]'
    '[contains(concat(" ", normalize-space(@class), " "), " h5 ")])',
    'string(.//span[contains(concat(" ", normalize-space(@class), " "), " text-primary ")])',
    './/span[contains(concat(" ", normalize-space(@class), " "), " price ")]',
    './/*[contains(concat(" ", normalize-space(@class), " "), " price ")]',
)

_NOTE_XPATHS = (
    './/span[contains(@class, "delivery-text")]',
    './/span[contains(concat(" ", normalize-space(@class), " "), " text-gray-400 ")]',
)


def _joined_text(node, *xpaths: str) -> str:
    """Return the first non-empty XPath string result (used for split prices).

    Unlike first_text(), this supports XPath ``string(...)`` / ``normalize-space``
    expressions, which return a single string instead of a node list.
    """
    for xpath in xpaths:
        try:
            result = node.xpath(xpath)
        except Exception:
            continue
        if isinstance(result, str):
            value = normalise_price(result)
            if value:
                return value
        elif isinstance(result, list):
            for item in result:
                value = normalise_price(item)
                if value:
                    return value
    return ""


def parse(html: str, page_url: str) -> list[dict]:
    """Return product listings found in CCL search HTML."""
    if not html:
        return []
    try:
        tree = lxml_html.fromstring(html)
    except Exception:
        return []

    listings: list[dict] = []
    try:
        seen_nodes: set[int] = set()
        cards: list = []
        for xpath in _CARD_XPATHS:
            for card in tree.xpath(xpath):
                if id(card) not in seen_nodes:
                    seen_nodes.add(id(card))
                    cards.append(card)
        for card in cards:
            try:
                title = first_text(card, *_TITLE_XPATHS)
                href = first_attr(card, "href", *_LINK_XPATHS)
                price = _joined_text(card, *_PRICE_XPATHS)
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
    return dedupe(listings)
