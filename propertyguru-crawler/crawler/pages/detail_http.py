"""
HTTP 详情页爬虫
从 PropertyGuru 详情页中提取 __NEXT_DATA__ JSON，供上层解析器使用
"""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup

from crawler.http.client import HttpClient
from utils.logger import get_logger

logger = get_logger("DetailHttpCrawler")


class DetailHttpCrawler:
    """负责通过 HTTP 获取详情页并提取 __NEXT_DATA__ JSON 的爬虫"""

    def __init__(self):
        self.http_client = HttpClient()

    def get_page_content_sync(self, url: str, **kwargs) -> str:
        """同步获取详情页 HTML"""
        response = self.http_client.get_sync(url, **kwargs)
        return response.text

    async def get_page_content(self, url: str, **kwargs) -> str:  # pragma: no cover - 目前主要使用同步接口
        """异步获取详情页 HTML"""
        response = await self.http_client.get_async(url, **kwargs)
        return await response.text()

    def fetch_next_data(self, url: str, **kwargs) -> dict[str, Any]:
        """获取详情页并解析出 __NEXT_DATA__ JSON"""
        html = self.get_page_content_sync(url, **kwargs)
        return self.parse_next_data(html)

    @staticmethod
    def parse_next_data(html: str) -> dict[str, Any]:
        """从 HTML 中提取 __NEXT_DATA__ JSON"""
        soup = BeautifulSoup(html, "lxml")
        script_tag = soup.find("script", id="__NEXT_DATA__", type="application/json")
        if not script_tag or not script_tag.string:
            raise ValueError("未找到 __NEXT_DATA__ JSON 脚本")

        try:
            return json.loads(script_tag.string)
        except json.JSONDecodeError as exc:  # pragma: no cover - JSON 解析异常记录日志
            logger.error("解析 __NEXT_DATA__ JSON 失败: %s", exc)
            raise
