# 数据库重构总结

## 📋 重构概述

本次重构将爬虫项目的数据库层改造为**基于 ORM 的抽象接口设计**，支持多种数据库后端，提供统一的操作方式。

### 主要目标

1. ✅ **统一接口** - 所有数据库操作通过 SQLAlchemy ORM，不使用原生 SQL
2. ✅ **多数据库支持** - MySQL, PostgreSQL, Supabase
3. ✅ **接口抽象** - 清晰的抽象层设计，易于扩展
4. ✅ **配置灵活** - 支持环境变量和代码配置两种方式
5. ✅ **向后兼容** - 保持与现有代码的兼容性

## 🏗️ 新架构设计

```
┌─────────────────────────────────────┐
│     Application Layer (爬虫)         │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Database Factory                │
│  (根据配置创建数据库实例)              │
└──────────┬────────────┬──────────────┘
           │            │
┌──────────▼───┐  ┌────▼──────────────┐
│ MySQL Manager│  │PostgreSQL Manager │
│  (基于ORM)    │  │  (基于ORM)         │
└──────────────┘  └───────────────────┘
      │                   │
      │                   ├─ 常规 PostgreSQL
      │                   └─ Supabase
      │
┌─────▼─────────────────────────────┐
│  SQLAlchemy ORM + Models          │
└───────────────────────────────────┘
```

## 📁 新增文件

### 核心文件

1. **`crawler/database_interface.py`** - 数据库抽象接口
   - 定义 `SQLDatabaseInterface` 抽象类
   - 规范所有数据库管理器的接口

2. **`crawler/database_mysql.py`** - MySQL 管理器
   - 基于 ORM 的 MySQL 实现
   - 支持 SSL 连接
   - 自动重连机制

3. **`crawler/database_postgresql.py`** - PostgreSQL/Supabase 管理器
   - 基于 ORM 的 PostgreSQL 实现
   - 支持常规 PostgreSQL 和 Supabase
   - 自动连接测试

4. **`crawler/database_factory.py`** - 数据库工厂
   - 统一的数据库实例创建接口
   - 自动从环境变量加载配置
   - 支持自定义配置

### 文档和示例

5. **`docs/DATABASE_USAGE.md`** - 使用指南
   - 详细的配置说明
   - ORM 操作示例
   - 性能优化建议

6. **`docs/DATABASE_REFACTORING.md`** - 重构总结（本文档）

7. **`examples/database_example.py`** - 示例代码
   - 8 个实用示例
   - 涵盖所有常见操作

## 🔧 接口设计

### SQLDatabaseInterface 抽象接口

```python
class SQLDatabaseInterface(ABC):
    """SQL数据库抽象接口（基于 ORM）"""

    @abstractmethod
    def _connect(self) -> None:
        """建立数据库连接"""
        pass

    @abstractmethod
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话（上下文管理器）"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """测试数据库连接"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭数据库连接池"""
        pass

    @property
    @abstractmethod
    def engine(self) -> Engine | None:
        """获取SQLAlchemy engine对象"""
        pass

    @property
    @abstractmethod
    def Session(self) -> sessionmaker[Session] | None:
        """获取SQLAlchemy Session工厂"""
        pass

    @property
    @abstractmethod
    def db_type(self) -> str:
        """获取数据库类型"""
        pass
```

## 📝 使用方式对比

### 旧方式（原生 SQL）

```python
# 不推荐：原生 SQL
sql = "SELECT * FROM listing_info WHERE listing_id = %(id)s"
result = db.execute(sql, {"id": 123})
row = result.fetchone()
```

### 新方式（ORM）

```python
# ✅ 推荐：使用 ORM
with db.get_session() as session:
    listing = session.query(ListingInfoORM).filter_by(listing_id=123).first()
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install psycopg2-binary>=2.9.9
```

### 2. 配置环境变量

```bash
# .env 文件
DB_TYPE=postgresql  # 或 mysql, supabase

# PostgreSQL 配置
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=password
PG_DATABASE=property_search
```

### 3. 使用数据库

```python
from crawler.database_factory import get_database
from crawler.orm_models import ListingInfoORM

# 创建数据库实例
db = get_database()

# ORM 操作
with db.get_session() as session:
    listing = session.query(ListingInfoORM).first()
    print(listing.title)

# 关闭连接
db.close()
```

## 🔄 迁移指南

### 从旧代码迁移

**原代码：**
```python
from crawler.database import MySQLManager

config = {"uri": "mysql://..."}
db = MySQLManager(config)

# 原生 SQL
sql = "SELECT * FROM listing_info WHERE price < %(price)s"
result = db.execute(sql, {"price": 1000000})
rows = result.fetchall()
```

**新代码：**
```python
from crawler.database_factory import get_database
from crawler.orm_models import ListingInfoORM

db = get_database(db_type='mysql')

# ORM 查询
with db.get_session() as session:
    listings = session.query(ListingInfoORM)\
        .filter(ListingInfoORM.price < 1000000)\
        .all()
```

## 🌟 新特性

### 1. 统一的 ORM 接口

