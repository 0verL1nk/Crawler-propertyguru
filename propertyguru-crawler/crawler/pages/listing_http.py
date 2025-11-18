"""
HTTP基础的列表页爬虫实现
适用于不需要JavaScript渲染的列表页
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup

from crawler.http.client import HttpClient
from crawler.pages.base import PageCrawler
from crawler.pages.parsing_utils import extract_listing_ids_from_html, parse_listing_cards_from_html

if TYPE_CHECKING:
    from crawler.models import ListingInfo
from utils.logger import get_logger

logger = get_logger("ListingHttpCrawler")


class ListingHttpCrawler(PageCrawler):
    """HTTP基础的列表页爬虫"""

    BASE_URL = "https://www.propertyguru.com.sg/property-for-sale"

    def __init__(self):
        """
        初始化HTTP列表页爬虫

        Args:
            use_zenrows: 是否使用ZenRows服务
            zenrows_apikey: ZenRows API密钥
        """
        self.http_client = HttpClient()
        self.enable_geocoding = False

    async def get_page_content(self, url: str) -> str:
        """
        异步获取页面内容

        Args:
            url: 页面URL

        Returns:
            页面HTML内容
        """
        response = await self.http_client.get_async(url)
        return await response.text()

    def get_page_content_sync(self, url: str) -> str:
        """
        同步获取页面内容

        Args:
            url: 页面URL

        Returns:
            页面HTML内容
        """
        response = self.http_client.get_sync(url)
        return response.text

    async def crawl_listing_page(self, page_num: int, enable_geocoding: bool | None = None) -> list[ListingInfo]:
        """
        异步爬取列表页

        Args:
            page_num: 页码
            enable_geocoding: 是否启用地理编码

        Returns:
            房源信息列表
        """
        url = f"{self.BASE_URL}/{page_num}"
        logger.debug(f"爬取列表页: {url}")

        try:
            html_content = await self.get_page_content(url)
            return parse_listing_cards_from_html(html_content, enable_geocoding or self.enable_geocoding)
        except Exception as e:
            logger.error(f"爬取列表页失败: {e}")
            return []

    def crawl_listing_page_sync(self, page_num: int, enable_geocoding: bool | None = None) -> list[ListingInfo]:
        """
        同步爬取列表页

        Args:
            page_num: 页码
            enable_geocoding: 是否启用地理编码

        Returns:
            房源信息列表
        """
        url = f"{self.BASE_URL}/{page_num}"
        logger.debug(f"爬取列表页: {url}")

        try:
            html_content = self.get_page_content_sync(url)
            return parse_listing_cards_from_html(html_content, enable_geocoding or self.enable_geocoding)
        except Exception as e:
            logger.error(f"爬取列表页失败: {e}")
            return []

    async def get_listing_ids_from_page(self, page_num: int) -> list[tuple[int, str]]:
        """
        从页面获取房源ID和URL列表（异步）

        Args:
            page_num: 页码

        Returns:
            (listing_id, detail_url) 元组列表
        """
        url = f"{self.BASE_URL}/{page_num}"
        logger.debug(f"获取列表页房源IDs: {url}")

        try:
            html_content = await self.get_page_content(url)
            return extract_listing_ids_from_html(html_content)
        except Exception as e:
            logger.error(f"获取列表页房源IDs失败: {e}")
            return []

    def get_max_pages(self, base_page: int | None = None) -> int | None:
        """获取最大页数（同步）"""
        if base_page and base_page > 1:
            url = f"{self.BASE_URL}/{base_page}"
        else:
            url = self.BASE_URL
        logger.debug("获取列表页最大页数: %s", url)

        try:
            html_content = self.get_page_content_sync(url)
            total_pages = self._extract_total_pages_from_html(html_content)

            if total_pages is None:
                logger.warning("未能从列表页解析出最大页数")
            else:
                logger.info("解析到最大页数: %s", total_pages)

            return total_pages
        except Exception as exc:  # pragma: no cover - 网络异常日志即可
            logger.error("获取列表页最大页数失败: %s", exc)
            return None

    @staticmethod
    def _extract_total_pages_from_html(html_content: str) -> int | None:
        """从 __NEXT_DATA__ JSON 中解析 paginationData.totalPages"""
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, "lxml")
        script_tag = soup.find("script", id="__NEXT_DATA__", type="application/json")
        if not script_tag or not script_tag.string:
            logger.debug("列表页未找到 __NEXT_DATA__ 脚本")
            return None

        try:
            data: dict[str, Any] = json.loads(script_tag.string)
        except json.JSONDecodeError as exc:
            logger.debug("解析 __NEXT_DATA__ JSON 失败: %s", exc)
            return None

        pagination_data = (
            data.get("props", {})
            .get("pageProps", {})
            .get("pageData", {})
            .get("data", {})
            .get("paginationData", {})
        )

        total_pages = pagination_data.get("totalPages") if isinstance(pagination_data, dict) else None
        if total_pages is None:
            return None

        try:
            total_pages_int = int(total_pages)
        except (TypeError, ValueError):
            logger.debug("paginationData.totalPages 非数字: %s", total_pages)
            return None

        if total_pages_int <= 0:
            logger.debug("paginationData.totalPages 非正整数: %s", total_pages_int)
            return None

        return total_pages_int
