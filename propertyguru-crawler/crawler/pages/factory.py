"""
页面爬虫工厂
根据配置创建相应的页面爬虫实例
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crawler.pages.base import PageCrawler
from crawler.pages.listing_http import ListingHttpCrawler


class PageCrawlerFactory:
    """页面爬虫工厂类"""

    @staticmethod
    def create_listing_crawler(crawler_type: str | None = None) -> PageCrawler:
        """
        创建列表页爬虫实例

        Args:
            crawler_type: 爬虫类型 ('http' 或 'browser')
                         如果为 None，从环境变量 PAGE_CRAWLER_TYPE 读取

        Returns:
            页面爬虫实例
        """
        if crawler_type is None:
            crawler_type = os.getenv("PAGE_CRAWLER_TYPE", "browser").lower()

        if crawler_type == "http":
            # 检查是否启用ZenRows
            use_zenrows = os.getenv("USE_ZENROWS", "false").lower() == "true"
            zenrows_apikey = os.getenv("ZENROWS_APIKEY")

            return ListingHttpCrawler(use_zenrows=use_zenrows, zenrows_apikey=zenrows_apikey)

        else:
            # 对于browser类型，我们需要返回现有的浏览器实现
            # 这里我们暂时抛出异常，因为需要在主爬虫中处理
            raise NotImplementedError("Browser-based crawler should be handled in main crawler")

    @staticmethod
    def create_detail_crawler() -> PageCrawler:
        """
        创建详情页爬虫实例
        详情页始终需要浏览器支持

        Returns:
            页面爬虫实例
        """
        # 详情页需要JavaScript渲染，必须使用浏览器
        raise NotImplementedError("Detail page crawler should be handled in main crawler")
