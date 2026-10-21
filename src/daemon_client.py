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
    timeout: int = 20,
    no_cache: bool = False,
    force_stealth: bool = False,
    raw: bool = False,
    ready_markers: tuple[str, ...] | list[str] | None = None,
    settle_wait: float | None = None,
    verbose: bool = False,
    port: int = DAEMON_PORT,
) -> Optional[str]:
    """Dispatch scrape request to persistent warm daemon.

    Set ``raw=True`` to ask for the original HTML instead of Markdown and
    ``ready_markers`` to wait for a specific client-rendered block.
    """
    payload = {
        "url": url,
        "force_stealth": force_stealth,
        "timeout": timeout,
        "no_cache": no_cache,
        "raw": raw,
        "verbose": verbose,
    }
    if ready_markers:
        payload["ready_markers"] = list(ready_markers)
    if settle_wait is not None:
        payload["settle_wait"] = settle_wait
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://{DAEMON_HOST}:{port}/scrape",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        # A forced stealth render may have to launch a cold browser first, so it
        # gets a generous client timeout; the ordinary path keeps the tight one
        # so a slow daemon falls back to a local scrape quickly.
        client_timeout = timeout + 180 if (force_stealth or raw) else timeout + 2
        with urllib.request.urlopen(req, timeout=client_timeout) as resp:
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
