# PropertyGuru 系统部署指南（面向新手）

本指南旨在帮助新手用户快速部署 PropertyGuru 爬虫和搜索引擎系统。根据您的偏好，我们将介绍：
- 爬虫：本地部署（不使用Docker）
- 搜索引擎：Docker部署（推荐）

## 系统要求

### 硬件要求
- **CPU**: 至少 2 核
- **内存**: 至少 4GB RAM（推荐 8GB）
- **存储**: 至少 20GB 可用磁盘空间
- **网络**: 稳定的互联网连接

### 操作系统
- **Linux**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **macOS**: 10.15+ (Intel 或 Apple Silicon)
- **Windows**: Windows 10+ with WSL2 (推荐)

## 第一部分：搜索引擎部署（Docker部署 - 推荐）

搜索引擎包含 Web UI 和 API 服务，以及 PostgreSQL 数据库。使用Docker部署是最简单的方式。

### 1. 安装 Docker 和 Docker Compose

#### Ubuntu/Debian
```bash
# 更新包索引
sudo apt update

# 安装必要的包
sudo apt install apt-transport-https ca-certificates curl gnupg lsb-release

# 添加 Docker 官方 GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 仓库
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io

# 安装 Docker Compose
sudo apt install docker-compose-plugin

# 验证安装
docker --version
docker compose version
```

#### macOS
```bash
# 使用 Homebrew 安装
brew install --cask docker

# 启动 Docker Desktop 应用程序
# 然后在终端中验证
docker --version
docker compose version
```

#### Windows (WSL2)
1. 安装 WSL2: https://docs.microsoft.com/en-us/windows/wsl/install
2. 安装 Docker Desktop: https://docs.docker.com/desktop/windows/install/

### 2. 克隆项目代码

```bash
# 安装 git（如果尚未安装）
sudo apt install git  # Ubuntu/Debian
# 或
brew install git      # macOS

# 克隆项目
git clone https://github.com/0verL1nk/Crawler-propertyguru.git
cd Crawler-propertyguru
```
- 如果直接下载了zip,解压后进入项目也是一样的
### 3. 部署搜索引擎

在部署搜索引擎之前，请确保正确配置环境变量，特别是OpenAI API密钥。

```bash
# 进入搜索引擎目录
cd propertyguru-auto-searcher

# 配置环境变量（重要！）
cp config.example.env .env
# 编辑 .env 文件，设置 OpenAI API 密钥和其他配置
# 至少需要设置 OPENAI_API_KEY=sk-your-api-key-here还有数据库DATABASE_URL
# 注意：Docker部署会使用docker-compose.yml中的环境变量，但.env文件中的配置会覆盖默认值

docker build -t propertyguru-auto-searcher .

docker run -d --name propertyguru-auto-searcher\
  -e DATABASE_URL="database_url" \
  -e OPENAI_API_KEY=api_key \
  -e OPENAI_API_BASE=base_url \
  -e OPENAI_CHAT_MODEL=model_name \
  -p 8080:8080 \
  propertyguru-auto-searcher
```

服务启动后，可以通过以下地址访问：
- **Web UI**: http://localhost:8080
- **API**: http://localhost:8080/api/v1
- **数据库**: localhost:5432

## 第二部分：爬虫部署（本地部署）

爬虫用于从 PropertyGuru 网站抓取数据并存储到数据库中。我们推荐使用本地部署方式。

### 1. 安装系统依赖

#### Ubuntu/Debian
```bash
# 更新包索引
sudo apt update

# 安装基础依赖
sudo apt install -y \
  wget curl git unzip software-properties-common \
  build-essential xvfb x11-xkb-utils \
  xfonts-100dpi xfonts-75dpi xfonts-scalable xfonts-base

# 安装 Python 3.10+
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# 安装 Chrome 浏览器
wget -q -O /tmp/google-chrome-stable_current_amd64.deb \
  https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y /tmp/google-chrome-stable_current_amd64.deb
rm /tmp/google-chrome-stable_current_amd64.deb
```

#### macOS
```bash
# 安装 Homebrew（如果尚未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装依赖
brew install python@3.10

# 安装 Chrome 浏览器
brew install --cask google-chrome
```

### 2. 部署爬虫

项目提供了自动安装脚本setup.sh，可以自动安装所有依赖和配置环境：

```bash
# 进入爬虫目录
cd ../propertyguru-crawler

# 复制并配置环境变量（重要！）
cp env.example .env
# 编辑 .env 文件，至少配置以下必填项：
# 1. 数据库连接信息（POSTGRESQL_URI 或 PG_* 系列配置）
# 2. 浏览器配置（BROWSER_TYPE 等）
# 3. HTTP爬虫配置（USE_HTTP_CRAWLER 等）

# 运行自动安装脚本
./setup.sh

# 脚本会自动完成以下操作：
# 1. 检查系统类型和Python版本
# 2. 安装系统依赖（Chrome浏览器、Xvfb等）
# 3. 安装uv包管理器
# 4. 安装Python依赖
# 5. 配置环境变量
# 6. 创建必要的目录
# 7. 测试安装是否成功

# 运行测试
uv run python main.py --test-single
```

