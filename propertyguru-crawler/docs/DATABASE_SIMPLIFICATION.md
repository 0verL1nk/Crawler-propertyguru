# 数据库配置简化说明

## 📝 变更概述

根据用户反馈："supabase也是pgsql,不用单独列出来"，我们简化了数据库配置：

- ✅ **移除** `DB_TYPE=supabase` 选项
- ✅ **统一** 使用 `DB_TYPE=postgresql` 配置所有 PostgreSQL 变体
- ✅ **保留** Supabase IPv6 警告（自动检测直连地址）
- ✅ **向后兼容** 如果使用 `DB_TYPE=supabase` 会自动转换为 `postgresql` 并警告

## 🔄 迁移指南

### 旧配置（已废弃）

```bash
DB_TYPE=supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_PASSWORD=your_password
```

### 新配置（推荐）

```bash
DB_TYPE=postgresql
POSTGRESQL_URI=postgresql://postgres.xxx:password@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres
```

## 💡 核心原理

Supabase 本质就是托管的 PostgreSQL 服务，使用标准 PostgreSQL 协议连接。

- **相同点：**
  - 使用相同的 PostgreSQL 驱动（psycopg2）
  - 使用相同的 SQLAlchemy ORM
  - 使用相同的 SQL 语法
  - 使用相同的连接池配置

- **唯一区别：**
  - 连接字符串不同（主机名不同）
  - Supabase 提供额外的 REST API、Auth 等功能（爬虫用不到）

## ⚠️ 重要提醒：IPv4 vs IPv6

Supabase 有两种连接方式：

| 连接方式 | 主机名 | IPv4 | IPv6 | 推荐 |
|---------|--------|------|------|------|
| **Connection Pooling** | `aws-*.pooler.supabase.com` | ✅ | ✅ | **推荐** |
| Direct Connection | `db.*.supabase.co` | ❌ | ✅ | 不推荐 |

**必须使用 Connection Pooling 连接！** 直连仅支持 IPv6，大多数环境无法连接。

## 🛠️ 自动检测

代码会自动检测 Supabase 直连地址并警告：

```python
# 如果检测到这种 URI：
# postgresql://...@db.xxx.supabase.co:5432/postgres

# 会输出警告：
⚠️ 警告：检测到 Supabase 直连地址 (db.*.supabase.co)
   直连仅支持 IPv6，大多数 IPv4 环境无法连接
   建议改用连接池地址：aws-*.pooler.supabase.com
```

## 📊 支持的 PostgreSQL 变体

使用 `DB_TYPE=postgresql` 可以连接：

- ✅ 本地 PostgreSQL
- ✅ Docker PostgreSQL
- ✅ Supabase
- ✅ AWS RDS PostgreSQL
- ✅ Azure Database for PostgreSQL
- ✅ Google Cloud SQL PostgreSQL
- ✅ DigitalOcean Managed PostgreSQL
- ✅ Heroku Postgres
- ✅ 任何兼容 PostgreSQL 的数据库

## 🚀 快速配置

### 方式1：使用完整 URI（最简单）

```bash
DB_TYPE=postgresql
POSTGRESQL_URI=<从 Supabase Dashboard 复制的连接字符串>
```

### 方式2：分项配置

```bash
DB_TYPE=postgresql
PG_HOST=aws-1-ap-southeast-2.pooler.supabase.com
PG_PORT=5432
PG_USER=postgres.rlfsvixfbyauygglwsoi
PG_PASSWORD=your_password
PG_DATABASE=postgres
PG_SSL_MODE=require
```

## 📚 相关文档

- [数据库使用指南](DATABASE_USAGE.md)
- [Supabase 快速开始](SUPABASE_QUICKSTART.md)
- [数据库重构总结](DATABASE_REFACTORING.md)

## ✅ 兼容性保证

- 现有使用 `DB_TYPE=supabase` 的配置会自动转换为 `postgresql`
- 输出友好的警告信息
- 无需修改代码即可继续使用

---

**总结：** Supabase 就是 PostgreSQL，用 PostgreSQL 的方式配置即可！🎉
