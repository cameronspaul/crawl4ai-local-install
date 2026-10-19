"""Anti-bot stealth browser tier built on invisible_playwright (patched Firefox).

This is the last-resort scraper tier. It drives the C++-patched anti-detect
Firefox from https://github.com/feder-cr/invisible_playwright, whose fingerprint
is produced inside the engine (no JS shim) and whose pointer motion is humanized,
so it gets past Cloudflare / DataDome / PerimeterX style walls that the plain
HTTP tier and the Crawl4AI Chromium tier cannot.

Everything here is optional and lazily imported: importing this module must not
cost anything on the common fast path. If the package or its engine are missing,
`available()` is False and the caller falls back to its other tiers.

Local note (Windows): the Firefox content-process sandbox on this machine blocks
the Juggler protocol used by invisible_playwright, which makes `new_page()` hang.
Setting MOZ_DISABLE_CONTENT_SANDBOX=1 for the child process is required here and
is applied automatically below (opt out with WEBSCRAPE_STEALTH_KEEP_SANDBOX=1).
"""

from __future__ import annotations

import os
import queue
import re
import sys
import threading
import time
from concurrent.futures import Future
from typing import Callable, Optional

# The engine reads this from its own environment at spawn time. It fixes the
# hang described in the module docstring and has no effect on the fingerprint a
# page can read.
if sys.platform == "win32" and not os.environ.get("WEBSCRAPE_STEALTH_KEEP_SANDBOX"):
    os.environ.setdefault("MOZ_DISABLE_CONTENT_SANDBOX", "1")

#: Pages that are actually an anti-bot interstitial rather than the content.
#: Kept deliberately specific: a challenge page is short, so a long article that
#: merely mentions one of these words is not flagged.
CHALLENGE_PATTERNS = [
    re.compile(r"cf-browser-verification", re.I),
    re.compile(r"cloudflare ray id", re.I),
    re.compile(r"enable javascript and cookies to continue", re.I),
    re.compile(r"<title>\s*Just a moment\.\.\.\s*</title>", re.I),
    re.compile(r"<title>\s*Access Denied\s*</title>", re.I),
    re.compile(r"attention required!?\s*\|\s*cloudflare", re.I),
    re.compile(r"checking your browser before accessing", re.I),
    re.compile(r"verifying you are (a )?human", re.I),
    re.compile(r"please (wait|verify) while we (check|verify)", re.I),
    re.compile(r"you have been blocked", re.I),
    re.compile(r"access to this page has been denied", re.I),
    re.compile(r"unusual traffic from your (computer|network)", re.I),
    re.compile(r"px-captcha|_pxhd|datadome|challenge-platform", re.I),
    re.compile(r"are you a robot\?", re.I),
    re.compile(r"just a moment while we (check|verify)", re.I),
    re.compile(r"press\s*&?\s*hold to confirm", re.I),
    re.compile(r"keep holding", re.I),
]

#: A challenge interstitial is small. Anything past this is treated as real
#: content even if it happens to contain one of the phrases above.
_MAX_CHALLENGE_CHARS = 9000


def looks_like_challenge(text: Optional[str]) -> bool:
    """True when `text` reads like an anti-bot wall rather than a real page."""
    if not text:
        return False
    if len(text) > _MAX_CHALLENGE_CHARS:
        return False
    return any(pat.search(text) for pat in CHALLENGE_PATTERNS)


def _engine_present() -> bool:
    """Cheap check that the patched engine is already unpacked in the cache.

    Avoids a surprise ~250 MB download in the middle of a scrape: if the engine
    is not there, this tier simply reports unavailable and the install script is
    the documented way to fetch it.
    """
    try:
        from invisible_core.download import cache_dir_for_seal
        from invisible_core.seal import active_seal

        d = cache_dir_for_seal(active_seal())
        return d.is_dir() and any(d.iterdir())
    except Exception:
        return False


_AVAILABLE: Optional[bool] = None


def available() -> bool:
    """True when the stealth tier can actually be used right now."""
    global _AVAILABLE
    if _AVAILABLE is None:
        try:
            import invisible_playwright  # noqa: F401

            _AVAILABLE = _engine_present()
        except Exception:
            _AVAILABLE = False
    return _AVAILABLE


def _markdown(html: str, url: str, convert: Optional[Callable[[str, str], str]]) -> str:
    if not html:
        return ""
    if convert is None:
        return html
    return convert(html, url)


