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

try:
    import undetected_chromedriver as uc
except ImportError:
    uc = None

from utils.logger import get_logger
from utils.retry import retry_on_error

logger = get_logger("BrowserManager")


# JavaScript 脚本常量 - 用于禁用媒体功能
DISABLE_MEDIA_JS = """
// 禁用媒体设备 API
Object.defineProperty(navigator, 'mediaDevices', {
    get: () => undefined
});
Object.defineProperty(navigator, 'getUserMedia', {
    get: () => undefined
});
Object.defineProperty(navigator, 'webkitGetUserMedia', {
    get: () => undefined
});
Object.defineProperty(navigator, 'mozGetUserMedia', {
    get: () => undefined
});
Object.defineProperty(navigator, 'msGetUserMedia', {
    get: () => undefined
});

// 阻止 video 和 audio 元素加载
(function() {
    const originalCreateElement = document.createElement;
    document.createElement = function(tagName) {
        const element = originalCreateElement.call(document, tagName);
        if (tagName.toLowerCase() === 'video' || tagName.toLowerCase() === 'audio') {
            element.remove();
            return originalCreateElement.call(document, 'div');
        }
        return element;
    };

    // 阻止现有视频/音频元素加载
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeName === 'VIDEO' || node.nodeName === 'AUDIO') {
                    node.remove();
                }
            });
        });
    });
    observer.observe(document.body || document.documentElement, {
        childList: true,
        subtree: true
    });
})();
"""

# 需要阻止的媒体文件扩展名
BLOCKED_MEDIA_URLS = [
    "*.mp4",
    "*.webm",
    "*.ogg",
    "*.avi",
    "*.mov",
    "*.wmv",
    "*.flv",
    "*.mkv",
    "*.m4v",
    "*.3gp",
]


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

    def find_elements(self, by: str, value: str) -> list[Any]:
        """查找多个元素"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return list(driver.find_elements(by, value))

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

    def find_elements(self, by: str, value: str) -> list[Any]:
        """查找多个元素"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return list(driver.find_elements(by, value))

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


