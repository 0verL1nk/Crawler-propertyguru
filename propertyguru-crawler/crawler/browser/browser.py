"""
浏览器模块主文件
提供向后兼容的接口和公共工具函数
"""

from __future__ import annotations

# 保持向后兼容的导入
from .base import Browser
from .drivers.local import LocalBrowser
from .drivers.remote import RemoteBrowser
from .drivers.undetected import UndetectedBrowser
from .factory import BrowserFactory

# 公共工具函数
from .utils import configure_performance_options, setup_media_blocking_cdp

__all__ = [
    "Browser",
    "BrowserFactory",
    "LocalBrowser",
    "RemoteBrowser",
    "UndetectedBrowser",
    "configure_performance_options",
    "setup_media_blocking_cdp",
]
