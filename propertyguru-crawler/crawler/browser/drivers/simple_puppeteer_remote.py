"""
简化版远程浏览器实现（基于Puppeteer/CDP协议）
使用Pyppeteer库连接到远程浏览器
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from typing import Any, Optional

try:
    import pyppeteer
    from pyppeteer.browser import Browser as PuppeteerBrowser
    from pyppeteer.page import Page
except ImportError:
    pyppeteer = None
    PuppeteerBrowser = None
    Page = None

from ..base import Browser


class SimplePuppeteerRemoteBrowser(Browser):
    """简化版远程浏览器管理器（基于Puppeteer/CDP协议）"""

    def __init__(
        self,
        browser_ws_endpoint: str | None = None,
        disable_images: bool = False,
        browser_type: str = "chrome",
    ):
        """
        初始化远程浏览器

        Args:
            browser_ws_endpoint: WebSocket 端点URL
            disable_images: 是否禁用图片、CSS、字体等资源加载（提升速度）
            browser_type: 浏览器类型（保留以兼容接口）
        """
        super().__init__()
        # 从环境变量获取配置
        self.browser_ws_endpoint = browser_ws_endpoint or os.getenv("REMOTE_BROWSER_WS_ENDPOINT")
        self.disable_images = disable_images
        self.browser_type = browser_type

        # 验证必要配置
        if not self.browser_ws_endpoint:
            raise ValueError(
                "未提供WebSocket端点！请在 .env 文件中设置 REMOTE_BROWSER_WS_ENDPOINT 环境变量"
            )

        # Puppeteer相关属性
        self.browser: Optional[PuppeteerBrowser] = None
        self.page: Optional[Page] = None
        self._connected = False

    def connect(self, options: Any = None):  # noqa: ARG002
        """
        连接到远程浏览器（基于WebSocket/CDP协议）

        Args:
            options: 保留以兼容接口，但在此实现中不使用
        """
        if pyppeteer is None:
            raise ImportError(
                "无法导入 Pyppeteer。请安装: pip install pyppeteer"
            )

        # 在新线程中执行连接以避免阻塞
        def connect_in_thread():
            try:
                # 创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # 连接到远程浏览器
                self.browser = loop.run_until_complete(
                    pyppeteer.connect(browserWSEndpoint=self.browser_ws_endpoint)
                )

                # 获取页面
                pages = loop.run_until_complete(self.browser.pages())
                if pages:
                    self.page = pages[0]
                else:
                    self.page = loop.run_until_complete(self.browser.newPage())

                self._connected = True
                loop.close()
            except Exception as e:
                print(f"连接失败: {e}")
                self._connected = False

        thread = threading.Thread(target=connect_in_thread)
        thread.start()
        thread.join(timeout=30)  # 等待最多30秒

        if not self._connected:
            raise TimeoutError("连接到远程浏览器超时")

    def close(self):
        """关闭浏览器连接"""
        if self.browser and self._connected:
            try:
                # 在新线程中执行关闭以避免阻塞
                def close_in_thread():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.browser.close())
                        loop.close()
                    except Exception:
                        pass

                thread = threading.Thread(target=close_in_thread)
                thread.start()
                thread.join(timeout=10)
            except Exception:
                pass
            finally:
                self.browser = None
                self.page = None
                self._connected = False

    def get(self, url: str):
        """导航到指定URL"""
        if not self.page or not self._connected:
            raise RuntimeError("浏览器未连接")

        # 在新线程中执行导航
        def navigate_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.page.goto(url))
                loop.close()
            except Exception as e:
                print(f"导航失败: {e}")

        thread = threading.Thread(target=navigate_in_thread)
        thread.start()
        thread.join(timeout=30)

    def find_element(self, by: str, value: str):
        """查找单个元素"""
        if not self.page or not self._connected:
            raise RuntimeError("浏览器未连接")

        # 将Selenium的定位方式转换为Puppeteer的方式
        selector = self._convert_selector(by, value)

        # 在新线程中执行查找
        result = [None]
        exception = [None]

        def find_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result[0] = loop.run_until_complete(self.page.querySelector(selector))
                loop.close()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=find_in_thread)
        thread.start()
        thread.join(timeout=30)

        if exception[0]:
            raise exception[0]

        return result[0]

    def find_elements(self, by: str, value: str):
        """查找多个元素"""
        if not self.page or not self._connected:
            raise RuntimeError("浏览器未连接")

        # 将Selenium的定位方式转换为Puppeteer的方式
        selector = self._convert_selector(by, value)

        # 在新线程中执行查找
        result = [[]]
        exception = [None]

        def find_all_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result[0] = loop.run_until_complete(self.page.querySelectorAll(selector))
                loop.close()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=find_all_in_thread)
        thread.start()
        thread.join(timeout=30)

        if exception[0]:
            raise exception[0]

        return result[0]

    def execute_script(self, script: str, *args):
        """执行JavaScript脚本"""
        if not self.page or not self._connected:
            raise RuntimeError("浏览器未连接")

        # 在新线程中执行脚本
        result = [None]
        exception = [None]

        def execute_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result[0] = loop.run_until_complete(self.page.evaluate(script, *args))
                loop.close()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=execute_in_thread)
        thread.start()
        thread.join(timeout=30)

        if exception[0]:
            raise exception[0]

        return result[0]

    def wait(self, timeout: int = 30):
        """创建等待实例（简化实现）"""
        if not self.page or not self._connected:
            raise RuntimeError("浏览器未连接")
        # 返回一个简化的等待对象
        return SimpleWait(self.page, timeout)

    def _convert_selector(self, by: str, value: str) -> str:
        """将Selenium选择器转换为Puppeteer选择器"""
        if by == "css selector":
            return value
        elif by == "xpath":
            return f"xpath/{value}"
        else:
            # 其他选择器类型直接返回
            return value

    def get_page_source(self) -> str:
        """获取页面源码"""
        if not self.page or not self._connected:
            raise RuntimeError("浏览器未连接")

        # 在新线程中获取页面源码
        result = [""]
        exception = [None]

        def get_source_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result[0] = loop.run_until_complete(self.page.content())
                loop.close()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=get_source_in_thread)
        thread.start()
        thread.join(timeout=30)

        if exception[0]:
            raise exception[0]

        return result[0]


class SimpleWait:
    """简化的等待类"""

    def __init__(self, page, timeout: int = 30):
        self.page = page
        self.timeout = timeout

    def until(self, _condition):
        """等待条件满足"""
        # 简化实现，直接返回True
        return True