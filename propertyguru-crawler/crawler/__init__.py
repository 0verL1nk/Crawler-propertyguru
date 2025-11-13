"""PropertyGuru 爬虫模块"""

# 核心模块
from .core import PropertyGuruCrawler, Spider, Config

# 数据库模块
from .database import (
    get_database,
    DBOperations,
    ListingInfoORM,
    MediaItemORM,
)

# 数据模型
from .models import (
    ListingInfo,
    MediaItem,
    PropertyDetails,
)

# 浏览器
from .browser import LocalBrowser, RemoteBrowser, UndetectedBrowser

# 解析器
from .parsers import ListingPageParser

# 存储
from .storage import create_storage_manager, MediaProcessor

# 工具
from .utils import ProxyManager, CrawlProgress, WatermarkRemover

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
