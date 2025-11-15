"""
Pyppeteer-based remote browser driver (remote_new)
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import threading
import time
from typing import Any

from selenium.common.exceptions import TimeoutException

from ..base import Browser

try:
    import pyppeteer
except ImportError:  # pragma: no cover - optional dependency
    pyppeteer = None

PyppeteerBrowser = Any
ElementHandle = Any
Page = Any



class _AsyncLoopThread:
    """Dedicated event-loop thread for running Pyppeteer coroutines."""

    def __init__(self, name: str = "PyppeteerLoop"):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name=name, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro):
        if self._loop.is_closed():
            raise RuntimeError("Event loop is closed")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def stop(self):
        if not self._loop.is_closed():
            if self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)
            try:
                self._loop.close()
            except RuntimeError:
                pass

    def is_closed(self) -> bool:
        return self._loop.is_closed()


class PyppeteerElement:
    """Minimal Selenium-like wrapper over Pyppeteer ElementHandle."""

    def __init__(self, handle: ElementHandle, owner: PyppeteerBrowserNew):
        self._handle = handle
        self._owner = owner

    @property
    def handle(self) -> ElementHandle:
        return self._handle

    def __bool__(self) -> bool:  # pragma: no cover - convenience
        return self._handle is not None

    def find_element(self, by: str, value: str) -> PyppeteerElement | None:
        selector = self._owner._convert_selector(by, value)
        return self._owner._run(self._query_selector(selector))

    def find_elements(self, by: str, value: str) -> list[PyppeteerElement]:
        selector = self._owner._convert_selector(by, value)
        return self._owner._run(self._query_selector_all(selector))

    def get_attribute(self, name: str) -> str | None:
        return self._owner._run(self._get_attribute(name))

    @property
    def text(self) -> str:
        return self._owner._run(self._get_inner_text()) or ""

    def click(self):
        self._owner._run(self._handle.click())

    def is_displayed(self) -> bool:
        return self._owner._run(self._is_displayed())

    def is_enabled(self) -> bool:
        return self._owner._run(self._is_enabled())

    async def _query_selector(self, selector: tuple[str, str]) -> PyppeteerElement | None:
        strategy, value = selector
        handle: ElementHandle | None
        if strategy == "css":
            handle = await self._handle.querySelector(value)
        else:  # xpath
            matches = await self._handle.xpath(value)
            handle = matches[0] if matches else None
        return PyppeteerElement(handle, self._owner) if handle else None

    async def _query_selector_all(self, selector: tuple[str, str]) -> list[PyppeteerElement]:
        strategy, value = selector
        if strategy == "css":
            handles = await self._handle.querySelectorAll(value)
        else:
            handles = await self._handle.xpath(value)
        return [PyppeteerElement(handle, self._owner) for handle in handles]

    async def _get_attribute(self, name: str) -> str | None:
        return await self._handle.evaluate("(el, attr) => el.getAttribute(attr)", name)

    async def _get_inner_text(self) -> str:
        return await self._handle.evaluate("el => el.innerText || ''")

    async def _is_displayed(self) -> bool:
        return await self._handle.evaluate(
            "el => !!(el.offsetParent || el.getClientRects().length)"
        )

    async def _is_enabled(self) -> bool:
        return await self._handle.evaluate(
            "el => !(el.disabled || el.getAttribute('aria-disabled') === 'true')"
        )


class PyppeteerBrowserNew(Browser):
    """Remote browser powered by Pyppeteer (remote_new)."""

    def __init__(
        self,
        browser_ws_endpoint: str | None = None,
        disable_images: bool = False,
        browser_type: str = "chrome",
    ) -> None:
        super().__init__()
        self.browser_ws_endpoint = browser_ws_endpoint or os.getenv("REMOTE_BROWSER_WS_ENDPOINT")
        self.disable_images = disable_images
        self.browser_type = browser_type

        if not self.browser_ws_endpoint:
            raise ValueError("REMOTE_BROWSER_WS_ENDPOINT is required for remote_new browser")

        if pyppeteer is None:
            raise ImportError("pyppeteer is not installed. Please `pip install pyppeteer`." )

        self._loop_runner = _AsyncLoopThread()
        self.browser: PyppeteerBrowser | None = None
        self.page: Page | None = None
        self._closing = False

    def _run(self, coro):
        return self._loop_runner.run(coro)

    def connect(self, options: Any = None):  # noqa: ARG002
        self._run(self._connect())

    async def connect_async(self, options: Any = None):  # noqa: ARG002
        await asyncio.to_thread(self.connect)

    async def _connect(self):
        self.browser = await pyppeteer.connect(browserWSEndpoint=self.browser_ws_endpoint)
        pages = await self.browser.pages()
        if pages:
            self.page = pages[0]
        else:
            self.page = await self.browser.newPage()

        if self.disable_images:
            await self._configure_resource_blocking()

        # 让浏览器实例本身扮演 WebDriver，以兼容现有等待/解析逻辑
        self.driver = self

    def close(self):
        if self._closing:
            return
        self._closing = True
        try:
            if not self._loop_runner.is_closed():
                self._run(self._close())
        except RuntimeError:
            pass
        finally:
            self._loop_runner.stop()

    async def _close(self):
        with contextlib.suppress(Exception):
            if self.page:
                await self.page.close()
        with contextlib.suppress(Exception):
            if self.browser:
                await self.browser.disconnect()
        self.page = None
        self.browser = None
        self.driver = None

    def get(self, url: str):
        if not self.page:
            raise RuntimeError("Browser not connected")
        self._run(self.page.goto(url, waitUntil="networkidle2"))

    def find_element(self, by: str, value: str):
        if not self.page:
            raise RuntimeError("Browser not connected")
        selector = self._convert_selector(by, value)
        return self._run(self._query_selector(selector))

    def find_elements(self, by: str, value: str):
        if not self.page:
            raise RuntimeError("Browser not connected")
        selector = self._convert_selector(by, value)
        return self._run(self._query_selector_all(selector))

    def execute_script(self, script: str, *args):
        if not self.page:
            raise RuntimeError("Browser not connected")
        js_args = [arg.handle if isinstance(arg, PyppeteerElement) else arg for arg in args]
        return self._run(self.page.evaluate(script, *js_args))

    def wait(self, timeout: int = 30):
        return SimpleWait(self, timeout)

    def get_page_source(self) -> str:
        if not self.page:
            raise RuntimeError("Browser not connected")
        return self._run(self.page.content())

    def _convert_selector(self, by: str, value: str) -> tuple[str, str]:
        if by.lower() in {"css selector", "css"}:
            return "css", value
        if by.lower() == "xpath":
            return "xpath", value
        return "css", value

    async def _query_selector(self, selector: tuple[str, str]):
        if not self.page:
            return None
        strategy, value = selector
        handle = await (self.page.querySelector(value) if strategy == "css" else self.page.xpath(value))
        if isinstance(handle, list):  # xpath returns list
            handle = handle[0] if handle else None
        return PyppeteerElement(handle, self) if handle else None

    async def _query_selector_all(self, selector: tuple[str, str]):
        if not self.page:
            return []
        strategy, value = selector
        handles = await (self.page.querySelectorAll(value) if strategy == "css" else self.page.xpath(value))
        return [PyppeteerElement(handle, self) for handle in handles]

    async def _configure_resource_blocking(self):
        if not self.page:
            return
        await self.page.setRequestInterception(True)
        blocked = {
            ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
            ".css", ".woff", ".woff2", ".ttf", ".otf",
            ".mp4", ".webm", ".ogg", ".mp3", ".wav",
        }

        async def intercept(request):
            url = request.url.lower()
            if any(url.endswith(ext) for ext in blocked):
                await request.abort()
            else:
                await request.continue_()

        self.page.on("request", lambda request: asyncio.ensure_future(intercept(request)))


class SimpleWait:
    """轻量级的 WebDriverWait 替代品，兼容现有解析逻辑。"""

    def __init__(self, browser: PyppeteerBrowserNew, timeout: int = 30, poll_frequency: float = 0.5):
        self.browser = browser
        self.timeout = timeout
        self.poll_frequency = poll_frequency

    def until(self, condition):
        end_time = time.time() + self.timeout
        last_exc: Exception | None = None
        while True:
            try:
                value = condition(self.browser)
                if value:
                    return value
            except Exception as exc:  # pragma: no cover - best effort fallback
                last_exc = exc

            if time.time() > end_time:
                if last_exc:
                    raise TimeoutException("Condition not met before timeout") from last_exc
                raise TimeoutException("Condition not met before timeout")
            time.sleep(self.poll_frequency)
