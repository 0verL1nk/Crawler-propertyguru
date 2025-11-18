"""
HTTP客户端模块
支持直接HTTP请求和外部服务（如ZenRows）请求
"""

from __future__ import annotations

import os
from typing import Any

import aiohttp
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.logger import get_logger

logger = get_logger("HttpClient")


from crawler.http.providers import create_provider


class HttpClient:
    """HTTP客户端封装"""

    def __init__(
        self,
        provider_name: str | None = None,
        provider_options: dict | None = None,
    ):
        """
        初始化HTTP客户端

        Args:
            provider_name: 具体的 HTTP 供应商名称，默认为 env HTTP_PROVIDER
            provider_options: 额外的供应商配置
        """
        provider_name = provider_name or self._default_provider()
        options = provider_options.copy() if provider_options else {}
        options = self._fill_provider_options(provider_name, options)
        self.provider = create_provider(provider_name, **options)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_sync(self, url: str, **kwargs) -> requests.Response:
        """
        同步GET请求

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            requests.Response对象
        """
        return self.provider.send_sync(url, **kwargs)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_async(self, url: str, session: aiohttp.ClientSession | None = None, **kwargs) -> aiohttp.ClientResponse:
        """
        异步GET请求

        Args:
            url: 请求URL
            session: aiohttp会话（可选）
            **kwargs: 其他请求参数

        Returns:
            aiohttp.ClientResponse对象
        """
        return await self.provider.send_async(url, session, **kwargs)

    def _default_provider(self) -> str:
        configured = os.getenv("HTTP_PROVIDER")
        if not configured:
            return "zenrows"
        return (configured or "direct").lower()

    def _fill_provider_options(
        self,
        provider_name: str,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        provider = provider_name.lower()
        if provider == "zenrows":
            options.setdefault("api_key",os.getenv("ZENROWS_APIKEY"))
            if not options["api_key"]:
                raise ValueError("ZenRows provider requires ZENROWS_APIKEY")
        elif provider == "scraperapi":
            options.setdefault("api_key", os.getenv("SCRAPERAPI_KEY"))
            if not options["api_key"]:
                raise ValueError("ScraperAPI provider requires SCRAPERAPI_KEY")
        elif provider == "scrapingbee":
            options.setdefault("api_key", os.getenv("SCRAPINGBEE_API_KEY"))
            if not options["api_key"]:
                raise ValueError("ScrapingBee provider requires SCRAPINGBEE_API_KEY")
        elif provider == "oxylabs":
            options.setdefault("username", os.getenv("OXYLABS_USERNAME"))
            options.setdefault("password", os.getenv("OXYLABS_PASSWORD"))
            if not options["username"] or not options["password"]:
                raise ValueError("Oxylabs provider requires OXYLABS_USERNAME and OXYLABS_PASSWORD")
        elif provider == "firecrawl":
            options.setdefault("api_key", os.getenv("FIRECRAWL_API_KEY"))
            if not options["api_key"]:
                raise ValueError("Firecrawl provider requires FIRECRAWL_API_KEY")
        return options
