# 数据库初始化说明

## ⚠️ 重要提示

本搜索引擎项目与爬虫项目**共用同一个 PostgreSQL 数据库**。

请使用爬虫项目中的统一初始化脚本：

```
../propertyguru/sql/init_postgresql_unified.sql
```

## 架构说明

```
PostgreSQL 数据库
├── 核心数据表（爬虫写入，搜索引擎读取）
│   ├── listing_info          # 房源信息（含 AI 嵌入）
│   └── listing_media         # 多媒体资源
│
└── 搜索引擎专用表（搜索引擎写入）
    ├── search_logs           # 搜索日志
    └── user_feedback         # 用户反馈
```

## 初始化步骤

### 1. 本地 PostgreSQL

```bash
# 执行统一初始化脚本
cd ../propertyguru
psql -U postgres -d postgres -f sql/init_postgresql_unified.sql
```

### 2. Supabase

1. 打开 Supabase Dashboard
2. 进入 **SQL Editor**
3. 粘贴 `../propertyguru/sql/init_postgresql_unified.sql` 的内容
4. 点击 **Run** 执行

### 3. 配置连接

爬虫和搜索引擎使用**同一个数据库连接字符串**：

**爬虫 `.env`:**
```bash
DB_TYPE=postgresql
POSTGRESQL_URI=postgresql://postgres:password@localhost:5432/property_data
```

**搜索引擎 `config.env`:**
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/property_data
```

## 优势

✅ 数据实时同步（爬虫更新，搜索立即可见）  
✅ 无需数据同步脚本  
✅ 降低维护成本  
✅ 避免数据冗余  

## 详细文档

请查看：`../propertyguru/docs/UNIFIED_DATABASE.md`

