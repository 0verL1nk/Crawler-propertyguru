"""
高级爬虫示例
演示完整的爬虫流程：代理 + 数据库 + S3
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import hashlib

sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler import Spider, Config
from utils.logger import get_logger

logger = get_logger("AdvancedExample")


class AdvancedSpider:
    """高级爬虫类"""
    
    def __init__(self, config):
        self.spider = Spider(config)
        self.results = []
    
    def parse_page(self, response):
        """解析页面"""
        try:
            logger.info(f"正在解析: {response.url}")
            
            # 提取数据
            soup = response.soup
            title = soup.find('title')
            
            data = {
                'url': response.url,
                'title': title.text if title else '',
                'status_code': response.status_code,
                'content_length': len(response.content),
                'crawled_at': datetime.now().isoformat(),
                'url_hash': hashlib.md5(response.url.encode()).hexdigest()
            }
            
            # 提取所有链接
            links = []
            for a_tag in soup.find_all('a', href=True):
                links.append(a_tag['href'])
            data['links_count'] = len(links)
            
            logger.info(f"提取到 {len(links)} 个链接")
            
            # 保存到数据库
            if self.spider.db_manager:
                self.spider.save_to_db(data, collection='pages')
                logger.info("已保存到数据库")
            
            # 上传到S3
            if self.spider.s3_manager:
                json_data = json.dumps(data, ensure_ascii=False, indent=2)
                s3_key = f"pages/{data['url_hash']}.json"
                self.spider.save_to_s3(json_data, s3_key)
                logger.info("已上传到S3")
            
            self.results.append(data)
            
            return data
            
        except Exception as e:
            logger.error(f"解析失败: {response.url}, 错误: {e}")
            return None
    
    def run(self, urls):
        """运行爬虫"""
        logger.info(f"开始爬取 {len(urls)} 个页面")
        start_time = datetime.now()
        
        try:
            # 显示配置信息
            if self.spider.proxy_manager:
                stats = self.spider.proxy_manager.get_stats()
                logger.info(f"代理池: {stats['total']} 个代理可用")
            
            if self.spider.db_manager:
                logger.info("数据库已连接")
            
            if self.spider.s3_manager:
                logger.info("S3存储已配置")
            
            # 开始爬取
            self.spider.crawl(urls, callback=self.parse_page)
            
            # 统计结果
            elapsed = (datetime.now() - start_time).total_seconds()
            success_count = len(self.results)
            
            logger.info(f"\n{'='*50}")
            logger.info(f"爬取完成统计:")
            logger.info(f"  总URL数: {len(urls)}")
            logger.info(f"  成功数: {success_count}")
            logger.info(f"  失败数: {len(urls) - success_count}")
            logger.info(f"  总耗时: {elapsed:.2f}秒")
            logger.info(f"  平均耗时: {elapsed/len(urls):.2f}秒/URL")
            logger.info(f"{'='*50}\n")
            
            # 保存汇总报告
            self.save_report()
            
        except Exception as e:
            logger.error(f"爬取过程出错: {e}")
        finally:
            self.spider.close()
    
    def save_report(self):
        """保存爬取报告"""
        if not self.results:
            return
        
        report = {
            'total_pages': len(self.results),
            'timestamp': datetime.now().isoformat(),
            'pages': self.results
        }
        
        # 保存到文件
        report_path = Path('data/report.json')
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"报告已保存: {report_path}")


def main():
    """主函数"""
    # 加载配置
    try:
        config = Config.from_yaml('config.yaml')
        logger.info("已加载配置文件: config.yaml")
    except FileNotFoundError:
        logger.warning("未找到config.yaml，使用默认配置")
        config = {
            'crawler': {
                'concurrency': 5,
                'timeout': 30,
                'delay': 1,
                'use_proxy': False,
            }
        }
        config = Config(config)
    
    # 创建高级爬虫
    advanced_spider = AdvancedSpider(config)
    
    # 要爬取的URL列表
    urls = [
        'https://httpbin.org/html',
        'https://httpbin.org/links/5',
        'https://httpbin.org/json',
        'https://httpbin.org/uuid',
        'https://httpbin.org/user-agent',
    ]
    
    # 运行爬虫
    advanced_spider.run(urls)


if __name__ == '__main__':
    logger.info("="*60)
    logger.info("高级爬虫示例 - 完整功能演示")
    logger.info("="*60)
    
    main()

