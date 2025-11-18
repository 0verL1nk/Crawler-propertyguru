"""Manual test for inspecting ZenRows responses.

Usage::

    ZENROWS_APIKEY=xxx \
    ZENROWS_TEST_URL=https://www.propertyguru.com.sg/property-for-sale/29 \
    ZENROWS_TEST_OUTPUT=zenrows_page.html \
    uv run pytest tests/test_zenrows_dump.py -s

This test saves the HTML content to ``zenrows_page_dump.html`` by default and
prints the first 200 characters so you can quickly verify what was returned.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from requests import HTTPError

from crawler.http.providers import ZenRowsHttpProvider

API_KEY_ENV = "ZENROWS_APIKEY"
DEFAULT_URL = "https://www.propertyguru.com.sg/property-for-sale/29"
DEFAULT_OUTPUT = "zenrows_page_dump.html"

pytestmark = pytest.mark.skipif(
    not os.getenv(API_KEY_ENV),
    reason=f"Set {API_KEY_ENV} before running this test",
)


def _get_output_path() -> Path:
    override = os.getenv("ZENROWS_TEST_OUTPUT")
    if override:
        return Path(override)
    return Path.cwd() / DEFAULT_OUTPUT


def test_zenrows_dump() -> None:
    api_key = os.environ[API_KEY_ENV]
    target_url = os.getenv("ZENROWS_TEST_URL", DEFAULT_URL)
    provider = ZenRowsHttpProvider(api_key=api_key)
    status_code = None
    reason = ""

    try:
        response = provider.send_sync(target_url, timeout=60)
        html = response.text
        status_code = response.status_code
        reason = str(response.reason)
    except HTTPError as exc:
        resp = exc.response
        status_code = resp.status_code if resp is not None else None
        reason = getattr(resp, "reason", str(exc)) if resp is not None else str(exc)
        html = resp.text if resp is not None else ""
        print(
            f"ZenRows request returned HTTP error {status_code}: {reason}. "
            "Body has been dumped for inspection."
        )

    output_path = _get_output_path()
    output_path.write_text(html, encoding="utf-8")

    metadata = output_path.with_suffix(output_path.suffix + ".meta.txt")
    metadata.write_text(
        f"status_code: {status_code}\nreason: {reason}\nurl: {target_url}\n",
        encoding="utf-8",
    )

    preview = (html or "")[:200].replace("\n", " ")
    print(f"Saved body to {output_path.resolve()}")
    print(f"Saved metadata to {metadata.resolve()}")
    print(f"Preview: {preview}")

    if html:
        lowered = html.lower()
        if "<html" in lowered or "<!doctype" in lowered:
            print("Response looks like HTML.")
        else:
            print("Response does not look like HTML (possibly JSON / error payload).")
    else:
        print("Response body empty.")


if __name__ == "__main__":  # pragma: no cover - convenience runner
    if not os.getenv(API_KEY_ENV):
        raise SystemExit(f"Please set {API_KEY_ENV} before running this script")
    test_zenrows_dump()
