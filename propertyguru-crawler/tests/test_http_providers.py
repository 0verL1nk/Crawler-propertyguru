"""Live HTTP provider smoke tests.

Set RUN_HTTP_PROVIDER_TESTS=1 to enable these tests. Each test hits the real
service and therefore requires valid credentials for the target provider.
"""

from __future__ import annotations

import importlib
import os

pytest_spec = importlib.util.find_spec("pytest")
if pytest_spec:
    pytest = importlib.import_module("pytest")
else:  # pragma: no cover - allow linting without pytest installed
    pytest = None  # type: ignore

from crawler.http.providers import (
    DirectHttpProvider,
    FirecrawlHttpProvider,
    ScraperApiHttpProvider,
    ScrapingBeeHttpProvider,
    ZenRowsHttpProvider,
)

try:
    from crawler.http.providers import OxylabsHttpProvider
except ImportError:  # pragma: no cover - optional dependency guard
    OxylabsHttpProvider = None  # type: ignore

RUN_LIVE_TESTS = os.getenv("RUN_HTTP_PROVIDER_TESTS") == "1"

if pytest:  # pragma: no branch
    pytestmark = pytest.mark.skipif(
        not RUN_LIVE_TESTS,
        reason="Set RUN_HTTP_PROVIDER_TESTS=1 to run live HTTP provider tests.",
    )
else:  # pragma: no cover - allow importing file without pytest
    pytestmark = []

TARGET_URL = os.getenv(
    "TEST_PROVIDER_URL",
    "https://www.propertyguru.com.sg/property-for-sale/1",
)


def _assert_looks_like_html(html: str) -> None:
    lowered = html.lower()
    assert "<html" in lowered or "<!doctype" in lowered, "response is not HTML"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"Environment variable {name} is required for this test")
    return value


def test_direct_provider_sync() -> None:
    provider = DirectHttpProvider()
    response = provider.send_sync(TARGET_URL, timeout=30)
    _assert_looks_like_html(response.text)


def test_zenrows_provider_sync() -> None:
    api_key = _require_env("ZENROWS_APIKEY")
    provider = ZenRowsHttpProvider(api_key=api_key)
    response = provider.send_sync(TARGET_URL, timeout=30)
    _assert_looks_like_html(response.text)


def test_scraperapi_provider_sync() -> None:
    api_key = _require_env("SCRAPERAPI_KEY")
    provider = ScraperApiHttpProvider(api_key=api_key)
    response = provider.send_sync(TARGET_URL, timeout=30)
    _assert_looks_like_html(response.text)


def test_scrapingbee_provider_sync() -> None:
    api_key = _require_env("SCRAPINGBEE_API_KEY")
    provider = ScrapingBeeHttpProvider(api_key=api_key)
    response = provider.send_sync(TARGET_URL, timeout=30, params={"render_js": "false"})
    _assert_looks_like_html(response.text)


def test_firecrawl_provider_sync() -> None:
    api_key = _require_env("FIRECRAWL_API_KEY")
    provider = FirecrawlHttpProvider(api_key=api_key)
    response = provider.send_sync(TARGET_URL, timeout=60)
    _assert_looks_like_html(response.text)


# pytest may be None in environments without the dependency; guard decorator usage
if pytest:  # pragma: no branch
    async_mark = pytest.mark.asyncio
else:  # pragma: no cover
    def async_mark(fn):
        return fn


@async_mark
async def test_firecrawl_provider_async() -> None:
    api_key = _require_env("FIRECRAWL_API_KEY")
    provider = FirecrawlHttpProvider(api_key=api_key)
    response = await provider.send_async(TARGET_URL, timeout=60)
    html = await response.text()
    _assert_looks_like_html(html)


@pytest.mark.skipif(OxylabsHttpProvider is None, reason="Oxylabs provider not available")
def test_oxylabs_provider_sync() -> None:
    username = _require_env("OXYLABS_USERNAME")
    password = _require_env("OXYLABS_PASSWORD")
    provider = OxylabsHttpProvider(username=username, password=password)
    response = provider.send_sync(TARGET_URL, timeout=60)
    _assert_looks_like_html(response.text)
