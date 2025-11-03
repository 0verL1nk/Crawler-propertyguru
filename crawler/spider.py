"""
爬虫核心引擎
"""

import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional, Protocol, Union, cast

import aiohttp
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.logger import get_logger

from .config import Config
from .database import DatabaseManager
from .proxy_manager import ProxyManager
from .storage import StorageManagerProtocol, create_storage_manager


class DatabaseProtocol(Protocol):
    """数据库协议接口"""

    def insert_one(self, collection: str, document: dict[str, Any]) -> Any:
        """插入单条记录"""
        ...

    def insert_many(self, collection: str, documents: list[dict[str, Any]]) -> Any:
        """插入多条记录"""
        ...


logger = get_logger("Spider")


class Response:
    """响应对象封装"""

    def __init__(
        self, url: str, status_code: int, content: bytes, headers: dict, encoding: str = "utf-8"
    ):
        self.url = url
        self.status_code = status_code
        self.content = content
        self.headers = headers
        self.encoding = encoding
        self._text: Optional[str] = None
        self._soup: Optional[BeautifulSoup] = None
        self._json: Optional[dict[Any, Any]] = None

    @property
    def text(self) -> str:
        """获取文本内容"""
        if self._text is None:
            self._text = self.content.decode(self.encoding, errors="ignore")
        assert self._text is not None  # 类型守卫
        return self._text

    @property
    def soup(self) -> BeautifulSoup:
        """获取BeautifulSoup对象"""
        if self._soup is None:
            self._soup = BeautifulSoup(self.text, "lxml")
        assert self._soup is not None  # 类型守卫
        return self._soup

    def json(self) -> dict[Any, Any]:
        """解析JSON"""
        if self._json is None:
            import json

            self._json = json.loads(self.text)
        assert self._json is not None  # 类型守卫
        return self._json

    def xpath(self, xpath: str):
        """XPath选择器"""
        from lxml import etree

        tree = etree.HTML(self.text)
        return tree.xpath(xpath)

    def css(self, selector: str):
        """CSS选择器"""
        return self.soup.select(selector)


