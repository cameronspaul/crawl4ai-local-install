"""Tests for the shared anti-bot / thin-page content gate.

The gate decides whether a fast HTTP result is real content or an
interstitial that should escalate to the stealth browser.

Run with:
    python -m unittest discover -s tests -p "test_content_gate.py"
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import scrapepage  # noqa: E402
import stealth  # noqa: E402


REDDIT_WALL_MD = """Reddit - Prove your humanity

# Prove your humanity

We're committed to safety and security. But not for bots. Complete the
challenge below and let us know you're a real person.

## Header & footer links
L10    [Reddit, Inc. © "2026". All rights reserved.](https://www.redditinc.com/)
L11    [User Agreement](https://www.reddit.com/help/useragreement)
L12    [Privacy Policy](https://www.reddit.com/help/privacypolicy)
L13    [Content Policy](https://www.reddit.com/help/contentpolicy)
L14    [Help](https://support.reddithelp.com/hc/en-us)
"""

BLOCKED_MD = """You've been blocked by network security.

If you think you've been blocked by mistake, file a ticket below and we'll
look into it.
"""

OLD_REDDIT_MD = """Welcome to Reddit

# Log in to use old Reddit

To keep Reddit safe, accounts are required to access old Reddit. Log in, or
continue without an account on reddit.com.
"""

CLOUDFLARE_MANAGED_MD = """Just a moment...

# www.cars.com

## Performing security verification

This website uses a security service to protect against malicious bots. This
page is displayed while the website verifies you are not a bot.
"""

TURNSTILE_MD = """Let's confirm you are human

# Let's confirm you are human

Complete the security check before continuing. This step verifies that you are
not a bot, which helps to protect your account and prevent spam.
"""

THIN_MD = """Speed test

## Header & footer links
L8    [Home](https://example.com/)
L9    [About](https://example.com/about)
L10   [Contact](https://example.com/contact)
"""

GOOD_MD = """The quick brown fox jumps over the lazy dog. This is a real article with
several sentences of actual prose, not a bot wall or a navigation shell.
It contains enough words to be accepted by the fast tier without escalating.
"""

LOGIN_MD = """Sign in to continue

Welcome back. Sign in to continue to your account and pick up where you left
off. Members get access to saved articles, newsletters and a personalized
feed. New here? Create a free account today. It only takes a moment to join
and you can unsubscribe at any time. We never sell your personal information.
"""

MEDIUM_MD = """A short but complete page. It has a few sentences of ordinary prose, enough
to be a real page but not enough to satisfy the eager fast-tier word count.
Nothing here looks like a captcha or a bot check, so the browser result should
still be accepted when it comes back from stealth.
"""


class ChallengeDetectionTests(unittest.TestCase):
    def test_reddit_humanity_wall_is_rejected(self):
        self.assertFalse(stealth.is_usable_content(REDDIT_WALL_MD))

    def test_network_security_wall_is_rejected(self):
        self.assertFalse(stealth.is_usable_content(BLOCKED_MD))

    def test_old_reddit_login_wall_is_rejected(self):
        self.assertFalse(stealth.is_usable_content(OLD_REDDIT_MD))

    def test_cloudflare_managed_challenge_is_rejected(self):
        self.assertFalse(stealth.is_usable_content(CLOUDFLARE_MANAGED_MD))

    def test_turnstile_human_check_is_rejected(self):
        self.assertFalse(stealth.is_usable_content(TURNSTILE_MD))

    def test_thin_header_footer_shell_is_rejected(self):
        self.assertFalse(stealth.is_usable_content(THIN_MD))

    def test_normal_prose_is_accepted(self):
        self.assertTrue(stealth.is_usable_content(GOOD_MD))

    def test_long_article_mentioning_bots_is_accepted(self):
        article = "A long article about robots and verifying you are human. " * 250
        self.assertGreater(len(article), 9000)
        self.assertTrue(stealth.is_usable_content(article))


class AggressiveFastGateTests(unittest.TestCase):
    """The fast tier escalates eagerly; the final browser result stays lenient."""

    FAST = dict(min_words=stealth._MIN_BODY_WORDS_FAST, aggressive=True)

    def test_login_wall_escalates_but_browser_result_is_accepted(self):
        self.assertFalse(stealth.is_usable_content(LOGIN_MD, **self.FAST))
        self.assertTrue(stealth.is_usable_content(LOGIN_MD))

    def test_medium_length_page_escalates_but_browser_result_is_accepted(self):
        self.assertFalse(stealth.is_usable_content(MEDIUM_MD, **self.FAST))
        self.assertTrue(stealth.is_usable_content(MEDIUM_MD))

    def test_article_mentioning_captcha_escalates_but_browser_result_is_accepted(self):
        article = "This guide explains how captcha systems work and why they matter. " * 100
        self.assertLess(len(article), stealth._MAX_CHALLENGE_CHARS_FAST)
        self.assertFalse(stealth.is_usable_content(article, **self.FAST))
        self.assertTrue(stealth.is_usable_content(article))

    def test_very_long_article_is_not_escalated(self):
        article = "This guide explains how captcha systems work and why they matter. " * 500
        self.assertGreater(len(article), stealth._MAX_CHALLENGE_CHARS_FAST)
        self.assertTrue(stealth.is_usable_content(article, **self.FAST))

    def test_html_wall_with_large_script_is_rejected(self):
        html = (
            "<html><head><title>Reddit - Prove your humanity</title>"
            "<script>" + "var padding = 1;" * 1000 + "</script></head>"
            "<body><h1>Prove your humanity</h1>"
            "<p>Complete the challenge below and let us know you're a real person.</p>"
            "</body></html>"
        )
        self.assertGreater(len(html), 9000)
        self.assertFalse(stealth.is_usable_content(html, min_words=5))


class FastTierFallbackTests(unittest.TestCase):
    def test_wall_from_fast_tier_escalates_to_stealth(self):
        with patch.object(scrapepage, "is_daemon_alive", lambda: False), \
             patch.object(scrapepage, "get_cached_scrape", lambda key: None), \
             patch.object(scrapepage, "set_cached_scrape") as cache_set, \
             patch.object(scrapepage, "try_fast_html", lambda *a, **k: (True, "<html></html>")), \
             patch.object(scrapepage, "fast_html_to_markdown", lambda *a, **k: REDDIT_WALL_MD), \
             patch.object(scrapepage, "_try_stealth", lambda *a, **k: GOOD_MD):
            result = scrapepage.scrape_single("https://www.reddit.com/r/test/comments/1")

        self.assertEqual(result, GOOD_MD)
        self.assertFalse(
            any(call.args[1] == REDDIT_WALL_MD for call in cache_set.call_args_list),
            "wall results must not be cached",
        )


if __name__ == "__main__":
    unittest.main()
