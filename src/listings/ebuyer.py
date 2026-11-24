"""Listing parser for Ebuyer search-result pages.

The captured ``research/ebuyer.html`` uses semantic product tiles::

    <a data-testid="product-card" href="/some-product-716079#colcode=71607903"
       aria-label="Brand Full Product Name">
      <p data-testid="product-card-brand">Brand</p>
      <h2 data-testid="product-card-name-without-brand">Full Product Name</h2>
      <p data-testid="price"><span>£99.99</span>
         <span><span data-testid="ticket-price">£129.99</span></span></p>
    </a>

All lookups are defensive: a missing field becomes an empty string.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from lxml import html as lxml_html

from .base import (
    absolute_url,
    clean_text,
    dedupe,
    first_attr,
    first_text,
    make_listing,
)

SITE_NAME = "Ebuyer"
DOMAINS = ("www.ebuyer.com", "ebuyer.com")

__all__ = ["SITE_NAME", "DOMAINS", "build_search_url", "parse"]

_SEARCH_URL = "https://www.ebuyer.com/search"

# The first one is the selector actually present in the captured HTML; the
# rest are cheap fallbacks for future markup tweaks.
_CARD_XPATHS = (
    "//*[@data-testid='product-card']",
    "//a[contains(concat(' ', normalize-space(@class), ' '), ' product-card ')]",
    "//li[.//a[@data-testid='product-card']]",
    "//a[@href][.//*[@data-testid='price']]",
)

_PRICE_XPATHS = (
    ".//*[@data-testid='price']/span[1]/text()",
    ".//*[@data-testid='price']/*[1]/text()",
    ".//*[@data-testid='price']/text()",
    ".//*[contains(@class,'price')][not(@data-testid='ticket-price')]/text()",
)

_TITLE_XPATHS = (
    "@aria-label",
    ".//*[@data-testid='product-card-name-without-brand']/text()",
    ".//h2/text()",
    ".//h2/span/text()",
    ".//img[@data-testid='picture-img']/@alt",
)

_LINK_XPATHS = (
    "self::a/@href",
    ".//a[@data-testid='product-card']/@href",
    ".//a[@href]/@href",
)


def build_search_url(query: str) -> str:
    """Return the Ebuyer search URL for *query* (URL-encoded)."""
    return f"{_SEARCH_URL}?q={quote_plus(query or '')}"


def _cards(tree):
    for xpath in _CARD_XPATHS:
        try:
            found = tree.xpath(xpath)
        except Exception:
            continue
        if found:
            return found
    return []


def parse(html: str, page_url: str) -> list[dict]:
    """Turn Ebuyer search HTML into a list of uniform listing dictionaries."""
    try:
        tree = lxml_html.fromstring(html)
    except Exception:
        return []

    listings: list[dict] = []
    for card in _cards(tree):
        try:
            brand = first_text(card, ".//*[@data-testid='product-card-brand']/text()")
            short_name = first_text(
                card,
                ".//*[@data-testid='product-card-name-without-brand']/text()",
                ".//h2/text()",
            )
            title = first_text(card, "@aria-label")
            if not title:
                combined = clean_text(f"{brand} {short_name}") if brand and short_name else (short_name or brand)
                title = combined or first_text(card, *_TITLE_XPATHS[1:])
            if not title:
                # Advert/skeleton placeholders have no usable product name.
                continue

            price = first_text(card, *_PRICE_XPATHS)
            url = absolute_url(page_url, first_attr(card, "href", *_LINK_XPATHS))

            was = first_text(card, ".//*[@data-testid='ticket-price']/text()")
            note = f"Was {was}" if was and was != price else ""

            listings.append(make_listing(title=title, price=price, url=url, note=note))
        except Exception:
            # One broken card must never abort the whole page.
            continue

    return dedupe(listings)
