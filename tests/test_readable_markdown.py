"""Tests for the lossless, readable Markdown layout.

Run with:
    python -m unittest discover -s tests -p "test_readable_markdown.py"
"""

import os
import re
import sys
import unittest
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import scrapepage  # noqa: E402

SECTIONS = {scrapepage._HEADER_SECTION, scrapepage._IMAGE_SECTION}


def data_counter(text: str, strip_numbers: bool = False) -> Counter:
    """Count non-blank content lines, ignoring layout headings/numbering."""
    counts: Counter = Counter()
    for line in text.splitlines():
        if not line.strip():
            continue
        if strip_numbers and re.match(r"^L\d{1,5} ", line):
            # Formatted as f"L{number:<5} " -> a fixed 7-character prefix.
            line = line[7:]
        if line in SECTIONS:
            continue
        counts[line] += 1
    return counts


HTML_FIXTURE = """
<html><head><title>Test Page</title></head><body>
<header><nav><a href="/home">Home</a><a href="/about">About</a></nav></header>
<main>
<h1>Test Page</h1>
<p>Hello world.</p>
<p>Second paragraph.</p>
<img src="https://example.com/pic.png" alt="A picture">
</main>
<footer><a href="/privacy">Privacy</a><a href="/terms">Terms</a></footer>
</body></html>
"""


class WhitespaceTests(unittest.TestCase):
    def test_de_gaps_without_touching_visible_text(self):
        raw = "\ufeffTitle   \n\n\n\n\nBody   \r\n\r\n\r\nEnd"
        cleaned = scrapepage.normalize_markdown_whitespace(raw)
        self.assertEqual(cleaned, "Title\n\nBody\n\nEnd")
        self.assertNotIn("\ufeff", cleaned)
        self.assertTrue(all(line == line.rstrip() for line in cleaned.splitlines()))

    def test_empty_input(self):
        self.assertEqual(scrapepage.normalize_markdown_whitespace(""), "")
        self.assertEqual(scrapepage.normalize_markdown_whitespace("  \n\n "), "")


class ReorderTests(unittest.TestCase):
    def test_every_line_survives_exactly_once(self):
        raw = "\n".join(
            [
                "Title",
                "",
                "[Home](https://example.com/home)",
                "[Home](https://example.com/home)",  # duplicate must be kept
                "",
                "![alt](https://example.com/a.png)",
                "",
                "Body text",
                "[Privacy](https://example.com/privacy)",
            ]
        )
        nav_keys = {
            "[Home](https://example.com/home)",
            "[Privacy](https://example.com/privacy)",
        }
        image_keys = {"![alt](https://example.com/a.png)"}
        out = scrapepage.format_readable_markdown(raw, nav_keys, image_keys)

        self.assertEqual(data_counter(raw), data_counter(out, strip_numbers=True))
        self.assertEqual(data_counter(raw)["[Home](https://example.com/home)"], 2)
        self.assertIn(scrapepage._HEADER_SECTION, out)
        self.assertIn(scrapepage._IMAGE_SECTION, out)
        self.assertLess(out.index("Body text"), out.index(scrapepage._HEADER_SECTION))
        self.assertLess(out.index(scrapepage._HEADER_SECTION), out.index(scrapepage._IMAGE_SECTION))

    def test_source_order_and_final_line_numbers(self):
        raw = "\n".join(
            [
                "[Z](https://example.com/z)",
                "[A](https://example.com/a)",
                "![one](https://example.com/1.png)",
                "![two](https://example.com/2.png)",
                "Body",
            ]
        )
        out = scrapepage.format_readable_markdown(
            raw,
            nav_keys={"[Z](https://example.com/z)", "[A](https://example.com/a)"},
            image_keys={"![one](https://example.com/1.png)", "![two](https://example.com/2.png)"},
        )
        numbered = []
        for number, line in enumerate(out.splitlines(), 1):
            match = re.match(r"^L(\d+)\s+(.*)$", line)
            if match:
                numbered.append((int(match.group(1)), number, match.group(2)))
        self.assertEqual(len(numbered), 4)
        self.assertEqual([n for n, _, _ in numbered], [p for _, p, _ in numbered])
        self.assertEqual([text for _, _, text in numbered[0:2]], ["[Z](https://example.com/z)", "[A](https://example.com/a)"])
        self.assertEqual([text for _, _, text in numbered[2:4]], ["![one](https://example.com/1.png)", "![two](https://example.com/2.png)"])

    def test_removing_a_middle_block_does_not_leave_double_blanks(self):
        raw = "First\n\n[Moved](https://example.com/m)\n\nSecond"
        out = scrapepage.format_readable_markdown(raw, nav_keys={"[Moved](https://example.com/m)"})
        self.assertFalse(re.search(r"\n[ \t]*\n[ \t]*\n", out))
        self.assertEqual(data_counter(raw), data_counter(out, strip_numbers=True))

    def test_no_appendix_when_nothing_matches(self):
        raw = "Title\n\nBody"
        out = scrapepage.format_readable_markdown(raw)
        self.assertEqual(out, "Title\n\nBody")
        self.assertNotIn(scrapepage._HEADER_SECTION, out)


