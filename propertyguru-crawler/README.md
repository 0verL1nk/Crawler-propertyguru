# 爬虫框架 (Crawler Framework)

一个安全、高效的 Python 爬虫框架，支持代理IP管理、多种数据库存储和 S3 云存储。

## ✨ 特性

- 🚀 **高性能**: 支持异步请求和并发控制
- 🔒 **安全可靠**: 动态住宅代理（自动IP轮换）、请求重试、错误处理
- 🌐 **多种浏览器**:
  - **Undetected Chrome** - 增强反检测能力，绕过 Cloudflare（推荐）
  - Bright Data Scraping Browser - 云端浏览器服务
  - 标准 Chrome - 本地测试和开发
- 🛡️ **反爬虫绕过**: 基于 undetected-chromedriver，可处理 JS 渲染、验证码
- 💾 **多种存储**: 支持 MySQL、MongoDB、Redis 和 AWS S3
- 📊 **数据处理**: 集成数据清洗和结构化处理
- 🔐 **SSL支持**: 支持SSL证书配置（Bright Data代理必需）
- 📝 **日志记录**: 完善的日志系统，支持文件轮转
- ⚙️ **灵活配置**: YAML配置文件，环境变量支持

## 📦 安装

### 🚀 一键安装（推荐 - Linux/Ubuntu）

```bash
# 克隆项目
git clone <your-repo-url>
cd propertyguru

# 运行自动安装脚本
./setup.sh
```

安装脚本会自动完成：
- ✅ 安装系统依赖（Xvfb、构建工具等）
- ✅ 安装 Google Chrome
- ✅ 安装 uv 包管理器
- ✅ 安装所有 Python 依赖
- ✅ 配置虚拟显示支持
- ✅ 创建必要的目录和配置文件
- ✅ 测试安装是否成功

### 手动安装

#### 使用 uv (推荐)

```bash
# 克隆项目
git clone <your-repo-url>
cd propertyguru

# 安装系统依赖（Ubuntu/Debian）
sudo apt-get update
sudo apt-get install -y xvfb x11-xkb-utils xfonts-100dpi xfonts-75dpi xfonts-scalable xfonts-cyrillic

# 安装 Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt-get install -y ./google-chrome-stable_current_amd64.deb

# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 使用 uv 安装依赖
uv sync
uv pip install pyvirtualdisplay

# 激活虚拟环境
# Linux/Mac
source .venv/bin/activate
```

#### 使用 pip

```bash
pip install -r requirements.txt
pip install pyvirtualdisplay
```

## 🚀 快速开始

### 1. 配置环境

复制 `env.example` 为 `.env` 并填写配置：

```bash
cp env.example .env
```

编辑 `.env` 文件，配置代理和其他服务：

```bash
# ===== 浏览器配置（重要！）=====
# 浏览器类型：undetected（推荐）, remote, local
BROWSER_TYPE=undetected

# 虚拟显示模式（推荐 - 原生 Linux 服务器，WSL2 用户建议设为 false）
BROWSER_HEADLESS=false
BROWSER_USE_VIRTUAL_DISPLAY=false   # WSL2 环境建议设为 false
BROWSER_DISABLE_IMAGES=true         # 禁用资源加载，大幅提升速度

# ===== 代理配置 =====
# 动态住宅代理（推荐用于批量爬取）
PROXY_URL=http://brd-customer-xxx:password@brd.superproxy.io:33335

# ===== 图片处理（可选）=====
WATERMARK_REMOVER_PRODUCT_SERIAL=your_serial
WATERMARK_REMOVER_PRODUCT_CODE=067003

# ===== 数据库配置 =====
MYSQL_URI=mysql+pymysql://root:password@localhost:3306/crawler_db
MONGODB_URI=mongodb://localhost:27017/crawler_db
```

### 2. 代理配置说明

#### 动态住宅代理（推荐使用）
- **适用场景**:
  - 批量下载网站数据
  - 大规模图片处理（去水印等）
  - 大规模爬取任务
  - 任何需要避免IP封禁的场景
