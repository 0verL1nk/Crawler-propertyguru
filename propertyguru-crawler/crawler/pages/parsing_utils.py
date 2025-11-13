"""
页面解析工具
提供统一的页面解析接口，支持浏览器元素和HTML字符串
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from crawler.models import ListingInfo
from crawler.parsers.parsers import ListingPageParser
from utils.logger import get_logger

logger = get_logger("PageParsingUtils")


class MockBrowser:
    """模拟浏览器对象，用于解析HTML字符串"""

    def __init__(self, html_content: str):
        self.page_source = html_content
        self.soup = BeautifulSoup(html_content, "html.parser")

    def find_element(self, _by: Any, value: str) -> Any:
        """查找单个元素"""
        element = self.soup.select_one(value)
        if element:
            return MockWebElement(element)
        return None

    def find_elements(self, _by: Any, value: str) -> list[Any]:
        """查找多个元素"""
        elements = self.soup.select(value)
        return [MockWebElement(elem) for elem in elements]

    @property
    def driver(self) -> MockBrowser:
        """返回自身作为driver"""
        return self

    def wait(self, timeout: int = 10):
        """返回一个简单的等待对象（用于兼容性）"""
        return SimpleWait()


class SimpleWait:
    """简化的等待类，用于HTTP解析兼容性"""

    def until(self, condition):
        """简化实现，直接返回True"""
        # For HTTP parsing, we don't need to actually wait
        # Just return True to indicate condition is met
        return True


class MockWebElement:
    """模拟WebElement对象，用于解析HTML字符串"""

    def __init__(self, soup_element: Any):
        self.soup_element = soup_element
        self.tag_name = getattr(soup_element, 'name', '') if soup_element else ""

    @property
    def text(self) -> str:
        """获取元素文本"""
        return self.soup_element.get_text(strip=True)

    def get_attribute(self, name: str) -> str | None:
        """获取元素属性"""
        if hasattr(self.soup_element, 'get'):
            return self.soup_element.get(name)
        return None

    def find_element(self, _by: Any, value: str) -> Any:
        """查找子元素"""
        element = self.soup_element.select_one(value)
        if element:
            return MockWebElement(element)
        return None

    def find_elements(self, _by: Any, value: str) -> list[Any]:
        """查找多个子元素"""
        elements = self.soup_element.select(value)
        return [MockWebElement(elem) for elem in elements]

    @property
    def location_once_scrolled_into_view(self) -> dict:
        """模拟位置属性"""
        return {"x": 0, "y": 0}

    @property
    def size(self) -> dict:
        """模拟大小属性"""
        return {"width": 0, "height": 0}


def parse_listing_cards_from_html(
    html_content: str, enable_geocoding: bool | None = None
) -> list[ListingInfo]:
    """
    从HTML内容解析房源卡片

    Args:
        html_content: HTML内容
        enable_geocoding: 是否启用地理编码

    Returns:
        房源信息列表
    """
    try:
        mock_browser = MockBrowser(html_content)
        parser = ListingPageParser(mock_browser, enable_geocoding=enable_geocoding)

        # 查找搜索结果根元素
        root = mock_browser.find_element("css selector", "div.search-result-root")
        if not root:
            logger.warning("未找到搜索结果根元素")
            return []

        # 查找所有房产卡片元素
        cards = root.find_elements("css selector", 'div[da-id="parent-listing-card-v2-regular"]')
        logger.info(f"找到 {len(cards)} 个房产卡片")

        # 缓存所有卡片的HTML内容
        cards_html = []
        for idx, card in enumerate(cards, 1):
            try:
                # 获取卡片的outerHTML
                if hasattr(card, 'soup_element'):
                    html = str(card.soup_element)
                    if html:
                        cards_html.append(html)
                    else:
                        logger.warning(f"第 {idx} 个卡片获取HTML失败")
            except Exception as e:
                logger.warning(f"获取第 {idx} 个卡片HTML失败: {e}")
                continue

        logger.info(f"成功缓存 {len(cards_html)} 个卡片的HTML内容")

        # 解析卡片HTML
        listings = []
        total_cards = len(cards_html)
        logger.debug(f"开始解析 {total_cards} 个房产卡片...")

        for idx, card_html in enumerate(cards_html, 1):
            logger.debug(f"解析第 {idx}/{total_cards} 个卡片...")
            try:
                listing = parser.parse_listing_card_html(card_html)
                if listing:
                    listings.append(listing)
                    logger.debug(f"✓ 成功解析: {listing.listing_id} - {listing.title}")
                else:
                    logger.debug(f"✗ 解析失败: 第 {idx} 个卡片（返回 None）")
            except Exception as e:
                logger.warning(f"解析第 {idx} 个卡片时出错: {e}", exc_info=True)
                continue

        return listings

    except Exception as e:
        logger.error(f"从HTML解析房源卡片失败: {e}")
        return []


def extract_listing_ids_from_html(html_content: str) -> list[tuple[int, str]]:
    """
    从HTML内容提取房源ID和URL

    Args:
        html_content: HTML内容

    Returns:
        (listing_id, detail_url) 元组列表
    """
    try:
        mock_browser = MockBrowser(html_content)
        # 创建解析器实例但不赋值给变量，因为我们只需要它来初始化解析环境
        ListingPageParser(mock_browser)

        # 查找搜索结果根元素
        root = mock_browser.find_element("css selector", "div.search-result-root")
        if not root:
            logger.warning("未找到搜索结果根元素")
            return []

        # 查找所有房产卡片元素
        cards = root.find_elements("css selector", 'div[da-id="parent-listing-card-v2-regular"]')
        logger.info(f"找到 {len(cards)} 个房产卡片")

        listing_ids = []
        for card in cards:
            try:
                # 提取ID和URL
                if hasattr(card, 'soup_element'):
                    # 从HTML属性中提取listing_id
                    listing_id_attr = card.soup_element.get("da-listing-id")
                    if listing_id_attr:
                        listing_id = int(listing_id_attr)

                        # 提取detail_url
                        footer_link = card.soup_element.select_one("a.card-footer")
                        if footer_link and footer_link.get("href"):
                            from urllib.parse import urljoin
                            detail_url = urljoin("https://www.propertyguru.com.sg", footer_link["href"])

                            if listing_id and detail_url:
                                listing_ids.append((listing_id, detail_url))
            except Exception as e:
                logger.debug(f"提取ID时出错: {e}")
                continue

        logger.info(f"提取到 {len(listing_ids)} 个房源ID")
        return listing_ids

    except Exception as e:
        logger.error(f"从HTML提取房源IDs失败: {e}")
        return []