class ConversionTests(unittest.TestCase):
    def test_dom_classification_moves_links_and_images(self):
        raw = scrapepage.fast_html_to_markdown(HTML_FIXTURE, "https://example.com/", readable=False)
        out = scrapepage.fast_html_to_markdown(HTML_FIXTURE, "https://example.com/", readable=True)

        self.assertEqual(data_counter(raw), data_counter(out, strip_numbers=True))
        self.assertIn(scrapepage._HEADER_SECTION, out)
        self.assertIn(scrapepage._IMAGE_SECTION, out)

        body = out.split(scrapepage._HEADER_SECTION)[0]
        appendix = out.split(scrapepage._HEADER_SECTION)[1]
        self.assertIn("# Test Page", body)
        self.assertIn("Hello world.", body)
        self.assertIn("Second paragraph.", body)
        self.assertNotIn("https://example.com/pic.png", body)
        for expected in (
            "[Home](https://example.com/home)",
            "[About](https://example.com/about)",
            "[Privacy](https://example.com/privacy)",
            "[Terms](https://example.com/terms)",
        ):
            self.assertIn(expected, appendix)
        self.assertIn("![A picture](https://example.com/pic.png)", appendix)

    def test_raw_opt_out_matches_legacy_conversion(self):
        raw = scrapepage.fast_html_to_markdown(HTML_FIXTURE, "https://example.com/", readable=False)
        self.assertNotIn(scrapepage._HEADER_SECTION, raw)
        self.assertIn("[Home](https://example.com/home)", raw)
        self.assertIn("![A picture](https://example.com/pic.png)", raw)

    def test_raw_out_captures_pre_layout_markdown(self):
        captured = []
        out = scrapepage.fast_html_to_markdown(HTML_FIXTURE, "https://example.com/", raw_out=captured)
        self.assertEqual(len(captured), 1)
        self.assertNotEqual(captured[0], out)
        self.assertEqual(data_counter(captured[0]), data_counter(out, strip_numbers=True))


class CacheKeyTests(unittest.TestCase):
    def test_markdown_cache_key_is_versioned(self):
        from cache import make_markdown_cache_key

        key = make_markdown_cache_key("https://example.com")
        self.assertNotEqual(key, "https://example.com")
        self.assertEqual(key, make_markdown_cache_key("https://example.com"))
        self.assertNotEqual(key, make_markdown_cache_key("https://example.org"))


class RealSampleTests(unittest.TestCase):
    def test_cached_reddit_sample_is_de_gapped_and_lossless(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache", "gta6_top.md"
        )
        if not os.path.exists(path):
            self.skipTest("cached sample not present")
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            raw = handle.read()
        out = scrapepage.format_readable_markdown(raw)
        # Trailing spaces / BOM are deliberately removed by the de-gap step.
        self.assertEqual(
            data_counter(scrapepage.normalize_markdown_whitespace(raw)),
            data_counter(out, strip_numbers=True),
        )
        self.assertTrue(all(line == line.rstrip() for line in out.splitlines()))
        self.assertFalse(re.search(r"\n[ \t]*\n[ \t]*\n", out))  # no run of 2+ blank lines
        self.assertLess(len(out.splitlines()), len(raw.splitlines()))


if __name__ == "__main__":
    unittest.main()
