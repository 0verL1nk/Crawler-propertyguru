# Supabase 快速配置指南

## 🚀 5分钟快速开始

Supabase 本质就是**托管的 PostgreSQL**，无需特殊 SDK，直接使用标准 PostgreSQL 连接即可！

## 📋 步骤1：创建 Supabase 项目

1. 访问 [supabase.com](https://supabase.com)
2. 注册/登录账号
3. 点击 "New Project"
4. 填写项目信息：
   - Name: `property-crawler`
   - Database Password: 设置一个强密码（**保存好这个密码！**）
   - Region: 选择 `Singapore (Southeast Asia)` 或最近的区域
5. 点击 "Create new project" 并等待初始化（约2分钟）

## 📋 步骤2：获取连接字符串

1. 项目创建完成后，进入项目
2. 点击左侧菜单 **Settings** → **Database**
3. 向下滚动到 **Connection String** 部分
4. ⚠️ **重要：选择连接方式**

### 连接方式对比

| 连接方式 | 主机名 | IPv4 | IPv6 | 推荐 |
|---------|--------|------|------|------|
| **Connection pooling** | `aws-*.pooler.supabase.com` | ✅ | ✅ | **推荐** |
| Direct connection | `db.*.supabase.co` | ❌ | ✅ | 不推荐 |

**结论：强烈推荐使用 "Connection pooling"（连接池），因为：**
- ✅ 支持 IPv4 和 IPv6
- ✅ 性能更好（内置连接池）
- ✅ 更稳定（自动重连）
- ✅ 适合爬虫等高并发场景

5. 选择 **"Connection pooling"** 标签
6. 模式选择 **"Session"**（推荐）或 **"Transaction"**
7. 复制连接字符串，格式类似：

```
postgresql://postgres.rlfsvixfbyauygglwsoi:[YOUR-PASSWORD]@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres
```

⚠️ **注意：**
- `[YOUR-PASSWORD]` 需要替换为步骤1设置的数据库密码
- 确保使用 `pooler.supabase.com`（不是 `supabase.co`）

## 📋 步骤3：配置爬虫

编辑爬虫项目的 `.env` 文件：

```bash
# 最简单的方式：直接使用 PostgreSQL 配置
DB_TYPE=postgresql
POSTGRESQL_URI=postgresql://postgres.rlfsvixfbyauygglwsoi:YOUR_PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres
```

**就这么简单！** ✅

## 📋 步骤4：初始化数据库表

运行 SQL 脚本创建表结构：

### 方式1：使用 Supabase Dashboard（推荐）

1. 在 Supabase Dashboard 点击左侧 **SQL Editor**
2. 点击 "New query"
3. 复制粘贴 `sql/init.sql` 的内容
4. 点击 "Run" 执行

### 方式2：使用命令行

```bash
# 安装 PostgreSQL 客户端（如果还没有）
# Ubuntu/Debian
sudo apt install postgresql-client

# macOS
brew install postgresql

# 连接并执行
psql "postgresql://postgres.rlfsvixfbyauygglwsoi:YOUR_PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres" -f sql/init.sql
```

## 📋 步骤5：测试连接

```python
from crawler.database_factory import get_database

# 创建数据库实例
db = get_database()

# 测试连接
if db.test_connection():
    print("✅ Supabase 连接成功！")
    print(f"数据库类型: {db.db_type}")
else:
    print("❌ 连接失败")

# 关闭连接
db.close()
```

## 🎯 完整配置示例

### .env 文件

```bash
# ===========================================
# Supabase 配置（推荐：最简单的方式）
# ===========================================
DB_TYPE=postgresql
POSTGRESQL_URI=postgresql://postgres.rlfsvixfbyauygglwsoi:YOUR_PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres

# 连接池配置（可选，默认值已足够）
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# 其他数据库配置...
# MongoDB 配置
MONGODB_URI=mongodb://localhost:27017/crawler_db

# 地理编码配置
ENABLE_GEOCODING=false
```

## 💡 使用技巧

### 1. 查看数据

在 Supabase Dashboard：
- 点击 **Table Editor**
- 选择 `listings` 表
- 可视化查看和编辑数据

### 2. 执行 SQL 查询

在 **SQL Editor** 中：

```sql
-- 查询前10条记录
SELECT * FROM listings LIMIT 10;

-- 统计房源数量
SELECT COUNT(*) FROM listings;

-- 查询价格最高的房源
SELECT listing_id, title, price
FROM listings
ORDER BY price DESC
LIMIT 10;
```

### 3. 设置 API 访问（可选）

Supabase 自动为你的表生成 RESTful API：

1. 进入 **Settings** → **API**
2. 复制 **URL** 和 **anon public** key
3. 可以通过 HTTP 请求访问数据

```bash
# 示例：获取房源列表
curl 'https://rlfsvixfbyauygglwsoi.supabase.co/rest/v1/listings?select=*&limit=10' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

### 4. 启用实时订阅（可选）

如果需要实时监听数据变化：

1. 进入 **Database** → **Replication**
2. 找到 `listings` 表
3. 点击开关启用 Replication

## 🔧 故障排查

### 连接超时

**问题：** 连接失败或超时

**解决：**
1. 检查密码是否正确
2. 确认项目区域（region）是否匹配
3. **检查是否使用了连接池（pooler）连接**：
   - ✅ 正确：`aws-1-ap-southeast-2.pooler.supabase.com` (支持 IPv4)
   - ❌ 错误：`db.xxxxx.supabase.co` (仅支持 IPv6)
4. 检查防火墙设置
5. 确保连接字符串完整

### IPv6 连接问题

**问题：** "Network is unreachable" 或 "Cannot assign requested address"

**原因：** Supabase 直连（Direct connection）仅支持 IPv6，但你的环境不支持 IPv6

**解决：** 使用连接池（Connection pooling）连接

```bash
# ❌ 错误：直连地址（仅 IPv6）
POSTGRESQL_URI=postgresql://...@db.xxxxx.supabase.co:5432/postgres

# ✅ 正确：连接池地址（IPv4 + IPv6）
POSTGRESQL_URI=postgresql://...@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres
```

### 检查 IPv6 支持

```bash
# 测试是否支持 IPv6
ping6 google.com

# 如果失败，必须使用连接池连接
```

### SSL 错误

**问题：** SSL 相关错误

**解决：** 确保连接字符串包含 `?sslmode=require`

```bash
# 正确格式（自动添加）
postgresql://...?sslmode=require
```

### 连接池满

**问题：** "too many connections"

**解决：** 调整连接池配置

```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

## 📊 免费额度

Supabase 免费层级包括：

- ✅ 500 MB 数据库存储
- ✅ 无限 API 请求
- ✅ 500 MB 文件存储
- ✅ 2 GB 带宽/月
- ✅ 500,000 Edge Function 调用
- ✅ 自动暂停（7天不活跃）

对于爬虫项目来说，**完全够用**！🎉

## 🚀 生产环境建议

### 1. 使用连接池

已默认启用（`pooler.supabase.com`）

### 2. 定期备份

Supabase 自动每日备份，但建议：

```bash
# 手动导出备份
pg_dump "postgresql://..." > backup_$(date +%Y%m%d).sql
```

### 3. 监控性能

在 Supabase Dashboard：
- **Reports** → **Database**
- 查看连接数、查询性能等

### 4. 索引优化

```sql
-- 为常用查询字段添加索引
CREATE INDEX idx_price ON listings(price);
CREATE INDEX idx_bedrooms ON listings(bedrooms);
CREATE INDEX idx_location ON listings(location);
```

## 🔄 从 MySQL 迁移数据

如果已有 MySQL 数据：

```python
from crawler.database_factory import get_database
from crawler.orm_models import ListingInfoORM

# 连接 MySQL
mysql_db = get_database(db_type='mysql')

# 连接 Supabase
pg_db = get_database(db_type='postgresql')

# 迁移数据
with mysql_db.get_session() as mysql_session:
    listings = mysql_session.query(ListingInfoORM).all()

    print(f"开始迁移 {len(listings)} 条记录...")

    with pg_db.get_session() as pg_session:
        for i, listing in enumerate(listings, 1):
            # 创建新对象
            new_listing = ListingInfoORM()
            for key, value in listing.__dict__.items():
                if not key.startswith('_'):
                    setattr(new_listing, key, value)

            pg_session.add(new_listing)

            if i % 100 == 0:
                print(f"已迁移 {i}/{len(listings)}")

    print("✅ 迁移完成！")
```

## 📚 相关文档

- [数据库使用指南](DATABASE_USAGE.md)
- [数据库重构总结](DATABASE_REFACTORING.md)
- [Supabase 官方文档](https://supabase.com/docs)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)

## ❓ 常见问题

**Q: Supabase 和普通 PostgreSQL 有什么区别？**

A: Supabase 就是托管的 PostgreSQL + 额外功能（API、Auth、Storage等）。对于爬虫，直接当 PostgreSQL 用即可。

**Q: 需要安装 Supabase Python SDK 吗？**

A: **不需要！** 直接用 SQLAlchemy ORM 即可，性能更好。

**Q: 免费额度够用吗？**

A: 对于中小型爬虫项目，500MB 完全够用。可以存储几十万条房源记录。

**Q: 如何升级到付费版？**

A: 在 Dashboard → **Settings** → **Billing** 中升级。按需付费，价格合理。

**Q: 数据安全吗？**

A: Supabase 提供：
- 自动每日备份
- SSL 加密传输
- 行级安全策略（RLS）
- SOC 2 Type II 认证

---

🎉 **恭喜！你已经完成 Supabase 配置！**

开始爬取数据吧！