class UndetectedBrowser:
    """基于undetected-chromedriver的本地浏览器管理器（增强反检测）"""

    def __init__(
        self,
        headless: bool = False,
        version_main: int | None = None,
        use_subprocess: bool = True,
        disable_images: bool = False,
        use_virtual_display: bool = False,
        **kwargs,
    ):
        """
        初始化Undetected浏览器

        Args:
            headless: 是否使用无头模式
            version_main: Chrome主版本号（可选，自动检测）
            use_subprocess: 是否使用子进程模式
            disable_images: 是否禁用图片加载（提升速度）
            use_virtual_display: 是否使用虚拟显示（有头模式但不显示窗口，需要安装xvfb）
            **kwargs: 传递给undetected_chromedriver的其他参数

        Examples:
            >>> # 基本使用
            >>> browser = UndetectedBrowser()
            >>>
            >>> # 无头模式
            >>> browser = UndetectedBrowser(headless=True)
            >>>
            >>> # 有头模式但不显示窗口（推荐）
            >>> browser = UndetectedBrowser(use_virtual_display=True)
            >>>
            >>> # 指定Chrome版本
            >>> browser = UndetectedBrowser(version_main=120)
            >>>
            >>> # 禁用图片加载（加速爬取）
            >>> browser = UndetectedBrowser(disable_images=True)
        """
        if uc is None:
            raise ImportError(
                "无法导入undetected_chromedriver。请安装: pip install undetected-chromedriver"
            )

        self.headless = headless
        self.version_main = version_main
        self.use_subprocess = use_subprocess
        self.disable_images = disable_images
        self.use_virtual_display = use_virtual_display
        self.kwargs = kwargs

        # 浏览器驱动和虚拟显示
        self.driver: uc.Chrome | None = None
        self.connection = None  # 本地浏览器没有连接对象
        self.display: Any = None  # 虚拟显示（pyvirtualdisplay.Display）

        logger.info(
            f"Undetected浏览器已初始化（headless={headless}, "
            f"virtual_display={use_virtual_display}, disable_images={disable_images}）"
        )

    def _configure_performance_options(self, options: Options) -> None:
        """配置性能优化选项（禁用图片、CSS、字体等）"""
        logger.info("已启用资源优化：禁用图片、CSS、字体、视频加载")

        # Chrome preferences 配置
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2,
            "profile.managed_default_content_settings.media_stream": 2,
            "profile.managed_default_content_settings.media_stream_mic": 2,
            "profile.managed_default_content_settings.media_stream_camera": 2,
            "profile.default_content_setting_values.media_stream_mic": 2,
            "profile.default_content_setting_values.media_stream_camera": 2,
            "profile.default_content_setting_values.autoplay": 2,
            "profile.default_content_setting_values.notifications": 2,
        }
        options.add_experimental_option("prefs", prefs)

        # Chrome 命令行参数
        performance_args = [
            "--blink-settings=imagesEnabled=false",
            "--disable-extensions",
            "--disable-plugins",
            "--mute-audio",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-sync",
            "--disable-translate",
            "--hide-scrollbars",
            "--metrics-recording-only",
            "--no-first-run",
            "--safebrowsing-disable-auto-update",
            "--disable-ipc-flooding-protection",
        ]
        for arg in performance_args:
            options.add_argument(arg)

    def _setup_media_blocking_cdp(self) -> None:
        """通过 CDP 设置媒体阻止功能"""
        if not self.driver:
            return

        try:
            # 注入 JavaScript 禁用媒体 API
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": DISABLE_MEDIA_JS},
            )

            # 启用 Network 域并阻止媒体资源
            try:
                self.driver.execute_cdp_cmd("Network.enable", {})
                self.driver.execute_cdp_cmd(
                    "Network.setBlockedURLs",
                    {"urls": BLOCKED_MEDIA_URLS},
                )
            except Exception as e:
                logger.debug(f"Network 域设置失败（不影响使用）: {e}")

            # 禁用媒体权限
            try:
                for permission_name in ["camera", "microphone"]:
                    self.driver.execute_cdp_cmd(
                        "Browser.setPermission",
                        {
                            "origin": "https://*",
                            "permission": {"name": permission_name},
                            "setting": "denied",
                        },
                    )
            except Exception as e:
                logger.debug(f"权限设置失败（不影响使用）: {e}")

            logger.debug("已通过 CDP 禁用媒体访问和资源加载")
        except Exception as e:
            logger.warning(f"通过 CDP 禁用媒体失败（不影响使用）: {e}")

    @retry_on_error(max_retries=3, retry_delay=5, logger_instance=logger)
    def connect(self, options: Options | None = None):
        """
        连接到本地浏览器

        Args:
            options: Chrome选项（可选）
        """
        logger.info("正在启动Undetected浏览器...")

        # 启动虚拟显示（如果启用）
        if self.use_virtual_display and not self.headless:
            try:
                from pathlib import Path

                from pyvirtualdisplay import Display

                # 检测是否在 WSL2 环境
                proc_version = Path("/proc/version")
                is_wsl2 = proc_version.exists() and "microsoft" in proc_version.read_text().lower()

                if is_wsl2:
                    logger.warning(
                        "检测到 WSL2 环境，虚拟显示可能不稳定。"
                        "建议：1) 使用无头模式 BROWSER_HEADLESS=true；"
                        "2) 或关闭虚拟显示 BROWSER_USE_VIRTUAL_DISPLAY=false"
                    )

                self.display = Display(visible=False, size=(1920, 1080))
                self.display.start()
                logger.info("虚拟显示已启动（有头模式但不显示窗口）")
            except ImportError:
                logger.warning(
                    "pyvirtualdisplay 未安装，将使用普通模式。"
                    "安装方法：pip install pyvirtualdisplay 和 sudo apt-get install xvfb"
                )
            except Exception as e:
                error_msg = str(e)
                if "Read-only file system" in error_msg or "/tmp/.X11-unix" in error_msg:
                    logger.warning(
                        f"WSL2 环境限制：无法启动虚拟显示 - {e}\n"
                        "解决方案：\n"
                        "  1. 使用无头模式：BROWSER_HEADLESS=true\n"
                        "  2. 使用普通有头模式：BROWSER_USE_VIRTUAL_DISPLAY=false\n"
                        "  3. 在 Windows 上使用 VcXsrv：https://sourceforge.net/projects/vcxsrv/\n"
                        "当前将继续使用普通模式..."
                    )
                else:
                    logger.warning(f"启动虚拟显示失败: {e}，将使用普通模式")

        # 创建或使用提供的选项
        if options is None:
            options = Options()

        # 无头模式下设置窗口大小
        if self.headless:
            options.add_argument("--window-size=1920,1080")
            logger.debug("无头模式：设置窗口大小为 1920x1080")

        # 配置性能优化（如果启用）
        if self.disable_images:
            self._configure_performance_options(options)

        # 准备 undetected-chromedriver 参数
        uc_options: dict[str, Any] = {
            "options": options,
        }
        if self.headless:
            uc_options["headless"] = True
        if self.version_main:
            uc_options["version_main"] = self.version_main
        if self.use_subprocess:
            uc_options["use_subprocess"] = self.use_subprocess

        # 合并其他自定义参数
        uc_options.update(self.kwargs)

        # 创建 undetected Chrome 驱动
        self.driver = uc.Chrome(**uc_options)

        # 通过 CDP 进一步配置媒体阻止（如果启用）
        if self.disable_images:
            self._setup_media_blocking_cdp()

        logger.info("Undetected浏览器启动成功")

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

    def find_elements(self, by: str, value: str) -> list[Any]:
        """查找多个元素"""
        if not self.driver:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        assert self.driver is not None  # 类型收缩
        driver = self.driver
        return list(driver.find_elements(by, value))

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
        等待验证码解决（undetected浏览器通常能自动通过验证码）

        Args:
            _detect_timeout: 检测超时时间（毫秒，未使用）

        Returns:
            验证码状态: 'solved'
        """
        logger.info("Undetected浏览器通常能自动通过验证码检测")
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

        # 停止虚拟显示（如果启动了）
        if self.display:
            try:
                self.display.stop()
                logger.debug("虚拟显示已停止")
            except Exception as e:
                logger.warning(f"停止虚拟显示失败: {e}")
            finally:
                self.display = None

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