- **特点**:
  - 每次请求自动切换不同的住宅IP
  - 不易被封禁，适合大规模处理
  - 真实用户网络环境
- **配置**: `zone-residential_proxy1`

```bash
# 在 .env 文件中配置
PROXY_URL=http://brd-customer-xxx-zone-residential_proxy1:pass@brd.superproxy.io:33335
```

#### 为什么选择动态住宅代理？
- ✅ **适合大规模处理**: 每次请求自动切换IP，避免IP被封禁
- ✅ **适合图片处理**: 大规模图片去水印等操作不会被限制
- ✅ **真实用户IP**: 来自真实住宅网络，成功率高
- ✅ **自动轮换**: 无需手动管理，系统自动切换IP

#### 代理池（从文件加载）
创建 `proxies.txt` 文件，每行一个代理：

```
http://ip1:port1
http://username:password@ip2:port2
socks5://ip3:port3
```

### 3. 浏览器配置说明

项目支持三种浏览器模式，通过 `BROWSER_TYPE` 环境变量配置：

#### 🎯 Undetected Chrome（推荐）
- **适用场景**:
  - 生产环境爬取
  - 对抗反爬虫检测
  - 绕过 Cloudflare、Imperva 等防护（5秒盾等）
  - 模拟真实用户行为
- **特点**:
  - 基于 undetected-chromedriver
  - 自动绕过 webdriver 检测
  - 自动处理 Chrome 版本匹配
  - 支持无头模式、有头模式、虚拟显示模式
  - 可禁用图片/资源加载，大幅提升速度
- **配置**:

**方式1: 虚拟显示模式（推荐 - 原生 Linux 服务器）**
```bash
BROWSER_TYPE=undetected
BROWSER_HEADLESS=false
BROWSER_USE_VIRTUAL_DISPLAY=true  # 有头模式但不显示窗口
BROWSER_DISABLE_IMAGES=true       # 禁用资源加载，提升速度
```
⚠️ **WSL2 用户注意**：虚拟显示在 WSL2 中可能不稳定，建议使用方式2或方式3

**方式2: 有头模式（本地开发）**
```bash
BROWSER_TYPE=undetected
BROWSER_HEADLESS=false
BROWSER_USE_VIRTUAL_DISPLAY=false
BROWSER_DISABLE_IMAGES=true
```

**方式3: 无头模式（可能触发检测）**
```bash
BROWSER_TYPE=undetected
BROWSER_HEADLESS=true
BROWSER_DISABLE_IMAGES=true
```

#### 🌐 Remote Browser（Bright Data）
- **适用场景**:
  - 需要云端浏览器服务
  - 自动验证码解决
  - 全球IP分布需求
- **配置**:
```bash
BROWSER_TYPE=remote
BROWSER_AUTH=brd-customer-xxx-zone-scraping_browser1:password
```

#### 🔧 Local Browser（测试）
- **适用场景**:
  - 本地开发测试
  - 快速调试
- **配置**:
```bash
BROWSER_TYPE=local
BROWSER_HEADLESS=false
```

#### 浏览器对比

| 特性 | Undetected (虚拟显示) | Undetected (无头) | Remote | Local |
|-----|---------------------|-----------------|--------|-------|
| 反检测能力 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| 5秒盾绕过 | ✅ | ❌ | ✅ | ❌ |
| 成本 | 免费 | 免费 | 付费 | 免费 |
| 配置难度 | 简单 | 简单 | 中等 | 简单 |
| 稳定性 | 高 | 中 | 高 | 中 |
| 服务器适用 | ✅ | ✅ | ✅ | ❌ |
| 验证码处理 | 需手动 | 需手动 | 自动 | 需手动 |
| 资源消耗 | 中 | 低 | 低 | 中 |

> 💡 **推荐配置**:
> - **服务器生产环境**: `undetected + 虚拟显示模式` - 最佳反检测效果
> - **本地开发调试**: `undetected + 有头模式` - 可视化调试
> - **无服务器/云函数**: `remote` - 云端托管

详细使用指南: [Undetected Chrome 使用文档](docs/UNDETECTED_CHROME_USAGE.md)

### 4. 编写爬虫