如果自动安装脚本无法使用，也可以手动安装：

```bash
# 复制并配置环境变量（重要！）
cp env.example .env
# 编辑 .env 文件，至少配置以下必填项：
# 1. 数据库连接信息（POSTGRESQL_URI 或 PG_* 系列配置）
# 2. 浏览器配置（BROWSER_TYPE 等）
# 3. HTTP爬虫配置（USE_HTTP_CRAWLER 等）,注意选择一个供应商,推荐scraperAPI
# 安装 uv 包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync

# 安装额外依赖
uv pip install pyvirtualdisplay

# 运行测试
uv run python main.py --test-single
```

## 配置说明

### 数据库配置

无论使用哪种部署方式，都需要正确配置数据库连接信息：

```bash
# PostgreSQL 连接信息（连接到搜索引擎的数据库）
POSTGRESQL_URI=postgresql://property_user:property_password@localhost:5432/property_search?sslmode=true

# 或分别配置
PG_HOST=localhost
PG_PORT=5432
PG_USER=property_user
PG_PASSWORD=property_password
PG_DATABASE=property_search
PG_SSLMODE=disable
```

### 爬虫配置

爬虫需要配置代理和浏览器信息：

```bash
# 使用 HTTP 爬虫（推荐）
USE_HTTP_CRAWLER=true
USE_HTTP_DETAIL_CRAWLER=true

# 浏览器配置
BROWSER_TYPE=undetected
BROWSER_HEADLESS=false
BROWSER_USE_VIRTUAL_DISPLAY=true
BROWSER_DISABLE_IMAGES=true
```

### 搜索引擎配置

搜索引擎需要配置 OpenAI API 密钥：

```bash
# OpenAI Compatible API 配置
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_CHAT_MODEL=gpt-3.5-turbo
```

## 常见问题和故障排除

### 1. Docker 相关问题

#### 问题：Docker 权限不足
```bash
# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
# 然后注销并重新登录
```

#### 问题：端口被占用
```bash
# 查看占用端口的进程
sudo netstat -tlnp | grep :8080
sudo netstat -tlnp | grep :5432

# 杀死占用端口的进程
sudo kill -9 <PID>
```

### 2. 数据库相关问题

#### 问题：无法连接到数据库
```bash
# 检查 PostgreSQL 是否运行
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS

# 检查数据库连接
psql -U property_user -d property_search -h localhost -p 5432
```

#### 问题：pgvector 扩展未安装
```bash
# 安装 pgvector 扩展
sudo -u postgres psql -d property_search -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3. 爬虫相关问题

#### 问题：浏览器驱动未找到
```bash
# 安装 Chrome 浏览器
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
sudo apt-get install -f
```

#### 问题：代理配置错误
```bash
# 检查代理连接
curl -x http://your-proxy-host:port https://httpbin.org/ip
```

## 最佳实践和性能优化

### 1. 数据库优化

```bash
# 调整 PostgreSQL 配置
sudo nano /etc/postgresql/14/main/postgresql.conf

# 推荐设置
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

### 2. 爬虫性能优化

```bash
# 在 config.yaml 中调整并发设置
crawler:
  concurrency: 5        # 并发数
  timeout: 30          # 请求超时
  delay: 1             # 请求间隔
  random_delay: [0, 2] # 随机延迟范围
```

### 3. 搜索引擎优化

```bash
# 在 .env 中调整排序权重
RANK_WEIGHT_TEXT=0.5      # 文本相关度权重
RANK_WEIGHT_PRICE=0.3     # 价格匹配度权重
RANK_WEIGHT_RECENCY=0.2   # 新鲜度权重
```

## 验证部署

### 1. 检查服务状态

```bash
# Docker 部署（搜索引擎）
docker compose ps

# 本地部署（爬虫）
ps aux | grep "property"
```

### 2. 测试 API

```bash
# 测试搜索引擎健康检查
curl http://localhost:8080/health

# 测试搜索功能（需要先有数据）
curl -X POST http://localhost:8080/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "3 bedroom condo", "options": {"top_k": 5}}'
```

### 3. 检查数据库

```bash
# 连接到数据库
psql -U property_user -d property_search

# 检查表是否存在
\d

# 检查数据量
SELECT COUNT(*) FROM listing_info;
SELECT COUNT(*) FROM listing_media;
```

## 下一步

部署完成后，你可以：

1. **导入数据**: 使用爬虫项目导入房源数据
2. **测试搜索**: 尝试各种自然语言查询
3. **查看 Web UI**: 浏览前端界面
4. **配置监控**: 添加日志和性能监控
5. **生产部署**: 参考生产环境配置进行优化

恭喜你完成了 PropertyGuru 系统的部署！