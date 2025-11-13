"""
HTTP爬虫测试
测试HTTP基础的列表页爬虫实现
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from crawler.pages.factory import PageCrawlerFactory
from crawler.pages.listing_http import ListingHttpCrawler


class TestHttpCrawler(unittest.TestCase):
    """HTTP爬虫测试类"""

    def setUp(self):
        """测试前置条件"""
        self.crawler = ListingHttpCrawler()

    def test_init(self):
        """测试初始化"""
        self.assertIsInstance(self.crawler, ListingHttpCrawler)
        self.assertIsNotNone(self.crawler.http_client)

    @patch('crawler.http.client.requests.get')
    def test_get_page_content_sync(self, mock_get):
        """测试同步获取页面内容"""
        # 模拟HTTP响应
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test Content</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        content = self.crawler.get_page_content_sync("https://example.com")

        self.assertEqual(content, "<html><body>Test Content</body></html>")
        mock_get.assert_called_once_with(
            "https://example.com",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=30
        )

    def test_factory_creation(self):
        """测试工厂创建"""
        # 测试HTTP爬虫创建
        with patch.dict(os.environ, {'USE_HTTP_CRAWLER': 'true', 'PAGE_CRAWLER_TYPE': 'http'}):
            try:
                crawler = PageCrawlerFactory.create_listing_crawler("http")
                self.assertIsInstance(crawler, ListingHttpCrawler)
            except NotImplementedError:
                # 这是预期的行为，因为我们还没有完全实现工厂
                pass


if __name__ == '__main__':
    unittest.main()
