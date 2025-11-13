"""
本地浏览器实现
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions as Options
from selenium.webdriver.support.wait import WebDriverWait

from ..base import Browser
from ..utils import configure_performance_options, setup_media_blocking_cdp


class LocalBrowser(Browser):
    """本地浏览器管理器（用于测试）"""

    def __init__(
        self,
        headless: bool = False,
        options: Options | None = None,
        disable_images: bool = False,
        page_load_strategy: str = "eager",
    ):
        """
        初始化本地浏览器

        Args:
            headless: 是否使用无头模式
            options: Chrome选项，如不提供则使用默认选项
            disable_images: 是否禁用图片、CSS、字体等资源加载（提升速度）
            page_load_strategy: 页面加载策略，'normal'（默认）、'eager'（更快）或 'none'（最快）
        """
        super().__init__()
        if Chrome is None:
            raise ImportError("无法导入Chrome驱动。请确保已安装selenium: pip install selenium")

        self.headless = headless
        self.options = options or Options()
        self.disable_images = disable_images
        self.page_load_strategy = page_load_strategy
        self.display: Any = None  # 虚拟显示

        # 添加必要的稳定性参数（树莓派/ARM64 必需）
        stability_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-setuid-sandbox",
        ]
        for arg in stability_args:
            self.options.add_argument(arg)

        if headless:
            self.options.add_argument("--headless=new")
            self.options.add_argument("--window-size=1920,1080")
        else:
            # 有头模式也需要窗口大小
            self.options.add_argument("--window-size=1920,1080")

        # 配置性能优化（如果启用）
        if self.disable_images:
            configure_performance_options(self.options)

        # 设置页面加载策略（提升性能）
        self.options.page_load_strategy = self.page_load_strategy

        # 浏览器驱动
        self.driver: Chrome | None = None
        self.connection = None  # 本地浏览器没有连接对象

    def connect(self, options: Options | None = None):
        """
        连接到本地浏览器

        Args:
            options: Chrome选项，如不提供则使用初始化的选项
        """
        try:
            if options is None:
                options = self.options

            # 检查是否需要启动虚拟显示（有头模式且无 DISPLAY）
            import os

            use_virtual_display = (
                not self.headless and not os.getenv("DISPLAY") and os.name != "nt"
            )
            if use_virtual_display:
                try:
                    from pyvirtualdisplay import Display

                    # 检测是否在 WSL2 环境
                    proc_version = Path("/proc/version")
                    is_wsl2 = proc_version.exists() and "microsoft" in proc_version.read_text().lower()

                    if is_wsl2:
                        # WSL2 环境下虚拟显示可能不稳定
                        pass
                    else:
                        self.display = Display(visible=False, size=(1920, 1080))
                        self.display.start()

                except ImportError:
                    pass  # pyvirtualdisplay 未安装，使用普通模式

            driver_path = os.getenv("CHROMEDRIVER_PATH")
            browser_path = os.getenv("CHROME_BINARY_PATH")

            # 设置浏览器路径（如果指定）
            if browser_path and Path(browser_path).exists():
                options.binary_location = browser_path

            # 创建Chrome驱动
            if driver_path and Path(driver_path).exists():
                from selenium.webdriver.chrome.service import Service
                service = Service(executable_path=driver_path)
                self.driver = Chrome(service=service, options=options)
            else:
                self.driver = Chrome(options=options)

            # 通过 CDP 进一步配置媒体阻止（如果启用）
            if self.disable_images:
                setup_media_blocking_cdp(self.cdp)

        except Exception as e:
            raise e

    def close(self):
        """关闭浏览器连接"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None

        if self.display:
            try:
                self.display.stop()
            except Exception:
                pass
            finally:
                self.display = None

    def get(self, url: str):
        """导航到指定URL"""
        if not self.driver:
            raise RuntimeError("浏览器未连接")
        self.driver.get(url)

    def find_element(self, by: str, value: str):
        """查找单个元素"""
        if not self.driver:
            raise RuntimeError("浏览器未连接")
        return self.driver.find_element(by, value)

    def find_elements(self, by: str, value: str):
        """查找多个元素"""
        if not self.driver:
            raise RuntimeError("浏览器未连接")
        return self.driver.find_elements(by, value)

    def execute_script(self, script: str, *args):
        """执行JavaScript脚本"""
        if not self.driver:
            raise RuntimeError("浏览器未连接")
        return self.driver.execute_script(script, *args)

    def wait(self, timeout: int = 30):
        """创建WebDriverWait实例"""
        if not self.driver:
            raise RuntimeError("浏览器未连接")
        return WebDriverWait(self.driver, timeout=timeout)

    def cdp(self, cmd: str, params: dict[str, Any] | None = None) -> Any:
        """执行CDP命令"""
        if not self.driver:
            raise RuntimeError("浏览器未连接")
        result = self.driver.execute(
            "executeCdpCommand",
            {
                "cmd": cmd,
                "params": params or {},
            },
        )
        return result.get("value")

    def get_page_source(self) -> str:
        """获取页面源码"""
        if not self.driver:
            raise RuntimeError("浏览器未连接")
        return self.driver.page_source
