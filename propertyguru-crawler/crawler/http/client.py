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


class HttpClient:
    """HTTP客户端封装"""

    def __init__(self, use_zenrows: bool = False, zenrows_apikey: str | None = None):
        """
        初始化HTTP客户端

        Args:
            use_zenrows: 是否使用ZenRows服务
            zenrows_apikey: ZenRows API密钥
        """
        self.use_zenrows = use_zenrows
        self.zenrows_apikey = zenrows_apikey or os.getenv("ZENROWS_APIKEY")

        if self.use_zenrows and not self.zenrows_apikey:
            logger.warning("ZenRows已启用但未提供API密钥，将使用直接HTTP请求")
            self.use_zenrows = False

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
        if self.use_zenrows and self.zenrows_apikey:
            return self._get_via_zenrows_sync(url, **kwargs)
        else:
            return self._get_direct_sync(url, **kwargs)

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
        if self.use_zenrows and self.zenrows_apikey:
            return await self._get_via_zenrows_async(url, session, **kwargs)
        else:
            return await self._get_direct_async(url, session, **kwargs)

    def _get_direct_sync(self, url: str, **kwargs) -> requests.Response:
        """
        直接HTTP GET请求（同步）

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            requests.Response对象
        """
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        timeout = kwargs.pop("timeout", 30)

        logger.debug(f"发送直接HTTP请求: {url}")
        response = requests.get(url, headers=headers, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    async def _get_direct_async(self, url: str, session: aiohttp.ClientSession | None = None, **kwargs) -> aiohttp.ClientResponse:
        """
        直接HTTP GET请求（异步）

        Args:
            url: 请求URL
            session: aiohttp会话（可选）
            **kwargs: 其他请求参数

        Returns:
            aiohttp.ClientResponse对象
        """
        headers = kwargs.pop("headers", {})
        headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 30))

        if session:
            logger.debug(f"通过会话发送直接HTTP请求: {url}")
            response = await session.get(url, headers=headers, timeout=timeout, **kwargs)
        else:
            async with aiohttp.ClientSession(timeout=timeout) as new_session:
                logger.debug(f"发送直接HTTP请求: {url}")
                response = await new_session.get(url, headers=headers, **kwargs)

        return response

    def _get_via_zenrows_sync(self, url: str, **kwargs) -> requests.Response:
        """
        通过ZenRows服务的GET请求（同步）

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            requests.Response对象
        """
        params: dict[str, Any] = {
            "url": url,
            "apikey": self.zenrows_apikey,
            "js_render": "false",  # 列表页不需要JS渲染
            "premium_proxy": "true"
        }

        # 合并额外参数
        extra_params = kwargs.pop("params", {})
        params.update(extra_params)

        headers = kwargs.pop("headers", {})
        timeout = kwargs.pop("timeout", 30)

        zenrows_url = "https://api.zenrows.com/v1/"
        logger.debug(f"通过ZenRows发送请求: {url}")
        response = requests.get(zenrows_url, params=params, headers=headers, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    async def _get_via_zenrows_async(self, url: str, session: aiohttp.ClientSession | None = None, **kwargs) -> aiohttp.ClientResponse:
        """
        通过ZenRows服务的GET请求（异步）

        Args:
            url: 请求URL
            session: aiohttp会话（可选）
            **kwargs: 其他请求参数

        Returns:
            aiohttp.ClientResponse对象
        """
        params: dict[str, Any] = {
            "url": url,
            "apikey": self.zenrows_apikey,
            "js_render": "false",  # 列表页不需要JS渲染
            "premium_proxy": "true"
        }

        # 合并额外参数
        extra_params = kwargs.pop("params", {})
        params.update(extra_params)

        headers = kwargs.pop("headers", {})
        timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", 30))

        zenrows_url = "https://api.zenrows.com/v1/"

        if session:
            logger.debug(f"通过会话和ZenRows发送请求: {url}")
            response = await session.get(zenrows_url, params=params, headers=headers, timeout=timeout, **kwargs)
        else:
            async with aiohttp.ClientSession(timeout=timeout) as new_session:
                logger.debug(f"通过ZenRows发送请求: {url}")
                response = await new_session.get(zenrows_url, params=params, headers=headers, **kwargs)

        return response