def _read_page(page, url: str, convert, settle_wait: float, min_chars: int = 200) -> Optional[str]:
    """Pull markdown off a page once it is actually rendered.

    Re-reads while the page still looks like a challenge wall (which may solve
    itself) or still looks unrendered (a client-side app that finished its
    network but not its paint). A short page whose content has stopped changing
    is accepted early, so genuinely tiny pages don't pay the full window.
    """
    def read() -> str:
        return _markdown(page.content(), page.url or url, convert)

    md = read()
    prev = None
    stable = 0
    deadline = time.time() + settle_wait
    while time.time() < deadline:
        if not looks_like_challenge(md) and len(md.strip()) >= min_chars:
            break
        stable = stable + 1 if (md and md == prev) else 0
        if stable >= 2 and not looks_like_challenge(md):
            break
        prev = md
        try:
            page.wait_for_timeout(1000)
        except Exception:
            break
        try:
            md = read()
        except Exception:
            break

    if looks_like_challenge(md):
        return None
    return md


def _open(browser, timeout: float):
    page = browser.new_page()
    page.set_default_navigation_timeout(timeout * 1000)
    return page


def scrape(
    url: str,
    convert: Optional[Callable[[str, str], str]] = None,
    timeout: int = 30,
    settle_wait: float = 8.0,
    verbose: bool = False,
) -> Optional[str]:
    """One-shot stealth scrape: launch, render, tear down.

    Returns markdown, or None when the page could not be rendered or is still
    sitting behind an unsolved challenge wall.
    """
    from invisible_playwright import InvisiblePlaywright

    if verbose:
        print(f"[stealth] launching patched Firefox for '{url}'", file=sys.stderr)

    with InvisiblePlaywright(
        headless=True,
        humanize=True,
        show_cursor=False,
        timezone="auto",
        locale="auto",
    ) as browser:
        page = _open(browser, timeout)
        resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        try:
            page.wait_for_load_state("networkidle", timeout=4000)
        except Exception:
            pass
        if verbose and resp is not None:
            print(f"[stealth] HTTP {resp.status} for '{url}'", file=sys.stderr)
        return _read_page(page, url, convert, settle_wait)


class WarmStealth:
    """A single stealth browser owned by one worker thread and reused.

    Playwright's sync objects may only be used from the thread that created
    them, so requests are serialized through a queue to a dedicated owner
    thread. When a request fails the browser is thrown away and rebuilt on the
    next one, which keeps a wedged session from poisoning later scrapes.
    """

    def __init__(self, settle_wait: float = 8.0) -> None:
        self._settle_wait = settle_wait
        self._jobs: "queue.Queue" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._closed = False

    def _ensure_thread(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name="stealth-browser", daemon=True)
            self._thread.start()

    def _run(self) -> None:
        from invisible_playwright import InvisiblePlaywright

        launcher = None
        browser = None
        while True:
            job = self._jobs.get()
            if job is None:
                break
            url, convert, timeout, fut = job
            try:
                if browser is None:
                    launcher = InvisiblePlaywright(
                        headless=True,
                        humanize=True,
                        show_cursor=False,
                        timezone="auto",
                        locale="auto",
                    )
                    browser = launcher.__enter__()
                page = _open(browser, timeout)
                page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                try:
                    page.wait_for_load_state("networkidle", timeout=4000)
                except Exception:
                    pass
                md = _read_page(page, url, convert, self._settle_wait)
                try:
                    page.close()
                except Exception:
                    pass
                fut.set_result(md)
            except Exception as exc:
                # The browser may be wedged; drop it so the next job relauches.
                if launcher is not None:
                    try:
                        launcher.__exit__(None, None, None)
                    except Exception:
                        pass
                launcher = None
                browser = None
                fut.set_exception(exc)

        if launcher is not None:
            try:
                launcher.__exit__(None, None, None)
            except Exception:
                pass

    def fetch(
        self,
        url: str,
        convert: Optional[Callable[[str, str], str]] = None,
        timeout: int = 30,
    ) -> Optional[str]:
        """Render `url` on the warm browser. Raises on a hard browser failure."""
        if self._closed:
            raise RuntimeError("stealth session is closed")
        self._ensure_thread()
        fut: Future = Future()
        self._jobs.put((url, convert, timeout, fut))
        # The worker applies its own navigation timeout; allow generous slack
        # for a cold browser launch on top of it.
        return fut.result(timeout=timeout + 120)

    def close(self) -> None:
        self._closed = True
        if self._thread is not None and self._thread.is_alive():
            self._jobs.put(None)
            self._thread.join(timeout=30)
