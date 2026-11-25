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


class QueryUnderstandingTests(unittest.TestCase):
    def test_typo_is_corrected_into_a_reformulated_query(self):
        with patch.object(websearch, "_suggest_spelling", lambda token: "unofficial" if token == "unoficcal" else ""):
            variants = websearch.corrected_queries("gta 6 unoficcal pc port reddit")
        self.assertEqual(variants, ["gta 6 unofficial pc port reddit"])

    def test_no_reformulation_when_spelling_is_fine(self):
        with patch.object(websearch, "_suggest_spelling", lambda token: token):
            self.assertEqual(websearch.corrected_queries("python asyncio tutorial"), [])

    def test_site_hints_from_word_and_operator(self):
        self.assertEqual(websearch.detect_site_hint("gta 6 pc port reddit"), "reddit.com")
        self.assertEqual(websearch.detect_site_hint("site:github.com ffmpeg"), "github.com")
        self.assertIsNone(websearch.detect_site_hint("python asyncio tutorial"))

    def test_relevance_ranking_prefers_specific_site_results_and_dedupes(self):
        generic = {"title": "Grand Theft Auto V", "body": "Rockstar games", "href": "https://rockstargames.com/gta-v"}
        specific = {
            "title": "GTA 6 unofficial PC port", "body": "reddit discussion",
            "href": "https://www.reddit.com/r/GTA6/comments/1", "date": "2 days ago",
        }
        query = "gta 6 unofficial pc port reddit"
        ranked = websearch.rank_and_dedupe([generic, specific, dict(specific)], query, "reddit.com")
        self.assertEqual(len(ranked), 2)
        self.assertIn("reddit.com", ranked[0]["href"])

    def test_site_word_is_not_a_content_token(self):
        self.assertEqual(websearch.query_tokens("gta 6 pc port reddit site:github.com"), {"gta", "pc", "port"})

    def test_query_variants_include_typo_site_and_phrase_facets(self):
        variants = websearch.build_query_variants(
            "gta 6 unoffical pc port reddit", "gta 6 unofficial pc port reddit", "reddit.com"
        )
        self.assertEqual(len(variants), 3)
        self.assertIn("gta 6 unofficial pc port reddit", variants)
        self.assertTrue(any("site:reddit.com" in v and "reddit" not in v.split("site:")[0] for v in variants))
        self.assertTrue(any(v.startswith('"unofficial pc port"') for v in variants))

    def test_fresh_specific_result_beats_old_generic_thread_on_hinted_site(self):
        query = "gta 6 unofficial pc port reddit"
        old_thread = {
            "title": "GTA 6 on PC?!?!",
            "body": "Rockstar only mentioned PS5 and Xbox series x/s No PC! Waiting for a PC port.",
            "href": "https://www.reddit.com/r/GTA6/comments/18bjlvh/",
        }
        fresh_article = {
            "title": "Unofficial GTA 6 PC port makes rapid progress",
            "body": "The race for an unofficial GTA 6 PC port just heated up.",
            "href": "https://www.techradar.com/gaming/unofficial-gta-6-pc-port",
            "date": "1 day ago",
        }
        ranked = websearch.rank_and_dedupe(
            [old_thread, fresh_article], query, site_hint="reddit.com"
        )
        self.assertIn("techradar.com", ranked[0]["href"])

    def test_domain_diversity_cap_keeps_other_sites(self):
        rows = [
            {"title": "unofficial pc port guide", "href": f"https://a.example/{i}", "body": "unofficial pc port"}
            for i in range(4)
        ]
        rows.append({
            "title": "unofficial pc port news", "href": "https://b.example/1",
            "body": "unofficial pc port",
        })
        ranked = websearch.rank_and_dedupe(rows, "unofficial pc port")
        self.assertEqual(len(ranked), 4)
        self.assertEqual(sum("a.example" in r["href"] for r in ranked), 3)


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
