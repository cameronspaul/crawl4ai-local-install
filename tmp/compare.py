import asyncio
import os
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(PROJECT_DIR, "browsers"))
os.environ.setdefault("CRAWL4_AI_BASE_DIRECTORY", PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, "src"))

import scrapepage  # noqa: E402
import stealth  # noqa: E402

OUT = os.path.join(PROJECT_DIR, "tmp", "results")
os.makedirs(OUT, exist_ok=True)

TARGETS = [
    ("flights_manila_elnido", "https://www.google.com/travel/flights?q=Flights%20from%20Manila%20to%20El%20Nido"),
    ("boats_gili", "https://12go.asia/en/travel/bali/gili-trawangan"),
]

TIMEOUT = 40


def verdict(md):
    if not md:
        return "EMPTY"
    if scrapepage.looks_like_challenge(md):
        return "CHALLENGE"
    n = len(md.strip())
    if n < 100:
        return f"tiny({n})"
    if n < 800:
        return f"thin({n})"
    return f"ok({n})"


def save(name, tier, md):
    with open(os.path.join(OUT, f"{name}.{tier}.md"), "w", encoding="utf-8") as fh:
        fh.write(md or "")


def run_fast(name, url):
    t = time.time()
    ok, res = scrapepage.try_fast_scrape(url, timeout=10)
    md = res if ok else ""
    save(name, "fast", md)
    return "fast-http", verdict(md), time.time() - t, res[:60] if not ok else ""


def run_browser(name, url):
    t = time.time()
    try:
        md = asyncio.run(scrapepage.browser_scrape(url, verbose=False, timeout=TIMEOUT))
        save(name, "chromium", md)
        return "chromium", verdict(md), time.time() - t, ""
    except Exception as exc:
        save(name, "chromium", "")
        return "chromium", "ERROR", time.time() - t, scrapepage.format_error(str(exc))[:70]


def run_stealth(name, url):
    t = time.time()
    try:
        md = stealth.scrape(url, scrapepage.fast_html_to_markdown, timeout=TIMEOUT, verbose=True)
        save(name, "stealth", md)
        return "stealth", verdict(md), time.time() - t, ""
    except Exception as exc:
        save(name, "stealth", "")
        return "stealth", "ERROR", time.time() - t, str(exc)[:70]


summary = []
for name, url in TARGETS:
    print(f"\n{'#'*90}\n# {name}\n# {url}\n{'#'*90}", flush=True)
    for fn in (run_fast, run_browser, run_stealth):
        tier, v, dt, note = fn(name, url)
        print(f"  {tier:9s} {v:16s} {dt:6.1f}s  {note}", flush=True)
        summary.append((name, tier, v, dt))

print("\n\n============================ SUMMARY ============================")
for name in [t[0] for t in TARGETS]:
    print(f"\n{name}:")
    for n, tier, v, dt in summary:
        if n == name:
            print(f"    {tier:9s} {v:16s} {dt:5.1f}s")
print(f"\nfull markdown written to: {OUT}")
