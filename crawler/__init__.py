"""
安全高效的爬虫框架
支持代理IP、数据库存储、S3云存储和远程浏览器API
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .browser import RemoteBrowser, scrape_with_browser
from .config import Config
from .spider import Spider

__all__ = ["Spider", "Config", "RemoteBrowser", "scrape_with_browser"]
