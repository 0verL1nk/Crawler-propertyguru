# 数据库使用指南

## 概述

爬虫项目支持多种数据库后端，通过统一的 ORM 接口进行操作：

- **MySQL** - 传统关系型数据库
- **PostgreSQL** - 开源关系型数据库（支持搜索引擎集成）
  - 包括各种托管服务：Supabase、AWS RDS、Azure Database 等

**注意：** Supabase 本质就是 PostgreSQL，使用 `DB_TYPE=postgresql` 配置即可。

所有数据库操作统一使用 SQLAlchemy ORM，无需编写原生 SQL。

## 快速开始

### 1. 配置数据库

编辑 `.env` 文件：

```bash
# 选择数据库类型
DB_TYPE=mysql  # 可选: mysql, postgresql

# MySQL 配置
MYSQL_URI=mysql+pymysql://root:password@localhost:3306/crawler_db

# 或 PostgreSQL 配置（包括 Supabase）
# DB_TYPE=postgresql
# POSTGRESQL_URI=postgresql://postgres:password@localhost:5432/property_search

# Supabase 示例（本质就是 PostgreSQL）
# DB_TYPE=postgresql
# POSTGRESQL_URI=postgresql://postgres.xxx:password@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres
```

### 2. 创建数据库实例

```python
from crawler.database_factory import get_database

# 方式1: 使用环境变量配置（推荐）
db = get_database()

# 方式2: 明确指定类型
db = get_database(db_type='postgresql')

# 方式3: 提供完整配置
db = get_database(
    db_type='postgresql',
    config={
        'host': 'localhost',
        'port': 5432,
        'username': 'postgres',
        'password': 'password',
        'database': 'property_search'
    }
)
```

### 3. 使用 ORM 操作数据

```python
from crawler.orm_models import ListingInfoORM

# 查询单条记录
with db.get_session() as session:
    listing = session.query(ListingInfoORM).filter_by(listing_id=60157325).first()
    if listing:
        print(f"找到房源: {listing.title}")

# 查询多条记录
with db.get_session() as session:
    listings = session.query(ListingInfoORM)\
        .filter(ListingInfoORM.price < 1000000)\
        .filter(ListingInfoORM.bedrooms == 3)\
        .limit(10)\
        .all()

# 添加新记录
with db.get_session() as session:
    new_listing = ListingInfoORM(
        listing_id=123456,
        title="Test Listing",
        price=950000,
        bedrooms=3,
        location="Punggol"
    )
    session.add(new_listing)
    # 自动提交

# 批量添加
with db.get_session() as session:
    listings = [
        ListingInfoORM(listing_id=1, title="Listing 1"),
        ListingInfoORM(listing_id=2, title="Listing 2"),
    ]
    session.add_all(listings)

# 更新记录
with db.get_session() as session:
    listing = session.query(ListingInfoORM).filter_by(listing_id=123456).first()
    if listing:
        listing.title = "Updated Title"
        listing.price = 1000000
        # 自动提交

# 删除记录
with db.get_session() as session:
    listing = session.query(ListingInfoORM).filter_by(listing_id=123456).first()
    if listing:
        session.delete(listing)
```

## 数据库配置详解

### MySQL 配置

**方式1: 使用 URI（推荐）**

```bash
MYSQL_URI=mysql+pymysql://username:password@host:port/database
```

**方式2: 分项配置**

```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DATABASE=crawler_db
MYSQL_CHARSET=utf8mb4

# SSL 配置（可选）
MYSQL_SSL_DISABLED=false
MYSQL_SSL_CA=/path/to/ca.pem
MYSQL_SSL_CERT=/path/to/client-cert.pem
MYSQL_SSL_KEY=/path/to/client-key.pem
```

### PostgreSQL 配置

**方式1: 使用 URI（推荐）**

```bash
POSTGRESQL_URI=postgresql://postgres:password@localhost:5432/property_search
```

**方式2: 分项配置**

