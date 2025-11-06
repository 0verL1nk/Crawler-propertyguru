"""
PropertyGuru爬虫主入口
支持测试模式：
- 测试单个房源: python main.py --test-single
- 测试第一页: python main.py --test-page
- 测试十页: python main.py --test-pages 10
- 爬取全部: python main.py [start_page] [end_page]
- 重置进度: python main.py --reset-progress

支持断点续传：
- 爬虫会自动保存进度到 crawl_progress.json
- 中断后重新运行会自动从上次的位置继续
- 使用 --reset-progress 可以重置进度
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from crawler.config import Config
from crawler.propertyguru_crawler import PropertyGuruCrawler
from utils.logger import get_logger

# 先加载配置以获取日志级别
config_file = Path("config.yaml")
if config_file.exists():
    temp_config = Config.from_yaml(str(config_file))
    log_config = temp_config.get_section("logging")
    log_level = log_config.get("level", "INFO")
    log_file = log_config.get("file", "logs/crawler.log")
    log_rotation = log_config.get("rotation", "10 MB")
    log_retention = log_config.get("retention", "30 days")
else:
    log_level = "INFO"
    log_file = "logs/crawler.log"
    log_rotation = "10 MB"
    log_retention = "30 days"

logger = get_logger(
    "Main", log_file=log_file, level=log_level, rotation=log_rotation, retention=log_retention
)


def load_config():
    """加载配置文件"""
    config_file = Path("config.yaml")
    if not config_file.exists():
        logger.error(f"配置文件不存在: {config_file}")
        sys.exit(1)
    config = Config.from_yaml(str(config_file))
    logger.info("配置加载成功")
    return config


def reset_progress():
    """重置爬取进度"""
    from crawler.progress_manager import CrawlProgress

    progress_file = os.getenv("CRAWL_PROGRESS_FILE", "crawl_progress.json")
    progress = CrawlProgress(progress_file=progress_file)
    progress.reset()
    logger.info("进度已重置")


def run_test_single(crawler: PropertyGuruCrawler):
    """运行测试模式：爬取第一页的第一个房源"""
    logger.info("=" * 60)
    logger.info("测试模式：爬取第一页的第一个房源")
    logger.info("=" * 60)
    asyncio.run(crawler.test_single_listing())


def run_test_page(crawler: PropertyGuruCrawler):
    """运行测试模式：爬取第一页"""
    logger.info("=" * 60)
    logger.info("测试模式：爬取第一页的所有房源")
    logger.info("=" * 60)
    asyncio.run(crawler.run(start_page=1, end_page=1))


def run_test_pages(crawler: PropertyGuruCrawler, num_pages: int):
    """运行测试模式：爬取指定页数"""
    logger.info("=" * 60)
    logger.info(f"测试模式：爬取前 {num_pages} 页")
    logger.info("=" * 60)
    asyncio.run(crawler.run(start_page=1, end_page=num_pages))


def run_normal_mode(crawler: PropertyGuruCrawler, start_page: int, end_page: int | None = None):
    """运行正常模式：爬取指定页面范围"""
    logger.info("=" * 60)
    logger.info(f"开始爬取，起始页: {start_page}, 结束页: {end_page or '全部'}")
    logger.info("=" * 60)
    asyncio.run(crawler.run(start_page=start_page, end_page=end_page))


def run_update_mode(
    crawler: PropertyGuruCrawler, interval_minutes: int = 5, max_pages: int | None = None
):
    """运行更新模式：从第一页开始，遇到已存在的记录就停止，支持循环"""
    logger.info("=" * 60)
    logger.info("更新模式：从第一页开始爬取最新数据")
    logger.info(f"循环间隔: {interval_minutes} 分钟" if interval_minutes > 0 else "只执行一次")
    if max_pages:
        logger.info(f"最大页数限制: {max_pages}")
    logger.info("=" * 60)
    asyncio.run(crawler.run_update_mode(interval_minutes=interval_minutes, max_pages=max_pages))


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="PropertyGuru爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --test-single              # 测试单个房源
  python main.py --test-page                # 测试第一页
  python main.py --test-pages 10            # 测试前10页
  python main.py 1 100                      # 爬取第1-100页
  python main.py 1                          # 从第1页开始爬取所有页
  python main.py --reset-progress           # 重置进度
  python main.py --update-mode              # 更新模式（每5分钟循环一次）
  python main.py --update-mode --interval 10 # 更新模式（每10分钟循环一次）
  python main.py --update-mode --interval 0  # 更新模式（只执行一次）
  python main.py --update-mode --max-pages 5 # 更新模式（最多爬5页）
        """,
    )

    # 测试模式选项（互斥）
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument(
        "--test-single", action="store_true", help="测试模式：爬取第一页的第一个房源"
    )
    test_group.add_argument(
        "--test-page", action="store_true", help="测试模式：爬取第一页的所有房源"
    )
    test_group.add_argument("--test-pages", type=int, metavar="N", help="测试模式：爬取前N页")

    # 其他选项
    parser.add_argument("--reset-progress", action="store_true", help="重置爬取进度")
    parser.add_argument(
        "--update-mode",
        action="store_true",
        help="更新模式：从第一页开始，遇到已存在的记录就停止",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        metavar="MINUTES",
        help="更新模式循环间隔（分钟），0 表示只执行一次（默认：5）",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        metavar="N",
        help="更新模式最大爬取页数（默认：不限制，但遇到已存在就停止）",
    )

    # 位置参数：起始页和结束页
    parser.add_argument("start_page", type=int, nargs="?", default=None, help="起始页码（默认：1）")
    parser.add_argument(
        "end_page", type=int, nargs="?", default=None, help="结束页码（默认：爬取所有页）"
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    crawler = None

    try:
        # 重置进度模式
        if args.reset_progress:
            reset_progress()
            return

        # 加载配置并创建爬虫实例
        config = load_config()
        crawler = PropertyGuruCrawler(config)

        # 根据参数选择运行模式
        if args.test_single:
            run_test_single(crawler)
        elif args.test_page:
            run_test_page(crawler)
        elif args.test_pages:
            run_test_pages(crawler, args.test_pages)
        elif args.update_mode:
            # 更新模式
            run_update_mode(crawler, interval_minutes=args.interval, max_pages=args.max_pages)
        else:
            # 正常模式
            start_page = args.start_page if args.start_page is not None else 1
            end_page = args.end_page
            run_normal_mode(crawler, start_page, end_page)

        logger.info("=" * 60)
        logger.info("爬取完成")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("用户中断爬取")
    except Exception as e:
        logger.error(f"爬取失败: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if crawler:
            crawler.close()


if __name__ == "__main__":
    main()
