# PostgreSQL 快速切换指南

## 📌 问题说明

你的爬虫提示 "MySQL SSL 连接已启用"，但你已经设置了 PostgreSQL。这是因为 `.env` 文件中的 `DB_TYPE` 配置可能不正确。

## ✅ 解决步骤

### 1. 检查 `.env` 配置

确保 `.env` 文件中设置了正确的数据库类型：

```bash
# ========== 数据库配置 ==========
DB_TYPE=postgresql  # ⚠️ 必须设置为 postgresql

# PostgreSQL 配置（本地或云端）
POSTGRESQL_URI=postgresql://username:password@host:port/database

# 或者使用 Supabase（也是 PostgreSQL）
# DB_TYPE=postgresql
# POSTGRESQL_URI=postgresql://postgres.xxx:password@aws-*.pooler.supabase.com:5432/postgres
```

### 2. 注释掉 MySQL 配置（可选）

如果不再使用 MySQL，可以注释掉相关配置：

```bash
# MySQL 配置（已停用）
# MYSQL_HOST=localhost
# MYSQL_PORT=3306
# MYSQL_USER=root
# MYSQL_PASSWORD=password
# MYSQL_DATABASE=property_db
```

### 3. 运行测试

```bash
cd /home/ling/Crawler/propertyguru
uv run python main.py --test-single
```

你应该看到类似这样的输出：

```
2025-11-07 17:15:42 | INFO | crawler.database_factory:get_database:XXX - SQL 数据库已初始化: postgresql
2025-11-07 17:15:42 | DEBUG | crawler.db_operations:__init__:42 - 使用新的 SQL 数据库接口: postgresql
```

## 📋 完整的 `.env` PostgreSQL 配置示例

### 方式1：本地 PostgreSQL

```bash
# 数据库类型
DB_TYPE=postgresql

# PostgreSQL 连接（方式1：完整URI）
POSTGRESQL_URI=postgresql://postgres:your_password@localhost:5432/property_data

# 或者使用分开的配置（方式2）
# PG_HOST=localhost
# PG_PORT=5432
# PG_USER=postgres
# PG_PASSWORD=your_password
# PG_DATABASE=property_data
# PG_SSL_MODE=prefer

# 地理编码
ENABLE_GEOCODING=true
```

### 方式2：Supabase（推荐连接池）

```bash
# 数据库类型
DB_TYPE=postgresql

# Supabase Connection Pooling (推荐，支持 IPv4/IPv6)
POSTGRESQL_URI=postgresql://postgres.rlfsvixfbyauygglwsoi:[YOUR-PASSWORD]@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres

# ⚠️ 不推荐：Direct Connection (仅IPv6)
# POSTGRESQL_URI=postgresql://postgres.rlfsvixfbyauygglwsoi:[YOUR-PASSWORD]@db.rlfsvixfbyauygglwsoi.supabase.co:5432/postgres

# 地理编码
ENABLE_GEOCODING=true
```

## 🔍 验证数据库连接

### 测试连接

```bash
cd /home/ling/Crawler/propertyguru
uv run python -c "
from crawler.database_factory import get_database

db = get_database()
print(f'数据库类型: {db.db_type}')
print('连接测试...')
if db.test_connection():
    print('✅ 连接成功！')
else:
    print('❌ 连接失败')
"
```

### 检查表结构

```bash
# 连接到 PostgreSQL
psql -U postgres -d property_data

# 查看所有表
\dt

# 应该看到：
#  listing_info
#  listing_media
#  search_logs
#  user_feedback

# 查看 listing_info 表结构
\d listing_info

# 退出
\q
```

## 🚀 初始化数据库（如果还没有）

### 1. 创建数据库

```bash
# 本地 PostgreSQL
createdb -U postgres property_data

# 或者在 psql 中
psql -U postgres
CREATE DATABASE property_data;
\q
```

### 2. 执行初始化脚本

```bash
cd /home/ling/Crawler/propertyguru
psql -U postgres -d property_data -f sql/init_postgresql_unified.sql
```

### 3. Supabase 用户

1. 打开 Supabase Dashboard
2. 进入 **SQL Editor**
3. 粘贴 `sql/init_postgresql_unified.sql` 的内容
4. 点击 **Run** 执行

## 📊 两个项目共用数据库

爬虫和搜索引擎项目现在使用同一个 PostgreSQL 数据库：

```
PostgreSQL 数据库 (property_data)
├── 核心数据表（爬虫写入，搜索引擎读取）
│   ├── listing_info          # 房源信息 + AI 嵌入
│   └── listing_media         # 多媒体资源
│
└── 搜索引擎专用表（搜索引擎写入）
    ├── search_logs           # 搜索日志
    └── user_feedback         # 用户反馈
```

### 配置示例

**爬虫项目 `.env`:**
```bash
DB_TYPE=postgresql
POSTGRESQL_URI=postgresql://postgres:password@localhost:5432/property_data
```

**搜索引擎项目 `config.env`:**
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/property_data
```

## ❓ 常见问题

### Q1: 提示 "MySQL SSL 连接已启用"

**原因：** `.env` 中 `DB_TYPE` 未设置或设置错误

**解决：**
```bash
# 检查 .env 文件
grep DB_TYPE .env

# 应该是：
# DB_TYPE=postgresql

# 如果是空的或者是 mysql，修改为 postgresql
```

### Q2: 提示 "module 'psycopg2' has no attribute '__version__'"

**原因：** 缺少 PostgreSQL 驱动

**解决：**
```bash
uv add psycopg2-binary
```

### Q3: Supabase 连接超时

**原因：** 使用了只支持 IPv6 的 Direct Connection

**解决：** 切换到 Connection Pooling
```bash
# ✅ 正确（Connection Pooling）
POSTGRESQL_URI=postgresql://postgres.xxx:pass@aws-*.pooler.supabase.com:5432/postgres

# ❌ 错误（Direct Connection，IPv6-only）
# POSTGRESQL_URI=postgresql://postgres.xxx:pass@db.xxx.supabase.co:5432/postgres
```

### Q4: 如何从 MySQL 迁移到 PostgreSQL

```bash
# 1. 备份 MySQL 数据
mysqldump -u root -p property_db > mysql_backup.sql

# 2. 使用工具转换（推荐使用 pgloader）
pgloader mysql://user:pass@localhost/property_db postgresql://postgres:pass@localhost/property_data

# 3. 或者使用爬虫重新爬取（推荐）
uv run python main.py --reset-progress
uv run python main.py 1 100
```

## 📚 相关文档

- [统一数据库架构](UNIFIED_DATABASE.md)
- [数据库使用指南](DATABASE_USAGE.md)
- [Supabase 快速开始](SUPABASE_QUICKSTART.md)

---

**现在运行测试：**

```bash
cd /home/ling/Crawler/propertyguru
uv run python main.py --test-single
```

如果看到 "SQL 数据库已初始化: postgresql"，恭喜你切换成功！🎉
