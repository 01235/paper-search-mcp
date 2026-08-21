# tests/test_arxiv.py
import unittest
from unittest.mock import patch

from paper_search_mcp.academic_platforms.arxiv import ArxivSearcher, _build_search_query


class TestCourtesyPacing(unittest.TestCase):
    """No previous mechanism enforced arXiv's documented 3-second minimum
    request interval *between* calls (only backoff *within* one already-
    failed call's retries) -- confirmed by triggering arXiv's own rate
    limiter with a handful of rapid manual requests, 2026-08-21.
    """

    def test_first_request_does_not_wait(self):
        searcher = ArxivSearcher()
        with patch(
            "paper_search_mcp.academic_platforms.arxiv.time.sleep"
        ) as mock_sleep:
            searcher._wait_for_courtesy_window()
        mock_sleep.assert_not_called()

    def test_second_request_waits_out_the_remaining_window(self):
        searcher = ArxivSearcher()
        # fake_now advances by 0.1s per time.monotonic() call so the two
        # _wait_for_courtesy_window() calls don't collapse to one instant.
        fake_now = [100.0]

        def advancing_monotonic():
            fake_now[0] += 0.1
            return fake_now[0]

        with (
            patch(
                "paper_search_mcp.academic_platforms.arxiv.time.monotonic",
                side_effect=advancing_monotonic,
            ),
            patch("paper_search_mcp.academic_platforms.arxiv.time.sleep") as mock_sleep,
        ):
            searcher._wait_for_courtesy_window()
            searcher._wait_for_courtesy_window()

        mock_sleep.assert_called_once()
        (waited,) = mock_sleep.call_args.args
        self.assertAlmostEqual(
            waited, ArxivSearcher._MIN_REQUEST_INTERVAL - 0.1, places=6
        )

    def test_request_after_the_window_has_elapsed_does_not_wait(self):
        searcher = ArxivSearcher()
        searcher._last_request_at = 0.0
        with patch(
            "paper_search_mcp.academic_platforms.arxiv.time.monotonic",
            return_value=ArxivSearcher._MIN_REQUEST_INTERVAL + 10,
        ):
            with patch(
                "paper_search_mcp.academic_platforms.arxiv.time.sleep"
            ) as mock_sleep:
                searcher._wait_for_courtesy_window()
        mock_sleep.assert_not_called()


class TestBuildSearchQuery(unittest.TestCase):
    """A plain multi-word query hangs arXiv's search backend unless phrase-
    quoted (confirmed empirically 2026-08-21); these lock in the fix without
    hitting the network.
    """

    def test_single_word_left_bare(self):
        self.assertEqual(_build_search_query("transformer"), "all:transformer")

    def test_multi_word_gets_phrase_quoted(self):
        self.assertEqual(
            _build_search_query("Attention Is All You Need"),
            'all:"Attention Is All You Need"',
        )

    def test_already_quoted_passed_through(self):
        self.assertEqual(
            _build_search_query('all:"exact phrase"'), 'all:"exact phrase"'
        )

    def test_explicit_field_prefix_passed_through_unwrapped(self):
        self.assertEqual(
            _build_search_query("ti:Attention Is All You Need"),
            "ti:Attention Is All You Need",
        )

    def test_boolean_operator_passed_through(self):
        self.assertEqual(
            _build_search_query("transformer AND attention"),
            "all:transformer AND attention",
        )

    def test_empty_query(self):
        self.assertEqual(_build_search_query("   "), "all:")


class TestArxivSearcher(unittest.TestCase):
    def test_search(self):
        searcher = ArxivSearcher()
        papers = searcher.search("machine learning", max_results=10)
        print(f"Found {len(papers)} papers for query 'machine learning':")
        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper.title} (ID: {paper.paper_id})")
        if not papers:
            self.skipTest("arXiv API is unavailable or rate-limited")
        self.assertEqual(len(papers), 10)
        self.assertTrue(papers[0].title)

    def test_search_multi_word_natural_language_query(self):
        """Regression test: this exact query used to hang before the
        HTTPS + phrase-quoting fix.
        """
        searcher = ArxivSearcher()
        papers = searcher.search("Attention Is All You Need", max_results=3)
        if not papers:
            self.skipTest("arXiv API is unavailable or rate-limited")
        self.assertTrue(any("attention" in p.title.lower() for p in papers))


if __name__ == "__main__":
    unittest.main()
