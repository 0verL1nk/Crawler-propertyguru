"""
远程浏览器API管理器
基于Bright Data Scraping Browser，支持CDP命令、验证码处理、文件下载等
"""

from __future__ import annotations

import os
import time
from base64 import standard_b64decode
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from selenium.webdriver import ChromeOptions as Options
from selenium.webdriver import Remote
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection as Connection
from selenium.webdriver.support.wait import WebDriverWait

try:
    from selenium.webdriver import Chrome
except ImportError:
    Chrome = None  # type: ignore[assignment, misc]

from utils.logger import get_logger

logger = get_logger("BrowserManager")


class RemoteBrowser:
    """远程浏览器管理器"""

    def __init__(
        self,
        auth: str | None = None,
        server_addr: str | None = None,
        browser_type: str = "chrome",
    ):
        """
        初始化远程浏览器

        Args:
            auth: 认证信息，格式: 'username:password' 或从环境变量 BROWSER_AUTH 读取
            server_addr: 服务器地址，如不提供则自动构建
            browser_type: 浏览器类型，'chrome' 或 'firefox'

        Examples:
            >>> # 从环境变量读取配置
            >>> browser = RemoteBrowser()
            >>>
            >>> # 手动指定认证信息
            >>> browser = RemoteBrowser(auth='user:pass')
        """
        # 从环境变量获取配置
        self.auth = auth or os.getenv("BROWSER_AUTH")
        self.browser_type = browser_type

        if not self.auth:
            raise ValueError(
                "未提供认证信息！请在 .env 文件中设置 BROWSER_AUTH 环境变量，"
                "格式: BROWSER_AUTH=brd-customer-xxx-zone-scraping_browser1:password"
            )

        # 构建服务器地址
        if server_addr:
            self.server_addr = server_addr
        else:
            # Bright Data默认端口是9515
            self.server_addr = f"https://{self.auth}@brd.superproxy.io:9515"

        # 浏览器驱动
        self.driver: Remote | None = None
        self.connection: Connection | None = None

        logger.info(f"远程浏览器已初始化: {self.browser_type}")

    def connect(self, options: Options | None = None):
        """
        连接到远程浏览器

        Args:
            options: Chrome选项，如不提供则使用默认选项
        """
        try:
            logger.info("正在连接远程浏览器...")

            # 验证认证信息格式
            if self.auth and ":" in self.auth:
                username = self.auth.split(":")[0]
                if not username.startswith("brd-customer-"):
                    logger.warning(
                        f"警告：用户名格式可能不正确。期望格式: brd-customer-xxx-zone-scraping_browser1"
                        f"，当前用户名: {username}"
                    )

            # 创建连接
            self.connection = Connection(self.server_addr, "goog", self.browser_type)

            # 创建驱动
            if options is None:
                options = Options()

            self.driver = Remote(self.connection, options=options)

            logger.info("远程浏览器连接成功")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"连接远程浏览器失败: {error_msg}")

            # 提供更详细的错误提示
            if "Wrong customer name" in error_msg or "customer" in error_msg.lower():
                logger.error("=" * 60)
                logger.error("❌ 认证失败：用户名（customer name）不正确")
                logger.error("=" * 60)
                logger.error("请检查 .env 文件中的 BROWSER_AUTH 配置：")
                logger.error("")
                logger.error(
                    "正确格式: BROWSER_AUTH=brd-customer-xxx-zone-scraping_browser1:password"
                )
                logger.error("")
                if self.auth:
                    username = self.auth.split(":")[0] if ":" in self.auth else self.auth
                    logger.error(f"当前用户名: {username}")
                    logger.error("")
                    logger.error("常见问题：")
                    logger.error("  1. 用户名格式错误（应包含 brd-customer- 前缀）")
                    logger.error("  2. Zone 名称错误（应为 scraping_browser1）")
                    logger.error("  3. 用户名中包含空格或特殊字符")
                    logger.error("  4. 认证信息已过期或无效")
                logger.error("=" * 60)

            raise

    def cdp(self, cmd: str, params: dict[str, Any] | None = None) -> Any:
        """
        执行CDP命令（Chrome DevTools Protocol）

        Args:
            cmd: CDP命令名
            params: 命令参数

        Returns:
            命令执行结果

        Examples:
            >>> browser.cdp('Page.getFrameTree')
            >>> browser.cdp('Download.enable', {'allowedContentTypes': ['application/octet-stream']})
        """
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver

        result = driver.execute(
            "executeCdpCommand",
            {
                "cmd": cmd,
                "params": params or {},
            },
        )
        return result.get("value")

    def get(self, url: str):
        """
        导航到指定URL

        Args:
            url: 目标URL
        """
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver

        logger.info(f"导航到: {url}")
        driver.get(url)

    def find_element(self, by: str, value: str):
        """查找元素"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return driver.find_element(by, value)

    def find_elements(self, by: str, value: str) -> list:
        """查找多个元素"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return driver.find_elements(by, value)

    def execute_script(self, script: str, *args):
        """执行JavaScript"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return driver.execute_script(script, *args)

    def wait(self, timeout: int = 30):
        """创建WebDriverWait实例"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return WebDriverWait(driver, timeout=timeout)

    def enable_download(self, allowed_content_types: list[str] | None = None):
        """
        启用文件下载

        Args:
            allowed_content_types: 允许的内容类型，默认 ['application/octet-stream']
        """
        if allowed_content_types is None:
            allowed_content_types = ["application/octet-stream"]

        logger.info("启用文件下载功能...")
        self.cdp("Download.enable", {"allowedContentTypes": allowed_content_types})
        logger.info("文件下载已启用")

    def download_file(self, download_trigger: Callable, filename: str, timeout: int = 60) -> bool:
        """
        下载文件

        Args:
            download_trigger: 触发下载的函数（如点击按钮）
            filename: 保存文件名
            timeout: 超时时间（秒）

        Returns:
            是否成功

        Example:
            >>> browser.enable_download()
            >>> browser.get('https://example.com')
            >>> browser.download_file(
            ...     lambda: browser.find_element(By.CSS_SELECTOR, 'button.download').click(),
            ...     'file.csv'
            ... )
        """
        try:
            logger.info(f"触发下载，保存至: {filename}")

            # 触发下载
            download_trigger()

            # 等待下载完成
            logger.info("等待下载完成...")
            assert self.driver is not None  # 类型收缩
            driver = self.driver
            wait = WebDriverWait(driver, timeout=timeout, ignored_exceptions=(KeyError,))

            def get_download_id():
                result = self.cdp("Download.getLastCompleted")
                return result.get("id")

            download_id = wait.until(lambda _: get_download_id())

            # 获取下载内容
            logger.info(f"下载完成，下载ID: {download_id}")
            response = self.cdp("Download.getDownloadedBody", {"id": download_id})

            # 解码内容
            if response.get("base64Encoded"):
                body = standard_b64decode(response["body"])
            else:
                body = bytes(response["body"], "utf8")

            # 保存文件
            with Path(filename).open("wb") as f:
                f.write(body)

            logger.info(f"文件已保存: {filename}，大小: {len(body)} 字节")
            return True

        except Exception as e:
            logger.error(f"下载文件失败: {e}")
            return False

    def wait_for_captcha(self, detect_timeout: int = 10000) -> str:
        """
        等待验证码解决

        Args:
            detect_timeout: 检测超时时间（毫秒）

        Returns:
            验证码状态: 'solved', 'failed', 'timeout'
        """
        try:
            logger.info("等待验证码检测和解决...")

            result = self.cdp(
                "Captcha.waitForSolve",
                {
                    "detectTimeout": detect_timeout,
                },
            )

            status: str = result.get("status", "unknown")
            logger.info(f"验证码状态: {status}")

            return status

        except Exception as e:
            logger.error(f"验证码处理失败: {e}")
            return "failed"

    def enable_inspect(self, wait_time: int = 10) -> str | None:
        """
        启用调试模式（提供检查会话URL）

        Args:
            wait_time: 等待时间（秒），让用户有时间打开检查URL

        Returns:
            检查URL或None
        """
        try:
            logger.info("启用检查会话...")

            # 获取frame
            frames = self.cdp("Page.getFrameTree")
            frame_id = frames["frameTree"]["frame"]["id"]

            # 启用检查
            inspect = self.cdp("Page.inspect", {"frameId": frame_id})
            inspect_url = inspect.get("url")

            if inspect_url:
                logger.info(f"检查会话URL: {inspect_url}")
                logger.info(f"继续执行前等待 {wait_time} 秒...")
                time.sleep(wait_time)
                return str(inspect_url)

            return None

        except Exception as e:
            logger.error(f"启用检查会话失败: {e}")
            return None

    def get_page_source(self) -> str:
        """获取页面源码"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return str(driver.page_source)

    def get_screenshot(self, filename: str) -> bool:
        """
        截取屏幕截图

        Args:
            filename: 保存文件名

        Returns:
            是否成功
        """
        try:
            if not self.driver:
                raise RuntimeError("浏览器未连接，请先调用 connect()")
            assert self.driver is not None  # 类型收缩
            driver = self.driver

            driver.save_screenshot(filename)
            logger.info(f"截图已保存: {filename}")
            return True
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return False

    def close(self):
        """关闭浏览器连接"""
        if self.driver:
            try:
                logger.info("关闭浏览器会话...")
                self.driver.quit()
                logger.info("浏览器会话已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}")
            finally:
                self.driver = None
                self.connection = None

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    def __del__(self):
        """析构函数"""
        self.close()


class LocalBrowser:
    """本地浏览器管理器（用于测试）"""

    def __init__(self, headless: bool = False, options: Options | None = None):
        """
        初始化本地浏览器

        Args:
            headless: 是否使用无头模式
            options: Chrome选项，如不提供则使用默认选项
        """
        if Chrome is None:
            raise ImportError("无法导入Chrome驱动。请确保已安装selenium: pip install selenium")

        self.headless = headless
        self.options = options or Options()
        if headless:
            self.options.add_argument("--headless")
            self.options.add_argument("--disable-gpu")

        # 浏览器驱动
        self.driver: Chrome | None = None
        self.connection = None  # 本地浏览器没有连接对象

        logger.info(f"本地浏览器已初始化（headless={headless}）")

    def connect(self, options: Options | None = None):
        """
        连接到本地浏览器

        Args:
            options: Chrome选项，如不提供则使用初始化的选项
        """
        try:
            logger.info("正在启动本地浏览器...")

            if options is None:
                options = self.options

            # 创建Chrome驱动
            self.driver = Chrome(options=options)

            logger.info("本地浏览器启动成功")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"启动本地浏览器失败: {error_msg}")

            if "chromedriver" in error_msg.lower() or "executable" in error_msg.lower():
                logger.error("=" * 60)
                logger.error("❌ Chrome驱动未找到")
                logger.error("=" * 60)
                logger.error("请安装Chrome驱动：")
                logger.error("")
                logger.error("方法1: 使用webdriver-manager")
                logger.error("  pip install webdriver-manager")
                logger.error("")
                logger.error("方法2: 手动下载chromedriver")
                logger.error("  https://chromedriver.chromium.org/downloads")
                logger.error("")

            raise

    def cdp(self, cmd: str, params: dict[str, Any] | None = None) -> Any:
        """
        执行CDP命令（Chrome DevTools Protocol）

        Args:
            cmd: CDP命令名
            params: 命令参数

        Returns:
            命令执行结果
        """
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver

        result = driver.execute(
            "executeCdpCommand",
            {
                "cmd": cmd,
                "params": params or {},
            },
        )
        return result.get("value")

    def get(self, url: str):
        """
        导航到指定URL

        Args:
            url: 目标URL
        """
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver

        logger.info(f"导航到: {url}")
        driver.get(url)

    def find_element(self, by: str, value: str):
        """查找元素"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return driver.find_element(by, value)

    def find_elements(self, by: str, value: str) -> list:
        """查找多个元素"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return driver.find_elements(by, value)

    def execute_script(self, script: str, *args):
        """执行JavaScript"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return driver.execute_script(script, *args)

    def wait(self, timeout: int = 30):
        """创建WebDriverWait实例"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return WebDriverWait(driver, timeout=timeout)

    def enable_download(self, allowed_content_types: list[str] | None = None):
        """
        启用文件下载

        Args:
            allowed_content_types: 允许的内容类型，默认 ['application/octet-stream']
        """
        if allowed_content_types is None:
            allowed_content_types = ["application/octet-stream"]

        logger.info("启用文件下载功能...")
        self.cdp("Download.enable", {"allowedContentTypes": allowed_content_types})
        logger.info("文件下载已启用")

    def download_file(self, download_trigger: Callable, filename: str, timeout: int = 60) -> bool:
        """
        下载文件

        Args:
            download_trigger: 触发下载的函数（如点击按钮）
            filename: 保存文件名
            timeout: 超时时间（秒）

        Returns:
            是否成功
        """
        try:
            logger.info(f"触发下载，保存至: {filename}")

            # 触发下载
            download_trigger()

            # 等待下载完成
            logger.info("等待下载完成...")
            assert self.driver is not None  # 类型收缩
            driver = self.driver
            wait = WebDriverWait(driver, timeout=timeout, ignored_exceptions=(KeyError,))

            def get_download_id():
                result = self.cdp("Download.getLastCompleted")
                return result.get("id")

            download_id = wait.until(lambda _: get_download_id())

            # 获取下载内容
            logger.info(f"下载完成，下载ID: {download_id}")
            response = self.cdp("Download.getDownloadedBody", {"id": download_id})

            # 解码内容
            if response.get("base64Encoded"):
                body = standard_b64decode(response["body"])
            else:
                body = bytes(response["body"], "utf8")

            # 保存文件
            with Path(filename).open("wb") as f:
                f.write(body)

            logger.info(f"文件已保存: {filename}，大小: {len(body)} 字节")
            return True

        except Exception as e:
            logger.error(f"下载文件失败: {e}")
            return False

    def wait_for_captcha(self, _detect_timeout: int = 10000) -> str:
        """
        等待验证码解决（本地浏览器不支持，返回'solved'）

        Args:
            _detect_timeout: 检测超时时间（毫秒，未使用）

        Returns:
            验证码状态: 'solved'
        """
        logger.warning("本地浏览器不支持验证码自动解决，跳过验证码检测")
        return "solved"

    def enable_inspect(self, wait_time: int = 10) -> str | None:
        """
        启用调试模式（提供检查会话URL）

        Args:
            wait_time: 等待时间（秒），让用户有时间打开检查URL

        Returns:
            检查URL或None
        """
        try:
            logger.info("启用检查会话...")

            # 获取frame
            frames = self.cdp("Page.getFrameTree")
            frame_id = frames["frameTree"]["frame"]["id"]

            # 启用检查
            inspect = self.cdp("Page.inspect", {"frameId": frame_id})
            inspect_url = inspect.get("url")

            if inspect_url:
                logger.info(f"检查会话URL: {inspect_url}")
                logger.info(f"继续执行前等待 {wait_time} 秒...")
                time.sleep(wait_time)
                return str(inspect_url)

            return None

        except Exception as e:
            logger.error(f"启用检查会话失败: {e}")
            return None

    def get_page_source(self) -> str:
        """获取页面源码"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return str(driver.page_source)

    def get_screenshot(self, filename: str) -> bool:
        """
        截取屏幕截图

        Args:
            filename: 保存文件名

        Returns:
            是否成功
        """
        try:
            if not self.driver:
                raise RuntimeError("浏览器未连接，请先调用 connect()")
            assert self.driver is not None  # 类型收缩
            driver = self.driver

            driver.save_screenshot(filename)
            logger.info(f"截图已保存: {filename}")
            return True
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return False

    def close(self):
        """关闭浏览器连接"""
        if self.driver:
            try:
                logger.info("关闭浏览器会话...")
                self.driver.quit()
                logger.info("浏览器会话已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    def __del__(self):
        """析构函数"""
        self.close()


# 便捷函数
def scrape_with_browser(url: str, callback: Callable | None = None, auth: str | None = None) -> Any:
    """
    使用远程浏览器爬取网页（便捷函数）

    Args:
        url: 目标URL
        callback: 回调函数，接收browser实例作为参数
        auth: 认证信息（可选，默认从环境变量读取）

    Returns:
        回调函数的返回值

    Example:
        >>> def parse_page(browser):
        ...     elements = browser.find_elements(By.TAG_NAME, 'p')
        ...     return [el.text for el in elements]
        >>>
        >>> data = scrape_with_browser('https://example.com', callback=parse_page)
    """
    browser = RemoteBrowser(auth=auth)

    try:
        browser.connect()
        browser.get(url)

        if callback:
            return callback(browser)
        else:
            return browser.get_page_source()

    finally:
        browser.close()