class Spider:
    """爬虫主类"""

    def __init__(self, config: Union[Config, dict]):
        """
        初始化爬虫

        Args:
            config: 配置对象或字典
        """
        if isinstance(config, dict):
            self.config = Config(config)
        else:
            self.config = config

        # 爬虫配置
        self.crawler_config = self.config.get_section("crawler")
        self.concurrency = self.crawler_config.get("concurrency", 5)
        self.timeout = self.crawler_config.get("timeout", 30)
        self.max_retries = self.crawler_config.get("max_retries", 3)
        self.retry_delay = self.crawler_config.get("retry_delay", 2)
        self.delay = self.crawler_config.get("delay", 1)
        self.random_delay = self.crawler_config.get("random_delay", [0, 2])
        self.use_proxy = self.crawler_config.get("use_proxy", True)
        self.rotate_user_agent = self.crawler_config.get("rotate_user_agent", True)
        self.verify_ssl = self.crawler_config.get("verify_ssl", True)

        # User-Agent生成器
        self.ua = UserAgent() if self.rotate_user_agent else None

        # 初始化组件
        self.proxy_manager: Optional[ProxyManager] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.s3_manager: Optional[StorageManagerProtocol] = None
        self.proxy_adapter: Optional[Any] = None

        self._init_components()

        # 会话
        self.session = requests.Session()

        # 配置代理和SSL（如果使用静态代理）
        self._setup_proxy_session()

        logger.info("爬虫初始化完成")

    def _init_components(self):
        """初始化各个组件"""
        self._init_proxy_manager()
        self._init_database_manager()
        self._init_s3_manager()

    def _init_proxy_manager(self):
        """初始化代理管理器"""
        if not self.use_proxy:
            return

        proxy_config = self.config.get_section("proxy")
        if not proxy_config.get("enabled", False):
            return

        try:
            self.proxy_manager = ProxyManager(proxy_config)
            logger.info("代理管理器已启用")
        except Exception as e:
            logger.warning(f"代理管理器初始化失败: {e}")

    def _init_database_manager(self):
        """初始化数据库管理器"""
        db_config = self.config.get_section("database")
        if not db_config:
            return

        try:
            self.db_manager = DatabaseManager(db_config)
            logger.info("数据库管理器已启用")
        except Exception as e:
            logger.warning(f"数据库管理器初始化失败: {e}")

    def _init_s3_manager(self):
        """初始化S3存储管理器"""
        s3_config = self.config.get_section("s3")
        if not s3_config or not s3_config.get("enabled", False):
            return

        try:
            # 使用工厂函数创建存储管理器（支持S3和七牛云）
            self.s3_manager = create_storage_manager(s3_config)
            logger.info("存储管理器已启用")
        except Exception as e:
            logger.warning(f"存储管理器初始化失败: {e}")

    def _setup_proxy_session(self):
        """设置会话代理（如果使用静态代理）"""
        # 如果使用代理适配器，设置静态代理到会话
        if self.proxy_adapter:
            proxies = self.proxy_adapter.get_proxies()
            if proxies:
                self.session.proxies.update(proxies)

    def _get_headers(self) -> dict:
        """获取请求头"""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # 随机User-Agent
        if self.ua:
            headers["User-Agent"] = self.ua.random
        else:
            headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

        return headers

    def _get_proxy(self) -> Optional[dict]:
        """获取代理"""
        if not self.proxy_manager:
            return None

        proxy = self.proxy_manager.get_proxy()
        if proxy:
            return proxy.get_proxy_dict()
        return None

    def _sleep(self):
        """请求间隔延迟"""
        if self.delay > 0:
            delay_time = self.delay

            # 添加随机延迟
            if self.random_delay:
                min_delay, max_delay = self.random_delay
                delay_time += random.uniform(min_delay, max_delay)

            time.sleep(delay_time)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch(self, url: str, method: str = "GET", **kwargs) -> Optional[Response]:
        """
        发送HTTP请求

        Args:
            url: URL
            method: 请求方法
            **kwargs: 其他请求参数

        Returns:
            Response对象
        """
        proxy_dict: Optional[dict[str, str]] = None
        try:
            # 准备参数
            headers = kwargs.pop("headers", {})
            headers.update(self._get_headers())

            proxy_dict = kwargs.pop("proxies", None) or self._get_proxy()
            timeout = kwargs.pop("timeout", self.timeout)
            verify = kwargs.pop("verify", self.verify_ssl)

            # 发送请求
            logger.debug(f"请求: {method} {url}")

            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                proxies=proxy_dict,
                timeout=timeout,
                verify=verify,
                **kwargs,
            )

            response.raise_for_status()

            # 标记代理成功
            if proxy_dict and self.proxy_manager:
                proxy = self.proxy_manager.get_proxy()
                if proxy:
                    self.proxy_manager.mark_success(proxy)

            # 请求延迟
            self._sleep()

            # 创建Response对象
            return Response(
                url=response.url,
                status_code=response.status_code,
                content=response.content,
                headers=dict(response.headers),
                encoding=response.encoding or "utf-8",
            )

        except requests.RequestException as e:
            logger.error(f"请求失败: {url}, 错误: {e}")

            # 标记代理失败
            if proxy_dict and self.proxy_manager:
                proxy = self.proxy_manager.get_proxy()
                if proxy:
                    self.proxy_manager.mark_failure(proxy)

            raise

    def get(self, url: str, **kwargs) -> Optional[Response]:
        """GET请求"""
        return self.fetch(url, "GET", **kwargs)

    def post(self, url: str, **kwargs) -> Optional[Response]:
        """POST请求"""
        return self.fetch(url, "POST", **kwargs)

    async def async_fetch(
        self, session: aiohttp.ClientSession, url: str, method: str = "GET", **kwargs
    ) -> Optional[Response]:
        """
        异步HTTP请求

        Args:
            session: aiohttp会话
            url: URL
            method: 请求方法
            **kwargs: 其他参数

        Returns:
            Response对象
        """
        try:
            headers = kwargs.pop("headers", {})
            headers.update(self._get_headers())

            proxy = kwargs.pop("proxy", None)
            if proxy is None and self.use_proxy:
                proxy_dict = self._get_proxy()
                if proxy_dict:
                    proxy = proxy_dict.get("http") or proxy_dict.get("https")

            timeout = aiohttp.ClientTimeout(total=kwargs.pop("timeout", self.timeout))

            logger.debug(f"异步请求: {method} {url}")

            async with session.request(
                method=method,
                url=url,
                headers=headers,
                proxy=proxy,
                timeout=timeout,
                ssl=self.verify_ssl,
                **kwargs,
            ) as response:
                content = await response.read()

                return Response(
                    url=str(response.url),
                    status_code=response.status,
                    content=content,
                    headers=dict(response.headers),
                    encoding=response.charset or "utf-8",
                )

        except Exception as e:
            logger.error(f"异步请求失败: {url}, 错误: {e}")
            return None

    async def async_crawl(self, urls: list[str], callback: Optional[Callable] = None):
        """
        异步批量爬取

        Args:
            urls: URL列表
            callback: 回调函数
        """
        async with aiohttp.ClientSession() as session:
            tasks = []

            for url in urls:
                task = asyncio.create_task(self.async_fetch(session, url))
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理响应
            if callback:
                for response in responses:
                    if isinstance(response, Response):
                        if asyncio.iscoroutinefunction(callback):
                            await callback(response)
                        else:
                            callback(response)

    def crawl(
        self,
        urls: list[str],
        callback: Optional[Callable] = None,
        max_workers: Optional[int] = None,
    ):
        """
        多线程批量爬取

        Args:
            urls: URL列表
            callback: 回调函数
            max_workers: 最大线程数
        """
        max_workers = max_workers or self.concurrency

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.get, url): url for url in urls}

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    response = future.result()
                    if response and callback:
                        callback(response)
                except Exception as e:
                    logger.error(f"爬取失败: {url}, 错误: {e}")

    def start(self, urls: list[str], callback: Optional[Callable] = None, async_mode: bool = False):
        """
        开始爬取

        Args:
            urls: URL列表
            callback: 回调函数
            async_mode: 是否使用异步模式
        """
        logger.info(f"开始爬取 {len(urls)} 个URL")
        start_time = time.time()

        try:
            if async_mode:
                # 异步模式
                asyncio.run(self.async_crawl(urls, callback))
            else:
                # 多线程模式
                self.crawl(urls, callback)
        finally:
            elapsed_time = time.time() - start_time
            logger.info(f"爬取完成，耗时: {elapsed_time:.2f}秒")

    def save_to_db(self, data: Union[dict, list[dict]], collection: Optional[str] = None):
        """
        保存数据到数据库

        Args:
            data: 数据
            collection: 集合/表名
        """
        if not self.db_manager:
            logger.warning("数据库管理器未初始化")
            return

        if collection is None:
            logger.warning("集合/表名不能为空")
            return

        db = self.db_manager.get_db()

        # 使用 Protocol 进行类型转换，因为 MongoDBManager 和 MySQLManager 都实现了这些方法
        db_protocol = cast("DatabaseProtocol", db)

        try:
            if isinstance(data, list):
                db_protocol.insert_many(collection, data)
            else:
                db_protocol.insert_one(collection, data)
            logger.info(f"数据保存成功: {collection}")
        except Exception as e:
            logger.error(f"数据保存失败: {e}")

    def save_to_s3(self, data: Union[str, bytes], s3_key: str):
        """
        保存数据到S3

        Args:
            data: 数据
            s3_key: S3键
        """
        if not self.s3_manager:
            logger.warning("S3管理器未初始化")
            return

        try:
            from io import BytesIO

            if isinstance(data, str):
                data = data.encode("utf-8")

            file_obj = BytesIO(data)
            self.s3_manager.upload_fileobj(file_obj, s3_key)
            logger.info(f"数据上传S3成功: {s3_key}")
        except Exception as e:
            logger.error(f"数据上传S3失败: {e}")

    def close(self):
        """关闭资源"""
        if self.session:
            self.session.close()

        if self.db_manager:
            self.db_manager.close()

        logger.info("爬虫资源已释放")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
