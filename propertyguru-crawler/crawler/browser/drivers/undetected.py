"""
Undetected Chrome浏览器实现
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import undetected_chromedriver as uc  # type: ignore[import-untyped]
except ImportError:
    uc = None

from selenium.webdriver import ChromeOptions as Options
from selenium.webdriver.support.wait import WebDriverWait

from ..base import Browser
from ..utils import configure_performance_options, setup_media_blocking_cdp


class UndetectedBrowser(Browser):
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
        """
        super().__init__()
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

    def connect(self, options: Options | None = None):
        """连接到Undetected浏览器"""
        if options is None:
            options = Options()

        # 配置选项
        if self.headless:
            options.add_argument("--headless=new")

        # 配置性能优化（如果启用）
        if self.disable_images:
            configure_performance_options(options)

        # 启动虚拟显示（如果启用）
        if self.use_virtual_display and not self.headless:
            try:
                from pyvirtualdisplay import Display

                # 检测是否在 WSL2 环境
                proc_version = Path("/proc/version")
                is_wsl2 = proc_version.exists() and "microsoft" in proc_version.read_text().lower()

                if is_wsl2:
                    pass  # WSL2环境下不启动虚拟显示
                else:
                    self.display = Display(visible=False, size=(1920, 1080))
                    self.display.start()
            except ImportError:
                pass  # pyvirtualdisplay未安装

        # 创建驱动
        self.driver = uc.Chrome(
            options=options,
            version_main=self.version_main,
            use_subprocess=self.use_subprocess,
            **self.kwargs,
        )

        # 通过 CDP 进一步配置媒体阻止（如果启用）
        if self.disable_images:
            setup_media_blocking_cdp(self.cdp)

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
