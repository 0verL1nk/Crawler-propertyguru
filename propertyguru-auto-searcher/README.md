# 🏠 PropertyGuru 智能搜索引擎

基于 Golang + PostgreSQL + pgvector 构建的房产智能搜索系统，支持自然语言查询和语义检索。

> **🚀 快速开始**: 想要快速部署？查看 [QUICKSTART.md](./QUICKSTART.md) | 完整 Docker 文档见 [DOCKER.md](./DOCKER.md)

## ✨ 特性

- **🤖 AI 语义理解**: 使用 OpenAI GPT 进行自然语言理解，支持复杂查询意图解析
- **🔍 智能搜索**: 结合 SQL 精确过滤和 PostgreSQL 全文检索
- **🎯 结构化验证**: 使用严格的数据结构验证 AI 返回结果，确保查询准确性
- **📊 混合排序**: 综合文本相关度、价格匹配度、新鲜度的智能排序
- **⚡ 高性能**: Go 并发处理 + 数据库索引优化
- **🧠 向量检索**: 支持 embedding 向量相似度搜索（可选）
- **📱 现代化 UI**: 响应式 Web 界面，支持移动端

## 🏗️ 架构

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   前端 UI    │ ──→ │  Golang API  │ ──→ │ PostgreSQL  │
│ (HTML+JS)   │      │   (Gin)      │      │ + pgvector  │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ↓
                    ┌────────────────┐
                    │  OpenAI GPT    │ ──→ 意图解析（AI）
                    │  PostgreSQL    │ ──→ 全文检索
                    │  Ranking       │ ──→ 混合排序
                    │  Validation    │ ──→ 结果验证
                    └────────────────┘
```

## 📋 前置条件

- **Go**: 1.21+
- **PostgreSQL**: 14+
- **pgvector**: 最新版本
- **OpenAI API Key**: 用于 AI 意图解析（必需）
- **系统**: Linux/MacOS/WSL2

## 🚀 快速开始

### 🐳 方式 1: Docker 部署（推荐）

使用 Docker Compose 一键启动所有服务（包括 PostgreSQL）：

```bash
# 1. 进入项目目录
cd propertyguru-auto-searcher

# 2. 启动所有服务
docker compose up -d

# 3. 查看日志
docker compose logs -f searcher

# 4. 访问服务
# Web UI: http://localhost:8080
# API: http://localhost:8080/api/v1
```

**详细 Docker 部署文档请查看**: [DOCKER.md](./DOCKER.md)

---

### 🔧 方式 2: 本地开发部署

### 1. 安装 PostgreSQL 和 pgvector

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# 安装 pgvector
sudo apt install postgresql-14-pgvector

# 或从源码编译
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 2. 初始化数据库

⚠️ **重要：本搜索引擎与爬虫项目共用同一个数据库**

- 爬虫项目：写入 `listing_info`, `listing_media`
- 搜索引擎：读取 `listing_info`，写入 `search_logs`, `user_feedback`

```bash
# 方式1：使用统一初始化脚本（推荐）
cd ../propertyguru
psql -U postgres -d postgres -f sql/init_postgresql_unified.sql

# 方式2：如果需要独立数据库（不推荐）
sudo -u postgres psql
CREATE USER property_user WITH PASSWORD 'your_password';
CREATE DATABASE property_search OWNER property_user;
GRANT ALL PRIVILEGES ON DATABASE property_search TO property_user;
\q

# 使用统一脚本初始化
psql -U property_user -d property_search -f ../propertyguru/sql/init_postgresql_unified.sql
```

**Supabase 用户：**
在 Supabase SQL Editor 中执行 `../propertyguru/sql/init_postgresql_unified.sql` 的内容即可

### 3. 配置环境变量

```bash
# 复制配置文件
cp config.example.env .env

# 编辑配置
vim .env
```

关键配置项：

```bash
# PostgreSQL
# 方式1：使用完整的数据库连接URL（推荐，优先级最高）
DATABASE_URL=postgresql://property_user:password@localhost:5432/property_search?sslmode=disable
# 或使用别名：
# POSTGRESQL_URI=postgresql://property_user:password@localhost:5432/property_search?sslmode=disable
# PG_DSN=postgresql://property_user:password@localhost:5432/property_search?sslmode=disable

# 方式2：分别配置各项（如果没有设置 DATABASE_URL，则使用以下配置）
# PG_HOST=localhost
# PG_PORT=5432
# PG_USER=property_user
# PG_PASSWORD=your_password
# PG_DATABASE=property_search
# PG_SSLMODE=disable

