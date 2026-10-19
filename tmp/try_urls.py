import io
import os
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(PROJECT_DIR, "browsers"))
os.environ.setdefault("CRAWL4_AI_BASE_DIRECTORY", PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, "src"))

import scrapepage  # noqa: E402

URLS = [
    "https://12go.asia/en/travel/el-nido/coron?date=2027-02-16&people=1&adults=1&direction=forward",
    "https://www.google.com/travel/flights/search?tfs=CBwQAhoqEgoyMDI3LTAyLTE3ag0IAxIJL20vMDE5NXBkcg0IAxIJL20vMDJodjVrQAFIAXABggELCP___________wGYAQI&hl=en-GB&gl=GB",
]

force = "--stealth" in sys.argv

for url in URLS:
    print(f"\n{'='*100}\n{url}\n{'='*100}", flush=True)
    t = time.time()
    try:
        content = scrapepage.scrape_single(url, force_stealth=force, verbose=True, timeout=40, no_cache=True)
        dt = time.time() - t
        print(f"\n>>> OK in {dt:.1f}s, {len(content)} chars", flush=True)
        print("--- first 500 chars ---")
        print(content[:500])
        print("--- last 300 chars ---")
        print(content[-300:])
    except Exception as exc:
        print(f"\n>>> FAILED in {time.time()-t:.1f}s: {exc}", flush=True)
