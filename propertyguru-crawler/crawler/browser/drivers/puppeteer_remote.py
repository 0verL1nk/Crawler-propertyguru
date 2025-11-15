"""
远程浏览器实现（基于Puppeteer/CDP协议）
使用Pyppeteer库连接到远程浏览器
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any, Dict, List, Optional

try:
    import pyppeteer
    from pyppeteer import launch
    from pyppeteer.browser import Browser as PuppeteerBrowser
    from pyppeteer.page import Page
except ImportError:
    pyppeteer = None
    launch = None
    PuppeteerBrowser = None
    Page = None

from ..base import Browser


class PuppeteerRemoteBrowser(Browser):
    """远程浏览器管理器（基于Puppeteer/CDP协议）"""

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
        self._loop: Optional[asyncio.AbstractEventLoop] = None

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

        # 获取当前事件循环
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            # 没有运行的事件循环，创建一个新的
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        # 连接到远程浏览器
        if self._loop.is_running():
            # 如果事件循环正在运行，我们需要在现有循环中执行协程
            # 但不能直接使用 run_until_complete，需要使用其他方式

            # 创建一个任务来连接浏览器
            async def connect_and_setup():
                import logging
                logging.info("开始连接到远程浏览器...")
                browser = await pyppeteer.connect(browserWSEndpoint=self.browser_ws_endpoint)
                logging.info("已连接到远程浏览器")
                pages = await browser.pages()
                logging.info(f"获取到 {len(pages)} 个页面")
                if pages:
                    page = pages[0]
                else:
                    page = await browser.newPage()

                if self.disable_images:
                    await self._configure_resource_blocking_internal(page)

                return browser, page

            # 在现有循环中调度任务
            import concurrent.futures
            import logging
            logging.info("在运行的事件循环中调度连接任务...")
            future = asyncio.run_coroutine_threadsafe(connect_and_setup(), self._loop)
            logging.info("等待连接结果...")
            self.browser, self.page = future.result(timeout=30)
            logging.info("连接完成")
        else:
            # 事件循环未运行，可以直接使用 run_until_complete
            import logging
            logging.info("在新事件循环中连接到远程浏览器...")
            self.browser = self._loop.run_until_complete(
                pyppeteer.connect(browserWSEndpoint=self.browser_ws_endpoint)
            )

            # 获取页面
            pages = self._loop.run_until_complete(self.browser.pages())
            if pages:
                self.page = pages[0]
            else:
                self.page = self._loop.run_until_complete(self.browser.newPage())

            # 配置性能优化
            if self.disable_images:
                self._loop.run_until_complete(self._configure_resource_blocking())

    async def _configure_resource_blocking(self):
        """配置资源拦截以禁用图片等资源加载"""
        if not self.page:
            return

        try:
            # 禁用图片、CSS、字体等资源
            await self.page.setRequestInterception(True)

            async def intercept_request(request):
                try:
                    url = request.url.lower()

                    # 阻止的资源类型
                    blocked_extensions = [
                        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
                        ".css", ".woff", ".woff2", ".ttf", ".otf",
                        ".mp4", ".webm", ".ogg", ".mp3", ".wav",
                    ]

                    # 检查是否应该阻止
                    should_block = any(url.endswith(ext) for ext in blocked_extensions)

                    if should_block:
                        await request.abort()
                    else:
                        await request.continue_()
                except Exception:
                    # 出现异常时继续请求
                    with contextlib.suppress(Exception):
                        await request.continue_()

            self.page.on('request', intercept_request)
        except Exception:
            pass

    def close(self):
        """关闭浏览器连接"""
        if self.browser:
            try:
                if self._loop and self._loop.is_running():
                    # 在运行的事件循环中，使用 run_coroutine_threadsafe
                    import concurrent.futures
                    future = asyncio.run_coroutine_threadsafe(self.browser.close(), self._loop)
                    future.result(timeout=10)
                else:
                    asyncio.run(self.browser.close())
            except Exception:
                pass
            finally:
                self.browser = None
                self.page = None

    def get(self, url: str):
        """导航到指定URL"""
        if not self.page:
            raise RuntimeError("浏览器未连接")

        if self._loop and self._loop.is_running():
            # 在运行的事件循环中，使用 run_coroutine_threadsafe
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(self.page.goto(url), self._loop)
            future.result(timeout=30)
        else:
            asyncio.run(self.page.goto(url))

    def find_element(self, by: str, value: str):
        """查找单个元素"""
        if not self.page:
            raise RuntimeError("浏览器未连接")

        # 将Selenium的定位方式转换为Puppeteer的方式
        selector = self._convert_selector(by, value)

        if self._loop and self._loop.is_running():
            # 在运行的事件循环中，使用 run_coroutine_threadsafe
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(self.page.querySelector(selector), self._loop)
            return future.result(timeout=30)
        else:
            return asyncio.run(self.page.querySelector(selector))

    def find_elements(self, by: str, value: str):
        """查找多个元素"""
        if not self.page:
            raise RuntimeError("浏览器未连接")

        # 将Selenium的定位方式转换为Puppeteer的方式
        selector = self._convert_selector(by, value)

        if self._loop and self._loop.is_running():
            # 在运行的事件循环中，使用 run_coroutine_threadsafe
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(self.page.querySelectorAll(selector), self._loop)
            return future.result(timeout=30)
        else:
            return asyncio.run(self.page.querySelectorAll(selector))

    def execute_script(self, script: str, *args):
        """执行JavaScript脚本"""
        if not self.page:
            raise RuntimeError("浏览器未连接")

        if self._loop and self._loop.is_running():
            # 在运行的事件循环中，使用 run_coroutine_threadsafe
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(self.page.evaluate(script, *args), self._loop)
            return future.result(timeout=30)
        else:
            return asyncio.run(self.page.evaluate(script, *args))

    def wait(self, timeout: int = 30):
        """创建等待实例（简化实现）"""
        if not self.page:
            raise RuntimeError("浏览器未连接")
        # 返回一个简化的等待对象
        return SimpleWait(self.page, timeout, self._loop)

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
        if not self.page:
            raise RuntimeError("浏览器未连接")

        if self._loop and self._loop.is_running():
            # 在运行的事件循环中，使用 run_coroutine_threadsafe
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(self.page.content(), self._loop)
            return future.result(timeout=30)
        else:
            return asyncio.run(self.page.content())


class SimpleWait:
    """简化的等待类"""

    def __init__(self, page, timeout: int = 30, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.page = page
        self.timeout = timeout
        self._loop = loop

    def until(self, _condition):
        """等待条件满足"""
        # 简化实现，直接返回True
        return True