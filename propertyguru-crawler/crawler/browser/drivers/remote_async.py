"""
远程浏览器实现（基于WebSocket/CDP协议）- 异步版本
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any

# 使用异步API
try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

from ..base import Browser


class AsyncRemoteBrowser(Browser):
    """远程浏览器管理器（基于WebSocket/CDP协议）- 异步版本"""

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
            browser_type: 浏览器类型，'chrome' 或 'firefox'
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

        # WebSocket/CDP相关属性
        self.playwright: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None

    async def connect(self, options: Any = None):  # noqa: ARG002
        """
        连接到远程浏览器（基于WebSocket/CDP协议）

        Args:
            options: 保留以兼容接口，但在此实现中不使用
        """
        if async_playwright is None:
            raise ImportError(
                "无法导入 Playwright。请安装: pip install playwright && playwright install chromium"
            )

        # 使用Playwright通过WebSocket连接
        self.playwright = await async_playwright().start()

        # 连接到远程浏览器
        self.browser = await self.playwright.chromium.connect_over_cdp(self.browser_ws_endpoint)

        # 获取或创建上下文
        contexts = self.browser.contexts
        if contexts:
            self.context = contexts[0]
        else:
            # 创建新上下文
            context_options: dict[str, Any] = {}
            if self.disable_images:
                # 配置资源拦截
                context_options["viewport"] = {"width": 1920, "height": 1080}
            self.context = await self.browser.new_context(**context_options)

        # 获取或创建页面
        pages = self.context.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = await self.context.new_page()

        # 配置性能优化
        if self.disable_images:
            await self._configure_resource_blocking()

    async def close(self):
        """关闭浏览器连接"""
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            finally:
                self.page = None

        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            finally:
                self.context = None

        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            finally:
                self.browser = None

        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
            finally:
                self.playwright = None

    async def get(self, url: str):
        """导航到指定URL"""
        if not self.page:
            raise RuntimeError("浏览器未连接")
        await self.page.goto(url)

    def find_element(self, by: str, value: str):
        """查找单个元素"""
        if not self.page:
            raise RuntimeError("浏览器未连接")
        # 将Selenium的定位方式转换为Playwright的方式
        selector = self._convert_selector(by, value)
        return self.page.query_selector(selector)

    def find_elements(self, by: str, value: str):
        """查找多个元素"""
        if not self.page:
            raise RuntimeError("浏览器未连接")
        # 将Selenium的定位方式转换为Playwright的方式
        selector = self._convert_selector(by, value)
        return self.page.query_selector_all(selector)

    def execute_script(self, script: str, *args):
        """执行JavaScript脚本"""
        if not self.page:
            raise RuntimeError("浏览器未连接")
        return self.page.evaluate(script, *args)

    def wait(self, timeout: int = 30):
        """创建等待实例（简化实现）"""
        if not self.page:
            raise RuntimeError("浏览器未连接")
        # 返回一个简化的等待对象
        return SimpleWait(self.page, timeout)

    def _convert_selector(self, by: str, value: str) -> str:
        """将Selenium选择器转换为Playwright选择器"""
        if by == "css selector":
            return value
        elif by == "xpath":
            return f"xpath={value}"
        else:
            # 其他选择器类型直接返回
            return value

    async def _configure_resource_blocking(self):
        """配置资源拦截以禁用图片等资源加载"""
        try:
            if not self.context:
                return

            # 禁用图片、CSS、字体等资源
            await self.context.route("**/*", lambda route: self._should_block_request(route))
        except Exception:
            pass

    def _should_block_request(self, route):
        """判断是否应该阻止请求"""
        try:
            url = route.request.url.lower()

            # 阻止的资源类型
            blocked_extensions = [
                ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
                ".css", ".woff", ".woff2", ".ttf", ".otf",
                ".mp4", ".webm", ".ogg", ".mp3", ".wav",
            ]

            # 检查是否应该阻止
            should_block = any(url.endswith(ext) for ext in blocked_extensions)

            if should_block:
                route.abort()
            else:
                route.continue_()

        except Exception:
            # 使用 contextlib.suppress 替代 try-except-pass
            with contextlib.suppress(Exception):
                route.continue_()

    def get_page_source(self) -> str:
        """获取页面源码"""
        if not self.page:
            raise RuntimeError("浏览器未连接")
        return self.page.content()


class SimpleWait:
    """简化的等待类"""

    def __init__(self, page, timeout: int = 30):
        self.page = page
        self.timeout = timeout

    def until(self, _condition):
        """等待条件满足"""
        # 简化实现，直接返回True
        return True