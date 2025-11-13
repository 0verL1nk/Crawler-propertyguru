"""
浏览器爬虫抽象基类
定义所有浏览器爬虫的统一接口
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from selenium.webdriver.support.wait import WebDriverWait


class Browser(ABC):
    """浏览器爬虫抽象基类"""

    def __init__(self):
        """初始化浏览器"""
        self.driver = None
        self.connection = None

    @abstractmethod
    def connect(self, options: Any = None) -> None:
        """
        连接到浏览器

        Args:
            options: 浏览器选项
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭浏览器连接"""
        pass

    @abstractmethod
    def get(self, url: str) -> None:
        """
        导航到指定URL

        Args:
            url: 目标URL
        """
        pass

    @abstractmethod
    def find_element(self, by: str, value: str) -> Any:
        """
        查找单个元素

        Args:
            by: 查找方式
            value: 查找值

        Returns:
            找到的元素
        """
        pass

    @abstractmethod
    def find_elements(self, by: str, value: str) -> list[Any]:
        """
        查找多个元素

        Args:
            by: 查找方式
            value: 查找值

        Returns:
            找到的元素列表
        """
        pass

    @abstractmethod
    def execute_script(self, script: str, *args) -> Any:
        """
        执行JavaScript脚本

        Args:
            script: JavaScript脚本
            *args: 脚本参数

        Returns:
            脚本执行结果
        """
        pass

    @abstractmethod
    def wait(self, timeout: int = 30) -> WebDriverWait:
        """
        创建WebDriverWait实例

        Args:
            timeout: 超时时间（秒）

        Returns:
            WebDriverWait实例
        """
        pass

    def cdp(self, _cmd: str, _params: dict[str, Any] | None = None) -> Any:
        """
        执行CDP命令（Chrome DevTools Protocol）
        默认实现，子类可根据需要重写

        Args:
            _cmd: CDP命令名
            _params: 命令参数

        Returns:
            命令执行结果
        """
        raise NotImplementedError("CDP命令未实现")

    def enable_download(self, _allowed_content_types: list[str] | None = None) -> None:
        """
        启用文件下载
        默认实现，子类可根据需要重写

        Args:
            _allowed_content_types: 允许的内容类型
        """
        raise NotImplementedError("文件下载功能未实现")

    def download_file(self, _download_trigger: Callable, _filename: str, _timeout: int = 60) -> bool:
        """
        下载文件
        默认实现，子类可根据需要重写

        Args:
            _download_trigger: 触发下载的函数
            _filename: 保存文件名
            _timeout: 超时时间（秒）

        Returns:
            是否成功
        """
        raise NotImplementedError("文件下载功能未实现")

    def wait_for_captcha(self, _detect_timeout: int = 10000) -> str:
        """
        等待验证码解决
        默认实现，子类可根据需要重写

        Args:
            _detect_timeout: 检测超时时间（毫秒）

        Returns:
            验证码状态
        """
        return "solved"  # 默认认为已解决

    def enable_inspect(self, _wait_time: int = 10) -> str | None:
        """
        启用调试模式
        默认实现，子类可根据需要重写

        Args:
            _wait_time: 等待时间（秒）

        Returns:
            检查URL或None
        """
        return None

    def get_page_source(self) -> str:
        """
        获取页面源码
        默认实现，子类可根据需要重写

        Returns:
            页面源码
        """
        raise NotImplementedError("获取页面源码功能未实现")

    def get_screenshot(self, _filename: str) -> bool:
        """
        截取屏幕截图
        默认实现，子类可根据需要重写

        Args:
            _filename: 保存文件名

        Returns:
            是否成功
        """
        raise NotImplementedError("截图功能未实现")

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """上下文管理器出口"""
        self.close()

    def __del__(self):
        """析构函数"""
        self.close()
