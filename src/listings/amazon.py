"""Listing parser for Amazon UK search-result pages.

The captured ``research/amazon.html`` uses one container per result::

    <div data-component-type="s-search-result" data-asin="B0DMTL43VR" ...>
      <h2><span>Corsair RM850e ...</span><a href="/Corsair-.../dp/B0DMTL43VR/..."></a></h2>
      <span class="a-price"><span class="a-offscreen">£82.99</span>...</span>
      <span class="a-icon-alt">4.6 out of 5 stars</span>
    </div>

Sponsored cards carry an ``AdHolder`` class and usually have ``href="#"``;
they are kept only when they still expose a real product title, and their URL
is reconstructed from ``data-asin`` in that case. Cards without a title are
skipped. Missing fields never raise.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from lxml import html as lxml_html

from .base import absolute_url, dedupe, first_attr, first_text, make_listing

SITE_NAME = "Amazon UK"
DOMAINS = ("www.amazon.co.uk", "amazon.co.uk")

__all__ = ["SITE_NAME", "DOMAINS", "build_search_url", "parse"]

_SEARCH_URL = "https://www.amazon.co.uk/s"

_CARD_XPATHS = (
    "//div[@data-component-type='s-search-result']",
    "//div[@data-asin][contains(concat(' ', normalize-space(@class), ' '), ' s-result-item ')]",
    "//div[contains(@class,'s-result-item')][.//h2]",
)

_TITLE_XPATHS = (
    ".//h2/span/text()",
    ".//h2//span/text()",
    ".//h2/@aria-label",
    ".//a[contains(@class,'s-link-style')]/span/text()",
    ".//img[@class='s-image']/@alt",
)

_PRICE_XPATHS = (
    ".//span[contains(@class,'a-price')]/span[@class='a-offscreen']/text()",
    ".//span[@class='a-offscreen']/text()",
    ".//span[contains(@class,'a-price')]//text()",
    ".//span[contains(@class,'a-color-price')]/text()",
)

_LINK_XPATHS = (
    ".//h2/a/@href",
    ".//a[contains(@class,'s-link-style')]/@href",
    ".//a[contains(@href,'/dp/')]/@href",
    ".//a[contains(@class,'a-link-normal')]/@href",
)

_RATING_XPATHS = (
    ".//span[@class='a-icon-alt']/text()",
    ".//i[contains(@class,'a-icon-star')]/../span/text()",
    ".//span[@aria-label][contains(@aria-label,'out of 5 stars')]/@aria-label",
)


def build_search_url(query: str) -> str:
    """Return the Amazon UK search URL for *query* (URL-encoded)."""
    return f"{_SEARCH_URL}?k={quote_plus(query or '')}"


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
    """Turn Amazon UK search HTML into a list of uniform listing dictionaries."""
    try:
        tree = lxml_html.fromstring(html)
    except Exception:
        return []

    listings: list[dict] = []
    for card in _cards(tree):
        try:
            title = first_text(card, *_TITLE_XPATHS)
            if not title or title.lower().startswith("sponsored"):
                # Ad/skeleton placeholders have no real product title.
                continue

            price = first_text(card, *_PRICE_XPATHS)
            url = absolute_url(page_url, first_attr(card, "href", *_LINK_XPATHS))
            if not url:
                asin = (card.get("data-asin") or "").strip()
                if asin:
                    url = absolute_url(page_url, f"/dp/{asin}")

            rating = first_text(card, *_RATING_XPATHS)
            is_ad = "AdHolder" in (card.get("class") or "") or bool(
                card.xpath(".//a[contains(@class,'puis-sponsored-label-text')]")
            )
            note_parts = [part for part in (rating, "Sponsored" if is_ad else "") if part]
            note = "; ".join(note_parts)

            listings.append(make_listing(title=title, price=price, url=url, note=note))
        except Exception:
            # A single malformed result must not break the rest of the page.
            continue

    return dedupe(listings)
