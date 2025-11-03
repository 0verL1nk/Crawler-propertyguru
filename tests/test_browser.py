"""
浏览器模块测试
测试 RemoteBrowser 类的功能
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from selenium.webdriver import ChromeOptions

from crawler.browser import RemoteBrowser, scrape_with_browser


class TestRemoteBrowser:
    """RemoteBrowser 测试类"""

    def test_init_with_auth(self):
        """测试使用 auth 参数初始化"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        assert browser.auth == "test_user:test_pass"
        assert browser.browser_type == "chrome"
        assert browser.server_addr == "https://test_user:test_pass@brd.superproxy.io:9515"

    def test_init_with_env_var(self, mock_env_vars):
        """测试从环境变量读取配置"""
        _ = mock_env_vars  # 显式使用，避免未使用警告
        browser = RemoteBrowser()
        assert browser.auth == "test_user:test_pass"
        assert browser.server_addr == "https://test_user:test_pass@brd.superproxy.io:9515"

    def test_init_with_server_addr(self):
        """测试使用自定义 server_addr"""
        browser = RemoteBrowser(
            auth="test_user:test_pass", server_addr="https://custom.server.com:8080"
        )
        assert browser.server_addr == "https://custom.server.com:8080"

    def test_init_without_auth(self):
        """测试没有提供认证信息时抛出异常"""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="未提供认证信息"),
        ):
            RemoteBrowser()

    def test_init_with_browser_type(self):
        """测试指定浏览器类型"""
        browser = RemoteBrowser(auth="test_user:test_pass", browser_type="firefox")
        assert browser.browser_type == "firefox"

    @patch("crawler.browser.Connection")
    @patch("crawler.browser.Remote")
    def test_connect(self, mock_remote, mock_connection, mock_selenium_driver):
        """测试连接浏览器"""
        _ = mock_connection  # 显式使用，避免未使用警告
        mock_remote.return_value = mock_selenium_driver

        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.connect()

        assert browser.driver is not None
        assert browser.connection is not None

    @patch("crawler.browser.Connection")
    @patch("crawler.browser.Remote")
    def test_connect_with_options(self, mock_remote, mock_connection, mock_selenium_driver):
        """测试使用自定义选项连接"""
        _ = mock_connection  # 显式使用，避免未使用警告
        mock_remote.return_value = mock_selenium_driver
        options = ChromeOptions()
        options.add_argument("--headless")

        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.connect(options=options)

        assert browser.driver is not None

    def test_connect_without_driver(self):
        """测试未连接时调用方法抛出异常"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = None

        with pytest.raises(RuntimeError, match="浏览器未连接"):
            browser.get("https://example.com")

    def test_get(self, mock_selenium_driver):
        """测试导航到URL"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver

        browser.get("https://example.com")

        mock_selenium_driver.get.assert_called_once_with("https://example.com")

    def test_find_element(self, mock_selenium_driver):
        """测试查找元素"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver

        element = browser.find_element("id", "test_id")

        mock_selenium_driver.find_element.assert_called_once_with("id", "test_id")
        assert element is not None

    def test_find_elements(self, mock_selenium_driver):
        """测试查找多个元素"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver

        elements = browser.find_elements("tag name", "div")

        mock_selenium_driver.find_elements.assert_called_once_with("tag name", "div")
        assert len(elements) == 2

    def test_execute_script(self, mock_selenium_driver):
        """测试执行JavaScript"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver

        result = browser.execute_script("return document.title")

        mock_selenium_driver.execute_script.assert_called_once_with("return document.title")
        assert result == "Script Result"

    def test_get_page_source(self, mock_selenium_driver):
        """测试获取页面源码"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver

        source = browser.get_page_source()

        assert source == "<html><body>Test Page</body></html>"

    def test_get_screenshot(self, mock_selenium_driver):
        """测试截图"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver

        result = browser.get_screenshot("test.png")

        mock_selenium_driver.save_screenshot.assert_called_once_with("test.png")
        assert result is True

    def test_get_screenshot_without_driver(self):
        """测试未连接时截图失败"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = None

        # get_screenshot 会捕获异常并返回 False，而不是抛出异常
        result = browser.get_screenshot("test.png")
        assert result is False

    def test_cdp(self, mock_selenium_driver):
        """测试执行CDP命令"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver
        mock_selenium_driver.execute.return_value = {"value": {"status": "solved"}}

        result = browser.cdp("Page.getFrameTree")

        assert result == {"status": "solved"}
        mock_selenium_driver.execute.assert_called_once()

    def test_cdp_with_params(self, mock_selenium_driver):
        """测试执行带参数的CDP命令"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver
        mock_selenium_driver.execute.return_value = {"value": {"result": "success"}}

        result = browser.cdp(
            "Download.enable", {"allowedContentTypes": ["application/octet-stream"]}
        )

        assert result == {"result": "success"}

    def test_wait_for_captcha(self, mock_selenium_driver):
        """测试等待验证码解决"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver
        mock_selenium_driver.execute.return_value = {"value": {"status": "solved"}}

        status = browser.wait_for_captcha()

        assert status == "solved"

    def test_wait_for_captcha_failed(self, mock_selenium_driver):
        """测试验证码处理失败"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver
        mock_selenium_driver.execute.side_effect = Exception("CDP error")

        status = browser.wait_for_captcha()

        assert status == "failed"

    def test_enable_download(self, mock_selenium_driver):
        """测试启用文件下载"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver
        mock_selenium_driver.execute.return_value = {"value": {}}

        browser.enable_download()

        mock_selenium_driver.execute.assert_called()

    def test_enable_download_with_content_types(self, mock_selenium_driver):
        """测试使用自定义内容类型启用下载"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver
        mock_selenium_driver.execute.return_value = {"value": {}}

        browser.enable_download(["application/pdf", "text/csv"])

        mock_selenium_driver.execute.assert_called()

    def test_close(self, mock_selenium_driver):
        """测试关闭浏览器"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = mock_selenium_driver
        browser.connection = MagicMock()

        browser.close()

        mock_selenium_driver.quit.assert_called_once()
        assert browser.driver is None
        assert browser.connection is None

    def test_close_without_driver(self):
        """测试关闭未连接的浏览器"""
        browser = RemoteBrowser(auth="test_user:test_pass")
        browser.driver = None

        # 不应抛出异常
        browser.close()

    def test_context_manager(self, mock_selenium_driver):
        """测试上下文管理器"""
        with patch("crawler.browser.Connection"), patch("crawler.browser.Remote") as mock_remote:
            mock_remote.return_value = mock_selenium_driver

            browser = RemoteBrowser(auth="test_user:test_pass")
            with browser:
                assert browser.driver is not None

            mock_selenium_driver.quit.assert_called_once()

    @patch("crawler.browser.RemoteBrowser")
    def test_scrape_with_browser(self, mock_browser_class, mock_selenium_driver):
        """测试便捷函数 scrape_with_browser"""
        mock_browser = MagicMock()
        mock_browser.driver = mock_selenium_driver
        mock_browser.get_page_source.return_value = "<html>Test</html>"
        mock_browser_class.return_value = mock_browser

        result = scrape_with_browser("https://example.com")

        mock_browser.connect.assert_called_once()
        mock_browser.get.assert_called_once_with("https://example.com")
        mock_browser.close.assert_called_once()
        assert result == "<html>Test</html>"

    @patch("crawler.browser.RemoteBrowser")
    def test_scrape_with_browser_callback(self, mock_browser_class, mock_selenium_driver):
        """测试使用回调函数的 scrape_with_browser"""
        mock_browser = MagicMock()
        mock_browser.driver = mock_selenium_driver
        mock_browser_class.return_value = mock_browser

        def callback(browser):
            _ = browser  # 显式使用，避免未使用警告
            return "callback result"

        result = scrape_with_browser("https://example.com", callback=callback)

        assert result == "callback result"
        mock_browser.close.assert_called_once()
