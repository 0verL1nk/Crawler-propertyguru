"""
浏览器爬虫工厂
根据配置创建相应的浏览器爬虫实例
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .drivers.local import LocalBrowser
from .drivers.remote import RemoteBrowser
from .drivers.undetected import UndetectedBrowser

if TYPE_CHECKING:
    from .base import Browser


class BrowserFactory:
    """浏览器爬虫工厂类"""

    @staticmethod
    def create_browser(browser_type: str | None = None, **kwargs) -> Browser:
        """
        创建浏览器爬虫实例

        Args:
            browser_type: 浏览器类型 ('undetected', 'local', 'remote')
                         如果为 None，从环境变量 BROWSER_TYPE 读取
            **kwargs: 传递给浏览器构造函数的参数

        Returns:
            浏览器爬虫实例

        Raises:
            ValueError: 当配置无效时
            ImportError: 当依赖包未安装时
        """
        if browser_type is None:
            browser_type = os.getenv("BROWSER_TYPE", "remote").lower()

        if browser_type == "undetected":
            # 使用 Undetected Chrome（推荐用于反爬虫检测）
            headless = kwargs.get("headless", os.getenv("BROWSER_HEADLESS", "false").lower() == "true")
            version_main = kwargs.get("version_main") or os.getenv("CHROME_VERSION")
            disable_images = kwargs.get("disable_images", os.getenv("BROWSER_DISABLE_IMAGES", "true").lower() == "true")
            use_virtual_display = kwargs.get("use_virtual_display", os.getenv("BROWSER_USE_VIRTUAL_DISPLAY", "false").lower() == "true")

            # ChromeDriver路径（可选：用于ARM64等非x86架构）
            driver_path = kwargs.get("driver_path") or os.getenv("CHROMEDRIVER_PATH")
            browser_path = kwargs.get("browser_path") or os.getenv("CHROME_BINARY_PATH")

            browser_kwargs = {}
            if driver_path:
                browser_kwargs["driver_executable_path"] = driver_path
            if browser_path:
                browser_kwargs["browser_executable_path"] = browser_path

            return UndetectedBrowser(
                headless=headless,
                version_main=int(version_main) if version_main else None,
                disable_images=disable_images,
                use_virtual_display=use_virtual_display,
                **browser_kwargs,
            )

        elif browser_type == "local":
            # 使用本地浏览器（测试）
            headless = kwargs.get("headless", os.getenv("BROWSER_HEADLESS", "false").lower() == "true")
            disable_images = kwargs.get("disable_images", os.getenv("BROWSER_DISABLE_IMAGES", "true").lower() == "true")
            page_load_strategy = kwargs.get("page_load_strategy", os.getenv("BROWSER_PAGE_LOAD_STRATEGY", "eager"))

            return LocalBrowser(
                headless=headless,
                disable_images=disable_images,
                page_load_strategy=page_load_strategy,
            )

        else:
            # 使用远程浏览器（WebSocket/CDP）
            browser_ws_endpoint = kwargs.get("browser_ws_endpoint") or os.getenv("REMOTE_BROWSER_WS_ENDPOINT")
            if not browser_ws_endpoint:
                raise ValueError(
                    "未配置REMOTE_BROWSER_WS_ENDPOINT环境变量\n"
                    "提示：\n"
                    "  - 使用远程浏览器：配置 REMOTE_BROWSER_WS_ENDPOINT\n"
                    "  - 格式: REMOTE_BROWSER_WS_ENDPOINT=wss://server:9222/devtools/browser/id"
                )

            disable_images = kwargs.get("disable_images", os.getenv("BROWSER_DISABLE_IMAGES", "true").lower() == "true")
            browser_type_param = kwargs.get("browser_type", "chrome")

            return RemoteBrowser(
                browser_ws_endpoint=browser_ws_endpoint,
                disable_images=disable_images,
                browser_type=browser_type_param,
            )
