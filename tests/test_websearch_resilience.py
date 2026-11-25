"""Tests for resilient web search: parallel engines and always-a-response.

Run with:
    python -m unittest discover -s tests
"""

import os
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import websearch  # noqa: E402


class RaceBackendTests(unittest.TestCase):
    def test_one_failing_engine_does_not_blank_out_the_others(self):
        class FakeDDGS:
            def __init__(self, timeout=None):
                self.timeout = timeout

            def text(self, query, backend=None, **kwargs):
                if backend == "bad":
                    raise RuntimeError("rate limited")
                return [{"title": f"{backend} result", "href": f"https://{backend}.com/1", "body": "snippet"}]

        with patch.object(websearch, "DDGS", FakeDDGS):
            rows = websearch._race_backends(
                "query", "text", ("bad", "good"), {}, 5, 1.0, 10
            )

        self.assertTrue(rows)
        self.assertTrue(all("bad" not in row["href"] for row in rows))
        self.assertTrue(any("good" in row["href"] for row in rows))

    def test_results_are_deduplicated_by_url(self):
        class FakeDDGS:
            def __init__(self, timeout=None):
                self.timeout = timeout

            def text(self, query, backend=None, **kwargs):
                return [
                    {"title": "shared", "href": "https://same.example/a", "body": ""},
                    {"title": f"unique {backend}", "href": f"https://{backend}.example/b", "body": ""},
                ]

        with patch.object(websearch, "DDGS", FakeDDGS):
            rows = websearch._race_backends(
                "query", "text", ("one", "two"), {}, 5, 1.0, 10
            )

        urls = [row["href"] for row in rows]
        self.assertEqual(urls.count("https://same.example/a"), 1)
        self.assertEqual(len(urls), 3)


class SearchResponseTests(unittest.TestCase):
    def stub(self, live_rows=None, stale_rows=None):
        stack = ExitStack()
        stack.enter_context(patch.object(websearch, "is_daemon_alive", lambda: False))
        stack.enter_context(patch.object(websearch, "get_cached_search", lambda key: None))
        stack.enter_context(patch.object(websearch, "set_cached_search", lambda key, results: None))
        stack.enter_context(
            patch.object(websearch, "set_last_good_search", lambda query, results, search_type="text": None)
        )
        stack.enter_context(
            patch.object(websearch, "get_last_good_search", lambda query, search_type="text": stale_rows)
        )
        stack.enter_context(
            patch.object(websearch, "_live_search", lambda *args, **kwargs: live_rows or [])
        )
        return stack

    def test_direct_search_links_when_all_engines_fail(self):
        with self.stub():
            results = websearch.search("never-returned query", max_results=10)

        self.assertEqual(len(results), 3)
        self.assertTrue(all(r["fallback"] is True for r in results))
        self.assertIn("google.com", results[0]["url"])

    def test_last_known_good_results_when_all_engines_fail(self):
        stale = [{
            "title": "Old result", "url": "https://old.example", "site": "old.example",
            "date": None, "source": "", "snippet": "cached",
        }]
        with self.stub(stale_rows=stale):
            results = websearch.search("stale query", max_results=10)

        self.assertEqual(results, stale)
        self.assertTrue(results[0]["stale"])

    def test_live_results_are_returned_without_fallback_flags(self):
        live = [{"title": "Fresh", "href": "https://fresh.example/a", "body": "today", "date": ""}]
        with self.stub(live_rows=live):
            results = websearch.search("fresh query", max_results=10)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Fresh")
        self.assertEqual(results[0]["site"], "fresh.example")
        self.assertFalse(results[0].get("stale"))
        self.assertFalse(results[0].get("fallback"))


class RecentDateTests(unittest.TestCase):
    def test_date_to_timestamp_handles_relative_and_absolute_dates(self):
        now = time.time()
        self.assertAlmostEqual(websearch.date_to_timestamp("35 minutes ago"), now - 35 * 60, delta=5)
        self.assertAlmostEqual(websearch.date_to_timestamp("Opinion17 hours ago"), now - 17 * 3600, delta=5)
        self.assertAlmostEqual(websearch.date_to_timestamp("3 days ago"), now - 3 * 86400, delta=5)
        self.assertAlmostEqual(
            websearch.date_to_timestamp("2026-11-24"),
            datetime(2026, 11, 24, tzinfo=timezone.utc).timestamp(), delta=1,
        )
        self.assertAlmostEqual(
            websearch.date_to_timestamp("Nov 24, 2026"),
            datetime(2026, 11, 24, tzinfo=timezone.utc).timestamp(), delta=1,
        )
        self.assertIsNone(websearch.date_to_timestamp(None))
        self.assertIsNone(websearch.date_to_timestamp("no date here"))

    def test_sort_by_date_puts_newest_first_and_undated_last(self):
        rows = [
            {"title": "old", "date": "2026-01-01"},
            {"title": "no date", "date": None},
            {"title": "new", "date": "2 hours ago"},
        ]
        self.assertEqual([r["title"] for r in websearch.sort_by_date(rows)],
                         ["new", "old", "no date"])

    def test_search_recent_sorts_live_results(self):
        live = [
            {"title": "old", "href": "https://old.example", "body": "", "date": "2026-01-01"},
            {"title": "new", "href": "https://new.example", "body": "", "date": "1 hour ago"},
        ]
        stack = ExitStack()
        stack.enter_context(patch.object(websearch, "is_daemon_alive", lambda: False))
        stack.enter_context(patch.object(websearch, "get_cached_search", lambda key: None))
        stack.enter_context(patch.object(websearch, "get_last_good_search", lambda q, s="text": None))
        stack.enter_context(patch.object(websearch, "_live_search", lambda *a, **k: live))
        with stack:
            results = websearch.search("recent query", max_results=10, recent=True)

        self.assertEqual([r["title"] for r in results], ["new", "old"])


class LastGoodCacheTests(unittest.TestCase):
    def test_roundtrip_and_case_insensitive_key(self):
        from src import cache

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(cache, "DB_PATH", os.path.join(tmp, "cache.db")):
                self.assertIsNone(cache.get_last_good_search("Some Query", "text"))
                cache.set_last_good_search(
                    "Some Query", [{"title": "ok", "url": "https://x"}], "text"
                )
                rows = cache.get_last_good_search("some query", "text")
                self.assertTrue(rows)
                self.assertEqual(rows[0]["title"], "ok")
                self.assertEqual(
                    cache.make_last_good_key("SOME QUERY", "text"),
                    cache.make_last_good_key("Some Query", "text"),
                )


if __name__ == "__main__":
    unittest.main()
