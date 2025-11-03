"""
动态住宅代理示例
演示如何使用 Bright Data 的动态住宅代理进行批量数据爬取
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler import Spider, Config
from utils.proxy import StaticProxy
from utils.logger import get_logger
import time

logger = get_logger("ResidentialProxyExample")


def test_residential_proxy():
    """测试动态住宅代理连接"""
    logger.info("=" * 60)
    logger.info("测试动态住宅代理")
    logger.info("=" * 60)
    
    # 从环境变量获取代理URL
    proxy_url = os.getenv('PROXY_URL')
    
    if not proxy_url:
        logger.error("未配置代理！请在 .env 文件中设置 PROXY_URL")
        logger.info("示例: PROXY_URL=http://user:pass@host:port")
        return False
    
    proxy = StaticProxy(proxy_url)
    
    # 测试代理
    logger.info("测试代理连接...")
    if proxy.test('https://geo.brdtest.com/welcome.txt'):
        logger.info("✅ 代理测试成功！")
    else:
        logger.error("❌ 代理测试失败")
        return False
    
    return True


def example_1_check_ip_rotation():
    """示例1: 验证IP轮换（动态代理特性）"""
    logger.info("\n" + "=" * 60)
    logger.info("示例1: 验证动态IP轮换")
    logger.info("=" * 60)
    
    import requests
    
    # 从环境变量获取代理
    proxy_url = os.getenv('PROXY_URL')
    if not proxy_url:
        logger.error("未配置 PROXY_URL 环境变量")
        return
    
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    logger.info("发送5次请求，观察IP变化...")
    
    for i in range(5):
        try:
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=proxies,
                timeout=30,
                verify=False
            )
            
            data = response.json()
            ip = data.get('origin', 'Unknown')
            
            logger.info(f"请求 {i+1}: IP = {ip}")
            time.sleep(2)  # 等待2秒
            
        except Exception as e:
            logger.error(f"请求失败: {e}")
    
    logger.info("\n💡 如果看到不同的IP地址，说明动态代理正在工作！")


def example_2_batch_crawl_with_proxy():
    """示例2: 使用动态代理批量爬取数据"""
    logger.info("\n" + "=" * 60)
    logger.info("示例2: 使用动态代理批量爬取")
    logger.info("=" * 60)
    
    # 配置爬虫使用动态代理
    config = {
        'crawler': {
            'concurrency': 5,  # 并发数
            'timeout': 30,
            'delay': 1,  # 请求间隔
            'random_delay': [0, 2],
            'use_proxy': False,  # 我们手动设置代理
            'rotate_user_agent': True,
        }
    }
    
    # 从环境变量获取代理URL
    proxy_url = os.getenv('PROXY_URL')
    if not proxy_url:
        logger.error("未配置 PROXY_URL，跳过代理设置")
        return
    
    # 创建爬虫
    spider = Spider(config)
    
    # 手动设置代理
    spider.session.proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    # 要爬取的URL列表
    urls = [
        'https://httpbin.org/html',
        'https://httpbin.org/json',
        'https://httpbin.org/uuid',
        'https://httpbin.org/user-agent',
        'https://httpbin.org/headers',
    ]
    
    results = []
    
    def parse_callback(response):
        """解析回调"""
        data = {
            'url': response.url,
            'status': response.status_code,
            'length': len(response.content)
        }
        results.append(data)
        logger.info(f"✅ 成功爬取: {response.url} (状态码: {response.status_code})")
    
    try:
        logger.info(f"开始爬取 {len(urls)} 个URL...")
        spider.crawl(urls, callback=parse_callback)
        
        logger.info(f"\n爬取完成！成功: {len(results)}/{len(urls)}")
        
    finally:
        spider.close()


def example_3_integrated_crawler():
    """示例3: 集成爬虫 - 代理 + 数据库 + 自动重试"""
    logger.info("\n" + "=" * 60)
    logger.info("示例3: 完整的爬虫流程")
    logger.info("=" * 60)
    
    from utils.proxy import ProxyAdapter
    
    # 从环境变量创建代理适配器
    proxy_url = os.getenv('PROXY_URL')
    if not proxy_url:
        logger.error("未配置 PROXY_URL")
        return
    
    proxy_adapter = ProxyAdapter(proxy_url)
    
    # 配置
    config = {
        'crawler': {
            'concurrency': 3,
            'timeout': 30,
            'max_retries': 3,  # 自动重试3次
            'delay': 1,
            'use_proxy': False,
        },
        'database': {
            'type': 'mongodb',
            'mongodb': {
                'host': 'localhost',
                'port': 27017,
                'database': 'crawler_db',
            }
        }
    }
    
    spider = Spider(config)
    
    # 设置代理
    proxies = proxy_adapter.get_proxies()
    if proxies:
        spider.session.proxies.update(proxies)
        logger.info("✅ 代理已配置")
    
    # 爬取目标
    urls = [
        'https://httpbin.org/delay/1',  # 延迟1秒
        'https://httpbin.org/delay/2',  # 延迟2秒
        'https://httpbin.org/anything',
    ]
    
    def parse_and_save(response):
        """解析并保存"""
        try:
            # 提取数据
            if response.url.endswith('/anything'):
                data = response.json()
            else:
                data = {
                    'url': response.url,
                    'status': response.status_code
                }
            
            # 保存到数据库（如果已配置）
            if spider.db_manager:
                spider.save_to_db(data, collection='crawled_data')
                logger.info(f"✅ 数据已保存到数据库: {response.url}")
            else:
                logger.info(f"✅ 爬取成功: {response.url}")
                
        except Exception as e:
            logger.error(f"处理失败: {e}")
    
    try:
        spider.crawl(urls, callback=parse_and_save)
    finally:
        spider.close()


def example_4_watermark_remover_with_proxy():
    """示例4: 使用动态代理进行图片去水印"""
    logger.info("\n" + "=" * 60)
    logger.info("示例4: 图片去水印 + 动态代理")
    logger.info("=" * 60)
    
    from crawler.watermark_remover import WatermarkRemover
    
    # 从环境变量获取代理（可选）
    proxy_url = os.getenv('PROXY_URL')
    
    # 创建去水印实例（自动从环境变量读取配置）
    remover = WatermarkRemover(proxy=proxy_url)
    
    # 测试图片路径
    input_image = "data/test_image.jpg"
    
    if Path(input_image).exists():
        try:
            logger.info(f"处理图片: {input_image}")
            result = remover.remove_watermark(input_image)
            
            if result:
                logger.info(f"✅ 成功！输出: {result}")
            else:
                logger.error("❌ 处理失败")
        finally:
            remover.close()
    else:
        logger.warning(f"测试图片不存在: {input_image}")
        logger.info("提示: 准备一张测试图片后再运行此示例")


def example_5_advanced_config():
    """示例5: 高级配置 - 会话管理和错误处理"""
    logger.info("\n" + "=" * 60)
    logger.info("示例5: 高级配置示例")
    logger.info("=" * 60)
    
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    # 创建会话
    session = requests.Session()
    
    # 配置重试策略
    retry_strategy = Retry(
        total=3,  # 总重试次数
        backoff_factor=1,  # 重试间隔
        status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的状态码
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 从环境变量配置代理
    proxy_url = os.getenv('PROXY_URL')
    if proxy_url:
        session.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        logger.info("✅ 代理已配置")
    else:
        logger.warning("未配置代理，将直接连接")
    
    # 设置超时
    timeout = (10, 30)  # (连接超时, 读取超时)
    
    # 测试URL
    test_urls = [
        'https://httpbin.org/status/200',
        'https://httpbin.org/delay/3',
    ]
    
    for url in test_urls:
        try:
            logger.info(f"请求: {url}")
            response = session.get(url, timeout=timeout, verify=False)
            response.raise_for_status()
            logger.info(f"✅ 成功: 状态码 {response.status_code}")
        except Exception as e:
            logger.error(f"❌ 失败: {e}")
    
    session.close()


def main():
    """主函数"""
    logger.info("动态住宅代理示例程序")
    logger.info("使用 Bright Data Residential Proxy")
    logger.info("")
    
    # 1. 测试代理连接
    if not test_residential_proxy():
        logger.error("代理测试失败，请检查配置")
        return
    
    # 2. 验证IP轮换
    example_1_check_ip_rotation()
    
    # 3. 批量爬取
    example_2_batch_crawl_with_proxy()
    
    # 4. 完整流程
    # example_3_integrated_crawler()
    
    # 5. 图片去水印
    # example_4_watermark_remover_with_proxy()
    
    # 6. 高级配置
    # example_5_advanced_config()
    
    logger.info("\n" + "=" * 60)
    logger.info("所有示例完成！")
    logger.info("=" * 60)


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("动态住宅代理示例程序")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📝 配置说明:")
    logger.info("  1. 复制 env.example 为 .env")
    logger.info("  2. 在 .env 文件中设置 PROXY_URL")
    logger.info("  3. 使用 zone-residential_proxy1 (动态住宅代理)")
    logger.info("")
    logger.info("💡 动态住宅代理的特点:")
    logger.info("  ✓ 每次请求使用不同的住宅IP（自动轮换）")
    logger.info("  ✓ IP来自真实用户的网络环境")
    logger.info("  ✓ 适合批量爬取，不易被封禁")
    logger.info("  ✓ 适合大规模图片处理，避免IP限流")
    logger.info("  ✓ 成功率高，适合大规模数据采集")
    logger.info("")
    logger.info("🚫 为什么不推荐静态ISP代理？")
    logger.info("  ✗ 固定IP，容易被限流或封禁")
    logger.info("  ✗ 不适合大规模处理任务")
    logger.info("  ✗ 长时间使用同一IP风险高")
    logger.info("")
    logger.info("✅ 推荐配置:")
    logger.info("  PROXY_URL=http://brd-customer-xxx-zone-residential_proxy1:pass@brd.superproxy.io:33335")
    logger.info("")
    
    main()
