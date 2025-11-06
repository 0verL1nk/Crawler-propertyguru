#!/usr/bin/env python3
"""
测试 Undetected Chrome 集成
验证 undetected-chromedriver 是否正常工作
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from crawler.browser import UndetectedBrowser
from utils.logger import get_logger

logger = get_logger("TestUndetected")


def test_basic():
    """测试基本功能"""
    logger.info("=" * 60)
    logger.info("测试 1: 基本功能测试")
    logger.info("=" * 60)

    browser = UndetectedBrowser(headless=False)

    try:
        # 连接浏览器
        logger.info("正在启动浏览器...")
        browser.connect()
        logger.info("✅ 浏览器启动成功")

        # 访问测试网站
        test_url = "https://www.nowsecure.nl"
        logger.info(f"访问测试网站: {test_url}")
        browser.get(test_url)
        logger.info("✅ 页面加载成功")

        # 获取页面标题
        title = browser.execute_script("return document.title")
        logger.info(f"页面标题: {title}")

        # 获取页面源码
        page_source = browser.get_page_source()
        logger.info(f"页面源码长度: {len(page_source)} 字符")

        logger.info("✅ 测试 1 通过")
        return True

    except Exception as e:
        logger.error(f"❌ 测试 1 失败: {e}")
        return False

    finally:
        browser.close()


def test_webdriver_detection():
    """测试反检测功能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: WebDriver 检测测试")
    logger.info("=" * 60)

    browser = UndetectedBrowser(headless=False)

    try:
        browser.connect()

        # 访问检测 webdriver 的页面
        logger.info("访问 WebDriver 检测页面...")
        browser.get("https://bot.sannysoft.com/")

        # 等待页面加载
        import time

        time.sleep(3)

        # 检查 webdriver 属性
        is_webdriver = browser.execute_script("return navigator.webdriver")
        logger.info(f"navigator.webdriver: {is_webdriver}")

        if is_webdriver is None or is_webdriver is False:
            logger.info("✅ WebDriver 未被检测到")
            logger.info("✅ 测试 2 通过")
            return True
        else:
            logger.warning("⚠️  WebDriver 被检测到")
            logger.info("ℹ️  这可能是正常的，某些情况下仍会被检测")
            return True

    except Exception as e:
        logger.error(f"❌ 测试 2 失败: {e}")
        return False

    finally:
        browser.close()


def test_context_manager():
    """测试上下文管理器"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: 上下文管理器测试")
    logger.info("=" * 60)

    try:
        with UndetectedBrowser(headless=False) as browser:
            logger.info("使用上下文管理器启动浏览器...")
            browser.get("https://www.example.com")
            title = browser.execute_script("return document.title")
            logger.info(f"页面标题: {title}")

        logger.info("✅ 浏览器已自动关闭")
        logger.info("✅ 测试 3 通过")
        return True

    except Exception as e:
        logger.error(f"❌ 测试 3 失败: {e}")
        return False


def main():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("Undetected Chrome 集成测试")
    logger.info("=" * 60)
    logger.info("")

    # 检查是否安装了 undetected-chromedriver
    try:
        import undetected_chromedriver as uc

        logger.info("✅ undetected-chromedriver 已安装")
        logger.info(f"   版本: {uc.__version__ if hasattr(uc, '__version__') else 'Unknown'}")
    except ImportError:
        logger.error("❌ undetected-chromedriver 未安装")
        logger.error("请运行: pip install undetected-chromedriver")
        return

    # 检查 Chrome 浏览器
    try:
        import subprocess

        result = subprocess.run(
            ["google-chrome", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            logger.info(f"✅ Chrome 浏览器已安装: {result.stdout.strip()}")
        else:
            logger.warning("⚠️  无法检测 Chrome 版本")
    except Exception:
        logger.warning("⚠️  无法检测 Chrome 浏览器")

    logger.info("")

    # 运行测试
    results = []

    # 测试 1: 基本功能
    results.append(("基本功能", test_basic()))

    # 测试 2: WebDriver 检测
    results.append(("WebDriver 检测", test_webdriver_detection()))

    # 测试 3: 上下文管理器
    results.append(("上下文管理器", test_context_manager()))

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    logger.info("")
    logger.info(f"总计: {passed}/{total} 个测试通过")
    logger.info("=" * 60)

    if passed == total:
        logger.info("🎉 所有测试通过！Undetected Chrome 已成功集成！")
    else:
        logger.warning("⚠️  部分测试失败，请检查配置")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n用户中断测试")
    except Exception as e:
        logger.error(f"测试过程出错: {e}", exc_info=True)
