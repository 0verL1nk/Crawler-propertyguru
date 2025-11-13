"""
页面爬取抽象基类
定义页面爬取的通用接口
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crawler.models import ListingInfo


class PageCrawler(ABC):
    """页面爬虫抽象基类"""

    @abstractmethod
    async def get_page_content(self, url: str) -> str:
        """
        获取页面内容

        Args:
            url: 页面URL

        Returns:
            页面HTML内容
        """
        pass

    @abstractmethod
    def get_page_content_sync(self, url: str) -> str:
        """
        同步获取页面内容

        Args:
            url: 页面URL

        Returns:
            页面HTML内容
        """
        pass

    @abstractmethod
    async def crawl_listing_page(self, page_num: int, enable_geocoding: bool | None = None) -> list[ListingInfo]:
        """
        爬取列表页

        Args:
            page_num: 页码
            enable_geocoding: 是否启用地理编码

        Returns:
            房源信息列表
        """
        pass

    @abstractmethod
    def crawl_listing_page_sync(self, page_num: int, enable_geocoding: bool | None = None) -> list[ListingInfo]:
        """
        同步爬取列表页

        Args:
            page_num: 页码
            enable_geocoding: 是否启用地理编码

        Returns:
            房源信息列表
        """
        pass

    @abstractmethod
    async def get_listing_ids_from_page(self, page_num: int) -> list[tuple[int, str]]:
        """
        从页面获取房源ID和URL列表

        Args:
            page_num: 页码

        Returns:
            (listing_id, detail_url) 元组列表
        """
        pass

    @abstractmethod
    def get_max_pages(self) -> int | None:
        """
        获取最大页数

        Returns:
            最大页数
        """
        pass
