"""PropertyGuru 爬虫模块"""

# 核心模块
# 浏览器
from .browser import LocalBrowser, RemoteBrowser, UndetectedBrowser
from .core import Config, PropertyGuruCrawler, Spider

# 数据库模块
from .database import (
    DBOperations,
    ListingInfoORM,
    MediaItemORM,
    get_database,
)

# 数据模型
from .models import (
    ListingInfo,
    MediaItem,
    PropertyDetails,
)

# 解析器
from .parsers import ListingPageParser

# 存储
from .storage import MediaProcessor, create_storage_manager

# 工具
from .utils import CrawlProgress, ProxyManager, WatermarkRemover

__all__ = [
    # 核心
    "PropertyGuruCrawler",
    "Spider",
    "Config",
    # 数据库
    "get_database",
    "DBOperations",
    "ListingInfoORM",
    "MediaItemORM",
    # 模型
    "ListingInfo",
    "MediaItem",
    "PropertyDetails",
    # 浏览器
    "LocalBrowser",
    "RemoteBrowser",
    "UndetectedBrowser",
    # 解析器
    "ListingPageParser",
    # 存储
    "create_storage_manager",
    "MediaProcessor",
    # 工具
    "ProxyManager",
    "CrawlProgress",
    "WatermarkRemover",
]
