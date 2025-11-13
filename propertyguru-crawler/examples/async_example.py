"""
异步爬虫示例
演示如何使用异步模式提高爬取效率
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler import Spider  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger("AsyncExample")


async def async_parse(response):
    """异步解析函数"""
    logger.info(f"异步处理: {response.url}")

    # 提取数据
    data = {
        "url": response.url,
        "status_code": response.status_code,
        "timestamp": datetime.now().isoformat(),
    }

    # 模拟一些异步处理
    await asyncio.sleep(0.1)

    logger.info(f"处理完成: {response.url}")
    return data


def main():
    """主函数"""
    # 创建配置
    config = {
        "crawler": {
            "concurrency": 10,  # 异步模式可以设置更高的并发数
            "timeout": 30,
            "delay": 0.5,  # 异步模式可以设置更短的延迟
            "use_proxy": False,
            "rotate_user_agent": True,
        }
    }

    # 创建爬虫实例
    spider = Spider(config)

    # 大量URL测试异步性能
    urls = [f"https://httpbin.org/delay/{i % 3 + 1}" for i in range(10)]  # 随机延迟1-3秒

    try:
        logger.info(f"开始异步爬取 {len(urls)} 个URL...")
        start_time = datetime.now()

        # 使用异步模式
        spider.start(urls, callback=async_parse, async_mode=True)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"异步爬取完成，总耗时: {elapsed:.2f}秒")
        logger.info(f"平均每个URL: {elapsed / len(urls):.2f}秒")

    except Exception as e:
        logger.error(f"爬取失败: {e}")
    finally:
        spider.close()


if __name__ == "__main__":
    main()
