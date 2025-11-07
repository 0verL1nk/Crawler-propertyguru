#!/usr/bin/env python3
"""
使用标准 Selenium 测试 Chromium（不使用 undetected_chromedriver）
"""
import sys
import time

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    print("✓ Selenium 导入成功")

    # 配置路径
    driver_path = "/home/ling/.local/bin/chromedriver"
    browser_path = "/usr/bin/chromium"

    print(f"✓ ChromeDriver 路径: {driver_path}")
    print(f"✓ Chromium 路径: {browser_path}")

    # 设置选项（针对树莓派优化）
    options = Options()
    options.binary_location = browser_path
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--single-process")
    options.add_argument("--window-size=1920,1080")

    # 创建服务
    service = Service(executable_path=driver_path)

    print("\n正在启动 Chromium（约需10-20秒）...")
    start_time = time.time()

    # 启动浏览器
    driver = webdriver.Chrome(service=service, options=options)

    elapsed = time.time() - start_time
    print(f"✓ Chromium 启动成功！耗时: {elapsed:.1f} 秒")

    # 测试访问网页
    print("\n正在访问测试网页...")
    driver.get("https://www.example.com")
    print(f"✓ 页面标题: {driver.title}")
    print(f"✓ 当前URL: {driver.current_url}")

    # 清理
    print("\n正在关闭浏览器...")
    driver.quit()
    print("✓ 标准 Selenium 测试完成！")
    print("\n如果这个测试成功，说明基础配置没问题。")
    print("问题可能在 undetected_chromedriver 上。")

except Exception as e:
    print(f"\n✗ 错误: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
