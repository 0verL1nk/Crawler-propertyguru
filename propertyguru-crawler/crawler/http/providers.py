"""
抽象的 HTTP 供应商（代理）实现，方便在不同供应商之间切换请求方式
"""

from __future__ import annotations

import abc
import types
from typing import Any, Mapping

import aiohttp
import requests


from utils.logger import get_logger

logger = get_logger("HttpProvider")


class HttpProvider(abc.ABC):
    """HTTP请求供应商接口。"""

    name: str

    @abc.abstractmethod
    def send_sync(self, url: str, **kwargs) -> requests.Response:
        """同步请求"""

    @abc.abstractmethod
    async def send_async(self, url: str, session: aiohttp.ClientSession | None = None, **kwargs) -> aiohttp.ClientResponse:
        """异步请求"""

    def _prepare_headers(self, kwargs: dict[str, Any]) -> dict[str, str]:
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        return headers

    def _prepare_timeout(self, kwargs: Mapping[str, Any]) -> int:
        return kwargs.get("timeout", 30)


class DirectHttpProvider(HttpProvider):
    name = "direct"

    def send_sync(self, url: str, **kwargs) -> requests.Response:
        headers = self._prepare_headers(kwargs)
        timeout = kwargs.pop("timeout", 30)
        logger.debug(f"发送直接HTTP请求: {url}")
        response = requests.get(url, headers=headers, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    async def send_async(self, url: str, session: aiohttp.ClientSession | None = None, **kwargs) -> aiohttp.ClientResponse:
        headers = self._prepare_headers(kwargs)
        timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 30))
        if session:
            response = await session.get(url, headers=headers, timeout=timeout, **kwargs)
        else:
            async with aiohttp.ClientSession(timeout=timeout) as new_session:
                response = await new_session.get(url, headers=headers, **kwargs)
        return response


class ZenRowsHttpProvider(HttpProvider):
    name = "zenrows"

    def __init__(self, api_key: str, base_url: str = "https://api.zenrows.com/v1/") -> None:
        self.api_key = api_key
        self.base_url = base_url

    def _build_params(self, url: str, extra_params: Mapping[str, Any]) -> dict[str, Any]:
        params = {
            "url": url,
            "apikey": self.api_key,
            "js_render": "true",
            "premium_proxy": "true",
        }
        params.update(extra_params)
        return params

    def send_sync(self, url: str, **kwargs) -> requests.Response:
        headers = self._prepare_headers(kwargs)
        timeout = kwargs.pop("timeout", 30)
        params = self._build_params(url, kwargs.pop("params", {}))
        logger.debug(f"通过ZenRows发送请求: {url}")
        response = requests.get(self.base_url, params=params, headers=headers, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    async def send_async(self, url: str, session: aiohttp.ClientSession | None = None, **kwargs) -> aiohttp.ClientResponse:
        headers = self._prepare_headers(kwargs)
        timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 30))
        params = self._build_params(url, kwargs.pop("params", {}))
        if session:
            response = await session.get(self.base_url, params=params, headers=headers, timeout=timeout, **kwargs)
        else:
            async with aiohttp.ClientSession(timeout=timeout) as new_session:
                response = await new_session.get(self.base_url, params=params, headers=headers, **kwargs)
        return response


class ScraperApiHttpProvider(HttpProvider):
    name = "scraperapi"

    def __init__(self, api_key: str, base_url: str = "https://api.scraperapi.com/") -> None:
        self.api_key = api_key
        self.base_url = base_url

    def _build_params(self, url: str, extra_params: Mapping[str, Any]) -> dict[str, Any]:
        params = {"api_key": self.api_key, "url": url}
        params.update(extra_params)
        return params

    def send_sync(self, url: str, **kwargs) -> requests.Response:
        headers = self._prepare_headers(kwargs)
        timeout = kwargs.pop("timeout", 30)
        params = self._build_params(url, kwargs.pop("params", {}))
        logger.debug(f"通过ScraperAPI发送请求: {url}")
        response = requests.get(self.base_url, params=params, headers=headers, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    async def send_async(self, url: str, session: aiohttp.ClientSession | None = None, **kwargs) -> aiohttp.ClientResponse:
        headers = self._prepare_headers(kwargs)
        timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 30))
        params = self._build_params(url, kwargs.pop("params", {}))
        if session:
            response = await session.get(self.base_url, params=params, headers=headers, timeout=timeout, **kwargs)
        else:
            async with aiohttp.ClientSession(timeout=timeout) as new_session:
                response = await new_session.get(self.base_url, params=params, headers=headers, **kwargs)
        return response


