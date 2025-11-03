"""
数据库存储示例
演示如何将爬取的数据保存到数据库
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler import Spider, Config
from utils.logger import get_logger

logger = get_logger("DatabaseExample")


def parse_and_save(response, spider):
    """解析并保存数据"""
    try:
        # 提取数据
        data = {
            'url': response.url,
            'status_code': response.status_code,
            'title': '',
            'crawled_at': datetime.now().isoformat(),
            'content_length': len(response.content)
        }
        
        # 提取标题
        soup = response.soup
        title = soup.find('title')
        if title:
            data['title'] = title.text
        
        logger.info(f"提取数据: {data['url']} - {data['title']}")
        
        # 保存到数据库
        spider.save_to_db(data, collection='crawled_pages')
        
        return data
    except Exception as e:
        logger.error(f"解析失败: {e}")


def main():
    """主函数"""
    # 使用YAML配置文件
    try:
        config = Config.from_yaml('config.yaml')
        logger.info("从config.yaml加载配置")
    except FileNotFoundError:
        # 如果没有配置文件，使用默认配置
        logger.warning("config.yaml不存在，使用默认配置")
        config = {
            'database': {
                'type': 'mongodb',
                'mongodb': {
                    'host': 'localhost',
                    'port': 27017,
                    'database': 'crawler_db',
                }
            },
            'crawler': {
                'concurrency': 3,
                'timeout': 30,
                'use_proxy': False,
            }
        }
        config = Config(config)
    
    # 创建爬虫实例
    spider = Spider(config)
    
    # 要爬取的URL
    urls = [
        'https://httpbin.org/html',
        'https://httpbin.org/json',
    ]
    
    try:
        logger.info("开始爬取并保存到数据库...")
        
        # 方式1: 使用lambda传递spider参数
        spider.crawl(urls, callback=lambda resp: parse_and_save(resp, spider))
        
        # 方式2: 直接保存字典数据
        test_data = {
            'type': 'test',
            'message': '这是一条测试数据',
            'timestamp': datetime.now().isoformat()
        }
        spider.save_to_db(test_data, collection='test_collection')
        
        logger.info("数据保存完成")
        
        # 如果使用MongoDB，可以查询数据
        if spider.db_manager:
            db = spider.db_manager.get_db()
            if hasattr(db, 'find_many'):
                # MongoDB
                records = db.find_many('crawled_pages', limit=5)
                logger.info(f"查询到 {len(records)} 条记录")
                for record in records:
                    logger.info(f"  - {record.get('url')} | {record.get('title')}")
        
    except Exception as e:
        logger.error(f"操作失败: {e}")
    finally:
        spider.close()


if __name__ == '__main__':
    logger.warning("提示: 请确保MongoDB服务正在运行")
    logger.warning("或者修改配置使用其他数据库")
    
    main()

