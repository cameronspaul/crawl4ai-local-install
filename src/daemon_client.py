import json
import socket
import urllib.error
import urllib.request
from typing import Any, Optional

DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 8765


def is_daemon_alive(port: int = DAEMON_PORT, timeout: float = 0.05) -> bool:
    """Quickly check if daemon socket is listening (50ms timeout)."""
    try:
        with socket.create_connection((DAEMON_HOST, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


def daemon_scrape(
    url: str,
    force_browser: bool = False,
    timeout: int = 20,
    no_cache: bool = False,
    port: int = DAEMON_PORT,
) -> Optional[str]:
    """Dispatch scrape request to persistent warm daemon."""
    payload = {
        "url": url,
        "force_browser": force_browser,
        "timeout": timeout,
        "no_cache": no_cache,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://{DAEMON_HOST}:{port}/scrape",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout + 2) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("success"):
                return body.get("content", "")
    except Exception:
        pass
    return None


def daemon_search(
    query: str,
    max_results: int = 10,
    search_type: str = "text",
    region: str = None,
    backend: str = "fast",
    no_cache: bool = False,
    port: int = DAEMON_PORT,
) -> Optional[list[dict[str, Any]]]:
    """Dispatch search request to persistent warm daemon."""
    payload = {
        "query": query,
        "max_results": max_results,
        "search_type": search_type,
        "region": region,
        "backend": backend,
        "no_cache": no_cache,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://{DAEMON_HOST}:{port}/search",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("success"):
                return body.get("results", [])
    except Exception:
        pass
    return None
