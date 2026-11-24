"""Listing parser for Scan (www.scan.co.uk) search results.

The search page renders one ``<li class="product">`` per result. Prices are
split across ``<small>`` elements ("£" + "44" + ".99"), so the whole price
element is read as text instead of relying on an attribute.
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
)

SITE_NAME = "Scan"
DOMAINS = ("www.scan.co.uk", "scan.co.uk")

# Token-style class matching avoids picking up "product-group" wrappers etc.
_PRODUCT = '//li[contains(concat(" ", normalize-space(@class), " "), " product ")]'
_PRICE = './/span[contains(concat(" ", normalize-space(@class), " "), " price ")]'
_STOCK = './/span[contains(concat(" ", normalize-space(@class), " "), " stock ")]'
_DESCRIPTION = './/span[contains(concat(" ", normalize-space(@class), " "), " description ")]'
_IMAGE_LINK = './/a[contains(concat(" ", normalize-space(@class), " "), " image ")]'
_DELIVERY = './/span[contains(concat(" ", normalize-space(@class), " "), " delivery-date ")]'


def build_search_url(query: str) -> str:
    """Return the Scan search URL for ``query``."""
    return "https://www.scan.co.uk/search?q=" + quote_plus(query)


def _visible_price(card) -> str:
    """Join the split price fragments ("£" + "44" + ".99") without spaces."""
    try:
        nodes = card.xpath(_PRICE)
    except Exception:
        return ""
    for node in nodes:
        price = normalise_price("".join(node.itertext()))
        if price:
            return price
    return ""


def parse(html: str, page_url: str) -> list[dict]:
    """Extract product listings from a Scan search-results page."""
    try:
        tree = lxml_html.fromstring(html)
    except Exception:
        return []

    listings: list[dict] = []
    for card in tree.xpath(_PRODUCT):
        title = first_text(
            card,
            "@data-description",
            _DESCRIPTION + "//a/span[1]",
            _DESCRIPTION + "//a",
            './/img[contains(@class, "image-std")]/@title',
        )
        href = first_attr(
            card,
            "href",
            _DESCRIPTION + "//a/@href",
            _IMAGE_LINK + "/@href",
            "@data-popover-iframe",
        )
        price = _visible_price(card) or first_text(card, "@data-price")
        stock = first_text(card, _STOCK)
        delivery = first_text(card, _DELIVERY + "//strong", _DELIVERY)

        note = ", ".join(part for part in (stock, delivery) if part)
        listings.append(
            make_listing(
                title=title,
                price=price,
                url=absolute_url(page_url, href),
                note=note,
            )
        )

    return dedupe(listings)
