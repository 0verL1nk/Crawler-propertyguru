# 统一数据库架构说明

## 📐 架构设计

爬虫项目和搜索引擎项目**共用同一个 PostgreSQL 数据库**，通过表分层实现职责分离：

```
PostgreSQL 数据库 (property_data)
│
├── 📝 核心数据表（爬虫写入，搜索引擎读取）
│   ├── listing_info          # 房源信息（含 AI 嵌入字段）
│   └── listing_media         # 多媒体资源
│
└── 🔍 搜索引擎专用表（搜索引擎写入）
    ├── search_logs           # 搜索日志
    └── user_feedback         # 用户反馈
```

## 🎯 为什么统一数据库？

### 优势

| 特性 | 分离数据库 | 统一数据库 ✅ |
|------|-----------|--------------|
| 数据一致性 | 需要同步脚本 | 实时一致 |
| 维护成本 | 高（两个库） | 低（一个库） |
| 数据冗余 | 有（需复制） | 无 |
| 搜索实时性 | 延迟（需同步） | 实时 |
| 部署复杂度 | 高 | 低 |

### 实际场景

```
爬虫: 新增/更新房源 → listing_info 表
       ↓ (实时)
搜索引擎: 读取最新房源 → 用户立即可搜索
```

## 📋 表结构详解

### 1. listing_info（核心表）

**职责划分：**
- **爬虫负责：** 基础字段（title, price, location...）
- **搜索引擎负责：** AI 字段（embedding, search_vector）

```sql
CREATE TABLE listing_info (
    -- 爬虫字段
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL UNIQUE,
    title VARCHAR(255),
    price DECIMAL(15,2),
    bedrooms INTEGER,
    location VARCHAR(255),
    ... (其他基础字段)
    is_completed BOOLEAN DEFAULT FALSE,  -- 爬虫状态

    -- 搜索引擎字段
    embedding vector(1536) DEFAULT NULL,  -- AI 向量嵌入
    search_vector tsvector,               -- 全文搜索向量

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. listing_media（爬虫专用）

```sql
CREATE TABLE listing_media (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL,
    media_type media_type_enum NOT NULL,
    media_url VARCHAR(500),
    ...
    FOREIGN KEY (listing_id) REFERENCES listing_info(listing_id)
);
```

### 3. search_logs（搜索引擎专用）

```sql
CREATE TABLE search_logs (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    filters JSONB,
    result_count INTEGER,
    duration_ms INTEGER,
    created_at TIMESTAMP
);
```

### 4. user_feedback（搜索引擎专用）

```sql
CREATE TABLE user_feedback (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL,
    feedback_type VARCHAR(20),  -- 'click', 'like', 'dislike'
    ...
    FOREIGN KEY (listing_id) REFERENCES listing_info(listing_id)
);
```

## 🚀 部署步骤

### 方式1：新建数据库（推荐）

```bash
# 1. 创建 PostgreSQL 数据库
createdb property_data

# 2. 执行统一初始化脚本
psql -d property_data -f sql/init_postgresql_unified.sql

# 3. 配置爬虫项目
# .env 文件
DB_TYPE=postgresql
POSTGRESQL_URI=postgresql://postgres:password@localhost:5432/property_data

# 4. 配置搜索引擎项目
# config.env 文件
DATABASE_URL=postgresql://postgres:password@localhost:5432/property_data
```

### 方式2：使用 Supabase

```bash
# 1. 在 Supabase Dashboard 创建项目

# 2. 进入 SQL Editor，粘贴 sql/init_postgresql_unified.sql 内容并执行

# 3. 获取连接字符串
# Settings → Database → Connection pooling

# 4. 配置两个项目使用同一个连接字符串
# 爬虫 .env
DB_TYPE=postgresql
POSTGRESQL_URI=postgresql://postgres.xxx:password@aws-*.pooler.supabase.com:5432/postgres

# 搜索引擎 config.env
DATABASE_URL=postgresql://postgres.xxx:password@aws-*.pooler.supabase.com:5432/postgres
```

## 🔄 工作流程

### 1. 爬虫写入数据

```python
# crawler/propertyguru_crawler.py
from crawler.database_factory import get_database
from crawler.orm_models import ListingInfoORM

db = get_database()  # 自动从 .env 读取配置

with db.get_session() as session:
    # 写入房源信息
    listing = ListingInfoORM(
        listing_id=12345,
        title="Beautiful Condo",
        price=1200000,
        bedrooms=3,
        location="Singapore",
        is_completed=True
    )
    session.add(listing)
    # 自动提交
```

### 2. 搜索引擎读取数据

```go
// propertyguru-auto-searcher/internal/repository/postgres.go
func (r *PostgresRepository) SearchListings(filters Filters) ([]Listing, error) {
    query := `
        SELECT id, listing_id, title, price, bedrooms, location, embedding
        FROM listing_info
        WHERE is_completed = true
          AND price BETWEEN $1 AND $2
        ORDER BY created_at DESC
        LIMIT $3
    `
    // ... 执行查询
}
```

### 3. 搜索引擎写入日志

```go
func (r *PostgresRepository) LogSearch(query string, resultIDs []int64) error {
    _, err := r.db.Exec(`
        INSERT INTO search_logs (query, result_ids, result_count, created_at)
        VALUES ($1, $2, $3, NOW())
    `, query, pq.Array(resultIDs), len(resultIDs))
    return err
}
```

## 📊 数据流向

```
用户 → 爬虫爬取数据
        ↓
    listing_info (写入)
        ↓
    触发器自动生成 search_vector
        ↓
    搜索引擎读取 (实时)
        ↓
    用户搜索
        ↓
    search_logs (写入)
        ↓
    用户点击/反馈
        ↓
    user_feedback (写入)
