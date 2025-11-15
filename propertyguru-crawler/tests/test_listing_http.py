"""Tests for ListingHttpCrawler helpers."""

from crawler.pages.listing_http import ListingHttpCrawler

SAMPLE_HTML = """
<html>
  <head>
    <script id="__NEXT_DATA__" type="application/json">
      {"props":{"pageProps":{"pageData":{"data":{"paginationData":{"totalPages":2743}}}}}}
    </script>
  </head>
  <body></body>
</html>
"""


def test_extract_total_pages_from_html_success():
    assert ListingHttpCrawler._extract_total_pages_from_html(SAMPLE_HTML) == 2743


def test_extract_total_pages_from_html_missing_script():
    assert ListingHttpCrawler._extract_total_pages_from_html("<html></html>") is None
