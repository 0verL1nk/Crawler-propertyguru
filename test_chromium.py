#!/usr/bin/env python3
"""
测试 Chromium 和 undetected_chromedriver 是否正确配置
"""
import os
import sys
from pathlib import Path

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.chrome.options import Options

    print("✓ undetected_chromedriver 导入成功")

    # 设置选项（针对树莓派优化）
    options = Options()
    options.add_argument("--headless=new")  # 使用新的无头模式
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--single-process")  # 单进程模式（减少内存占用）
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--window-size=1920,1080")

    # 配置路径
    driver_path = os.getenv("CHROMEDRIVER_PATH", "/home/ling/.local/bin/chromedriver")
    browser_path = os.getenv("CHROME_BINARY_PATH", "/usr/bin/chromium")

    print(f"✓ ChromeDriver 路径: {driver_path}")
    print(f"✓ Chromium 路径: {browser_path}")

    # 检查文件是否存在
    if not Path(driver_path).exists():
        print(f"✗ ChromeDriver 不存在: {driver_path}")
        sys.exit(1)

    if not Path(browser_path).exists():
        print(f"✗ Chromium 不存在: {browser_path}")
        sys.exit(1)

    print("✓ 文件路径验证通过")
    print("\n正在启动 Chromium（这在树莓派上可能需要20-30秒）...")
    print("请耐心等待...")

    # 尝试启动浏览器
    import time

    start_time = time.time()

    driver = uc.Chrome(
        driver_executable_path=driver_path,
        browser_executable_path=browser_path,
        options=options,
        version_main=142,  # Chromium 版本
        use_subprocess=False,  # 不使用子进程
    )

    elapsed = time.time() - start_time
    print(f"✓ Chromium 启动成功！耗时: {elapsed:.1f} 秒")

    # 测试访问网页
    print("\n正在访问测试网页...")
    driver.get("https://www.google.com")
    print(f"✓ 页面标题: {driver.title}")

    # 清理
    print("\n正在关闭浏览器...")
    driver.quit()
    print("✓ 测试完成！所有检查通过。")

except ImportError as e:
    print(f"✗ 导入错误: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
