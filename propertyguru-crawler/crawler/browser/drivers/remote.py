"""
远程浏览器实现（基于WebSocket/CDP协议）
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

# Support both sync and async API
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

from ..base import Browser


class RemoteBrowser(Browser):
    """远程浏览器管理器（基于WebSocket/CDP协议）"""

    def __init__(
        self,
        browser_ws_endpoint: str | None = None,
        disable_images: bool = False,
        browser_type: str = "chrome",
        use_async: bool = False,
    ):
        """
        初始化远程浏览器

        Args:
            browser_ws_endpoint: WebSocket 端点URL
            disable_images: 是否禁用图片、CSS、字体等资源加载（提升速度）
            browser_type: 浏览器类型，'chrome' 或 'firefox'
            use_async: 是否使用异步API
        """
        super().__init__()
        # 从环境变量获取配置
        self.browser_ws_endpoint = browser_ws_endpoint or os.getenv("REMOTE_BROWSER_WS_ENDPOINT")
        self.disable_images = disable_images
        self.browser_type = browser_type
        self.use_async = use_async

        # 线程执行器（用于在异步环境中复用 Playwright 同步API所需的专用线程）
        self._executor: ThreadPoolExecutor | None = None
        self._owner_thread_id: int | None = None

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

    def connect(self, options: Any = None):  # noqa: ARG002
        """
        连接到远程浏览器（基于WebSocket/CDP协议）

        Args:
            options: 保留以兼容接口，但在此实现中不使用
        """
        # 正确检测是否在 asyncio 事件循环中
        try:
            asyncio.get_running_loop()
            in_running_loop = True
        except RuntimeError:
            in_running_loop = False

        # 如果在运行中的事件循环中，使用专用线程执行同步连接
        if in_running_loop:
            self._ensure_executor()
            future = self._executor.submit(self._connect_sync)
            future.result()
            return

        # 同步路径（仅在没有运行事件循环时调用）
        self._connect_sync()

    def _run_on_browser_thread(self, func: Callable[..., Any], *args, **kwargs):
        """确保 Playwright 调用始终在浏览器所属线程上执行"""
        if not self._executor or threading.get_ident() == self._owner_thread_id:
            return func(*args, **kwargs)

        future = self._executor.submit(func, *args, **kwargs)
        return future.result()

    def _ensure_executor(self):
        if not self._executor:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="RemoteBrowser")

    def _connect_sync(self) -> None:
        """
        同步连接实现（将原有同步逻辑提取到此处），仅在非 asyncio 事件循环线程中调用。
        """
        if sync_playwright is None:
            raise ImportError(
                "无法导入 Playwright。请安装: pip install playwright && playwright install chromium"
            )

        # 使用Playwright通过WebSocket连接
        playwright_instance = sync_playwright()
        if playwright_instance is None:
            raise RuntimeError("无法启动 Playwright")
        self.playwright = playwright_instance.start()

        # 记录当前线程ID，确保后续操作运行在相同线程
        self._owner_thread_id = threading.get_ident()

        # 连接到远程浏览器
        self.browser = self.playwright.chromium.connect_over_cdp(self.browser_ws_endpoint)

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
            self.context = self.browser.new_context(**context_options)

        # 获取或创建页面
        pages = self.context.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = self.context.new_page()

        # 配置性能优化
        if self.disable_images:
            self._configure_resource_blocking()

    async def connect_async(self, options: Any = None) -> None:
        """
        异步连接接口：在 asyncio 环境中应调用此方法。
        - 如果浏览器对象配置为异步（use_async=True），直接 await 内部异步实现。
        - 否则在事件循环中通过线程池运行同步实现，避免阻塞事件循环。
        """
        if self.use_async:
            await self._connect_async()
            return

        self._ensure_executor()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._connect_sync)

    async def _connect_async(self):
        """异步连接到远程浏览器"""
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


    def close(self):
        """关闭浏览器连接"""

        def _close():
            if self.page:
                try:
                    self.page.close()
                except Exception:
                    pass
                finally:
                    self.page = None

            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
                finally:
                    self.context = None

            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass
                finally:
                    self.browser = None

            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception:
                    pass
                finally:
                    self.playwright = None

        self._run_on_browser_thread(_close)

    def get(self, url: str):
        """导航到指定URL"""
        if not self.page:
            raise RuntimeError("浏览器未连接")

        def _goto():
            self.page.goto(url)

        self._run_on_browser_thread(_goto)

    def find_element(self, by: str, value: str):
        """查找单个元素"""
        if not self.page:
            raise RuntimeError("浏览器未连接")
        selector = self._convert_selector(by, value)

        def _query():
            return self.page.query_selector(selector)

        return self._run_on_browser_thread(_query)

    def find_elements(self, by: str, value: str):
        """查找多个元素"""
        if not self.page:
            raise RuntimeError("浏览器未连接")
        selector = self._convert_selector(by, value)

        def _query_all():
            return self.page.query_selector_all(selector)

        return self._run_on_browser_thread(_query_all)

    def execute_script(self, script: str, *args):
        """执行JavaScript脚本"""
        if not self.page:
            raise RuntimeError("浏览器未连接")

        def _eval():
            return self.page.evaluate(script, *args)

        return self._run_on_browser_thread(_eval)

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

    def _configure_resource_blocking(self):
        """配置资源拦截以禁用图片等资源加载"""
        try:
            if not self.context:
                return

            # 禁用图片、CSS、字体等资源
            self.context.route("**/*", lambda route: self._should_block_request(route))
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

        def _content():
            return self.page.content()

        return self._run_on_browser_thread(_content)


class SimpleWait:
    """简化的等待类"""

    def __init__(self, page, timeout: int = 30):
        self.page = page
        self.timeout = timeout

    def until(self, _condition):
        """等待条件满足"""
        # 简化实现，直接返回True
        return True
