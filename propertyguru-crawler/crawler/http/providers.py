"""
抽象的 HTTP 供应商（代理）实现，方便在不同供应商之间切换请求方式
"""

from __future__ import annotations

import abc
from typing import Any, Mapping

import aiohttp
from aiohttp import BasicAuth
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
            "js_render": "false",
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
        return response

    async def send_async(self, url: str, session: aiohttp.ClientSession | None = None, **kwargs) -> aiohttp.ClientResponse:
        headers = self._prepare_headers(kwargs)
        timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 30))
        payload = self._build_payload(url, kwargs.pop("json", {}))
        if session:
            response = await session.post(
                self.base_url,
                auth=aiohttp.BasicAuth(self.username, self.password),
                json=payload,
                headers=headers,
                timeout=timeout,
                **kwargs,
            )
        else:
            async with aiohttp.ClientSession(timeout=timeout) as new_session:
                response = await new_session.post(
                    self.base_url,
                    auth=aiohttp.BasicAuth(self.username, self.password),
                    json=payload,
                    headers=headers,
                    **kwargs,
                )
        return response


PROVIDER_REGISTRY: dict[str, type[HttpProvider]] = {
    "direct": DirectHttpProvider,
    "zenrows": ZenRowsHttpProvider,
    "scraperapi": ScraperApiHttpProvider,
    "oxylabs": OxylabsHttpProvider,
}


def create_provider(name: str, **options: Any) -> HttpProvider:
    provider_cls = PROVIDER_REGISTRY.get(name.lower())
    if not provider_cls:
        raise ValueError(f"Unknown HTTP provider: {name}")
    return provider_cls(**options)