```python
# 所有数据库使用相同的 ORM 代码
with db.get_session() as session:
    # 查询
    listing = session.query(ListingInfoORM).filter_by(listing_id=123).first()

    # 插入
    new_listing = ListingInfoORM(listing_id=456, title="Test")
    session.add(new_listing)

    # 更新
    listing.title = "Updated"

    # 删除
    session.delete(listing)
```

### 2. 多数据库支持

```python
# MySQL
mysql_db = get_database(db_type='mysql')

# PostgreSQL
pg_db = get_database(db_type='postgresql')

# Supabase（托管 PostgreSQL）
supabase_db = get_database(db_type='supabase')
```

### 3. 灵活的配置方式

```python
# 方式1: 环境变量（推荐）
db = get_database()

# 方式2: 明确指定类型
db = get_database(db_type='postgresql')

# 方式3: 自定义配置
db = get_database(
    db_type='postgresql',
    config={'host': 'localhost', 'port': 5432, ...}
)
```

### 4. Supabase 支持

[Supabase](https://supabase.com) 是托管的 PostgreSQL，提供：
- 免费层级（500MB 数据库）
- 自动备份
- RESTful API
- 实时订阅
- 与搜索引擎无缝集成

```bash
# .env 配置
DB_TYPE=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PASSWORD=your_password
```

### 5. 双数据库支持

```python
# MySQL 用于数据存储
mysql_db = get_database(db_type='mysql')

# PostgreSQL 用于搜索引擎
pg_db = get_database(db_type='postgresql')

# 双写数据
with mysql_db.get_session() as mysql_session, \
     pg_db.get_session() as pg_session:

    mysql_session.add(listing)
    pg_session.add(listing)
```

## 🎯 最佳实践

### 1. 使用上下文管理器

```python
# ✅ 好的做法
with db.get_session() as session:
    listing = session.query(ListingInfoORM).first()
    # 自动提交和关闭

# ❌ 不推荐
session = db.Session()
try:
    listing = session.query(ListingInfoORM).first()
    session.commit()
finally:
    session.close()
```

### 2. 批量操作

```python
# ✅ 批量插入
with db.get_session() as session:
    listings = [ListingInfoORM(...) for _ in range(100)]
    session.add_all(listings)

# ❌ 逐条插入（慢）
for item in items:
    with db.get_session() as session:
        session.add(ListingInfoORM(...))
```

### 3. 查询优化

```python
# ✅ 只查询需要的列
session.query(ListingInfoORM.id, ListingInfoORM.title).all()

# ✅ 使用索引字段过滤
session.query(ListingInfoORM).filter_by(listing_id=123).first()

# ✅ 分页查询
session.query(ListingInfoORM).limit(20).offset(0).all()
```

## 📊 性能对比

| 操作 | 原生 SQL | ORM | 说明 |
|------|---------|-----|------|
| 简单查询 | 快 | 稍慢 | ORM 有轻微开销，但可忽略 |
| 复杂查询 | 快 | 相当 | ORM 查询优化器很好 |
| 批量插入 | 快 | 相当 | 使用 bulk_insert_mappings 可达到相近性能 |
| 代码维护 | 难 | 易 | ORM 代码更清晰易维护 |
| 数据库迁移 | 难 | 易 | ORM 抽象了数据库差异 |

## 🧪 测试

运行示例代码测试所有功能：

```bash
cd /home/ling/Crawler/propertyguru
python examples/database_example.py
```

## 🔗 相关资源

- [数据库使用指南](DATABASE_USAGE.md)
- [SQLAlchemy ORM 文档](https://docs.sqlalchemy.org/en/20/orm/)
- [Supabase Python 文档](https://supabase.com/docs/reference/python/installing)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)

## 📌 注意事项

1. **向后兼容**：旧的 `MySQLManager` 类仍然保留在 `database.py`，不影响现有代码
2. **渐进式迁移**：可以逐步将代码迁移到新的 ORM 接口
3. **依赖更新**：新增 `psycopg2-binary` 依赖，需要运行 `pip install -r requirements.txt`
4. **配置更新**：需要在 `.env` 中添加 `DB_TYPE` 等新配置项

## ✅ 重构清单

- [x] 创建抽象接口 `SQLDatabaseInterface`
- [x] 实现 MySQL 管理器（基于 ORM）
- [x] 实现 PostgreSQL 管理器（基于 ORM）
- [x] 实现 Supabase 支持
- [x] 创建数据库工厂
- [x] 更新 `requirements.txt`
- [x] 更新 `env.example`
- [x] 编写使用文档
- [x] 编写示例代码
- [x] 编写重构总结

## 🚧 后续计划

1. **连接池优化** - 根据实际负载调整连接池参数
2. **缓存层** - 集成 Redis 缓存热点数据
3. **读写分离** - 支持主从数据库配置
4. **性能监控** - 添加慢查询日志和性能统计
5. **迁移工具** - 提供数据迁移脚本（MySQL → PostgreSQL）

## 📧 反馈

如有问题或建议，请通过 Issue 反馈。