# OpenAI (必需 - 用于 AI 意图解析)
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1        # 或使用兼容的 API 端点
OPENAI_CHAT_MODEL=gpt-3.5-turbo                  # 聊天/意图解析模型
OPENAI_EMBEDDING_MODEL=text-embedding-3-small    # Embedding 模型
OPENAI_EMBEDDING_DIMENSIONS=1536
OPENAI_BATCH_SIZE=100
OPENAI_TIMEOUT=30

# Server
SERVER_PORT=8080

# 排序权重
RANK_WEIGHT_TEXT=0.5      # 文本相关度权重
RANK_WEIGHT_PRICE=0.3     # 价格匹配度权重
RANK_WEIGHT_RECENCY=0.2   # 新鲜度权重
```

> ⚠️ **重要**: `OPENAI_API_KEY` 是必需的，否则 AI 意图解析将不工作。
> 支持 OpenAI 官方 API 或任何兼容 OpenAI 格式的 API（如 Azure OpenAI、本地部署等）。

### 4. 安装依赖并运行

```bash
# 安装 Go 依赖
go mod download

# 运行服务
go run cmd/server/main.go
```

服务将在 `http://localhost:8080` 启动。

### 5. 访问Web界面

打开浏览器访问: `http://localhost:8080`

## 📡 API 文档

### 搜索接口

**POST** `/api/v1/search`

**请求体:**

```json
{
  "query": "我想找靠近地铁的三房公寓，预算120万以内",
  "filters": {
    "price_max": 1200000,
    "bedrooms": 3,
    "unit_type": "Condo",
    "mrt_distance_max": 1000
  },
  "options": {
    "top_k": 20,
    "offset": 0,
    "semantic": true
  }
}
```

**响应:**

```json
{
  "results": [
    {
      "listing_id": 60157325,
      "title": "619D Punggol Drive",
      "price": 1150000,
      "bedrooms": 3,
      "location": "Punggol",
      "mrt_station": "PE6 Oasis LRT",
      "mrt_distance_m": 500,
      "score": 0.92,
      "matched_reasons": ["三房", "靠近地铁", "价格符合"]
    }
  ],
  "total": 45,
  "intent": {
    "slots": {
      "price_max": 1200000,
      "bedrooms": 3,
      "mrt_distance_max": 1000
    },
    "semantic_keywords": ["靠近地铁", "公寓"],
    "confidence": 0.85
  },
  "took_ms": 125
}
```

### 获取房源详情

**GET** `/api/v1/listings/:id`

**响应:** 单个房源的完整信息

### Embedding 批量更新

**POST** `/api/v1/embeddings/batch`

用于批量更新房源的向量嵌入（Phase 2）。

**请求体:**

```json
{
  "embeddings": [
    {
      "listing_id": 60157325,
      "embedding": [0.1, 0.2, ..., 0.3],  // 1536维向量
      "text": "combined text for embedding"
    }
  ]
}
```

### 用户反馈

**POST** `/api/v1/feedback`

记录用户行为（点击、联系等）。

```json
{
  "search_id": "uuid",
  "listing_id": 60157325,
  "action": "click"
}
```

## 🔧 项目结构

```
propertyguru-auto-searcher/
├── cmd/
│   └── server/
│       └── main.go              # 服务入口
├── internal/
│   ├── config/
│   │   └── config.go            # 配置管理
│   ├── handler/
│   │   ├── search.go            # 搜索接口
│   │   ├── embedding.go         # Embedding 接口
│   │   └── feedback.go          # 反馈接口
│   ├── service/
│   │   ├── openai.go            # OpenAI 客户端（AI 意图解析）
│   │   ├── intent.go            # 意图解析服务
│   │   ├── search.go            # 搜索服务
│   │   └── ranker.go            # 排序服务
│   ├── model/
│   │   ├── listing.go           # 房源数据模型
│   │   ├── query.go             # 查询模型
│   │   └── intent.go            # 意图模型
│   └── repository/
│       └── postgres.go          # 数据库操作
├── web/
│   ├── index.html               # 前端页面
│   └── static/
│       ├── css/
│       └── js/
│           └── app.js           # 前端逻辑
├── sql/
│   └── init.sql                 # 数据库初始化脚本
├── go.mod
├── go.sum
├── config.example.env           # 配置示例
└── README.md
```

## 🎯 使用示例

### 自然语言查询示例

1. **简单查询**:
   ```
   3 bedroom condo in Punggol under 1.5M
   ```
   AI 解析: `{bedrooms: 3, unit_type: "Condo", location: "Punggol", price_max: 1500000}`

