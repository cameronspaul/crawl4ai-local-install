import os
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(PROJECT_DIR, "browsers"))
os.environ.setdefault("MOZ_DISABLE_CONTENT_SANDBOX", "1")
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, "src"))

from invisible_playwright import InvisiblePlaywright  # noqa: E402

URL = ("https://www.google.com/travel/flights/search?"
       "tfs=CBwQAhoqEgoyMDI3LTAyLTE3ag0IAxIJL20vMDE5NXBkcg0IAxIJL20vMDJodjVrQAFIAXABggELCP___________wGYAQI"
       "&hl=en-GB&gl=GB")

CONSENT = ["Accept all", "Allow all", "Reject all", "I agree", "Accept all cookies", "Alle akzeptieren"]

with InvisiblePlaywright(headless=True, humanize=True, show_cursor=False, timezone="auto", locale="auto") as browser:
    page = browser.new_page()
    page.set_default_navigation_timeout(45000)
    resp = page.goto(URL, wait_until="domcontentloaded", timeout=45000)
    print(f"status={resp.status if resp else None} url={page.url}")

    clicked = False
    for i in range(14):
        page.wait_for_timeout(2000)
        text = page.inner_text("body") or ""
        has_price = "£" in text
        markers = {k: (k.lower() in text.lower()) for k in ["Nonstop", "Best", "Cheapest", "Total duration", "Departure"]}
        print(f"t={(i+1)*2:2d}s len={len(text):6d} price={has_price} {markers}")

        if not clicked:
            for label in CONSENT:
                try:
                    loc = page.get_by_role("button", name=label, exact=False)
                    if loc.count() > 0:
                        loc.first.click(timeout=3000)
                        print(f"  clicked consent: {label}")
                        clicked = True
                        break
                except Exception:
                    pass
            if not clicked:
                for label in CONSENT:
                    try:
                        loc = page.get_by_text(label, exact=False)
                        if loc.count() > 0:
                            loc.first.click(timeout=3000)
                            print(f"  clicked text consent: {label}")
                            clicked = True
                            break
                    except Exception:
                        pass

        if has_price and markers.get("Nonstop"):
            print("  -> flight results detected")
            break

    print("\n--- final body text (first 600) ---")
    print((page.inner_text("body") or "")[:600])
