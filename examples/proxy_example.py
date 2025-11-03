"""
使用代理的爬虫示例
演示如何配置和使用代理IP池
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler import Spider, Config
from utils.logger import get_logger

logger = get_logger("ProxyExample")


def check_ip(response):
    """检查IP地址"""
    try:
        data = response.json()
        origin_ip = data.get('origin', 'Unknown')
        logger.info(f"当前IP: {origin_ip}")
        return origin_ip
    except Exception as e:
        logger.error(f"解析失败: {e}")


def main():
    """主函数"""
    # 配置代理
    config = {
        'proxy': {
            'enabled': True,
            'pool_type': 'file',  # 从文件加载代理
            'proxy_file': 'proxies.txt',  # 代理文件路径
            'max_fails': 3,
            'test_url': 'https://httpbin.org/ip'
        },
        'crawler': {
            'concurrency': 3,
            'timeout': 30,
            'use_proxy': True,
            'rotate_user_agent': True,
        }
    }
    
    # 创建爬虫实例
    spider = Spider(config)
    
    # 测试代理
    if spider.proxy_manager:
        logger.info("测试所有代理...")
        spider.proxy_manager.test_all_proxies()
        
        # 显示代理统计
        stats = spider.proxy_manager.get_stats()
        logger.info(f"代理统计: {stats}")
    
    # 使用代理爬取
    urls = [
        'https://httpbin.org/ip',
        'https://httpbin.org/headers',
    ]
    
    try:
        logger.info("开始使用代理爬取...")
        spider.crawl(urls, callback=check_ip)
    except Exception as e:
        logger.error(f"爬取失败: {e}")
    finally:
        spider.close()


if __name__ == '__main__':
    # 注意: 运行此示例前，需要创建 proxies.txt 文件
    # 每行一个代理，格式: http://ip:port 或 http://user:pass@ip:port
    
    # 如果没有代理，可以注释掉proxy配置部分
    logger.warning("提示: 请确保 proxies.txt 文件存在并包含有效代理")
    logger.warning("或者将 config['proxy']['enabled'] 设置为 False")
    
    main()

