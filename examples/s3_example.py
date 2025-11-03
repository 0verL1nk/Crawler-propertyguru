"""
S3存储示例
演示如何将爬取的数据上传到AWS S3
"""

import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler import Spider, Config
from utils.logger import get_logger

logger = get_logger("S3Example")


def parse_and_upload(response, spider):
    """解析并上传到S3"""
    try:
        # 提取数据
        data = {
            'url': response.url,
            'status_code': response.status_code,
            'crawled_at': datetime.now().isoformat(),
            'content': response.text[:1000],  # 只保存前1000字符
        }
        
        # 生成S3文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"crawled_data/{timestamp}_{response.url.split('/')[-1]}.json"
        
        # 上传到S3
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        spider.save_to_s3(json_data, filename)
        
        logger.info(f"数据已上传: {filename}")
        
        return data
    except Exception as e:
        logger.error(f"上传失败: {e}")


def main():
    """主函数"""
    # 使用配置文件
    try:
        config = Config.from_yaml('config.yaml')
    except FileNotFoundError:
        logger.warning("config.yaml不存在，使用默认配置")
        config = {
            's3': {
                'enabled': True,
                'aws_access_key_id': 'YOUR_ACCESS_KEY',
                'aws_secret_access_key': 'YOUR_SECRET_KEY',
                'bucket_name': 'your-bucket-name',
                'region_name': 'us-east-1',
                'prefix': 'crawled_data/',
                'encrypt': True
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
    
    if not spider.s3_manager:
        logger.error("S3管理器未初始化，请检查配置")
        return
    
    # 要爬取的URL
    urls = [
        'https://httpbin.org/json',
        'https://httpbin.org/uuid',
    ]
    
    try:
        logger.info("开始爬取并上传到S3...")
        
        # 爬取并上传
        spider.crawl(urls, callback=lambda resp: parse_and_upload(resp, spider))
        
        # 也可以直接上传本地文件
        # spider.s3_manager.upload_file('local_file.txt', 's3_key.txt')
        
        # 列出S3中的文件
        files = spider.s3_manager.list_files(prefix='crawled_data/')
        logger.info(f"S3中的文件数: {len(files)}")
        for file_key in files[:5]:  # 只显示前5个
            logger.info(f"  - {file_key}")
        
        logger.info("上传完成")
        
    except Exception as e:
        logger.error(f"操作失败: {e}")
    finally:
        spider.close()


if __name__ == '__main__':
    logger.warning("提示: 请在config.yaml或环境变量中配置AWS凭证")
    logger.warning("需要设置: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME")
    
    main()
