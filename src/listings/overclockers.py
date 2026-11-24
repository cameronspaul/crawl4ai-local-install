"""Listing parser for Overclockers UK (www.overclockers.co.uk) search results.

Each result is a ``<div class="product-tile">`` containing a product-name
link, a visible ``span.js-unit-price`` and an availability message. The
``data-tracking-product-tile`` JSON uses ex-VAT prices, so the visible price
is preferred here.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from lxml import html as lxml_html

from .base import absolute_url, dedupe, first_attr, first_text, make_listing

SITE_NAME = "Overclockers"
DOMAINS = ("www.overclockers.co.uk", "overclockers.co.uk")

_TILE = '//div[contains(concat(" ", normalize-space(@class), " "), " product-tile ")]'
_NAME_LINK = (
    './/div[contains(concat(" ", normalize-space(@class), " "), '
    '" product-tile-product-name ")]//a'
)
_UNIT_PRICE = (
    './/span[contains(concat(" ", normalize-space(@class), " "), " js-unit-price ")]'
)
_PRICE_BLOCK = (
    './/div[contains(concat(" ", normalize-space(@class), " "), " js-price ")]'
)
_AVAILABILITY = (
    './/div[contains(concat(" ", normalize-space(@class), " "), '
    '" product-availability ")]//span[contains(@class, "text-truncate")]'
)
_IMAGE_LINK = (
    './/div[contains(concat(" ", normalize-space(@class), " "), '
    '" image-container ")]//a'
)


def build_search_url(query: str) -> str:
    """Return the Overclockers search URL for ``query``."""
    return (
        "https://www.overclockers.co.uk/search?q="
        + quote_plus(query)
        + "&search-button=&lang=en_GB"
    )


def parse(html: str, page_url: str) -> list[dict]:
    """Extract product listings from an Overclockers search-results page."""
    try:
        tree = lxml_html.fromstring(html)
    except Exception:
        return []

    listings: list[dict] = []
    for card in tree.xpath(_TILE):
        title = first_text(
            card,
            _NAME_LINK,
            "@aria-label",
            './/img[contains(@class, "bg-product-img")]/@alt',
            './/img[@alt]/@alt',
        )
        href = first_attr(
            card,
            "href",
            _NAME_LINK + "/@href",
            _IMAGE_LINK + "/@href",
        )
        price = first_text(
            card,
            _UNIT_PRICE,
            _PRICE_BLOCK,
            './/span[contains(@class, "value")]/@content',
        )
        note = first_text(
            card,
            _AVAILABILITY,
            './/span[contains(@class, "product-availability-message")]',
            './/div[contains(@class, "product-availability")]/@data-available',
        )

        listings.append(
            make_listing(
                title=title,
                price=price,
                url=absolute_url(page_url, href),
                note=note,
            )
        )

    return dedupe(listings)
