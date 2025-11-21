"""Manual test helper to verify Oxylabs HTTP responses include pagination data.

Run with:
    uv run python tests/manual/test_oxylabs_pagination.py --page 47 --provider oxylabs

Requires the relevant provider credentials set in the environment (e.g. OXYLABS_USERNAME
and OXYLABS_PASSWORD).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from bs4 import BeautifulSoup

from crawler.http.client import HttpClient
from crawler.pages.listing_http import ListingHttpCrawler


def _parse_total_pages(html: str) -> int | None:
    """Reuse the production parser to inspect pagination."""
    return ListingHttpCrawler._extract_total_pages_from_html(html)


def _extract_next_data(html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "lxml")
    script_tag = soup.find("script", id="__NEXT_DATA__", type="application/json")
    if not script_tag or not script_tag.string:
        return None
    return json.loads(script_tag.string)


def run_test(url: str, provider: str | None, timeout: int) -> None:
    print(f"Requesting {url} via provider={provider or 'default'} (timeout={timeout}s)...")
    client = HttpClient(provider_name=provider)
    response = client.get_sync(url, timeout=timeout)
    print(f"Status: {response.status_code}")
    print(f"Headers: content-length={response.headers.get('Content-Length')} content-type={response.headers.get('Content-Type')}")

    html = response.text
    print(f"Fetched HTML length: {len(html):,}")

    total_pages = _parse_total_pages(html)
    print(f"paginationData.totalPages parsed via crawler parser: {total_pages}")

    next_data = _extract_next_data(html)
    if next_data is None:
        print("__NEXT_DATA__ not found or invalid JSON.")
    else:
        try:
            pagination = (
                next_data.get("props", {})
                .get("pageProps", {})
                .get("pageData", {})
                .get("data", {})
                .get("paginationData", {})
            )
            print(f"Raw paginationData keys: {sorted(pagination.keys()) if isinstance(pagination, dict) else 'N/A'}")
            print(f"Raw paginationData.totalPages: {pagination.get('totalPages') if isinstance(pagination, dict) else None}")
        except Exception as exc:  # pragma: no cover - manual diagnostics
            print(f"Failed to inspect paginationData: {exc}")


def build_listing_url(page: int) -> str:
    base = ListingHttpCrawler.BASE_URL
    return base if page <= 1 else f"{base}/{page}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual Oxylabs listing pagination tester")
    parser.add_argument("--page", type=int, default=1, help="Listing page number to request")
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Full URL to request (overrides --page)",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        help="HTTP provider name (defaults to env HTTP_PROVIDER)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds",
    )
    args = parser.parse_args()

    url = args.url or build_listing_url(args.page)

    try:
        run_test(url=url, provider=args.provider, timeout=args.timeout)
    except Exception as exc:  # pragma: no cover - manual troubleshooting surface
        print(f"Request failed: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
