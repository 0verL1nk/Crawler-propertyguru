# PropertyGuru 爬虫使用指南

## 概述

PropertyGuru爬虫用于爬取新加坡房产网站 propertyguru.com.sg 的房源信息，包括：
- 房源基本信息（价格、面积、位置等）
- 房产详细信息（Property details，以JSON格式存储）
- 房产描述
- 便利设施（Amenities）和公共设施（Facilities）
- 房贷计算信息
- 常见问题（FAQs）
- 媒体文件（图片/视频，去水印后上传S3）

## 环境要求

- Python 3.8+
- MySQL 数据库
- AWS S3 或七牛云存储（用于存储媒体文件）
- Bright Data Scraping Browser（用于访问网站）
- 动态住宅代理（推荐）

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

复制 `env.example` 为 `.env` 并填写配置：

```bash
# 必需配置
BROWSER_AUTH=your_bright_data_auth_token
PROXY_URL=http://brd-customer-xxx-zone-residential_proxy1:pass@brd.superproxy.io:33335

# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=crawler_data
MYSQL_USER=root
MYSQL_PASSWORD=your_password

# S3配置（用于存储媒体文件）
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_BUCKET_NAME=your_bucket_name
AWS_REGION=us-east-1

# 去水印API配置（可选）
WATERMARK_REMOVER_PRODUCT_SERIAL=your_serial
WATERMARK_REMOVER_PRODUCT_CODE=067003
WATERMARK_REMOVER_AUTHORIZATION=your_authorization
```

### 3. 初始化数据库

```bash
mysql -u root -p < sql/init.sql
```

### 4. 配置config.yaml

编辑 `config.yaml`，确保以下配置正确：

```yaml
database:
  type: "mysql"
  mysql:
    host: "localhost"
    port: 3306
    database: "crawler_data"
    username: "root"
    password: ""

s3:
  enabled: true
  type: "s3"
  bucket_name: "your-bucket-name"
  region_name: "us-east-1"

watermark_remover:
  enabled: true
```

### 5. 运行爬虫

#### 分阶段测试（推荐）

```bash
# 方式1: 使用测试脚本（交互式）
./test.sh

# 方式2: 直接使用命令行参数
# 测试第一页的第一个房源
python main.py --test-single

# 测试第一页的所有房源
python main.py --test-page

# 测试前10页
python main.py --test-pages 10

# 爬取全部页面
python main.py

# 爬取指定页面范围
python main.py 1 10  # 爬取第1页到第10页
python main.py 5     # 从第5页开始爬取到最后
```

## 数据模型

### 数据库表结构

1. **listing_info** - 房源基本信息
   - 包含标题、价格、面积、位置等基础信息
   - `property_details` 字段以JSON格式存储所有Property details信息

2. **listing_media** - 媒体文件
   - 存储图片和视频的S3 URL
   - 图片已去水印

3. **mortgage_calculator** - 房贷计算信息
   - 包含月供、首付、贷款利率等信息

4. **listing_faqs** - 常见问题
   - 存储FAQ的问题和答案

5. **listing_amenities** - 设施信息
   - 区分便利设施（amenity）和公共设施（facility）

## 功能特性

### 1. 多线程和批量处理

- 使用 `ThreadPoolExecutor` 进行并发爬取
- 数据库批量插入，提高性能
- 媒体文件异步下载和处理

### 2. 数据提取

- **列表页**: 提取房源卡片信息
- **详情页**: 提取完整房源信息
  - Property details（动态字段，以字典存储）
  - 描述信息
  - Amenities和Facilities
  - 房贷计算信息
  - FAQs
  - 媒体文件

### 3. 媒体处理

- 自动下载图片和视频
- 图片去水印（使用magiceraser.org API）
- 上传到S3存储
- 视频不去水印（根据需求）

### 4. 错误处理

- 自动重试机制
- 详细的日志记录
- 数据库去重（跳过已存在的房源）

### 5. 重试机制和断点续传

- **自动重试**: 爬取失败时自动重试，最多重试3次（可在config.yaml中配置）
- **指数退避**: 重试间隔逐步增加（2秒、4秒、8秒），避免频繁请求
- **断点续传**: 自动保存进度到 `crawl_progress.json` 文件
- **进度恢复**: 中断后重新运行会自动从上次的位置继续
- **进度重置**: 使用 `python main.py --reset-progress` 可以重置进度

## 注意事项

1. **代理配置**: 必须使用动态住宅代理，避免IP被封禁
2. **去水印**: 图片会自动去水印，视频不去水印
3. **数据去重**: 爬虫会自动检查房源是否已存在，避免重复爬取
4. **延迟设置**: 每个房源之间有2秒延迟，避免请求过快
5. **浏览器API**: 需要配置Bright Data Scraping Browser的认证信息

## 常见问题

### Q: 如何只爬取新房源？

A: 爬虫会自动检查数据库中是否已存在该房源，如果存在则跳过。可以通过修改代码实现增量爬取。

### Q: 如何处理失败的媒体文件？

A: 失败的媒体文件会被记录在日志中，但不会中断整个爬取流程。可以后续手动处理失败的媒体文件。

### Q: 如何修改爬取延迟？

A: 在 `propertyguru_crawler.py` 的 `run` 方法中修改 `time.sleep(2)` 的值。

### Q: Property details字段不固定怎么办？

A: 所有Property details字段以JSON格式存储在 `property_details` 字段中，使用图标的alt属性作为key，文本作为value。

### Q: 如何实现断点续传？

A: 爬虫会自动保存进度到 `crawl_progress.json` 文件。如果爬虫中断，重新运行时会自动从上次的位置继续。使用 `python main.py --reset-progress` 可以重置进度。

### Q: 重试机制如何工作？

A: 爬虫会在失败时自动重试，默认最多重试3次（可在config.yaml中配置 `max_retries`）。重试间隔会逐步增加（指数退避），避免频繁请求。重试间隔时间计算公式：`retry_delay * (2 ^ attempt)`，例如第1次重试等待2秒，第2次等待4秒，第3次等待8秒。

### Q: 如何避免网站新增数据导致的分页偏移问题？

A: 爬虫使用listing_id而不是页码来判断是否已完成。每一页爬取前，会先检查该页所有房源的listing_id是否已在数据库或进度文件中。如果已存在则跳过，这样可以：
- 避免重复爬取（即使网站新增了数据，导致相同房源出现在不同页码）
- 确保不遗漏新数据（新的房源会被正常爬取）
- 支持断点续传（即使分页发生变化，也能正确识别已完成的房源）

例如：爬取第1页时，网站新增了数据，导致第2页的内容变成了原来的第1页内容，爬虫会自动识别并跳过已爬取的房源，只爬取新的房源。

## 开发说明

### 项目结构

```
propertyguru/
├── crawler/
│   ├── propertyguru_crawler.py  # 主爬虫类
│   ├── parsers.py              # 页面解析器
│   ├── models.py               # 数据模型
│   ├── db_operations.py        # 数据库操作
│   ├── media_processor.py       # 媒体处理
│   └── ...
├── sql/
│   └── init.sql                # 数据库初始化脚本
├── main.py                     # 入口文件
└── config.yaml                # 配置文件
```

### 扩展功能

如需扩展功能，可以：

1. 修改 `parsers.py` 添加新的数据提取逻辑
2. 修改 `models.py` 添加新的数据模型
3. 修改 `db_operations.py` 添加新的数据库操作

## 许可证

MIT License
