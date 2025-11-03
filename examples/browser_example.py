"""
远程浏览器API示例
演示如何使用Bright Data Scraping Browser进行网页爬取
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from crawler.browser import RemoteBrowser, scrape_with_browser
from selenium.webdriver.common.by import By
from utils.logger import get_logger

logger = get_logger("BrowserExample")


def example_1_basic_scraping():
    """示例1: 基础爬取"""
    logger.info("=" * 60)
    logger.info("示例1: 基础网页爬取")
    logger.info("=" * 60)
    
    # 创建浏览器实例（自动从环境变量读取认证信息）
    browser = RemoteBrowser()
    
    try:
        # 连接浏览器
        browser.connect()
        
        # 访问网页
        url = 'https://example.com'
        browser.get(url)
        
        # 提取数据
        paragraphs = browser.find_elements(By.TAG_NAME, 'p')
        data = browser.execute_script(
            'return arguments[0].map(el => el.innerText)',
            paragraphs
        )
        
        logger.info(f"爬取到 {len(data)} 段文本:")
        for i, text in enumerate(data[:5], 1):  # 只显示前5条
            logger.info(f"  {i}. {text[:50]}...")
        
    finally:
        browser.close()


def example_2_with_inspect():
    """示例2: 启用调试模式"""
    logger.info("\n" + "=" * 60)
    logger.info("示例2: 启用调试模式（可检查会话）")
    logger.info("=" * 60)
    
    browser = RemoteBrowser()
    
    try:
        browser.connect()
        
        # 启用检查会话
        inspect_url = browser.enable_inspect(wait_time=10)
        if inspect_url:
            logger.info(f"可以在浏览器中打开此URL进行调试: {inspect_url}")
        
        # 访问网页
        browser.get('https://example.com')
        
        logger.info("页面已加载，可以查看调试信息")
        
    finally:
        browser.close()


def example_3_file_download():
    """示例3: 文件下载"""
    logger.info("\n" + "=" * 60)
    logger.info("示例3: 文件下载")
    logger.info("=" * 60)
    
    browser = RemoteBrowser()
    
    try:
        browser.connect()
        
        # 启用下载功能
        browser.enable_download()
        
        # 访问包含下载链接的页面
        url = os.getenv('TARGET_URL', 'https://example.com')
        browser.get(url)
        
        # 触发下载（需要根据实际页面调整选择器）
        selector = os.getenv('SELECTOR', 'button.download')
        filename = os.getenv('FILENAME', './downloads/file.csv')
        
        logger.info(f"查找下载按钮: {selector}")
        try:
            browser.download_file(
                download_trigger=lambda: browser.find_element(
                    By.CSS_SELECTOR, selector
                ).click(),
                filename=filename,
                timeout=60
            )
            logger.info(f"✅ 文件下载成功: {filename}")
        except Exception as e:
            logger.error(f"下载失败: {e}")
        
    finally:
        browser.close()


def example_4_captcha_solving():
    """示例4: 验证码自动解决"""
    logger.info("\n" + "=" * 60)
    logger.info("示例4: 验证码自动解决")
    logger.info("=" * 60)
    
    browser = RemoteBrowser()
    
    try:
        browser.connect()
        
        # 访问需要验证码的页面
        url = os.getenv('TARGET_URL', 'https://example.com')
        browser.get(url)
        
        # 等待验证码解决
        status = browser.wait_for_captcha(detect_timeout=30000)
        
        if status == 'solved':
            logger.info("✅ 验证码已解决")
            
            # 继续爬取
            page_source = browser.get_page_source()
            logger.info(f"页面内容长度: {len(page_source)} 字符")
        else:
            logger.warning(f"验证码状态: {status}")
        
    finally:
        browser.close()


def example_5_advanced_scraping():
    """示例5: 高级爬取（使用便捷函数）"""
    logger.info("\n" + "=" * 60)
    logger.info("示例5: 使用便捷函数爬取")
    logger.info("=" * 60)
    
    def parse_page(browser):
        """解析页面"""
        # 提取标题
        title = browser.find_element(By.TAG_NAME, 'title')
        title_text = title.get_attribute('innerText') if title else 'N/A'
        
        # 提取所有链接
        links = browser.find_elements(By.TAG_NAME, 'a')
        link_urls = [
            link.get_attribute('href') 
            for link in links 
            if link.get_attribute('href')
        ]
        
        # 截图
        browser.get_screenshot('screenshot.png')
        
        return {
            'title': title_text,
            'links_count': len(link_urls),
            'links': link_urls[:10]  # 只返回前10个
        }
    
    # 使用便捷函数
    result = scrape_with_browser(
        'https://example.com',
        callback=parse_page
    )
    
    logger.info(f"爬取结果:")
    logger.info(f"  标题: {result.get('title')}")
    logger.info(f"  链接数: {result.get('links_count')}")
    logger.info(f"  前几个链接: {result.get('links', [])[:3]}")


def example_6_context_manager():
    """示例6: 使用上下文管理器"""
    logger.info("\n" + "=" * 60)
    logger.info("示例6: 使用上下文管理器（推荐方式）")
    logger.info("=" * 60)
    
    # 使用with语句，自动管理连接和关闭
    with RemoteBrowser() as browser:
        browser.get('https://example.com')
        
        # 执行各种操作
        elements = browser.find_elements(By.TAG_NAME, 'p')
        logger.info(f"找到 {len(elements)} 个段落元素")
        
        # 截图
        browser.get_screenshot('context_screenshot.png')
        
    # 浏览器会自动关闭


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("远程浏览器API示例程序")
    logger.info("=" * 60)
    logger.info("")
    
    # 检查配置
    if not os.getenv('BROWSER_AUTH'):
        logger.error("❌ 未配置 BROWSER_AUTH 环境变量！")
        logger.info("")
        logger.info("请在 .env 文件中配置:")
        logger.info("  BROWSER_AUTH=brd-customer-xxx-zone-scraping_browser1:password")
        logger.info("")
        return
    
    # 运行示例
    try:
        # 示例1: 基础爬取
        example_1_basic_scraping()
        
        # 示例2: 调试模式
        # example_2_with_inspect()
        
        # 示例3: 文件下载
        # example_3_file_download()
        
        # 示例4: 验证码
        # example_4_captcha_solving()
        
        # 示例5: 便捷函数
        # example_5_advanced_scraping()
        
        # 示例6: 上下文管理器
        # example_6_context_manager()
        
    except Exception as e:
        logger.error(f"示例运行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()

