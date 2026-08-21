# tests/test_arxiv.py
import unittest
from paper_search_mcp.academic_platforms.arxiv import ArxivSearcher, _build_search_query


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
        self.assertEqual(_build_search_query('all:"exact phrase"'), 'all:"exact phrase"')

    def test_explicit_field_prefix_passed_through_unwrapped(self):
        self.assertEqual(_build_search_query("ti:Attention Is All You Need"), "ti:Attention Is All You Need")

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


if __name__ == '__main__':
    unittest.main()