class ScrapingBeeHttpProvider(HttpProvider):
    name = "scrapingbee"

    def __init__(self, api_key: str, base_url: str = "https://app.scrapingbee.com/api/v1") -> None:
        if not api_key:
            raise ValueError("ScrapingBee provider requires api_key")
        self.api_key = api_key
        self.base_url = base_url

    def _build_params(self, url: str, extra_params: Mapping[str, Any]) -> dict[str, Any]:
        params = {"api_key": self.api_key, "url": url}
        params.update(extra_params)
        return params

    def send_sync(self, url: str, **kwargs) -> requests.Response:
        headers = self._prepare_headers(kwargs)
        timeout = kwargs.pop("timeout", 30)
        params = self._build_params(url, kwargs.pop("params", {}))
        logger.debug(f"通过ScrapingBee发送请求: {url}")
        response = requests.get(self.base_url, params=params, headers=headers, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    async def send_async(self, url: str, session: aiohttp.ClientSession | None = None, **kwargs) -> aiohttp.ClientResponse:
        headers = self._prepare_headers(kwargs)
        timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 30))
        params = self._build_params(url, kwargs.pop("params", {}))
        logger.debug(f"通过ScrapingBee发送异步请求: {url}")
        if session:
            response = await session.get(self.base_url, params=params, headers=headers, timeout=timeout, **kwargs)
        else:
            async with aiohttp.ClientSession(timeout=timeout) as new_session:
                response = await new_session.get(self.base_url, params=params, headers=headers, **kwargs)
        return response


class OxylabsHttpProvider(HttpProvider):
    name = "oxylabs"

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = "https://realtime.oxylabs.io/v1/queries",
        source: str = "universal",
    ) -> None:
        self.username = username
        self.password = password
        self.base_url = base_url
        self.source = source

    def _build_payload(self, url: str, extra_payload: Mapping[str, Any]) -> dict[str, Any]:
        payload = {"source": self.source, "url": url}
        payload.update(extra_payload)
        return payload

    @staticmethod
    def _extract_html(data: Mapping[str, Any]) -> str:
        results = data.get("results")
        if not isinstance(results, list) or not results:
            raise ValueError("Oxylabs 响应缺少 results 字段")
        first = results[0]
        if not isinstance(first, Mapping):
            raise ValueError("Oxylabs 响应的 results[0] 不是对象")
        content = first.get("content")
        if not isinstance(content, str):
            raise ValueError("Oxylabs 响应缺少 results[0].content 字段")
        return content

    def send_sync(self, url: str, **kwargs) -> requests.Response:
        headers = self._prepare_headers(kwargs)
        timeout = kwargs.pop("timeout", 30)
        payload = self._build_payload(url, kwargs.pop("json", {}))
        logger.debug(f"通过Oxylabs发送请求: {url}")
        response = requests.post(
            self.base_url,
            auth=(self.username, self.password),
            json=payload,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )
        response.raise_for_status()
        data = response.json()
        html = self._extract_html(data)
        response._content = html.encode("utf-8")  # type: ignore[attr-defined]
        response.encoding = "utf-8"
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        response.oxylabs_json = data  # type: ignore[attr-defined]
        response.json = types.MethodType(lambda self, **_kwargs: data, response)  # type: ignore[assignment]
        return response

    async def send_async(self, url: str, session: aiohttp.ClientSession | None = None, **kwargs) -> aiohttp.ClientResponse:
        headers = self._prepare_headers(kwargs)
        timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 30))
        payload = self._build_payload(url, kwargs.pop("json", {}))
        logger.debug(f"通过Oxylabs发送异步请求: {url}")

        async def _request(active_session: aiohttp.ClientSession) -> aiohttp.ClientResponse:
            response = await active_session.post(
                self.base_url,
                auth=aiohttp.BasicAuth(self.username, self.password),
                json=payload,
                headers=headers,
                timeout=timeout,
                **kwargs,
            )
            response.raise_for_status()
            data = await response.json()
            html = self._extract_html(data)
            wrapped = _InMemoryHtmlResponse(
                status=response.status,
                headers=dict(response.headers),
                url=str(response.url),
                reason=response.reason,
                html=html,
                json_payload=data,
            )
            wrapped.oxylabs_json = data  # type: ignore[attr-defined]
            await response.release()
            return wrapped  # type: ignore[return-value]

        if session:
            return await _request(session)

        async with aiohttp.ClientSession(timeout=timeout) as new_session:
            return await _request(new_session)


