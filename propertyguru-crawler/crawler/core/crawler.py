"""
PropertyGuru爬虫主类
整合所有模块，实现完整的爬取流程
支持重试机制和断点续传
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from typing import TYPE_CHECKING, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from utils.logger import get_logger

from ..browser import BrowserFactory
from ..database import DatabaseManager  # 保留用于MongoDB
from ..database.factory import get_database
from ..database.operations import DBOperations

if TYPE_CHECKING:
    from ..database.interface import SQLDatabaseInterface
    from ..models import ListingInfo, MediaItem
    from .config import Config
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..pages.base import PageCrawler

# Import new HTTP-based crawling modules
from ..pages.factory import PageCrawlerFactory
from ..parsers import DetailPageParser, ListingPageParser
from ..storage import StorageManagerProtocol, create_storage_manager
from ..storage.media_processor import MediaProcessor
from ..utils.progress_manager import CrawlProgress
from ..utils.watermark_remover import WatermarkRemover

logger = get_logger("PropertyGuruCrawler")


class PropertyGuruCrawler:
    """PropertyGuru爬虫主类"""

    BASE_URL = "https://www.propertyguru.com.sg/property-for-sale"

    def __init__(self, config: Config):
        """
        初始化爬虫

        Args:
            config: 配置对象
        """
        self.config = config

        # 初始化组件
        self.browser: Any = None
        self.sql_db: SQLDatabaseInterface | None = None  # SQL数据库（MySQL/PostgreSQL）
        self.mongo_db: DatabaseManager | None = None  # MongoDB（旧的DatabaseManager）
        self.db_ops: DBOperations | None = None
        self.storage_manager: StorageManagerProtocol | None = None
        self.media_processor: MediaProcessor | None = None
        self.watermark_remover: WatermarkRemover | None = None

        # HTTP-based listing page crawler (optional)
        self.listing_http_crawler: PageCrawler | None = None

        # 爬虫配置
        crawler_config = self.config.get_section("crawler")
        self.max_retries = crawler_config.get("max_retries", 3) if crawler_config else 3
        self.retry_delay = crawler_config.get("retry_delay", 2) if crawler_config else 2

        # 地理编码配置
        self.enable_geocoding = os.getenv("ENABLE_GEOCODING", "false").lower() == "true"

        # 检测是否使用代理
        # 优先级：proxy.enabled > crawler.use_proxy > 环境变量 PROXY_URL
        proxy_config = self.config.get_section("proxy")
        self.use_proxy = True  # 默认使用代理

        if proxy_config:
            # 如果配置了 proxy.enabled，优先使用该配置
            self.use_proxy = proxy_config.get("enabled", True)
        elif crawler_config:
            # 否则使用 crawler.use_proxy
            self.use_proxy = crawler_config.get("use_proxy", True)

        # 如果 proxy.enabled=false，即使有 PROXY_URL 也不使用代理
        if proxy_config and not proxy_config.get("enabled", True):
            self.use_proxy = False

        # 如果没有设置代理URL且配置中未启用代理，则确认不使用代理
        if not os.getenv("PROXY_URL") and not self.use_proxy:
            logger.debug("检测到未配置代理（proxy.enabled=false 且未设置 PROXY_URL），将使用直连IP")

        # 直连IP时的配置（不使用代理时）
        self.direct_ip_limit_per_page = (
            crawler_config.get("direct_ip_limit_per_page", 1) if crawler_config else 1
        )
        self.direct_ip_delay = crawler_config.get("direct_ip_delay", 5) if crawler_config else 5

        # 进度管理器
        progress_file = os.getenv("CRAWL_PROGRESS_FILE", "crawl_progress.json")
        # 暂时不传入db_ops，因为在_init_components中db_ops还未初始化
        # 会在_init_components后设置
        self.progress = CrawlProgress(progress_file=progress_file)

        self._init_components()

        # 初始化完成后，设置db_ops到progress
        # 注意：如果配置了数据库，_init_database会设置db_ops
        if self.db_ops is not None:
            self.progress.db_ops = self.db_ops  # type: ignore[unreachable]

    def _init_browser(self):
        """初始化浏览器"""
        # 使用工厂模式创建浏览器实例
        logger.debug("使用浏览器工厂创建浏览器实例")
        self.browser = BrowserFactory.create_browser()
        logger.debug(f"浏览器实例创建成功: {type(self.browser).__name__}")

    def _init_database(self):
        """初始化数据库"""
        db_config = self.config.get_section("database")
        if db_config:
            # 使用新的工厂模式初始化 SQL 数据库（MySQL/PostgreSQL）
            try:
                self.sql_db = get_database()  # 从环境变量读取 DB_TYPE 配置
                logger.info(f"SQL 数据库已初始化: {self.sql_db.db_type}")

                # 创建数据库操作对象，兼容新旧接口
                self.db_ops = DBOperations(self.sql_db)
            except Exception as e:
                logger.error(f"SQL 数据库初始化失败: {e}")
                raise

            # 如果明确配置需要 MongoDB，则初始化（可选）
            # 注意：现在主要使用 SQL 数据库（MySQL/PostgreSQL），MongoDB 仅在特殊场景下使用
            mongodb_config = db_config.get("mongodb", {})
            if mongodb_config and mongodb_config.get("enabled", False):
                try:
                    self.mongo_db = DatabaseManager(db_config)
                    logger.info("MongoDB 已初始化")
                except Exception as e:
                    logger.warning(f"MongoDB 初始化失败（可选）: {e}")
            else:
                logger.debug("MongoDB 未启用，跳过初始化")

    def _init_storage(self):
        """初始化存储管理器"""
        s3_config = self.config.get_section("s3")
        if s3_config and s3_config.get("enabled", False):
            self.storage_manager = create_storage_manager(s3_config)

    def _init_proxy(self) -> tuple[Any | None, str | None]:
        """初始化代理配置，返回 (proxy_manager, direct_proxy_url)"""
        proxy_config = self.config.get_section("proxy")
        proxy_manager = None
        direct_proxy_url = None

        if proxy_config and proxy_config.get("pool_type") in {"direct_api", "cloudbypass"}:
            from ..utils.proxy_manager import ProxyManager

            pool_type = proxy_config.get("pool_type")
            try:
                proxy_manager = ProxyManager(proxy_config)
                if pool_type == "cloudbypass":
                    logger.debug("将使用 CloudBypass 住宅代理池")
                else:
                    logger.debug("将使用直连IP代理池（动态获取）")
            except Exception as e:
                logger.warning(f"初始化代理池失败（{pool_type}），将使用环境变量配置: {e}")

        if not proxy_manager:
            direct_proxy_url = os.getenv("PROXY_DIRECT_URL")
            if direct_proxy_url:
                logger.debug("将使用直连代理（PROXY_DIRECT_URL）")

        return proxy_manager, direct_proxy_url

    def _init_watermark_remover(self, proxy_manager: Any | None, direct_proxy_url: str | None):
        """初始化去水印工具"""
        watermark_config = self.config.get_section("watermark_remover")
        if not watermark_config or not watermark_config.get("enabled", False):
            return

        try:
            from utils.proxy import ProxyAdapter

            watermark_proxy_adapter = None
            if proxy_manager:
                watermark_proxy_adapter = ProxyAdapter(proxy_manager)
            elif direct_proxy_url:
                watermark_proxy_adapter = ProxyAdapter(direct_proxy_url)

            self.watermark_remover = WatermarkRemover(
                product_serial=os.getenv("WATERMARK_REMOVER_PRODUCT_SERIAL"),
                product_code=os.getenv("WATERMARK_REMOVER_PRODUCT_CODE"),
                authorization=os.getenv("WATERMARK_REMOVER_AUTHORIZATION"),
                proxy=watermark_proxy_adapter,
            )
        except Exception as e:
            logger.warning(f"初始化去水印工具失败: {e}")

    def _init_media_processor(self, proxy_manager: Any | None, direct_proxy_url: str | None):
        """初始化媒体处理器"""
        if self.storage_manager:
            # 读取去水印配置，决定是否立即处理
            watermark_config = self.config.get_section("watermark_remover")
            process_immediately = True
            if watermark_config:
                process_immediately = watermark_config.get("process_immediately", True)

            self.media_processor = MediaProcessor(
                storage_manager=self.storage_manager,
                watermark_remover=self.watermark_remover,
                proxy_url=direct_proxy_url,
                proxy_manager=proxy_manager,
                process_immediately=process_immediately,
            )

    def _init_components(self):
        """初始化各个组件"""
        self._init_browser()
        self._init_database()
        self._init_storage()
        proxy_manager, direct_proxy_url = self._init_proxy()
        self._init_watermark_remover(proxy_manager, direct_proxy_url)
        self._init_media_processor(proxy_manager, direct_proxy_url)
        self._init_http_crawler()
        logger.info("PropertyGuru爬虫初始化完成")

    def _init_http_crawler(self):
        """初始化HTTP爬虫（可选）"""
        try:
            # 检查是否启用HTTP爬虫
            use_http_crawler = os.getenv("USE_HTTP_CRAWLER", "false").lower() == "true"
            if use_http_crawler:
                self.listing_http_crawler = PageCrawlerFactory.create_listing_crawler("http")
                logger.info("HTTP列表页爬虫已初始化")
        except Exception as e:
            logger.warning(f"HTTP列表页爬虫初始化失败: {e}")

    def connect_browser(self):
        """连接浏览器"""
        if not self.browser:
            raise RuntimeError("浏览器未初始化")
        self.browser.connect()

    def _safe_navigate(self, url: str, max_retries: int = 2) -> None:
        """
        安全导航，自动处理 navigate_limit 和 WebSocket 连接错误

        Args:
            url: 要导航的URL
            max_retries: 最大重试次数（包括重启浏览器）
        """
        if not self.browser:
            raise RuntimeError("浏览器未初始化")
        for attempt in range(max_retries):
            try:
                self.browser.get(url)
                return  # 成功导航
            except Exception as nav_error:
                error_msg = str(nav_error)
                # 检查是否需要重新连接浏览器
                should_reconnect = False

                if "navigate_limit" in error_msg or "Page.navigate limit reached" in error_msg:
                    logger.warning(f"遇到导航限制（尝试 {attempt + 1}/{max_retries}）")
                    should_reconnect = True
                elif "cdp_ws_error" in error_msg or "WebSocket connection closed" in error_msg:
                    logger.warning(
                        f"WebSocket 连接关闭（尝试 {attempt + 1}/{max_retries}），将重新连接浏览器"
                    )
                    should_reconnect = True
                elif "cannot determine loading status" in error_msg:
                    logger.warning(
                        f"无法确定加载状态（尝试 {attempt + 1}/{max_retries}），可能是连接问题，将重新连接浏览器"
                    )
                    should_reconnect = True

                if should_reconnect and attempt < max_retries - 1:
                    logger.info("关闭并重新连接浏览器...")
                    time.sleep(2)
                    # 关闭并重新连接浏览器
                    if self.browser:
                        try:
                            self.browser.close()
                        except Exception as e:
                            logger.debug(f"关闭浏览器时出错（可忽略）: {e}")
                    self.connect_browser()
                    time.sleep(1)  # 等待浏览器完全启动
                elif should_reconnect:
                    logger.error("已达到最大重试次数，无法继续")
                    raise
                else:
                    # 其他错误直接抛出
                    raise

    def get_max_pages(
        self, max_retries: int = 3, base_page: int | None = None
    ) -> int | None:
        """
        获取最大页数（带重试机制）

        Args:
            max_retries: 最大重试次数
            base_page: 优先访问的页码（用于断点续传时避免总是从第1页请求）

        Returns:
            最大页数
        """
        for attempt in range(max_retries):
            try:
                if not self.browser:
                    raise RuntimeError("浏览器未初始化")
                page_to_check = max(1, base_page or 1)
                if page_to_check != 1:
                    logger.debug(f"获取最大页数时优先访问第 {page_to_check} 页")
                url = f"{self.BASE_URL}/{page_to_check}"
                self._safe_navigate(url)

                # 等待页面加载
                if not self.browser.driver:
                    raise RuntimeError("浏览器驱动未初始化")
                wait = WebDriverWait(self.browser.driver, timeout=30)
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[da-id="hui-pagination"]'))
                )

                parser = ListingPageParser(self.browser)
                max_pages = parser.get_max_pages()
                if max_pages:
                    return max_pages
                # 如果返回 None，可能是页面解析问题，重试
                if attempt < max_retries - 1:
                    logger.warning(
                        f"获取最大页数返回 None（尝试 {attempt + 1}/{max_retries}），将重试..."
                    )
                    time.sleep(2)
                    continue
                return None

            except Exception as e:
                error_msg = str(e)
                # 检查是否是 WebSocket 连接错误
                if (
                    "cdp_ws_error" in error_msg
                    or "WebSocket connection closed" in error_msg
                    or "cannot determine loading status" in error_msg
                ):
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"WebSocket 连接错误（尝试 {attempt + 1}/{max_retries}），"
                            "将重新连接浏览器并重试..."
                        )
                        time.sleep(2)
                        # 重新连接浏览器
                        if self.browser:
                            with contextlib.suppress(Exception):
                                self.browser.close()
                        self.connect_browser()
                        time.sleep(1)
                        continue
                    else:
                        logger.error("获取最大页数失败：已达到最大重试次数")
                        return None
                else:
                    # 其他错误，记录并返回 None
                    logger.error(f"获取最大页数失败: {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"将重试（尝试 {attempt + 1}/{max_retries}）...")
                        time.sleep(2)
                        continue
                    return None

        return None

    def get_listing_ids_from_page(self, page_num: int) -> list[tuple[int, str]]:
        """
        只获取列表页的房源ID和URL（轻量级，用于更新模式快速检查）

        Args:
            page_num: 页码

        Returns:
            (listing_id, detail_url) 元组列表
        """
        # 如果启用了HTTP爬虫且已初始化，优先使用HTTP爬虫
        if self.listing_http_crawler:
            try:
                logger.debug(f"使用HTTP爬虫获取列表页房源IDs: {page_num}")
                return self.listing_http_crawler.get_listing_ids_from_page(page_num)
            except Exception as e:
                logger.warning(f"HTTP爬虫失败，回退到浏览器爬虫: {e}")

        # 否则使用原有的浏览器爬虫
        try:
            if not self.browser:
                raise RuntimeError("浏览器未初始化")
            url = f"{self.BASE_URL}/{page_num}"
            logger.debug(f"获取列表页房源IDs: {url}")

            self._safe_navigate(url)

            # 等待搜索结果加载
            if not self.browser.driver:
                raise RuntimeError("浏览器驱动未初始化")
            wait = WebDriverWait(self.browser.driver, timeout=30)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.search-result-root")))

            # 只提取ID和URL，不解析详细信息
            parser = ListingPageParser(self.browser)
            cards = parser.extract_listing_cards()

            listing_ids = []
            for card in cards:
                try:
                    # 只提取ID和URL
                    listing_id = parser._extract_listing_id(card)
                    detail_url = parser._extract_detail_url(card)
                    if listing_id and detail_url:
                        listing_ids.append((listing_id, detail_url))
                except Exception as e:
                    logger.debug(f"提取ID时出错: {e}")
                    continue

            logger.info(f"页面 {page_num} 找到 {len(listing_ids)} 个房源ID")
            return listing_ids

        except Exception as e:
            logger.error(f"获取列表页房源IDs失败: {e}")
            return []

    def crawl_listing_page(
        self, page_num: int, enable_geocoding: bool | None = None
    ) -> list[ListingInfo]:
        """
        爬取列表页（完整解析，用于全量爬取）

        Args:
            page_num: 页码
            enable_geocoding: 是否启用地理编码，None 表示使用环境变量配置

        Returns:
            房源信息列表
        """
        # 如果启用了HTTP爬虫且已初始化，优先使用HTTP爬虫
        if self.listing_http_crawler:
            try:
                logger.debug(f"使用HTTP爬虫爬取列表页: {page_num}")
                return self.listing_http_crawler.crawl_listing_page_sync(page_num, enable_geocoding)
            except Exception as e:
                logger.warning(f"HTTP爬虫失败，回退到浏览器爬虫: {e}")

        # 否则使用原有的浏览器爬虫
        try:
            if not self.browser:
                raise RuntimeError("浏览器未初始化")
            url = f"{self.BASE_URL}/{page_num}"
            logger.debug(f"爬取列表页: {url}")

            self._safe_navigate(url)

            # 等待搜索结果加载
            if not self.browser.driver:
                raise RuntimeError("浏览器驱动未初始化")
            wait = WebDriverWait(self.browser.driver, timeout=30)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.search-result-root")))

            # 解析页面（优化：先缓存所有卡片HTML，再批量解析）
            parser = ListingPageParser(self.browser, enable_geocoding=enable_geocoding)
            cards_html = parser.extract_listing_cards_html()

            listings = []
            total_cards = len(cards_html)
            logger.debug(f"开始解析 {total_cards} 个房产卡片（使用HTML缓存优化）...")

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

            logger.info(f"页面 {page_num} 提取到 {len(listings)} 个房源")
            return listings

        except Exception as e:
            logger.error(f"爬取列表页失败: {e}")
            return []

    def crawl_detail_page(self, detail_url: str) -> dict | None:  # noqa: C901
        """
        爬取详情页

        Args:
            detail_url: 详情页URL

        Returns:
            详情数据字典，包含所有提取的信息
        """
        try:
            if not self.browser:
                raise RuntimeError("浏览器未初始化")
            logger.debug(f"爬取详情页: {detail_url}")

            # 添加延迟，避免导航限制
            time.sleep(2)

            # 使用安全导航方法，自动处理 navigate_limit 错误
            self._safe_navigate(detail_url)

            # 等待页面加载
            if not self.browser.driver:
                raise RuntimeError("浏览器驱动未初始化")
            wait = WebDriverWait(self.browser.driver, timeout=30)
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[da-id="property-details"]'))
            )

            parser = DetailPageParser(self.browser)

            # 提取所有信息
            logger.debug("开始提取详情页数据")
            property_details = parser.extract_property_details()
            logger.debug(f"Property details提取结果: {property_details is not None}")

            description_title, description = parser.extract_property_description()
            logger.debug(
                f"Description提取结果 - title: {description_title is not None}, description: {description is not None}"
            )

            amenities = parser.extract_amenities()
            facilities = parser.extract_facilities()
            media_urls = parser.extract_media_urls()

            # 如果property_details提取失败，尝试从URL提取listing_id并创建PropertyDetails对象
            if not property_details:
                # 尝试从URL提取listing_id
                listing_id = parser._extract_listing_id_from_url()

                if listing_id:
                    logger.debug(
                        f"property_details提取失败，但找到listing_id: {listing_id}，创建空的PropertyDetails对象"
                    )
                    from ..models import PropertyDetails

                    property_details = PropertyDetails(listing_id=listing_id)
                    property_details.property_details = {}
                else:
                    logger.warning(
                        "无法获取listing_id，无法创建PropertyDetails对象，description和description_title将无法保存"
                    )

            # 更新PropertyDetails的description、amenities和facilities字段
            if property_details:
                property_details.description = description
                property_details.description_title = description_title
                property_details.amenities = amenities  # 直接保存amenities列表
                property_details.facilities = facilities  # 直接保存facilities列表
                logger.debug(
                    f"PropertyDetails更新 - listing_id: {property_details.listing_id}, "
                    f"property_details字段数: {len(property_details.property_details) if property_details.property_details else 0}, "
                    f"description: {len(description) if description else 0} chars, "
                    f"description_title: {len(description_title) if description_title else 0} chars, "
                    f"amenities: {len(amenities) if amenities else 0} 项, "
                    f"facilities: {len(facilities) if facilities else 0} 项"
                )

            result = {
                "property_details": property_details,
                "amenities": amenities,
                "facilities": facilities,
                "media_urls": media_urls,
            }

            return result

        except Exception as e:
            logger.error(f"爬取详情页失败: {detail_url}, 错误: {e}")
            return None

    async def process_media(self, media_urls: list[tuple], listing_id: int) -> list[MediaItem]:
        """
        处理媒体文件

        Args:
            media_urls: [(media_type, url) 或 (media_type, url, element), ...] 列表
            listing_id: 房源ID

        Returns:
            MediaItem对象列表
        """
        if not self.media_processor:
            logger.warning("媒体处理器未初始化，跳过媒体处理")
            return []

        # 获取浏览器驱动，用于从浏览器直接获取图片
        browser_driver = None
        if self.browser and self.browser.driver:
            browser_driver = self.browser.driver

        return await self.media_processor.process_media_list(
            media_urls, listing_id, browser_driver=browser_driver
        )

    def _save_basic_info(self, listing: ListingInfo):
        """保存房源基本信息"""
        if not self.db_ops:
            raise RuntimeError("数据库操作未初始化")
        self.db_ops.save_listing_info(listing, flush=False)

    def _save_property_details_data(self, detail_data: dict):
        """保存房产详细信息和相关数据"""
        if not self.db_ops:
            raise RuntimeError("数据库操作未初始化")
        if detail_data.get("property_details"):
            details = detail_data["property_details"]
            logger.debug(
                f"准备保存PropertyDetails - listing_id: {details.listing_id}, "
                f"property_details字段数: {len(details.property_details) if details.property_details else 0}, "
                f"description: {len(details.description) if details.description else 0} chars, "
                f"description_title: {len(details.description_title) if details.description_title else 0} chars, "
                f"amenities: {len(details.amenities) if details.amenities else 0} 项, "
                f"facilities: {len(details.facilities) if details.facilities else 0} 项"
            )
            success = self.db_ops.save_property_details(details)
            if success:
                logger.debug(f"PropertyDetails保存成功: {details.listing_id}")
            else:
                logger.warning(f"PropertyDetails保存失败: {details.listing_id}")
        else:
            logger.warning("detail_data中没有property_details，跳过保存")

    def _save_media_data(self, detail_data: dict):
        """保存媒体数据"""
        if not self.db_ops:
            raise RuntimeError("数据库操作未初始化")
        if detail_data.get("media_items"):
            self.db_ops.save_media(detail_data["media_items"], flush=False)

    def save_listing_data(self, listing: ListingInfo, detail_data: dict):
        """
        保存房源数据到数据库

        Args:
            listing: 房源基本信息
            detail_data: 详情数据
        """
        if not self.db_ops:
            logger.warning("数据库操作未初始化")
            return

        try:
            # 先保存基本信息并刷新缓冲区，确保房源已存在
            # 使用 flush=True 确保立即写入数据库
            self.db_ops.save_listing_info(listing, flush=True)

            # 然后保存详细信息（property_details, description, amenities, facilities等）
            # amenities和facilities现在直接通过PropertyDetails保存到info表
            self._save_property_details_data(detail_data)
            self._save_media_data(detail_data)

            # 所有数据保存成功后，标记为已完成
            self.db_ops.mark_listing_completed(listing.listing_id)
            logger.debug(f"房源数据已保存并标记为完成: {listing.listing_id}")

        except Exception as e:
            logger.error(f"保存房源数据失败: {listing.listing_id}, 错误: {e}")
            # 如果保存失败，is_completed保持为false（默认值）
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    def _crawl_listing_with_retry(self, listing: ListingInfo):
        """
        爬取单个房源（带重试机制）
        注意：此方法不再检查是否已存在，因为已在run方法中过滤

        Args:
            listing: 房源基本信息

        Returns:
            详情数据字典

        Raises:
            Exception: 爬取失败时抛出异常
        """
        # 爬取详情页
        if not listing.url:
            raise ValueError(f"房源缺少URL: {listing.listing_id}")

        detail_data = self.crawl_detail_page(listing.url)
        if not detail_data:
            raise Exception(f"爬取详情页失败: {listing.listing_id}")

        return detail_data

    def _retry_crawl_listing(self, listing: ListingInfo) -> dict | None:
        """重试爬取房源详情，返回详情数据或None，如果已存在则返回特殊标记"""
        for attempt in range(self.max_retries):
            try:
                detail_data = self._crawl_listing_with_retry(listing)
                if isinstance(detail_data, dict):
                    return detail_data
                if detail_data is True:
                    return {"_exists": True}  # 已存在的标记
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"爬取房源失败（尝试 {attempt + 1}/{self.max_retries}）: "
                        f"{listing.listing_id}, {wait_time}秒后重试..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"爬取房源失败（已达最大重试次数）: {listing.listing_id}, 错误: {e}"
                    )
                    self.progress.mark_listing_failed(listing.listing_id)
                    return None
        return None

    async def _process_listing_media(self, detail_data: dict, listing_id: int):
        """处理房源媒体文件"""
        if detail_data.get("media_urls"):
            try:
                media_items = await self.process_media(detail_data["media_urls"], listing_id)
                detail_data["media_items"] = media_items
            except Exception as e:
                logger.warning(f"处理媒体文件失败: {listing_id}, 错误: {e}")

    async def crawl_listing(self, listing: ListingInfo) -> bool:
        """
        爬取单个房源（列表页+详情页）
        支持重试和进度记录

        Args:
            listing: 房源基本信息

        Returns:
            是否成功
        """
        try:
            # 在爬详情页前，先做地理编码（如果有地址且未编码）
            if (
                listing.location
                and not listing.latitude
                and not listing.longitude
                and self.enable_geocoding
            ):
                try:
                    from utils.geocoding import geocode_address

                    lat, lng = geocode_address(listing.location)
                    if lat and lng:
                        listing.latitude = lat
                        listing.longitude = lng
                        logger.debug(f"地理编码成功: {listing.location} -> ({lat}, {lng})")
                except Exception as e:
                    logger.warning(f"地理编码失败: {listing.location}, 错误: {e}")

            detail_data = self._retry_crawl_listing(listing)
            if detail_data and detail_data.get("_exists"):
                return True  # 已存在
            if not detail_data or not isinstance(detail_data, dict):
                return False

            await self._process_listing_media(detail_data, listing.listing_id)
            self.save_listing_data(listing, detail_data)

            # 标记为已完成
            self.progress.mark_listing_completed(listing.listing_id)

            return True

        except Exception as e:
            logger.error(f"爬取房源失败: {listing.listing_id}, 错误: {e}")
            self.progress.mark_listing_failed(listing.listing_id)
            return False

    async def test_single_listing(self):
        """
        测试模式：爬取第一页的第一个房源

        用于测试爬虫功能是否正常
        """
        try:
            # 如果启用了HTTP爬虫且已初始化，优先使用HTTP爬虫
            if self.listing_http_crawler:
                logger.info("获取第一页列表 (使用HTTP爬虫)...")

                # 使用HTTP爬虫获取列表页数据
                listings = self.listing_http_crawler.crawl_listing_page_sync(1)

                if not listings:
                    logger.error("第一页没有找到房源")
                    return

                first_listing = listings[0]
                logger.info(f"测试爬取第一个房源: {first_listing.listing_id} - {first_listing.title}")

                # 连接浏览器以爬取详情页（detail pages通常需要JavaScript）
                self.connect_browser()

                success = await self.crawl_listing(first_listing)

                if success:
                    logger.info("✅ 测试成功！第一个房源爬取完成")

                    # 刷新数据库缓冲区
                    if self.db_ops:
                        self.db_ops.flush_all()
                else:
                    logger.error("❌ 测试失败！请检查日志")

            else:
                # 回退到原有浏览器方式
                # 连接浏览器
                self.connect_browser()

                logger.info("获取第一页列表...")
                # 只解析第一个卡片，而不是解析所有卡片
                url = f"{self.BASE_URL}/1"
                logger.info(f"爬取列表页: {url}")

                if not self.browser:
                    raise RuntimeError("浏览器未初始化")
                self._safe_navigate(url)

                # 等待搜索结果加载
                if not self.browser.driver:
                    raise RuntimeError("浏览器驱动未初始化")
                wait = WebDriverWait(self.browser.driver, timeout=30)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.search-result-root")))

                # 解析页面，只提取第一个卡片（使用HTML缓存优化）
                parser = ListingPageParser(self.browser)
                cards_html = parser.extract_listing_cards_html()

                if not cards_html:
                    logger.error("第一页没有找到房源卡片")
                    return

                logger.info(f"找到 {len(cards_html)} 个房产卡片，只解析第一个...")
                first_listing = parser.parse_listing_card_html(cards_html[0])

                if not first_listing:
                    logger.error("解析第一个卡片失败")
                    return

                logger.info(f"测试爬取第一个房源: {first_listing.listing_id} - {first_listing.title}")

                success = await self.crawl_listing(first_listing)

                if success:
                    logger.info("✅ 测试成功！第一个房源爬取完成")

                    # 刷新数据库缓冲区
                    if self.db_ops:
                        self.db_ops.flush_all()
                else:
                    logger.error("❌ 测试失败！请检查日志")

        except Exception as e:
            logger.error(f"测试过程出错: {e}", exc_info=True)
            raise
        finally:
            # 关闭浏览器（当浏览器已连接时）
            if self.browser:
                self.browser.close()

    def _determine_end_page(self, end_page: int | None, reference_page: int | None = None) -> int | None:
        """确定结束页码"""
        if end_page is None:
            base_page = 1
            if reference_page and reference_page > 1:
                base_page = reference_page - 1
            elif self.progress.get_last_page() > 0:
                base_page = self.progress.get_last_page()

            logger.debug(f"获取最大页数...（参考页: {base_page}）")
            max_pages = self.get_max_pages(base_page=base_page)
            if not max_pages:
                logger.error("无法获取最大页数")
                return None
            logger.info(f"共 {max_pages} 页")
            return max_pages
        return end_page

    def _adjust_start_page_for_resume(self, start_page: int) -> int:
        """根据进度记录调整起始页码"""
        last_page = self.progress.get_last_page()
        if last_page > 0 and start_page <= last_page:
            logger.debug(f"发现进度记录，上次完成到第 {last_page} 页")
            logger.info(f"将从第 {last_page + 1} 页继续爬取")
            return max(start_page, last_page + 1)
        return start_page

    def _filter_completed_listings(
        self, listings: list[ListingInfo]
    ) -> tuple[list[ListingInfo], int, int]:
        """过滤已完成的房源（批量查询优化）"""
        new_listings = []
        skipped_count = 0
        completed_count = 0

        # 批量查询所有房源状态（优化：1次数据库查询替代N次）
        status_dict = {}
        if self.db_ops and listings:
            listing_ids = [listing.listing_id for listing in listings]
            status_dict = self.db_ops.batch_check_listings_status(listing_ids)
            logger.debug(f"批量查询 {len(listing_ids)} 个房源状态完成")

        for listing in listings:
            # 从批量查询结果获取状态
            status = status_dict.get(listing.listing_id, {"exists": False, "is_completed": False})

            if status["is_completed"]:
                skipped_count += 1
                completed_count += 1
                self.progress.mark_listing_completed(listing.listing_id)
                continue
            if status["exists"]:
                logger.debug(f"房源已存在但未完成，将重新爬取: {listing.listing_id}")
                new_listings.append(listing)
                continue
            if self.progress.is_listing_completed(listing.listing_id):
                skipped_count += 1
                completed_count += 1
                continue
            new_listings.append(listing)

        return new_listings, skipped_count, completed_count

    async def _crawl_page_listings(
        self, page_num: int, end_page: int, listings: list[ListingInfo]
    ) -> tuple[int, int]:
        """爬取页面中的所有房源"""
        success_count = 0
        fail_count = 0

        # 如果使用直连IP（不使用代理），限制每次只爬取一个房源
        original_count = len(listings)
        if not self.use_proxy:
            logger.debug("=" * 60)
            logger.debug("⚠️  检测到使用直连IP（不使用代理）")
            logger.debug(f"   限制每页只爬取 {self.direct_ip_limit_per_page} 个房源")
            logger.debug(f"   每个房源之间延迟 {self.direct_ip_delay} 秒")
            logger.debug("=" * 60)
            # 限制列表长度
            if original_count > self.direct_ip_limit_per_page:
                logger.debug(
                    f"   本页共有 {original_count} 个房源，仅爬取前 {self.direct_ip_limit_per_page} 个"
                )
            listings = listings[: self.direct_ip_limit_per_page]

        for idx, listing in enumerate(listings, 1):
            logger.debug(
                f"[{page_num}/{end_page}] [{idx}/{len(listings)}] 爬取房源: {listing.listing_id}"
            )

            success = await self.crawl_listing(listing)
            if success:
                success_count += 1
                logger.debug(f"✅ 成功: {listing.listing_id}")
            else:
                fail_count += 1
                logger.warning(f"❌ 失败: {listing.listing_id}")

            # 如果使用直连IP，使用更长的延迟
            if idx < len(listings):
                delay = self.direct_ip_delay if not self.use_proxy else 2
                logger.debug(f"等待 {delay} 秒后继续...")
                time.sleep(delay)

        return success_count, fail_count

    async def run(self, start_page: int = 1, end_page: int | None = None):
        """
        运行爬虫

        Args:
            start_page: 起始页码
            end_page: 结束页码（None表示爬取所有页）
        """
        try:
            self.connect_browser()

            start_page = self._adjust_start_page_for_resume(start_page)

            end_page = self._determine_end_page(end_page, reference_page=start_page)
            if end_page is None:
                return

            logger.info(f"开始爬取，页码范围: {start_page} - {end_page}")
            total_listings = 0
            success_count = 0
            fail_count = 0

            # 记录开始时间
            start_time = time.time()
            self.progress.start_session()

            # 记录初始统计信息（用于计算新增数量）
            completed_before = self.progress.get_completed_count()
            failed_before = self.progress.get_failed_count()

            for page_num in range(start_page, end_page + 1):
                logger.debug(f"{'=' * 60}")
                logger.info(f"开始爬取第 {page_num}/{end_page} 页")
                logger.debug(f"{'=' * 60}")

                listings = self.crawl_listing_page(page_num)
                if not listings:
                    logger.warning(f"第 {page_num} 页没有找到房源")
                    continue

                logger.debug(f"第 {page_num} 页找到 {len(listings)} 个房源")

                new_listings, skipped_count, completed_count = self._filter_completed_listings(
                    listings
                )

                if skipped_count > 0:
                    logger.debug(
                        f"跳过已完成的房源: {completed_count} 个 "
                        f"（已完成）, {skipped_count - completed_count} 个（其他原因）"
                    )

                if not new_listings:
                    logger.debug(f"第 {page_num} 页所有房源已完成，跳过")
                    self.progress.mark_page_completed(page_num)
                    continue

                logger.info(f"第 {page_num} 页待爬取房源: {len(new_listings)} 个")

                page_success, page_fail = await self._crawl_page_listings(
                    page_num, end_page, new_listings
                )
                success_count += page_success
                fail_count += page_fail
                total_listings += len(new_listings)

                if self.db_ops:
                    self.db_ops.flush_all()
                self.progress.mark_page_completed(page_num)

                logger.debug(f"{'=' * 60}")
                logger.info(
                    f"第 {page_num} 页爬取完成 - 成功 {page_success}/{len(new_listings)}, 失败 {page_fail}"
                )
                logger.debug(
                    f"总进度: 已完成 {self.progress.get_completed_count()} 个房源, "
                    f"失败 {self.progress.get_failed_count()} 个房源"
                )
                logger.debug(f"{'=' * 60}")

            # 最后刷新所有缓冲区
            if self.db_ops:
                self.db_ops.flush_all()

            # 计算耗时并保存统计
            elapsed_time = time.time() - start_time
            self.progress.end_session(success_count, elapsed_time)

            logger.info(f"{'=' * 60}")
            logger.info("爬取完成")
            logger.info(f"本次统计: 成功 {success_count}/{total_listings}, 失败 {fail_count}")
            logger.info(
                f"总耗时: {elapsed_time:.1f} 秒, 平均: {elapsed_time/success_count if success_count > 0 else 0:.2f} 秒/房源"
            )
            logger.info(
                f"总进度: 已完成 {self.progress.get_completed_count()} 个房源 "
                f"（本次新增 {self.progress.get_completed_count() - completed_before} 个）"
            )
            logger.info(
                f"失败房源: {self.progress.get_failed_count()} 个 "
                f"（本次新增 {self.progress.get_failed_count() - failed_before} 个）"
            )
            logger.info(f"{'=' * 60}")

        except Exception as e:
            logger.error(f"爬取过程出错: {e}", exc_info=True)
            raise
        finally:
            # 关闭浏览器
            if self.browser:
                self.browser.close()

    async def run_update_mode(self, interval_minutes: int = 5, max_pages: int | None = None):
        """
        更新模式：从第一页开始爬取最新数据，遇到已存在的记录就停止
        支持循环模式，每隔指定分钟执行一次

        Args:
            interval_minutes: 循环间隔（分钟），0 表示只执行一次
            max_pages: 最大爬取页数（None 表示不限制，但遇到已存在就停止）
        """
        import signal
        import time

        # 信号处理：优雅退出
        should_stop: bool = False

        def signal_handler(_sig, _frame):
            nonlocal should_stop
            logger.info("\n收到退出信号 (Ctrl+C)，正在退出...")
            should_stop = True

        def check_should_stop() -> bool:
            """检查是否应该停止（帮助 mypy 理解可达性）"""
            return should_stop

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        iteration = 0
        while not should_stop:
            iteration += 1
            logger.info("=" * 60)
            logger.info(f"更新模式 - 第 {iteration} 次循环")
            logger.info("=" * 60)

            try:
                # 开始计时
                start_time = time.time()
                self.progress.start_session()

                self.connect_browser()

                # 从第一页开始
                start_page = 1
                end_page = max_pages if max_pages else None

                # 如果指定了最大页数，先获取实际最大页数
                base_page_for_max = self.progress.get_last_page() or 1
                if end_page is None:
                    actual_max_pages = self.get_max_pages(base_page=base_page_for_max)
                    if actual_max_pages:
                        end_page = actual_max_pages
                    else:
                        logger.error("无法获取最大页数，跳过本次循环")
                        if interval_minutes > 0 and not should_stop:
                            logger.info(f"等待 {interval_minutes} 分钟后重试... (按 Ctrl+C 可退出)")
                            # 分块睡眠，每10秒检查一次退出信号
                            for _ in range(interval_minutes * 6):
                                if should_stop:
                                    logger.info("检测到退出信号，停止等待")  # type: ignore[unreachable]
                                    break
                                await asyncio.sleep(10)
                        continue
                else:
                    # 如果指定了最大页数，使用较小的值
                    actual_max_pages = self.get_max_pages(base_page=base_page_for_max)
                    if actual_max_pages:
                        end_page = min(end_page, actual_max_pages)

                logger.debug(f"开始爬取，页码范围: {start_page} - {end_page}")
                success_count = 0
                fail_count = 0
                total_processed = 0
                stopped_at_existing = False

                for page_num in range(start_page, end_page + 1):
                    if check_should_stop():
                        logger.debug("收到停止信号，退出爬取")
                        break

                    logger.info(f"{'=' * 60}")
                    logger.info(f"检查第 {page_num}/{end_page} 页（优化模式：逐个检查）")
                    logger.info(f"{'=' * 60}")

                    # 获取这一页的所有房源（包含列表页基本信息）
                    # 复用 crawl_listing_page，避免重复代码
                    # 注意：列表页不做地理编码，在详情页前再做
                    listings = self.crawl_listing_page(page_num, enable_geocoding=False)
                    if not listings:
                        logger.warning(f"第 {page_num} 页没有找到房源")
                        continue

                    logger.info(f"第 {page_num} 页找到 {len(listings)} 个房源")

                    # 逐个检查并爬取（遇到已存在就立即停止）
                    page_success = 0
                    page_fail = 0
                    new_count_in_page = 0

                    for idx, listing in enumerate(listings, 1):
                        if check_should_stop():
                            logger.info("收到停止信号，退出爬取")
                            break

                        total_processed += 1

                        # 检查数据库是否已存在
                        if self.db_ops:
                            is_completed = self.db_ops.check_listing_completed(listing.listing_id)

                            # 如果已完成，停止这一轮
                            if is_completed:
                                logger.info(
                                    f"[{page_num}] [{idx}/{len(listings)}] "
                                    f"遇到已存在房源: {listing.listing_id}，停止爬取"
                                )
                                stopped_at_existing = True
                                break

                            # 如果存在但未完成，跳过（避免重复爬取）
                            exists = self.db_ops.check_listing_exists(listing.listing_id)
                            if exists and not is_completed:
                                logger.info(
                                    f"[{page_num}] [{idx}/{len(listings)}] "
                                    f"房源已存在但未完成: {listing.listing_id}，跳过"
                                )
                                continue

                        # 新房源，爬取详情（listing 已包含列表页基本信息）
                        logger.info(
                            f"[{page_num}] [{idx}/{len(listings)}] "
                            f"爬取新房源: {listing.listing_id}"
                        )
                        new_count_in_page += 1

                        try:
                            # listing 已包含列表页的基本信息，直接爬详情页
                            success = await self.crawl_listing(listing)

                            if success:
                                page_success += 1
                                success_count += 1
                                logger.info(f"✅ [{listing.listing_id}] 成功")
                            else:
                                page_fail += 1
                                fail_count += 1
                                logger.warning(f"❌ [{listing.listing_id}] 失败")

                        except Exception as e:
                            logger.error(f"爬取房源 {listing.listing_id} 时出错: {e}")
                            page_fail += 1
                            fail_count += 1

                        # 延迟
                        delay = self.direct_ip_delay if not self.use_proxy else 2
                        logger.debug(f"等待 {delay} 秒后继续...")
                        await asyncio.sleep(delay)

                        # 进度保存（每5个房源保存一次）
                        if idx % 5 == 0:
                            if self.db_ops:
                                self.db_ops.flush_all()
                            self.progress.save_progress()

                    # 页面完成后的处理
                    if self.db_ops:
                        self.db_ops.flush_all()
                    self.progress.mark_page_completed(page_num)

                    logger.info(f"{'=' * 60}")
                    logger.info(
                        f"第 {page_num} 页完成 - 新房源 {new_count_in_page}, 成功 {page_success}, 失败 {page_fail}"
                    )
                    logger.info(f"{'=' * 60}")

                    # 如果遇到已存在的房源，停止爬取
                    if stopped_at_existing:
                        logger.info("✅ 已到达最新数据，停止爬取")
                        break

                    # 如果这页没有新房源，继续下一页
                    if new_count_in_page == 0:
                        logger.info(f"第 {page_num} 页没有新房源，继续检查下一页")

                # 最后刷新所有缓冲区
                if self.db_ops:
                    self.db_ops.flush_all()

                # 计算耗时并保存统计
                elapsed_time = time.time() - start_time
                self.progress.end_session(success_count, elapsed_time)

                logger.info("=" * 60)
                logger.info("本次更新完成")
                logger.info(
                    f"统计: 处理 {total_processed} 个房源, 成功 {success_count}, 失败 {fail_count}"
                )
                logger.info(f"耗时: {elapsed_time:.1f} 秒")
                if success_count > 0:
                    avg_time = elapsed_time / success_count
                    logger.info(f"平均处理时间: {avg_time:.2f} 秒/房源")
                if stopped_at_existing:
                    logger.info("停止原因: 遇到已存在的房源")
                logger.info("=" * 60)

            except Exception as e:
                logger.error(f"更新模式执行出错: {e}", exc_info=True)
                # 如果是数据库连接错误，不退出，等待后重试
                if "Lost connection to MySQL" in str(e) or "Can't connect to MySQL" in str(e):
                    logger.warning("检测到数据库连接错误，将在下次循环时重试")
                # 其他错误也不退出，继续循环
            finally:
                # 关闭浏览器
                if self.browser:
                    self.browser.close()

            # 如果设置了循环间隔，等待后继续
            if interval_minutes > 0 and not should_stop:
                logger.info(f"等待 {interval_minutes} 分钟后继续下一次循环... (按 Ctrl+C 可退出)")
                # 分块睡眠，每10秒检查一次退出信号，确保能快速响应 Ctrl+C
                for i in range(interval_minutes * 6):
                    if should_stop:
                        logger.info("检测到退出信号，停止等待")  # type: ignore[unreachable]
                        break
                    # 每分钟显示一次剩余时间
                    if i % 6 == 0 and i > 0:
                        remaining = interval_minutes - (i // 6)
                        logger.debug(f"还需等待 {remaining} 分钟...")
                    await asyncio.sleep(10)
            else:
                # 只执行一次，退出循环
                break

        logger.info("更新模式已停止")

    def close(self):
        """关闭所有资源"""
        if self.browser:
            self.browser.close()
        if self.db_ops:
            self.db_ops.flush_all()
        if self.sql_db:
            self.sql_db.close()
        if self.mongo_db:
            self.mongo_db.close()
