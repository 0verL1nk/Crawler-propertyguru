#!/usr/bin/env python3
"""
简化的 undetected_chromedriver 测试（针对树莓派优化）
"""
import sys
import time

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.chrome.options import Options

    print("✓ undetected_chromedriver 导入成功")

    # 配置路径
    driver_path = "/home/ling/.local/bin/chromedriver"
    browser_path = "/usr/bin/chromium"

    print(f"✓ ChromeDriver: {driver_path}")
    print(f"✓ Chromium: {browser_path}")

    # 配置选项（修复渲染器通信问题）
    options = Options()
    options.page_load_strategy = "eager"  # 不等待完整加载

    # 关键参数：修复渲染器通信问题
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")  # 避免共享内存问题
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-setuid-sandbox")
    # 注意：--single-process 可能导致超时，先不用
    # options.add_argument('--single-process')
    options.add_argument("--disable-blink-features=AutomationControlled")

    print("✓ 已配置渲染器通信参数")

    # 最小化配置
    print("\n正在启动 Chromium（树莓派上约需30-60秒）...")
    print("请耐心等待，不要中断...")

    start_time = time.time()

    # 使用最简单的配置
    driver = uc.Chrome(
        options=options,
        driver_executable_path=driver_path,
        browser_executable_path=browser_path,
        headless=True,  # 无头模式更快
        version_main=142,
        use_subprocess=False,  # 不使用子进程
        log_level=0,  # 详细日志
        no_sandbox=True,  # 禁用沙箱（树莓派建议）
    )

    elapsed = time.time() - start_time
    print(f"\n✓ Chromium 启动成功！耗时: {elapsed:.1f} 秒")

    # 设置超时
    driver.set_page_load_timeout(30)  # 30秒页面加载超时
    driver.set_script_timeout(30)  # 30秒脚本执行超时

    # 测试访问
    print("\n正在访问测试网页（30秒超时）...")
    try:
        driver.get("https://www.baidu.com")
        print(f"✓ 页面标题: {driver.title}")
        print(f"✓ 当前URL: {driver.current_url}")
    except Exception as e:
        print(f"⚠ 访问网页失败: {e}")
        print("尝试访问更简单的页面...")
        driver.get("data:text/html,<h1>Test Page</h1>")
        print("✓ 本地页面加载成功")

    # 清理
    print("\n正在关闭...")
    driver.quit()
    print("✓ 测试成功！")

except KeyboardInterrupt:
    print("\n\n用户中断。如果启动时间过长，可以尝试：")
    print("1. 确保没有其他 Chromium 进程在运行")
    print("2. 增加系统 SWAP 空间")
    print("3. 使用无头模式（已启用）")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ 错误: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
