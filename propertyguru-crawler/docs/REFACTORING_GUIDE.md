# Crawler 目录重构指南

## ⚠️ 重要提示

这是一个**大规模重构**，会影响所有导入语句。建议：
1. 提交当前代码到 Git
2. 创建新分支进行重构
3. 逐步测试确保功能正常

## 📁 当前结构（太乱）

```
crawler/
├── __init__.py
├── browser.py
├── config.py
├── database.py
├── database_factory.py
├── database_interface.py
├── database_mysql.py
├── database_postgresql.py
├── db_operations.py
├── media_processor.py
├── models.py
├── orm_models.py
├── parsers.py
├── progress_manager.py
├── propertyguru_crawler.py
├── proxy_manager.py
├── spider.py
├── storage.py
├── watermark_remover.py
└── watermark_remover_no_proxy.py
```

**问题：** 20个文件全部平铺，难以维护

## 📁 目标结构（清晰）

```
crawler/
├── __init__.py
├── core/                    # 核心爬虫逻辑
│   ├── __init__.py
│   ├── crawler.py          (原 propertyguru_crawler.py)
│   ├── spider.py
│   └── config.py
│
├── database/               # 数据库模块（7个文件）
│   ├── __init__.py
│   ├── factory.py          (原 database_factory.py)
│   ├── interface.py        (原 database_interface.py)
│   ├── mysql.py            (原 database_mysql.py)
│   ├── postgresql.py       (原 database_postgresql.py)
│   ├── operations.py       (原 db_operations.py)
│   ├── orm_models.py
│   └── legacy.py           (原 database.py)
│
├── models/                 # 数据模型
│   ├── __init__.py
│   └── listing.py          (原 models.py)
│
├── browser/                # 浏览器模块
│   ├── __init__.py
│   └── browser.py
│
├── parsers/                # 解析器
│   ├── __init__.py
│   └── parsers.py
│
├── storage/                # 存储模块
│   ├── __init__.py
│   ├── manager.py          (原 storage.py)
│   └── media_processor.py
│
└── utils/                  # 工具类（4个文件）
    ├── __init__.py
    ├── proxy_manager.py
    ├── progress_manager.py
    ├── watermark_remover.py
    └── watermark_remover_no_proxy.py
```

**优势：**
- ✅ 按功能分类，一目了然
- ✅ 数据库相关文件集中管理
- ✅ 更容易找到需要的模块
- ✅ 符合 Python 包的最佳实践

## 🚀 执行步骤

### 方式1：自动执行（推荐）

```bash
# 1. 提交当前代码
cd /home/ling/Crawler/propertyguru
git add -A
git commit -m "重构前保存：扁平 crawler 目录"

# 2. 创建新分支
git checkout -b refactor/organize-crawler

# 3. 执行重组脚本
uv run python scripts/reorganize_crawler.py

# 4. 更新导入语句（需要手动或使用下面的脚本）
uv run python scripts/update_imports.py

# 5. 检查错误
make check

# 6. 测试
uv run python main.py --test-single
```

### 方式2：手动执行（更安全）

参考下面的"导入更新清单"逐个文件修改

## 📝 导入更新清单

### main.py
```python
# 旧导入
from crawler.config import Config
from crawler.propertyguru_crawler import PropertyGuruCrawler

# 新导入
from crawler.core import Config, PropertyGuruCrawler
# 或者（推荐，因为 crawler/__init__.py 已导出）
from crawler import Config, PropertyGuruCrawler
```

### crawler/core/crawler.py (原 propertyguru_crawler.py)
```python
# 旧导入
from .browser import LocalBrowser, RemoteBrowser, UndetectedBrowser
from .database import DatabaseManager
from .database_factory import get_database
from .database_interface import SQLDatabaseInterface
from .db_operations import DBOperations
from .models import ListingInfo, MediaItem
from .media_processor import MediaProcessor
from .parsers import ListingPageParser
from .progress_manager import CrawlProgress
from .proxy_manager import ProxyManager
from .storage import create_storage_manager
from .watermark_remover import WatermarkRemover

# 新导入
from ..browser import LocalBrowser, RemoteBrowser, UndetectedBrowser
from ..database import get_database, DBOperations, DatabaseManager
from ..database.interface import SQLDatabaseInterface
from ..models import ListingInfo, MediaItem
from ..parsers import ListingPageParser
from ..storage import create_storage_manager, MediaProcessor
from ..utils import CrawlProgress, ProxyManager, WatermarkRemover
```

