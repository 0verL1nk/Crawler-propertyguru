"""
安全高效的爬虫框架
支持代理IP、数据库存储、对象存储（S3/七牛云）和远程浏览器API
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .browser import LocalBrowser, RemoteBrowser, UndetectedBrowser, scrape_with_browser
from .config import Config
from .spider import Spider
from .storage import S3Manager, StorageManagerProtocol, create_storage_manager

__all__ = [
    "Spider",
    "Config",
    "RemoteBrowser",
    "LocalBrowser",
    "UndetectedBrowser",
    "scrape_with_browser",
    "S3Manager",
    "create_storage_manager",
    "StorageManagerProtocol",
]
