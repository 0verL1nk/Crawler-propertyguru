"""Manual test for inspecting ScrapingBee responses.

Usage::

    SCRAPINGBEE_API_KEY=xxx \
    SCRAPINGBEE_TEST_URL=https://www.propertyguru.com.sg/property-for-sale/29 \
    uv run pytest tests/test_scrapingbee_dump.py -s

By default the HTML will be written to ``scrapingbee_page_dump.html`` under the
current working directory; override via ``SCRAPINGBEE_TEST_OUTPUT``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from crawler.http.providers import ScrapingBeeHttpProvider

API_KEY_ENV = "SCRAPINGBEE_API_KEY"
DEFAULT_URL = "https://www.propertyguru.com.sg/property-for-sale/29"
DEFAULT_OUTPUT = "scrapingbee_page_dump.html"

pytestmark = pytest.mark.skipif(
    not os.getenv(API_KEY_ENV),
    reason=f"Set {API_KEY_ENV} before running this test",
)


def _get_output_path() -> Path:
    override = os.getenv("SCRAPINGBEE_TEST_OUTPUT")
    if override:
        return Path(override)
    return Path.cwd() / DEFAULT_OUTPUT


def test_scrapingbee_dump(tmp_path) -> None:
    api_key = os.environ[API_KEY_ENV]
    target_url = os.getenv("SCRAPINGBEE_TEST_URL", DEFAULT_URL)
    provider = ScrapingBeeHttpProvider(api_key=api_key)
    response = provider.send_sync(target_url, timeout=60)
    html = response.text

    output_path = _get_output_path()
    output_path.write_text(html, encoding="utf-8")

    # 方便快速查看：stdout 打印前200字符
    preview = html[:200].replace("\n", " ")
    print(f"Saved HTML to {output_path.resolve()}")
    print(f"Preview: {preview}")

    lowered = html.lower()
    assert "<html" in lowered or "<!doctype" in lowered, "Response not HTML"


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    if not os.getenv(API_KEY_ENV):
        raise SystemExit(f"Please set {API_KEY_ENV} before running this script")
    test_scrapingbee_dump(tmp_path=None)  # type: ignore[arg-type]
