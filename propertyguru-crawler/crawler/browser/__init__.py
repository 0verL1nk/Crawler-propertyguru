"""浏览器模块"""

from .base import Browser
from .browser import (
    BrowserFactory,
    LocalBrowser,
    PyppeteerBrowserNew,
    RemoteBrowser,
    UndetectedBrowser,
    configure_performance_options,
    setup_media_blocking_cdp,
)

__all__ = [
    "Browser",
    "BrowserFactory",
    "LocalBrowser",
    "RemoteBrowser",
    "PyppeteerBrowserNew",
    "UndetectedBrowser",
    "configure_performance_options",
    "setup_media_blocking_cdp",
]