```

## 🛡️ 权限管理（可选）

如果需要更细粒度的权限控制：

```sql
-- 创建角色
CREATE ROLE crawler_role WITH LOGIN PASSWORD 'crawler_pass';
CREATE ROLE search_engine_role WITH LOGIN PASSWORD 'search_pass';

-- 爬虫角色：读写核心表
GRANT SELECT, INSERT, UPDATE ON listing_info TO crawler_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON listing_media TO crawler_role;

-- 搜索引擎角色：读核心表，写搜索表
GRANT SELECT ON listing_info TO search_engine_role;
GRANT SELECT ON listing_media TO search_engine_role;
GRANT SELECT, INSERT, UPDATE ON search_logs TO search_engine_role;
GRANT SELECT, INSERT, UPDATE ON user_feedback TO search_engine_role;
```

## 🔧 维护操作

### 查看数据库统计

```sql
-- 使用内置函数
SELECT * FROM get_database_stats();

-- 输出示例：
-- table_name      | row_count | table_size
-- ----------------+-----------+------------
-- listing_info    |     5000  | 2048 kB
-- listing_media   |    15000  | 5120 kB
-- search_logs     |     1000  | 256 kB
-- user_feedback   |      500  | 128 kB
```

### 查看摘要

```sql
-- 使用视图
SELECT * FROM listing_summary WHERE has_embedding = true LIMIT 10;

-- 查看热门搜索
SELECT * FROM popular_searches;
```

### 更新 Embedding

```python
# 批量更新 embedding
from crawler.database_factory import get_database
from crawler.orm_models import ListingInfoORM
import numpy as np

db = get_database()

with db.get_session() as session:
    # 获取没有 embedding 的房源
    listings = session.query(ListingInfoORM).filter(
        ListingInfoORM.embedding == None,
        ListingInfoORM.is_completed == True
    ).limit(100).all()

    for listing in listings:
        # 调用 OpenAI API 生成 embedding
        text = f"{listing.title} {listing.location} {listing.description}"
        embedding = get_embedding(text)  # 返回 1536 维向量

        # 更新 embedding 字段
        listing.embedding = embedding

    # 自动提交
```

### 清理旧数据

```sql
-- 清理30天前的搜索日志
DELETE FROM search_logs WHERE created_at < NOW() - INTERVAL '30 days';

-- 清理未完成的房源（超过7天）
DELETE FROM listing_info
WHERE is_completed = false
  AND created_at < NOW() - INTERVAL '7 days';
```

## ⚙️ 配置对比

### 爬虫项目配置 (.env)

```bash
# 数据库配置（PostgreSQL）
DB_TYPE=postgresql
POSTGRESQL_URI=postgresql://postgres:password@localhost:5432/property_data

# 或使用 Supabase
DB_TYPE=postgresql
POSTGRESQL_URI=postgresql://postgres.xxx:pass@aws-*.pooler.supabase.com:5432/postgres

# 地理编码
ENABLE_GEOCODING=true

# MongoDB（可选，用于原始数据）
MONGODB_URI=mongodb://localhost:27017/crawler_db
```

### 搜索引擎配置 (config.env)

```bash
# 数据库配置（同一个 PostgreSQL）
DATABASE_URL=postgresql://postgres:password@localhost:5432/property_data

# OpenAI API
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1

# 服务器配置
SERVER_PORT=8080
```

## 🎯 最佳实践

### 1. 数据隔离

虽然共用数据库，但遵循以下原则：

- ✅ 爬虫**只写**核心表（listing_info, listing_media）
- ✅ 搜索引擎**只读**核心表，**只写**搜索表
- ✅ 避免跨职责操作

### 2. 事务管理

```python
# 爬虫：使用事务确保数据一致性
with db.get_session() as session:
    # 插入房源
    listing = ListingInfoORM(...)
    session.add(listing)

    # 插入媒体
    for media in medias:
        media_obj = ListingMediaORM(listing_id=listing.listing_id, ...)
        session.add(media_obj)

    # 一起提交或回滚
```

### 3. 索引优化

统一脚本已包含所有必要索引：

- 基础索引（listing_id, price, bedrooms...）
- 向量索引（embedding - HNSW）
- 全文搜索索引（search_vector - GIN）
- 地理坐标索引（latitude, longitude）

### 4. 监控

```sql
-- 监控爬虫进度
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE is_completed = true) as completed,
    COUNT(*) FILTER (WHERE is_completed = false) as pending
FROM listing_info;

-- 监控搜索活跃度
SELECT
    DATE(created_at) as date,
    COUNT(*) as search_count,
    AVG(duration_ms) as avg_duration
FROM search_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

## 📚 相关文档

- [数据库使用指南](DATABASE_USAGE.md)
- [Supabase 快速开始](SUPABASE_QUICKSTART.md)
- [搜索引擎 README](../propertyguru-auto-searcher/README.md)

## ❓ 常见问题

**Q: 两个项目同时写入会冲突吗？**

A: 不会。爬虫写 `listing_info`，搜索引擎写 `search_logs`，表不同不冲突。

**Q: 如何处理 embedding 字段？**

A:
- 爬虫不管 embedding，默认 NULL
- 搜索引擎后台脚本批量更新 embedding
- 或者在爬虫中集成 embedding 生成

**Q: 性能会受影响吗？**

A: 不会。PostgreSQL 支持高并发，且：
- 爬虫主要写操作
- 搜索引擎主要读操作
- 读写分离，互不影响

**Q: 数据备份怎么办？**

A: 备份整个数据库即可：
```bash
pg_dump property_data > backup.sql
```

---

**总结：** 一个数据库，清晰分工，实时同步，简单高效！🎉