```python
from crawler import Spider, Config

# 加载配置
config = Config.from_yaml('config.yaml')

# 创建爬虫实例
spider = Spider(config)

# 定义爬取逻辑
async def parse(response):
    # 处理响应
    data = response.json()
    await spider.save_to_db(data)
    return data

# 开始爬取
urls = ['https://api.example.com/data']
spider.start(urls, parse)
```

### 4. 运行爬虫

#### PropertyGuru 爬虫

```bash
# 测试单个房源
uv run python main.py --test-single

# 测试单页爬取
uv run python main.py --test-page 1

# 更新模式（推荐 - 持续爬取最新数据）
uv run python main.py --update-mode

# 更新模式 + 自定义间隔（每10分钟一次）
uv run python main.py --update-mode --interval 10

# 更新模式 + 限制页数
uv run python main.py --update-mode --max-pages 5

# 爬取指定页数范围
uv run python main.py --start-page 1 --end-page 10
```

#### 其他示例

```bash
# 测试 Undetected Chrome
uv run python test_undetected.py

# 运行代理示例
uv run python examples/proxy_example.py

# 运行数据库示例
uv run python examples/database_example.py
```

## 📚 核心模块

### 代理管理器 (ProxyManager)

- 支持多种代理来源（文件、API、Redis）
- 自动检测代理可用性
- 智能失败重试和代理切换
- 代理使用统计

### 数据库管理器 (DatabaseManager)

- 支持 MySQL、MongoDB、SQLite
- 连接池管理
- 自动重连
- 批量操作优化

### S3 存储管理器 (S3Manager)

- AWS S3 上传/下载
- 支持大文件分片上传
- 自动加密
- 路径管理

### 爬虫引擎 (Spider)

- 并发请求控制
- 请求重试机制
- Cookie 和 Session 管理
- User-Agent 轮换
- 请求限速

## ⚙️ 配置说明

主要配置在 `config.yaml` 文件中：

```yaml
proxy:
  enabled: true
  pool_type: "file"  # file, api, redis
  max_fails: 3

database:
  type: "mongodb"  # mysql, mongodb, sqlite
  mongodb:
    host: "localhost"
    port: 27017
    database: "crawler_db"

s3:
  enabled: true
  bucket_name: "your-bucket"
  region_name: "us-east-1"

crawler:
  concurrency: 5
  timeout: 30
  max_retries: 3
```

## 📖 示例

查看 `examples/` 目录获取更多示例：

- `basic_example.py` - 基础爬虫示例
- `proxy_example.py` - 使用代理的示例
- `database_example.py` - 数据库存储示例
- `s3_example.py` - S3 存储示例
- `async_example.py` - 异步爬虫示例

## 🧪 测试

```bash
# 运行测试
make test

# 测试覆盖率
make test-cov
```

## 🔍 代码质量检查

项目配置了完整的静态检查和lint工具：

### 快速开始

```bash
# 安装开发依赖（包含lint工具）
make install-dev

# 运行所有检查
make check

# 自动格式化代码
make format
```

### 可用命令

| 命令 | 说明 |
|------|------|
| `make lint` | 运行ruff和flake8检查 |
| `make type-check` | 运行mypy类型检查 |
| `make check` | 运行所有检查（lint + type-check） |
| `make format` | 自动格式化代码（black + isort + ruff） |
| `make test` | 运行测试 |
| `make test-cov` | 运行测试并生成覆盖率报告 |
| `make clean` | 清理临时文件和缓存 |

### 使用Pre-commit（推荐）

```bash
# 安装pre-commit hooks（首次设置）
make pre-commit-install

# 手动运行所有文件的检查
make pre-commit-run
```

安装后，每次git commit时会自动运行代码检查和格式化。

### 详细说明

查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解完整的代码质量标准和开发流程。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

在提交代码前，请：
1. 运行 `make format` 格式化代码
2. 运行 `make check` 确保通过所有检查
3. 运行 `make test` 确保测试通过

详细指南请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 许可证

MIT License

## 📮 联系

如有问题，请提交 Issue 或联系维护者。

---

Made with ❤️ by Your Name
