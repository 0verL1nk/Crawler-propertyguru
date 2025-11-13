"""
HTTP基础的列表页爬虫实现
适用于不需要JavaScript渲染的列表页
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

    def __init__(self, use_zenrows: bool = False, zenrows_apikey: str | None = None):
        """
        初始化HTTP列表页爬虫

        Args:
            use_zenrows: 是否使用ZenRows服务
            zenrows_apikey: ZenRows API密钥
        """
        self.http_client = HttpClient(use_zenrows=use_zenrows, zenrows_apikey=zenrows_apikey)
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

    def get_max_pages(self) -> int | None:
        """
        获取最大页数（同步）

        Returns:
            最大页数
        """
        # 对于HTTP爬取，我们可以先尝试获取第一页来确定最大页数
        # 但这需要JavaScript渲染来获取分页信息，所以我们仍然需要浏览器
        # 这里简单返回None，表示需要使用浏览器获取

        # 或者我们可以实现一个简化版本，假设至少有100页
        logger.warning("HTTP爬虫无法准确获取最大页数，需要浏览器支持")
        return None