### crawler/database/operations.py (原 db_operations.py)
```python
# 旧导入
from .database import DatabaseManager, MySQLManager
from .database_interface import SQLDatabaseInterface
from .orm_models import ListingInfoORM, MediaItemORM

# 新导入
from .legacy import DatabaseManager, MySQLManager
from .interface import SQLDatabaseInterface
from .orm_models import ListingInfoORM, MediaItemORM

# TYPE_CHECKING 导入
if TYPE_CHECKING:
    from ..models import ListingInfo, MediaItem, PropertyDetails
```

### crawler/parsers/parsers.py
```python
# 旧导入
from .models import GreenScore, ListingAge, ListingInfo, MRTInfo

# 新导入
from ..models import GreenScore, ListingAge, ListingInfo, MRTInfo
```

### crawler/storage/media_processor.py
```python
# 旧导入
from .models import MediaItem
from .storage import StorageManagerProtocol
from .watermark_remover import WatermarkRemover

# 新导入
from ..models import MediaItem
from .manager import StorageManagerProtocol
from ..utils import WatermarkRemover
```

## 🔧 自动更新导入脚本

我已经创建了自动更新脚本，但由于改动较大，建议**先手动测试**一个模块，确认没问题后再批量执行。

## ✅ 验证步骤

重构后务必执行以下测试：

```bash
# 1. 语法检查
make check

# 2. 类型检查
make type-check

# 3. 测试单个房源
uv run python main.py --test-single

# 4. 测试第一页
uv run python main.py --test-page

# 5. 如果都通过，提交
git add -A
git commit -m "重构：重组 crawler 目录结构"
```

## 📊 影响范围评估

| 文件 | 受影响导入数 | 风险等级 |
|------|-------------|---------|
| main.py | 2行 | 🟢 低 |
| crawler/core/crawler.py | ~15行 | 🟡 中 |
| crawler/database/operations.py | ~5行 | 🟡 中 |
| crawler/parsers/parsers.py | ~3行 | 🟢 低 |
| crawler/storage/*.py | ~5行 | 🟢 低 |
| crawler/utils/*.py | ~2行 | 🟢 低 |
| examples/*.py | ~3行 | 🟢 低 |

**总计：** 约 35-40 处导入需要更新

## 🤔 要不要重构？

### 重构的好处 ✅
1. **更清晰的结构**：按功能分类
2. **更好的维护性**：找文件更容易
3. **符合规范**：Python 包的最佳实践
4. **扩展性更好**：添加新模块时有明确位置

### 重构的成本 ⚠️
1. **时间成本**：需要1-2小时
2. **测试成本**：需要全面测试
3. **风险**：可能引入导入错误（但可通过测试发现）

## 💡 推荐方案

### 方案A：现在重构（推荐）
```bash
# 执行自动重组
uv run python scripts/reorganize_crawler.py

# 然后逐个文件修复导入（或使用自动脚本）
# 测试通过后提交
```

**适合：** 项目还在活跃开发中，趁早重构

### 方案B：延后重构
暂时保持现状，等到：
- 文件数量继续增加（>30个）
- 或者需要添加新的大功能模块时

**适合：** 目前功能稳定，不想冒险

### 方案C：部分重构（折中）
只重组最混乱的部分，比如：
```
crawler/
├── database/           # 只重组数据库模块（7个文件）
└── utils/              # 只重组工具类（4个文件）
```

**适合：** 想改进但不想改动太大

## 🎯 我的建议

考虑到：
1. 你的项目已经比较成熟
2. 数据库模块刚重构完
3. 两个项目（爬虫+搜索引擎）已经联调

**建议：方案C - 部分重构**

只重组 `database/` 文件夹（7个文件集中管理），暂时保留其他文件。

```
crawler/
├── database/           # ✅ 重组：7个数据库文件
│   ├── factory.py
│   ├── interface.py
│   ├── mysql.py
│   ├── postgresql.py
│   ├── operations.py
│   ├── orm_models.py
│   └── legacy.py
├── browser.py          # ⏸️ 保留原位置
├── config.py
├── models.py
├── parsers.py
├── ... (其他文件保持不变)
```

**改动最小，风险最低，效果明显！**

---

**你的选择？**
1. 🚀 **现在全面重构** → 执行 `uv run python scripts/reorganize_crawler.py`
2. 📦 **部分重构（推荐）** → 我给你创建一个轻量级脚本
3. ⏸️ **暂时不动** → 保持现状
