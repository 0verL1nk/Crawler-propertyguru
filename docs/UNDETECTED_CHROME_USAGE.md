# Undetected Chrome 使用指南

## 简介

Undetected Chrome 是一个增强版的 ChromeDriver，专门用于绕过反爬虫检测。它基于 `undetected-chromedriver` 库，可以：

- 绕过 Cloudflare、Imperva 等反爬虫服务
- 避免被检测为自动化工具（webdriver 检测）
- 更好地模拟真实用户行为
- 自动处理 Chrome 版本匹配问题

## 安装

依赖已经添加到项目中，运行以下命令安装：

```bash
# 使用 pip
pip install undetected-chromedriver>=3.5.0

# 或者安装所有依赖
pip install -r requirements.txt
```

## 配置

### 1. 在 `.env` 文件中配置浏览器类型

```bash
# 使用 Undetected Chrome（推荐）
BROWSER_TYPE=undetected

# 可选：指定 Chrome 版本（不设置则自动检测）
# CHROME_VERSION=120

# 是否使用无头模式
BROWSER_HEADLESS=false
```

### 2. 浏览器类型说明

项目支持三种浏览器模式：

| 浏览器类型 | 说明 | 适用场景 | 配置 |
|----------|------|---------|------|
| `remote` | Bright Data 远程浏览器 | 需要云端浏览器服务 | 需要 `BROWSER_AUTH` |
| `local` | 标准 Chrome 浏览器 | 测试和开发 | 本地 Chrome + ChromeDriver |
| `undetected` | **Undetected Chrome** | **生产环境，对抗反爬虫** | 本地 Chrome（推荐） |

## 使用方法

### 方式 1：在爬虫项目中使用（已集成）

项目已经集成了 Undetected Chrome，只需设置环境变量即可：

```bash
# 在 .env 文件中
BROWSER_TYPE=undetected
BROWSER_HEADLESS=false
```

然后正常运行爬虫：

```bash
# 测试单个房源
python main.py --test-single

# 测试第一页
python main.py --test-page

# 爬取指定页面
python main.py 1 10
```

### 方式 2：直接使用 UndetectedBrowser 类

```python
from crawler.browser import UndetectedBrowser

# 创建浏览器实例
browser = UndetectedBrowser(
    headless=False,           # 是否无头模式
    version_main=None,        # Chrome 版本（None 则自动检测）
)

# 使用上下文管理器（推荐）
with UndetectedBrowser() as browser:
    browser.get("https://example.com")

    # 查找元素
    element = browser.find_element("css selector", "h1")
    print(element.text)

    # 执行 JavaScript
    result = browser.execute_script("return document.title")

    # 截图
    browser.get_screenshot("screenshot.png")
```

### 方式 3：完整示例

```python
from crawler.browser import UndetectedBrowser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_with_undetected():
    """使用 Undetected Chrome 爬取网页"""
    browser = UndetectedBrowser(headless=False)

    try:
        # 连接浏览器
        browser.connect()

        # 访问网页
        browser.get("https://www.propertyguru.com.sg")

        # 等待页面加载
        wait = browser.wait(timeout=30)
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )

        # 提取数据
        page_source = browser.get_page_source()
        print(f"页面长度: {len(page_source)} 字符")

        # 查找元素
        elements = browser.find_elements(By.TAG_NAME, "h1")
        for el in elements:
            print(el.text)

        # 截图
        browser.get_screenshot("page.png")

    finally:
        browser.close()

if __name__ == "__main__":
    scrape_with_undetected()
```

## 高级配置

### 自定义 Chrome 选项

```python
from selenium.webdriver import ChromeOptions
from crawler.browser import UndetectedBrowser

# 创建自定义选项
options = ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')

# 使用自定义选项
browser = UndetectedBrowser()
browser.connect(options=options)
```

### 指定 Chrome 版本

如果自动检测失败，可以手动指定版本：

```python
browser = UndetectedBrowser(
    version_main=120  # Chrome 120.x
)
```

或在环境变量中设置：

```bash
CHROME_VERSION=120
```

### 配合代理使用

```python
from selenium.webdriver import ChromeOptions

options = ChromeOptions()
options.add_argument('--proxy-server=http://proxy.example.com:8080')

browser = UndetectedBrowser()
browser.connect(options=options)
```

## 常见问题

### 1. Chrome 版本不匹配

**问题**: 提示 Chrome 版本与驱动不匹配

**解决方案**:
- 让库自动检测：不设置 `version_main` 参数
- 手动指定版本：`UndetectedBrowser(version_main=120)`
- 更新库：`pip install -U undetected-chromedriver`

### 2. 无头模式被检测

**问题**: 无头模式仍被网站检测为机器人

**解决方案**:
- 避免使用无头模式：`BROWSER_HEADLESS=false`
- 使用虚拟显示器（Linux）：
```bash
sudo apt-get install xvfb
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
```

### 3. 驱动初始化失败

**问题**: 无法启动 Chrome 浏览器

**解决方案**:
- 确保已安装 Chrome 浏览器
- Ubuntu/Debian:
```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f
```
- 检查 Chrome 版本：`google-chrome --version`

### 4. WSL2 环境下的问题

**问题**: 在 WSL2 中无法显示浏览器窗口

**解决方案**:
- 使用无头模式：`BROWSER_HEADLESS=true`
- 或者安装 X Server（如 VcXsrv）并设置 `DISPLAY` 变量

## 性能对比

| 特性 | 标准 Selenium | Undetected Chrome |
|-----|-------------|------------------|
| 检测率 | 高 | 低 |
| 启动速度 | 快 | 稍慢（首次） |
| 稳定性 | 高 | 高 |
| 反爬绕过 | ❌ | ✅ |
| Cloudflare 绕过 | ❌ | ✅ |
| 学习曲线 | 低 | 低 |

## 最佳实践

1. **生产环境推荐配置**:
```bash
BROWSER_TYPE=undetected
BROWSER_HEADLESS=false  # 或使用 Xvfb
```

2. **添加随机延迟**: 模拟真实用户行为
```python
import time
import random

browser.get(url)
time.sleep(random.uniform(2, 5))  # 2-5秒随机延迟
```

3. **设置合理的超时时间**:
```python
wait = browser.wait(timeout=30)
```

4. **错误处理**:
```python
try:
    browser.connect()
    browser.get(url)
except Exception as e:
    logger.error(f"爬取失败: {e}")
    browser.close()
    raise
```

5. **资源清理**: 始终关闭浏览器
```python
try:
    # 爬取逻辑
    pass
finally:
    browser.close()
```

## 参考资料

- [undetected-chromedriver GitHub](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
- [Selenium 文档](https://selenium-python.readthedocs.io/)
- [项目 README](../README.md)

## 技术支持

如遇到问题，请查看：
1. 项目日志文件：`logs/crawler.log`
2. 环境变量配置：`.env` 文件
3. 浏览器版本：`google-chrome --version`
