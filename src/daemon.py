import argparse
import http.server
import io
import json
import os
import socketserver
import sys
import threading
import time
from urllib.parse import urlparse

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(PROJECT_DIR, "browsers"))
os.environ.setdefault("CRAWL4_AI_BASE_DIRECTORY", PROJECT_DIR)
os.environ["INSIDE_DAEMON"] = "1"

sys.path.insert(0, os.path.join(PROJECT_DIR, "src"))

import cache
import primp
import scrapepage
import websearch

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

PID_FILE = os.path.join(PROJECT_DIR, ".cache", "daemon.pid")

# Global persistent connection pool
_primp_pool = primp.Client(impersonate="random", follow_redirects=True, timeout=12)


class DaemonHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence access logs for pure speed
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/ping", "/health"):
            self._send_json({"status": "ok", "uptime": time.time() - START_TIME})
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(post_body)
        except Exception:
            payload = {}

        if self.path == "/scrape":
            url = payload.get("url", "")
            force_browser = payload.get("force_browser", False)
            no_cache = payload.get("no_cache", False)
            timeout = payload.get("timeout", 20)

            if not url:
                self._send_json({"error": "URL required"}, status=400)
                return

            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url

            # Check cache first
            if not no_cache and not force_browser:
                cached = cache.get_cached_scrape(url)
                if cached:
                    self._send_json({"success": True, "cached": True, "content": cached})
                    return

            # Try pooled primp client
            if not force_browser:
                try:
                    resp = _primp_pool.get(url)
                    if resp.status_code == 200 and resp.text and len(resp.text.strip()) >= 80:
                        is_challenge = any(pat.search(resp.text[:3000]) for pat in scrapepage.CHALLENGE_PATTERNS)
                        if not is_challenge:
                            md = scrapepage.fast_html_to_markdown(resp.text, url)
                            md = scrapepage.remove_long_chunks(md)
                            if len(md.strip()) >= 40:
                                cache.set_cached_scrape(url, md)
                                self._send_json({"success": True, "cached": False, "source": "primp_pool", "content": md})
                                return
                except Exception:
                    pass

            # Fallback to single runner
            try:
                content = scrapepage.scrape_single(url, force_browser=force_browser, timeout=timeout, no_cache=no_cache)
                self._send_json({"success": True, "cached": False, "source": "fallback", "content": content})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)

        elif self.path == "/search":
            query = payload.get("query", "")
            max_results = payload.get("max_results", 10)
            search_type = payload.get("search_type", "text")
            region = payload.get("region", None)
            backend = payload.get("backend", "fast")
            no_cache = payload.get("no_cache", False)

            if not query:
                self._send_json({"error": "Query required"}, status=400)
                return

            try:
                results = websearch.search(
                    query=query,
                    max_results=max_results,
                    search_type=search_type,
                    region=region,
                    backend=backend,
                    no_cache=no_cache,
                )
                self._send_json({"success": True, "results": results})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)

        elif self.path == "/shutdown":
            self._send_json({"status": "shutting down"})
            threading.Thread(target=self.server.shutdown).start()

        else:
            self._send_json({"error": "not found"}, status=404)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


START_TIME = time.time()

def run_daemon(host=DEFAULT_HOST, port=DEFAULT_PORT):
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

    server = ThreadedHTTPServer((host, port), DaemonHandler)
    print(f"[DAEMON] Persistent scraping daemon started on http://{host}:{port} (PID: {os.getpid()})")
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Webscrape persistent local micro-daemon.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to listen on (default 8765)")
    args = parser.parse_args()
    run_daemon(port=args.port)