```bash
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=password
PG_DATABASE=property_search
PG_SSL_MODE=prefer  # 可选: disable, allow, prefer, require, verify-ca, verify-full
```

### Supabase 配置

[Supabase](https://supabase.com/docs/reference/python/installing) 是托管的 PostgreSQL 服务，**本质就是标准 PostgreSQL**。

**配置步骤:**

1. 在 Supabase 创建项目
2. 获取连接字符串：
   - 打开 Project Settings → Database
   - ⚠️ **重要：必须选择 "Connection pooling"**（不要选 "Direct connection"）
   - 原因：Direct connection 仅支持 IPv6，大多数环境不支持
   - 复制连接字符串（格式如下）

```
postgresql://postgres.{project}:[YOUR-PASSWORD]@aws-{region}.pooler.supabase.com:5432/postgres
```

⚠️ **关键：确保主机名包含 `pooler.supabase.com`**

3. 配置环境变量（**推荐方式1**）：

**方式1：使用完整连接字符串（最简单）**
```bash
# 直接使用 PostgreSQL 配置
DB_TYPE=postgresql
POSTGRESQL_URI=postgresql://postgres.rlfsvixfbyauygglwsoi:YOUR_PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres

# 或使用 Supabase 专用配置
DB_TYPE=supabase
SUPABASE_CONNECTION_STRING=postgresql://postgres.rlfsvixfbyauygglwsoi:YOUR_PASSWORD@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres
```

**方式2：分项配置（不推荐）**
```bash
DB_TYPE=supabase
SUPABASE_URL=https://rlfsvixfbyauygglwsoi.supabase.co
SUPABASE_PASSWORD=your_password
SUPABASE_USER=postgres.rlfsvixfbyauygglwsoi
SUPABASE_HOST=aws-1-ap-southeast-2.pooler.supabase.com
```

**优势:**
- 免费层级（500MB 数据库，无限 API 请求）
- 自动备份
- 连接池支持（pooler）
- 与搜索引擎无缝集成
- 标准 PostgreSQL 兼容

## 高级用法

### 1. 复杂查询

```python
from sqlalchemy import and_, or_

with db.get_session() as session:
    # 复杂条件
    listings = session.query(ListingInfoORM).filter(
        and_(
            ListingInfoORM.price < 1500000,
            ListingInfoORM.bedrooms >= 3,
            or_(
                ListingInfoORM.unit_type == 'Condo',
                ListingInfoORM.unit_type == 'HDB'
            )
        )
    ).all()

    # 排序
    listings = session.query(ListingInfoORM)\
        .order_by(ListingInfoORM.price.desc())\
        .limit(20)\
        .all()

    # 分页
    page = 1
    page_size = 20
    listings = session.query(ListingInfoORM)\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
```

### 2. 联表查询

```python
from crawler.orm_models import ListingInfoORM, ListingMediaORM

with db.get_session() as session:
    # 查询房源及其媒体
    results = session.query(ListingInfoORM, ListingMediaORM)\
        .join(ListingMediaORM, ListingInfoORM.listing_id == ListingMediaORM.listing_id)\
        .filter(ListingInfoORM.price < 1000000)\
        .all()

    for listing, media in results:
        print(f"{listing.title}: {media.media_url}")
```

### 3. 批量操作

```python
from sqlalchemy import update

with db.get_session() as session:
    # 批量更新
    session.query(ListingInfoORM)\
        .filter(ListingInfoORM.is_completed == False)\
        .update({'is_completed': True})

    # 批量删除
    session.query(ListingInfoORM)\
        .filter(ListingInfoORM.listing_id.in_([1, 2, 3]))\
        .delete(synchronize_session=False)
```

### 4. 事务控制

```python
with db.get_session() as session:
    try:
        # 多个操作在同一事务中
        listing1 = ListingInfoORM(listing_id=1, title="Test 1")
        listing2 = ListingInfoORM(listing_id=2, title="Test 2")

        session.add(listing1)
        session.flush()  # 立即执行但不提交

        session.add(listing2)

        # 如果没有异常，自动提交
    except Exception as e:
        # 发生异常，自动回滚
        print(f"事务失败: {e}")
        raise
```

### 5. 连接测试

```python
# 测试连接是否正常
if db.test_connection():
    print("✅ 数据库连接正常")
else:
    print("❌ 数据库连接失败")

# 获取数据库类型
print(f"当前数据库类型: {db.db_type}")

# 关闭连接池
db.close()
```

## 在爬虫中使用

### 示例：集成到爬虫主程序

```python
# main.py
from crawler.database_factory import get_database
from crawler.database_ops import DatabaseOperations

# 创建数据库实例
db = get_database()  # 自动从环境变量读取配置

# 创建数据库操作类
db_ops = DatabaseOperations(db)

# 在爬虫中使用
from crawler.propertyguru_crawler import PropertyGuruCrawler

crawler = PropertyGuruCrawler(
    browser=browser,
    db_ops=db_ops,
    use_proxy=False
)

# 爬取数据（自动保存到配置的数据库）
await crawler.run()

# 关闭连接
db.close()
```

## 双数据库配置

如果需要同时使用 MySQL 和 PostgreSQL（例如：MySQL 用于备份，PostgreSQL 用于搜索引擎）：

```python
from crawler.database_factory import get_database

# MySQL 实例
mysql_db = get_database(db_type='mysql')

# PostgreSQL 实例
pg_db = get_database(db_type='postgresql')

# 双写数据
with mysql_db.get_session() as mysql_session, \
     pg_db.get_session() as pg_session:

    # 保存到 MySQL
    mysql_session.add(listing)

    # 同时保存到 PostgreSQL
    pg_session.add(listing)

    # 两个数据库都会自动提交
```

## 性能优化建议

### 1. 连接池配置

```bash
# 根据并发量调整
DB_POOL_SIZE=10        # 连接池大小
DB_MAX_OVERFLOW=20     # 最大溢出连接
```

### 2. 批量操作

```python
# 使用 bulk_insert_mappings 提高插入性能
with db.get_session() as session:
    listings_data = [
        {'listing_id': 1, 'title': 'Test 1'},
        {'listing_id': 2, 'title': 'Test 2'},
        # ... 更多数据
    ]
    session.bulk_insert_mappings(ListingInfoORM, listings_data)
```

### 3. 查询优化

```python
# 只查询需要的列
with db.get_session() as session:
    results = session.query(
        ListingInfoORM.listing_id,
        ListingInfoORM.title,
        ListingInfoORM.price
    ).filter(ListingInfoORM.price < 1000000).all()
```

## 故障排查

### 连接失败

```python
# 检查连接
try:
    db = get_database()
    if db.test_connection():
        print("连接成功")
except Exception as e:
    print(f"连接失败: {e}")
```

### 查看 SQL 日志

在创建 engine 时启用 echo：

```python
# 临时调试
config = {'host': 'localhost', 'port': 5432, ...}
# 修改 database_postgresql.py 中的 echo=True
```

## 迁移数据

### MySQL → PostgreSQL

```python
from crawler.database_factory import get_database
from crawler.orm_models import ListingInfoORM

mysql_db = get_database(db_type='mysql')
pg_db = get_database(db_type='postgresql')

# 迁移数据
with mysql_db.get_session() as mysql_session:
    listings = mysql_session.query(ListingInfoORM).all()

    with pg_db.get_session() as pg_session:
        for listing in listings:
            # 创建新对象（避免 session 冲突）
            new_listing = ListingInfoORM()
            for key, value in listing.__dict__.items():
                if not key.startswith('_'):
                    setattr(new_listing, key, value)
            pg_session.add(new_listing)
```

## 参考链接

- [SQLAlchemy ORM 教程](https://docs.sqlalchemy.org/en/20/orm/tutorial.html)
- [Supabase Python 文档](https://supabase.com/docs/reference/python/installing)
- [PostgreSQL 连接字符串格式](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)
