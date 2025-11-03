"""
安全高效的爬虫框架
支持代理IP、数据库存储、对象存储（S3/七牛云）和远程浏览器API
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .browser import RemoteBrowser, scrape_with_browser
from .config import Config
from .spider import Spider
from .storage import QiniuManager, S3Manager, StorageManagerProtocol, create_storage_manager

__all__ = [
    "Spider",
    "Config",
    "RemoteBrowser",
    "scrape_with_browser",
    "S3Manager",
    "QiniuManager",
    "create_storage_manager",
    "StorageManagerProtocol",
]
