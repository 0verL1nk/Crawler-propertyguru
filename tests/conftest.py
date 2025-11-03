"""
Pytest 配置文件
提供公共 fixtures 和测试配置
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_env_vars(monkeypatch):
    """模拟环境变量"""
    env_vars = {
        "BROWSER_AUTH": "test_user:test_pass",
        "PROXY_URL": "http://test_user:test_pass@test.proxy.com:8080",
        "WATERMARK_REMOVER_PRODUCT_SERIAL": "test_serial",
        "WATERMARK_REMOVER_PRODUCT_CODE": "067003",
        "WATERMARK_REMOVER_AUTHORIZATION": "test_auth_token",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def test_image_path():
    """返回测试图片路径"""
    test_dir = Path(__file__).parent
    image_path = test_dir / "images" / "test1.jpg"
    return str(image_path) if image_path.exists() else None


@pytest.fixture
def mock_selenium_driver():
    """模拟 Selenium WebDriver"""
    driver = MagicMock()
    driver.page_source = "<html><body>Test Page</body></html>"
    driver.current_url = "https://example.com"
    driver.title = "Test Page"
    driver.find_element.return_value = MagicMock(text="Test Element")
    driver.find_elements.return_value = [MagicMock(text="Element 1"), MagicMock(text="Element 2")]
    driver.execute_script.return_value = "Script Result"
    driver.execute.return_value = {"value": {"status": "solved"}}
    driver.save_screenshot.return_value = True
    driver.get.return_value = None
    driver.quit.return_value = None
    return driver


@pytest.fixture
def mock_connection():
    """模拟 Selenium Connection"""
    connection = MagicMock()
    return connection


@pytest.fixture
def mock_requests_response():
    """模拟 requests.Response"""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"code": 100000, "result": {"job_id": "test_job_id"}}
    response.text = '{"code": 100000, "result": {"job_id": "test_job_id"}}'
    response.content = b"test content"
    response.ok = True
    return response


@pytest.fixture
def mock_proxy_manager():
    """模拟 ProxyManager"""
    from utils.proxy import ProxyManagerProtocol

    # 创建一个符合 ProxyManagerProtocol 的 mock
    proxy_manager = MagicMock(spec=ProxyManagerProtocol)
    proxy_obj = MagicMock()
    proxy_obj.get_proxy_dict.return_value = {
        "http": "http://test:pass@proxy.com:8080",
        "https": "http://test:pass@proxy.com:8080",
    }
    proxy_manager.get_proxy.return_value = proxy_obj
    proxy_manager.mark_success.return_value = None
    proxy_manager.mark_failure.return_value = None
    return proxy_manager


@pytest.fixture
def temp_proxy_file(tmp_path):
    """创建临时代理文件"""
    proxy_file = tmp_path / "proxies.txt"
    proxy_file.write_text(
        "http://user1:pass1@proxy1.com:8080\n"
        "http://user2:pass2@proxy2.com:8080\n"
        "socks5://proxy3.com:1080\n"
    )
    return str(proxy_file)


@pytest.fixture
def sample_config():
    """示例配置字典"""
    return {
        "proxy": {
            "enabled": True,
            "pool_type": "file",
            "proxy_file": "proxies.txt",
            "max_fails": 3,
            "test_url": "https://www.httpbin.org/ip",
        },
        "crawler": {
            "concurrency": 5,
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 2,
            "delay": 1,
            "random_delay": [0, 2],
            "use_proxy": True,
            "rotate_user_agent": True,
            "verify_ssl": True,
        },
    }
