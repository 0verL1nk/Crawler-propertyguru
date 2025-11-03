# 爬虫框架 (Crawler Framework)

一个安全、高效的 Python 爬虫框架，支持代理IP管理、多种数据库存储和 S3 云存储。

## ✨ 特性

- 🚀 **高性能**: 支持异步请求和并发控制
- 🔒 **安全可靠**: 动态住宅代理（自动IP轮换）、请求重试、错误处理
- 🌐 **远程浏览器**: 支持Bright Data Scraping Browser，可处理JS渲染、验证码
- 💾 **多种存储**: 支持 MySQL、MongoDB、Redis 和 AWS S3
- 📊 **数据处理**: 集成数据清洗和结构化处理
- 🔐 **SSL支持**: 支持SSL证书配置（Bright Data代理必需）
- 📝 **日志记录**: 完善的日志系统，支持文件轮转
- ⚙️ **灵活配置**: YAML配置文件，环境变量支持

## 📦 安装

### 使用 uv (推荐)

```bash
# 克隆项目
git clone <your-repo-url>
cd crawler-framework

# 使用 uv 安装依赖
uv sync

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 使用 pip

```bash
pip install -r requirements.txt
```

## 🚀 快速开始

### 1. 配置环境

复制 `env.example` 为 `.env` 并填写配置：

```bash
cp env.example .env
```

编辑 `.env` 文件，配置代理和其他服务：

```bash
# 动态住宅代理（推荐用于批量爬取）
PROXY_URL=http://brd-customer-xxx:password@brd.superproxy.io:33335

# 图片去水印API配置（可选）
WATERMARK_REMOVER_PRODUCT_SERIAL=your_serial
WATERMARK_REMOVER_PRODUCT_CODE=067003

# 数据库配置（可选）
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

### 3. 编写爬虫

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

### 4. 运行示例

```bash
# 运行基础示例
uv run python examples/basic_example.py

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

