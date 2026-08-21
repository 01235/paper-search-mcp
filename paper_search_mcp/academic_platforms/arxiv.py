# paper_search_mcp/sources/arxiv.py
import os
import re
import threading
import time
from datetime import datetime
from typing import List

import feedparser
import requests
from pypdf import PdfReader

from ..paper import Paper
from ..utils import extract_doi
from .base import PaperSource

_ARXIV_FIELD_PREFIX_RE = re.compile(r"^(ti|au|abs|co|jr|cat|rn|id|all):")
_ARXIV_BOOLEAN_OP_RE = re.compile(r"\b(AND|OR|ANDNOT)\b")


def _build_search_query(query: str) -> str:
    """Build an arXiv API ``search_query`` value from a free-text query.

    A bare multi-word query passed straight into ``all:`` (e.g.
    ``all:attention is all you need``) hits a pathologically slow -- often
    effectively hanging -- code path on arXiv's search backend; the exact
    same words as a quoted phrase (``all:"attention is all you need"``)
    return in well under a second. Confirmed empirically 2026-08-21 (see
    https://github.com/openags/paper-search-mcp/issues -- HTTP->HTTPS +
    unquoted multi-word query hang). Only a plain multi-word query gets
    phrase-quoted here: a caller already using arXiv's own syntax (a field
    prefix like ``ti:``/``au:``, an explicit ``AND``/``OR``/``ANDNOT``, or
    their own quoting) is passed straight through unchanged, since wrapping
    an already-structured query in quotes could change its meaning.
    """
    q = query.strip()
    if not q:
        return "all:"
    has_field_prefix = bool(_ARXIV_FIELD_PREFIX_RE.match(q))
    looks_structured = (
        '"' in q or bool(_ARXIV_BOOLEAN_OP_RE.search(q)) or has_field_prefix
    )
    if looks_structured:
        return q if has_field_prefix else f"all:{q}"
    if " " in q:
        return f'all:"{q}"'
    return f"all:{q}"