class _InMemoryHtmlResponse:
    """轻量封装，提供与 aiohttp.ClientResponse 部分类似的接口。"""

    def __init__(
        self,
        *,
        status: int,
        headers: Mapping[str, str],
        url: str,
        reason: str | None,
        html: str,
        json_payload: Mapping[str, Any],
    ) -> None:
        self.status = status
        self.headers = headers
        self.url = url
        self.reason = reason
        self.raw_json = json_payload
        self._html = html

    async def text(self) -> str:
        return self._html

    async def json(self) -> Mapping[str, Any]:
        return self.raw_json

    async def read(self) -> bytes:
        return self._html.encode("utf-8")

    def release(self) -> None:  # 兼容 aiohttp.ClientResponse 接口
        return None


class FirecrawlHttpProvider(HttpProvider):
    name = "firecrawl"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.firecrawl.dev/v2/scrape",
        default_formats: list[str] | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Firecrawl provider requires api_key")
        self.api_key = api_key
        self.base_url = base_url
        self.default_formats = default_formats or ["html"]

    def _auth_headers(self, headers: Mapping[str, Any]) -> dict[str, str]:
        merged_headers = {**headers}
        merged_headers.setdefault("Content-Type", "application/json")
        merged_headers["Authorization"] = f"Bearer {self.api_key}"
        return merged_headers

    def _build_payload(self, url: str, extra_payload: Mapping[str, Any]) -> dict[str, Any]:
        payload = {"url": url, "formats": self.default_formats}
        payload.update(extra_payload)
        return payload

    @staticmethod
    def _extract_html(data: Mapping[str, Any]) -> str:
        data_block = data.get("data")
        if not isinstance(data_block, Mapping):
            raise ValueError("Firecrawl 响应缺少 data 字段")
        html = data_block.get("html")
        if not isinstance(html, str):
            raise ValueError("Firecrawl 响应缺少 data.html 字段")
        return html

    def send_sync(self, url: str, **kwargs) -> requests.Response:
        headers = self._auth_headers(self._prepare_headers(kwargs))
        timeout = kwargs.pop("timeout", 30)
        payload = self._build_payload(url, kwargs.pop("json", {}))
        logger.debug(f"通过Firecrawl发送请求: {url}")
        response = requests.post(self.base_url, json=payload, headers=headers, timeout=timeout, **kwargs)
        response.raise_for_status()
        data = response.json()
        html = self._extract_html(data)
        response._content = html.encode("utf-8")
        response.encoding = "utf-8"
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        response.firecrawl_json = data  # type: ignore[attr-defined]
        response.json = types.MethodType(lambda self, **_kwargs: data, response)  # type: ignore[assignment]
        return response

    async def send_async(
        self,
        url: str,
        session: aiohttp.ClientSession | None = None,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        headers = self._auth_headers(self._prepare_headers(kwargs))
        timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 30))
        payload = self._build_payload(url, kwargs.pop("json", {}))
        logger.debug(f"通过Firecrawl发送异步请求: {url}")

        async def _request(active_session: aiohttp.ClientSession) -> aiohttp.ClientResponse:
            response = await active_session.post(self.base_url, json=payload, headers=headers, timeout=timeout, **kwargs)
            response.raise_for_status()
            data = await response.json()
            html = self._extract_html(data)
            wrapped = _InMemoryHtmlResponse(
                status=response.status,
                headers=dict(response.headers),
                url=str(response.url),
                reason=response.reason,
                html=html,
                json_payload=data,
            )
            wrapped.firecrawl_json = data  # type: ignore[attr-defined]
            await response.release()
            return wrapped  # type: ignore[return-value]

        if session:
            return await _request(session)

        async with aiohttp.ClientSession(timeout=timeout) as new_session:
            return await _request(new_session)


PROVIDER_REGISTRY: dict[str, type[HttpProvider]] = {
    "direct": DirectHttpProvider,
    "zenrows": ZenRowsHttpProvider,
    "scraperapi": ScraperApiHttpProvider,
    "scrapingbee": ScrapingBeeHttpProvider,
    "oxylabs": OxylabsHttpProvider,
    "firecrawl": FirecrawlHttpProvider,
}


def create_provider(name: str, **options: Any) -> HttpProvider:
    provider_cls = PROVIDER_REGISTRY.get(name.lower())
    if not provider_cls:
        raise ValueError(f"Unknown HTTP provider: {name}")
    return provider_cls(**options)