2. **复杂需求**:
   ```
   HDB near MRT with good view and spacious layout
   ```
   AI 解析: `{unit_type: "HDB", mrt_distance_max: 1000, keywords: ["view", "spacious"]}`

3. **多条件组合**:
   ```
   Landed property in Bukit Timah, 4 bed 3 bath, modern
   ```
   AI 解析: `{unit_type: "Landed", location: "Bukit Timah", bedrooms: 4, bathrooms: 3, keywords: ["modern"]}`

4. **价格区间**:
   ```
   New condo near Orchard, budget 2M max
   ```
   AI 解析: `{unit_type: "Condo", location: "Orchard", price_max: 2000000, build_year_min: 2015}`

### AI 意图解析能力

使用 **OpenAI GPT** 进行语义理解，自动提取结构化字段：

- **价格范围**: 支持 "$1.5M", "1500000", "1.5 million" 等多种格式
- **房间数量**: 自动识别 "3 bedroom", "3 bed", "三房" 等表达
- **房型枚举**: 严格验证为 `HDB | Condo | Landed | Executive`
- **地理位置**: 识别新加坡所有地区名称
- **MRT 距离**: 自动推断 "near MRT" 为 1000米，支持精确距离
- **语义关键词**: 提取 "spacious", "view", "modern" 等描述性关键词
- **数据验证**: 严格的结构体验证，确保字段类型和范围正确

> ✨ **AI 优势**: 无需维护复杂的正则表达式，支持自然表达，理解上下文和语义

## 🔄 与爬虫项目集成

本搜索引擎直接使用爬虫项目的数据库。集成步骤：

### 1. 修改爬虫项目配置

在爬虫项目的 `propertyguru/config.yaml` 中配置 PostgreSQL：

```yaml
database:
  type: "postgresql"
  
  postgresql:
    host: "localhost"
    port: 5432
    database: "property_search"
    username: "property_user"
    password: "your_password"
```

### 2. 爬虫数据写入

爬虫项目会自动将数据写入 PostgreSQL 的 `listing_info` 和 `listing_media` 表。搜索引擎直接读取这些表进行查询。

## 📊 性能优化

### 数据库索引

已创建的索引：

```sql
-- 搜索条件索引
CREATE INDEX idx_price ON listings(price);
CREATE INDEX idx_bedrooms ON listings(bedrooms);
CREATE INDEX idx_mrt_distance ON listings(mrt_distance_m);
CREATE INDEX idx_unit_type ON listings(unit_type);

-- 全文检索索引
CREATE INDEX idx_tsv ON listings USING GIN(tsv);

-- 向量索引（Phase 2）
CREATE INDEX idx_embedding ON listings 
USING hnsw (embedding vector_cosine_ops);
```

### 查询优化

- 使用参数化查询防止 SQL 注入
- 批量操作减少数据库往返
- 异步日志记录不阻塞主流程
- 连接池复用数据库连接

## 🚧 Phase 2 扩展计划

1. **向量检索**: 
   - 集成 OpenAI Embeddings
   - 实现语义相似度搜索
   - 混合检索（SQL + Vector）

2. **Learning-to-Rank**:
   - 收集搜索日志
   - 训练排序模型
   - A/B 测试优化

3. **RAG 推荐理由**:
   - LLM 生成推荐解释
   - 多房源对比分析

4. **个性化推荐**:
   - 用户行为分析
   - 协同过滤推荐

## 🎯 Makefile 快捷命令

项目提供了 Makefile 来简化 Docker 操作：

```bash
# 查看所有可用命令
make help

# 常用命令
make build          # 构建镜像
make up             # 启动服务
make down           # 停止服务
make logs           # 查看日志
make test           # 测试 API
make shell          # 进入容器
make db-shell       # 进入数据库
make db-backup      # 备份数据库
```

## 🐛 故障排除

### PostgreSQL 连接失败

```bash
# 检查 PostgreSQL 服务状态
sudo systemctl status postgresql

# 检查端口
sudo netstat -tlnp | grep 5432

# 测试连接
psql -U property_user -d property_search -h localhost
```

### pgvector 扩展未安装

```sql
-- 检查扩展
SELECT * FROM pg_available_extensions WHERE name = 'vector';

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS vector;
```

### Go 依赖问题

```bash
# 清理缓存
go clean -modcache

# 重新下载
go mod download

# 更新依赖
go mod tidy
```

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题，请通过 Issue 反馈。

