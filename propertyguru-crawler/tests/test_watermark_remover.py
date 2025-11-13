"""
去水印模块测试
测试 WatermarkRemover 类的功能
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from crawler.watermark_remover import WatermarkRemover


class TestWatermarkRemover:
    """WatermarkRemover 测试类"""

    def test_init_with_params(self):
        """测试使用参数初始化"""
        remover = WatermarkRemover(
            product_serial="test_serial",
            product_code="067003",
            authorization="test_auth",
        )
        assert remover.product_serial == "test_serial"
        assert remover.product_code == "067003"
        assert remover.authorization == "test_auth"

    def test_init_with_env_vars(self, mock_env_vars):
        """测试从环境变量读取配置"""
        _ = mock_env_vars  # 显式使用，避免未使用警告
        remover = WatermarkRemover()
        assert remover.product_serial == "test_serial"
        assert remover.product_code == "067003"

    def test_init_with_defaults(self):
        """测试使用默认值初始化"""
        with patch.dict(os.environ, {}, clear=True):
            remover = WatermarkRemover()
            assert remover.product_serial is not None
            assert remover.product_code == "067003"

    def test_init_with_proxy_string(self):
        """测试使用字符串代理初始化"""
        remover = WatermarkRemover(proxy="http://user:pass@proxy.com:8080")
        assert remover.proxy_adapter is not None

    def test_init_with_proxy_adapter(self):
        """测试使用 ProxyAdapter 初始化"""
        from utils.proxy import ProxyAdapter

        adapter = ProxyAdapter("http://user:pass@proxy.com:8080")
        remover = WatermarkRemover(proxy=adapter)
        assert remover.proxy_adapter == adapter

    def test_init_with_proxy_env_var(self, mock_env_vars):
        """测试从环境变量读取代理"""
        _ = mock_env_vars  # 显式使用，避免未使用警告
        remover = WatermarkRemover()
        assert remover.proxy_adapter is not None

    def test_get_headers(self):
        """测试获取请求头"""
        remover = WatermarkRemover(
            product_serial="test_serial",
            product_code="067003",
            authorization="test_auth",
        )
        headers = remover._get_headers()

        assert "Product-Serial" in headers
        assert "Product-Code" in headers
        assert "Authorization" in headers
        assert headers["Product-Serial"] == "test_serial"
        assert headers["Product-Code"] == "067003"
        assert headers["Authorization"] == "test_auth"

    def test_get_headers_with_content_type(self):
        """测试获取带 Content-Type 的请求头"""
        remover = WatermarkRemover()
        headers = remover._get_headers(content_type="application/json")

        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_get_headers_without_authorization(self):
        """测试没有授权时的请求头"""
        remover = WatermarkRemover(authorization=None)
        headers = remover._get_headers()

        assert "Authorization" not in headers

    @patch("crawler.watermark_remover.requests.Session.post")
    def test_create_job_success(self, mock_post, test_image_path):
        """测试成功创建任务"""
        if not test_image_path:
            pytest.skip("测试图片不存在")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 100000,
            "result": {"job_id": "test_job_id_123"},
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        remover = WatermarkRemover()
        job_id = remover.create_job(test_image_path)

        assert job_id == "test_job_id_123"
        mock_post.assert_called_once()

    @patch("crawler.watermark_remover.requests.Session.post")
    def test_create_job_file_not_found(self, mock_post):
        """测试文件不存在的情况"""
        remover = WatermarkRemover()
        job_id = remover.create_job("/nonexistent/image.jpg")

        assert job_id is None
        mock_post.assert_not_called()

    @patch("crawler.watermark_remover.requests.Session.post")
    def test_create_job_api_error(self, mock_post, test_image_path):
        """测试API返回错误"""
        if not test_image_path:
            pytest.skip("测试图片不存在")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 100001, "message": "API Error"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        remover = WatermarkRemover()
        job_id = remover.create_job(test_image_path)

        assert job_id is None

    @patch("crawler.watermark_remover.requests.Session.post")
    def test_create_job_network_error(self, mock_post, test_image_path):
        """测试网络错误"""
        if not test_image_path:
            pytest.skip("测试图片不存在")

        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        remover = WatermarkRemover()
        job_id = remover.create_job(test_image_path)

        assert job_id is None

    @patch("crawler.watermark_remover.requests.Session.get")
    def test_get_job_status_success(self, mock_get):
        """测试成功获取任务状态"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 100000,
            "result": {"status": "completed", "output_urls": ["https://example.com/image.jpg"]},
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        remover = WatermarkRemover()
        result = remover.get_job_status("test_job_id")

        assert result["code"] == 100000
        assert "result" in result

    @patch("crawler.watermark_remover.requests.Session.get")
    def test_get_job_status_error(self, mock_get):
        """测试获取任务状态失败"""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        remover = WatermarkRemover()
        result = remover.get_job_status("test_job_id")

        assert result == {}

    @patch("crawler.watermark_remover.WatermarkRemover.get_job_status")
    @patch("crawler.watermark_remover.time.sleep")
    def test_wait_for_completion_success(self, mock_sleep, mock_get_status):
        """测试等待任务完成成功"""
        _ = mock_sleep  # 显式使用，避免未使用警告
        # 模拟任务从进行中到完成
        # 注意：实际代码使用 output_url 而不是 output_urls
        mock_get_status.side_effect = [
            {"code": 300006, "message": {"zh": "处理中"}},  # 处理中
            {"code": 100000, "result": {"output_url": ["https://example.com/result.jpg"]}},
        ]

        remover = WatermarkRemover()
        result_url = remover.wait_for_completion("test_job_id", max_wait=10, check_interval=1)

        assert result_url == "https://example.com/result.jpg"
        assert mock_get_status.call_count == 2

    @patch("crawler.watermark_remover.WatermarkRemover.get_job_status")
    @patch("crawler.watermark_remover.time.sleep")
    def test_wait_for_completion_timeout(self, mock_sleep, mock_get_status):
        """测试等待任务超时"""
        _ = mock_sleep  # 显式使用，避免未使用警告
        mock_get_status.return_value = {"code": 100000, "result": {"status": "processing"}}

        remover = WatermarkRemover()
        result_url = remover.wait_for_completion("test_job_id", max_wait=2, check_interval=1)

        assert result_url is None

    @patch("crawler.watermark_remover.WatermarkRemover.get_job_status")
    @patch("crawler.watermark_remover.time.sleep")
    def test_wait_for_completion_failed(self, mock_sleep, mock_get_status):
        """测试任务失败"""
        _ = mock_sleep  # 显式使用，避免未使用警告
        mock_get_status.return_value = {"code": 100001, "message": "Task failed"}

        remover = WatermarkRemover()
        result_url = remover.wait_for_completion("test_job_id", max_wait=10, check_interval=1)

        assert result_url is None

    @patch("crawler.watermark_remover.WatermarkRemover.get_job_status")
    @patch("crawler.watermark_remover.time.sleep")
    def test_wait_for_completion_already_completed(self, mock_sleep, mock_get_status):
        """测试任务已完成"""
        _ = mock_sleep  # 显式使用，避免未使用警告
        # 注意：实际代码使用 output_url 而不是 output_urls
        mock_get_status.return_value = {
            "code": 100000,
            "result": {"output_url": ["https://example.com/result.jpg"]},
        }

        remover = WatermarkRemover()
        result_url = remover.wait_for_completion("test_job_id", max_wait=10, check_interval=1)

        assert result_url == "https://example.com/result.jpg"
        mock_get_status.assert_called_once()

    @patch("crawler.watermark_remover.WatermarkRemover.create_job")
    @patch("crawler.watermark_remover.WatermarkRemover.wait_for_completion")
    @patch("crawler.watermark_remover.WatermarkRemover.download_result")
    def test_remove_watermark_success(
        self, mock_download, mock_wait, mock_create_job, test_image_path
    ):
        """测试成功去除水印"""
        if not test_image_path:
            pytest.skip("测试图片不存在")

        mock_create_job.return_value = "test_job_id"
        mock_wait.return_value = "https://example.com/result.jpg"
        mock_download.return_value = True  # 下载成功

        remover = WatermarkRemover()
        result_path = remover.remove_watermark(test_image_path)

        assert result_path is not None
        assert str(result_path).endswith("_no_watermark.jpg")
        # 注意：实际代码会将字符串转换为 Path，所以需要检查 Path 对象
        expected_path = Path(test_image_path)
        mock_create_job.assert_called_once_with(expected_path)
        mock_wait.assert_called_once_with("test_job_id", max_wait=300)
        mock_download.assert_called_once()

    @patch("crawler.watermark_remover.WatermarkRemover.create_job")
    def test_remove_watermark_create_failed(self, mock_create_job, test_image_path):
        """测试创建任务失败"""
        if not test_image_path:
            pytest.skip("测试图片不存在")

        mock_create_job.return_value = None

        remover = WatermarkRemover()
        result_url = remover.remove_watermark(test_image_path)

        assert result_url is None

    @patch("crawler.watermark_remover.WatermarkRemover.create_job")
    @patch("crawler.watermark_remover.WatermarkRemover.wait_for_completion")
    def test_remove_watermark_wait_failed(self, mock_wait, mock_create_job, test_image_path):
        """测试等待任务完成失败"""
        if not test_image_path:
            pytest.skip("测试图片不存在")

        mock_create_job.return_value = "test_job_id"
        mock_wait.return_value = None

        remover = WatermarkRemover()
        result_url = remover.remove_watermark(test_image_path)

        assert result_url is None

    @patch("crawler.watermark_remover.requests.Session.post")
    def test_create_job_with_proxy(self, mock_post, test_image_path):
        """测试使用代理创建任务"""
        if not test_image_path:
            pytest.skip("测试图片不存在")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 100000,
            "result": {"job_id": "test_job_id"},
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        remover = WatermarkRemover(proxy="http://user:pass@proxy.com:8080")
        job_id = remover.create_job(test_image_path)

        assert job_id == "test_job_id"
        # 验证代理被使用
        call_kwargs = mock_post.call_args[1]
        assert "proxies" in call_kwargs or remover.session.proxies
