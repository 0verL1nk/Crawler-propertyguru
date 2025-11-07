#!/usr/bin/env python3
"""
重组 crawler 目录结构的脚本
将文件按功能分类到子文件夹中
"""

import shutil
from pathlib import Path


def main():
    # 项目根目录
    project_root = Path(__file__).parent.parent
    crawler_dir = project_root / "crawler"

    print("🔧 开始重组 crawler 目录...")
    print(f"📁 目标目录: {crawler_dir}")

    # 1️⃣ 创建子文件夹
    subdirs = ["core", "database", "models", "browser", "parsers", "storage", "utils"]
    for subdir in subdirs:
        (crawler_dir / subdir).mkdir(exist_ok=True)
        print(f"✅ 创建文件夹: {subdir}/")

    # 2️⃣ 定义文件移动映射
    file_moves = {
        # 核心模块
        "propertyguru_crawler.py": "core/crawler.py",
        "spider.py": "core/spider.py",
        "config.py": "core/config.py",
        # 数据库模块
        "database_factory.py": "database/factory.py",
        "database_interface.py": "database/interface.py",
        "database_mysql.py": "database/mysql.py",
        "database_postgresql.py": "database/postgresql.py",
        "db_operations.py": "database/operations.py",
        "orm_models.py": "database/orm_models.py",
        "database.py": "database/legacy.py",
        # 数据模型
        "models.py": "models/listing.py",
        # 浏览器
        "browser.py": "browser/browser.py",
        # 解析器
        "parsers.py": "parsers/parsers.py",
        # 存储
        "storage.py": "storage/manager.py",
        "media_processor.py": "storage/media_processor.py",
        # 工具类
        "proxy_manager.py": "utils/proxy_manager.py",
        "progress_manager.py": "utils/progress_manager.py",
        "watermark_remover.py": "utils/watermark_remover.py",
        "watermark_remover_no_proxy.py": "utils/watermark_remover_no_proxy.py",
    }

    # 3️⃣ 移动文件
    print("\n📦 移动文件...")
    for old_name, new_path in file_moves.items():
        old_file = crawler_dir / old_name
        new_file = crawler_dir / new_path

        if old_file.exists():
            shutil.move(str(old_file), str(new_file))
            print(f"   {old_name} → {new_path}")
        else:
            print(f"   ⚠️  文件不存在: {old_name}")

    # 4️⃣ 创建 __init__.py 文件
    print("\n📝 创建 __init__.py 文件...")

    # core/__init__.py
    (crawler_dir / "core" / "__init__.py").write_text(
        """\"\"\"核心爬虫模块\"\"\"

from .crawler import PropertyGuruCrawler
from .spider import Spider
from .config import Config

__all__ = ["PropertyGuruCrawler", "Spider", "Config"]
"""
    )

    # database/__init__.py
    (crawler_dir / "database" / "__init__.py").write_text(
        """\"\"\"数据库模块\"\"\"

from .factory import DatabaseFactory, get_database
from .interface import SQLDatabaseInterface
from .mysql import MySQLManager
from .postgresql import PostgreSQLManager
from .operations import DBOperations
from .orm_models import ListingInfoORM, MediaItemORM
from .legacy import DatabaseManager, MongoDBManager

__all__ = [
    "DatabaseFactory",
    "get_database",
    "SQLDatabaseInterface",
    "MySQLManager",
    "PostgreSQLManager",
    "DBOperations",
    "ListingInfoORM",
    "MediaItemORM",
    "DatabaseManager",
    "MongoDBManager",
]
"""
    )

    # models/__init__.py
    (crawler_dir / "models" / "__init__.py").write_text(
        """\"\"\"数据模型\"\"\"

from .listing import (
    ListingInfo,
    MediaItem,
    PropertyDetails,
    GreenScore,
    MRTInfo,
    ListingAge,
)

__all__ = [
    "ListingInfo",
    "MediaItem",
    "PropertyDetails",
    "GreenScore",
    "MRTInfo",
    "ListingAge",
]
"""
    )

    # browser/__init__.py
    (crawler_dir / "browser" / "__init__.py").write_text(
        """\"\"\"浏览器模块\"\"\"

from .browser import LocalBrowser, RemoteBrowser, UndetectedBrowser

__all__ = ["LocalBrowser", "RemoteBrowser", "UndetectedBrowser"]
"""
    )

    # parsers/__init__.py
    (crawler_dir / "parsers" / "__init__.py").write_text(
        """\"\"\"解析器模块\"\"\"

from .parsers import ListingPageParser

__all__ = ["ListingPageParser"]
"""
    )

    # storage/__init__.py
    (crawler_dir / "storage" / "__init__.py").write_text(
        """\"\"\"存储模块\"\"\"

from .manager import (
    StorageManagerProtocol,
    LocalStorageManager,
    S3StorageManager,
    create_storage_manager,
)
from .media_processor import MediaProcessor

__all__ = [
    "StorageManagerProtocol",
    "LocalStorageManager",
    "S3StorageManager",
    "create_storage_manager",
    "MediaProcessor",
]
"""
    )

    # utils/__init__.py
    (crawler_dir / "utils" / "__init__.py").write_text(
        """\"\"\"工具模块\"\"\"

from .proxy_manager import ProxyManager
from .progress_manager import CrawlProgress
from .watermark_remover import WatermarkRemover

__all__ = [
    "ProxyManager",
    "CrawlProgress",
    "WatermarkRemover",
]
"""
    )

    print("✅ 所有 __init__.py 文件已创建")

    # 5️⃣ 更新主 __init__.py
    print("\n📝 更新 crawler/__init__.py...")
    (crawler_dir / "__init__.py").write_text(
        """\"\"\"PropertyGuru 爬虫模块\"\"\"

# 核心模块
from .core import PropertyGuruCrawler, Spider, Config

# 数据库模块
from .database import (
    get_database,
    DBOperations,
    ListingInfoORM,
    MediaItemORM,
)

# 数据模型
from .models import (
    ListingInfo,
    MediaItem,
    PropertyDetails,
)

# 浏览器
from .browser import LocalBrowser, RemoteBrowser, UndetectedBrowser

# 解析器
from .parsers import ListingPageParser

# 存储
from .storage import create_storage_manager, MediaProcessor

# 工具
from .utils import ProxyManager, CrawlProgress, WatermarkRemover

__all__ = [
    # 核心
    "PropertyGuruCrawler",
    "Spider",
    "Config",
    # 数据库
    "get_database",
    "DBOperations",
    "ListingInfoORM",
    "MediaItemORM",
    # 模型
    "ListingInfo",
    "MediaItem",
    "PropertyDetails",
    # 浏览器
    "LocalBrowser",
    "RemoteBrowser",
    "UndetectedBrowser",
    # 解析器
    "ListingPageParser",
    # 存储
    "create_storage_manager",
    "MediaProcessor",
    # 工具
    "ProxyManager",
    "CrawlProgress",
    "WatermarkRemover",
]
"""
    )

    print("\n🎉 重组完成！")
    print("\n📋 新的目录结构：")
    print(
        """
crawler/
├── __init__.py
├── core/               # 核心爬虫
│   ├── __init__.py
│   ├── crawler.py
│   ├── spider.py
│   └── config.py
├── database/           # 数据库
│   ├── __init__.py
│   ├── factory.py
│   ├── interface.py
│   ├── mysql.py
│   ├── postgresql.py
│   ├── operations.py
│   ├── orm_models.py
│   └── legacy.py
├── models/             # 数据模型
│   ├── __init__.py
│   └── listing.py
├── browser/            # 浏览器
│   ├── __init__.py
│   └── browser.py
├── parsers/            # 解析器
│   ├── __init__.py
│   └── parsers.py
├── storage/            # 存储
│   ├── __init__.py
│   ├── manager.py
│   └── media_processor.py
└── utils/              # 工具
    ├── __init__.py
    ├── proxy_manager.py
    ├── progress_manager.py
    ├── watermark_remover.py
    └── watermark_remover_no_proxy.py
    """
    )

    print("\n⚠️  接下来需要：")
    print("1. 更新各个文件内的导入语句")
    print("2. 运行 'make check' 检查是否有错误")
    print("3. 测试爬虫是否正常工作")


if __name__ == "__main__":
    main()