class ArxivSearcher(PaperSource):
    """Searcher for arXiv papers"""

    # export.arxiv.org's HTTP endpoint hangs on the HTTP->HTTPS upgrade in
    # some network environments (observed: instant response over https://,
    # a 30s read-timeout-per-attempt hang over http:// with no server error
    # to retry against) — use https:// directly rather than relying on a
    # redirect that may never resolve.
    BASE_URL = "https://export.arxiv.org/api/query"

    # arXiv's API courtesy policy asks for no more than one request every 3
    # seconds: https://arxiv.org/help/api/user-manual#Quickstart . Nothing
    # previously enforced this *between* calls -- only backoff *within* one
    # already-failed call's retries -- so back-to-back search() calls (an
    # agent querying several topics in a row, or just rapid manual testing)
    # could outrun arXiv's own rate limiter on their own. This class is
    # instantiated once and reused for the server's whole lifetime (see the
    # module-level `arxiv_searcher` in server.py), so instance-level pacing
    # state actually protects real usage, not just one call.
    _MIN_REQUEST_INTERVAL = 3.0

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "paper-search-mcp/1.0 (mailto:openags@example.com)",
                "Accept": "application/atom+xml, application/xml;q=0.9, */*;q=0.8",
            }
        )
        self._last_request_at = 0.0
        self._pacing_lock = threading.Lock()

    def _wait_for_courtesy_window(self) -> None:
        """Block until at least _MIN_REQUEST_INTERVAL has passed since this
        instance's last request to BASE_URL.
        """
        with self._pacing_lock:
            wait = self._MIN_REQUEST_INTERVAL - (
                time.monotonic() - self._last_request_at
            )
            if wait > 0:
                time.sleep(wait)
            self._last_request_at = time.monotonic()

    def search(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        **kwargs,
    ) -> List[Paper]:
        params = {
            "search_query": _build_search_query(query),
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        response = None
        for attempt in range(3):
            self._wait_for_courtesy_window()
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=30)
            except requests.RequestException:
                time.sleep((attempt + 1) * 1.5)
                continue
            if response.status_code == 200:
                break
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep((attempt + 1) * 1.5)
                continue
            break

        if response is None or response.status_code != 200:
            return []

        feed = feedparser.parse(response.content)
        papers = []
        for entry in feed.entries:
            try:
                authors = [author.name for author in entry.authors]
                published = datetime.strptime(entry.published, "%Y-%m-%dT%H:%M:%SZ")
                updated = datetime.strptime(entry.updated, "%Y-%m-%dT%H:%M:%SZ")
                pdf_url = next(
                    (
                        link.href
                        for link in entry.links
                        if link.type == "application/pdf"
                    ),
                    "",
                )

                # Try to extract DOI from entry.doi or links or summary
                doi = (
                    entry.get("doi", "")
                    or extract_doi(entry.summary)
                    or extract_doi(entry.id)
                )
                for link in entry.links:
                    if link.get("title") == "doi":
                        doi = doi or extract_doi(link.href)

                papers.append(
                    Paper(
                        paper_id=entry.id.split("/")[-1],
                        title=entry.title,
                        authors=authors,
                        abstract=entry.summary,
                        url=entry.id,
                        pdf_url=pdf_url,
                        published_date=published,
                        updated_date=updated,
                        source="arxiv",
                        categories=[tag.term for tag in entry.tags],
                        keywords=[],
                        doi=doi,
                    )
                )
            except Exception as e:
                print(f"Error parsing arXiv entry: {e}")
        return papers

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
        response = requests.get(pdf_url)
        os.makedirs(save_path, exist_ok=True)
        output_file = f"{save_path}/{paper_id}.pdf"
        with open(output_file, "wb") as f:
            f.write(response.content)
        return output_file

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Read a paper and convert it to text format.

        Args:
            paper_id: arXiv paper ID
            save_path: Directory where the PDF is/will be saved

        Returns:
            str: The extracted text content of the paper
        """
        # First ensure we have the PDF
        pdf_path = f"{save_path}/{paper_id}.pdf"
        if not os.path.exists(pdf_path):
            pdf_path = self.download_pdf(paper_id, save_path)

        # Read the PDF
        try:
            reader = PdfReader(pdf_path)
            text = ""

            # Extract text from each page
            for page in reader.pages:
                text += page.extract_text() + "\n"

            return text.strip()
        except Exception as e:
            print(f"Error reading PDF for paper {paper_id}: {e}")
            return ""


if __name__ == "__main__":
    # 测试 ArxivSearcher 的功能
    searcher = ArxivSearcher()

    # 测试搜索功能
    print("Testing search functionality...")
    query = "machine learning"
    max_results = 5
    try:
        papers = searcher.search(query, max_results=max_results)
        print(f"Found {len(papers)} papers for query '{query}':")
        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper.title} (ID: {paper.paper_id})")
    except Exception as e:
        print(f"Error during search: {e}")

    # 测试 PDF 下载功能
    if papers:
        print("\nTesting PDF download functionality...")
        paper_id = papers[0].paper_id
        save_path = "./downloads"  # 确保此目录存在
        try:
            os.makedirs(save_path, exist_ok=True)
            pdf_path = searcher.download_pdf(paper_id, save_path)
            print(f"PDF downloaded successfully: {pdf_path}")
        except Exception as e:
            print(f"Error during PDF download: {e}")

    # 测试论文阅读功能
    if papers:
        print("\nTesting paper reading functionality...")
        paper_id = papers[0].paper_id
        try:
            text_content = searcher.read_paper(paper_id)
            print("\nFirst 500 characters of the paper content:")
            print(text_content[:500] + "...")
            print(f"\nTotal length of extracted text: {len(text_content)} characters")
        except Exception as e:
            print(f"Error during paper reading: {e}")
