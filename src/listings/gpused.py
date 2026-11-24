"""Listing parser for GPUsed (Shopify) collection and search pages."""
from __future__ import annotations

from urllib.parse import quote_plus

from lxml import html as lxml_html

from .base import absolute_url, dedupe, first_attr, first_text, make_listing

SITE_NAME = "GPUsed"
DOMAINS = ("www.gpused.co.uk", "gpused.co.uk")


def build_search_url(query: str) -> str:
    """Return the GPUsed search URL (or the full catalogue for an empty query)."""
    query = (query or "").strip()
    if not query:
        return "https://www.gpused.co.uk/collections/everything"
    return "https://www.gpused.co.uk/search?q=" + quote_plus(query)


# Verified against research/gpused.html: 16 repeated
# div.card-wrapper.product-card-wrapper cards inside li.grid__item.
_CARD_XPATHS = (
    '//div[contains(concat(" ", normalize-space(@class), " "), " product-card-wrapper ")]',
    '//li[contains(concat(" ", normalize-space(@class), " "), " grid__item ")]'
    '[.//a[contains(@href, "/products/")]]',
    '//div[contains(concat(" ", normalize-space(@class), " "), " card-wrapper ")]',
)

_TITLE_XPATHS = (
    './/h3[contains(concat(" ", normalize-space(@class), " "), " card__heading ")]',
    './/h3',
    './/h2',
    './/a[contains(concat(" ", normalize-space(@class), " "), " full-unstyled-link ")]',
    './/a[contains(@href, "/products/")]',
)

_LINK_XPATHS = (
    './/a[contains(@href, "/products/")]/@href',
    './/a[contains(concat(" ", normalize-space(@class), " "), " full-unstyled-link ")]/@href',
    './/h3[contains(@href, "/products/")]/@href',
    './/a/@href',
)

# Sale price is shown first in the captured markup (regular and sale both hold
# the same value); fall back to the regular price span.
_PRICE_XPATHS = (
    './/div[contains(concat(" ", normalize-space(@class), " "), " price__sale ")]'
    '//span[contains(concat(" ", normalize-space(@class), " "), " price-item--sale ")]',
    './/div[contains(concat(" ", normalize-space(@class), " "), " price__regular ")]'
    '//span[contains(concat(" ", normalize-space(@class), " "), " price-item--regular ")]',
    './/span[contains(concat(" ", normalize-space(@class), " "), " price-item ")]',
    './/*[contains(concat(" ", normalize-space(@class), " "), " price ")]',
)

_NOTE_XPATHS = (
    './/div[contains(concat(" ", normalize-space(@class), " "), " card__badge ")]',
    './/span[contains(concat(" ", normalize-space(@class), " "), " caption-large ")]',
)


def parse(html: str, page_url: str) -> list[dict]:
    """Return product listings found in a GPUsed collection/search page."""
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
    return dedupe(listings)
