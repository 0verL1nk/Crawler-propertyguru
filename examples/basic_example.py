"""
基础爬虫示例
演示如何使用爬虫框架进行简单的数据爬取
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler import Spider
from utils.logger import get_logger

logger = get_logger("BasicExample")


def parse_response(response):
    """
    解析响应

    Args:
        response: Response对象
    """
    logger.info(f"处理URL: {response.url}")
    logger.info(f"状态码: {response.status_code}")

    # 使用BeautifulSoup解析
    soup = response.soup
    title = soup.find("title")
    if title:
        logger.info(f"页面标题: {title.text}")

    # 提取数据
    data = {
        "url": response.url,
        "title": title.text if title else "",
        "status_code": response.status_code,
        "content_length": len(response.content),
    }

    return data


def main():
    """主函数"""
    # 创建简单配置
    config = {
        "crawler": {
            "concurrency": 3,
            "timeout": 30,
            "delay": 1,
            "use_proxy": False,
            "rotate_user_agent": True,
        },
        "logging": {"level": "INFO"},
    }

    # 创建爬虫实例
    spider = Spider(config)

    # 要爬取的URL列表
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/json",
        "https://httpbin.org/user-agent",
    ]

    try:
        # 方式1: 使用回调函数
        logger.info("方式1: 使用回调函数批量爬取")
        spider.crawl(urls, callback=parse_response)

        # 方式2: 单个请求
        logger.info("\n方式2: 单个GET请求")
        response = spider.get("https://httpbin.org/get")
        if response:
            logger.info(f"响应内容: {response.text[:200]}")

        # 方式3: POST请求
        logger.info("\n方式3: POST请求")
        post_data = {"key": "value", "name": "测试"}
        response = spider.post("https://httpbin.org/post", json=post_data)
        if response:
            result = response.json()
            logger.info(f"POST响应: {result.get('json')}")

    except Exception as e:
        logger.error(f"爬取失败: {e}")
    finally:
        spider.close()


if __name__ == "__main__":
    main()
