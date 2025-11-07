"""
数据库工厂
根据配置创建对应的数据库管理器实例
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crawler.database_interface import SQLDatabaseInterface

from utils.logger import get_logger

logger = get_logger("DatabaseFactory")


class DatabaseFactory:
    """数据库工厂类"""

    @staticmethod
    def create_sql_database(
        db_type: str | None = None, config: dict | None = None
    ) -> SQLDatabaseInterface:
        """
        创建SQL数据库实例

        Args:
            db_type: 数据库类型 ('mysql', 'postgresql')
                    注：Supabase 就是 PostgreSQL，直接使用 'postgresql'
                    如果为 None，从环境变量 DB_TYPE 读取
            config: 数据库配置字典
                    如果为 None，从环境变量读取

        Returns:
            数据库管理器实例

        Raises:
            ValueError: 不支持的数据库类型

        Examples:
            # 使用环境变量
            db = DatabaseFactory.create_sql_database()

            # 明确指定类型和配置
            db = DatabaseFactory.create_sql_database(
                db_type='postgresql',
                config={'host': 'localhost', 'port': 5432, ...}
            )

            # 使用 Supabase（就是 PostgreSQL）
            db = DatabaseFactory.create_sql_database(
                db_type='postgresql',
                config={'uri': 'postgresql://...@aws-*.pooler.supabase.com:5432/postgres'}
            )
        """
        # 确定数据库类型
        if db_type is None:
            db_type = os.getenv("DB_TYPE", "mysql").lower()

        # 向后兼容：将 supabase 映射为 postgresql
        if db_type == "supabase":
            logger.warning(
                "⚠️ DB_TYPE=supabase 已废弃，请使用 DB_TYPE=postgresql\n"
                "   Supabase 本质就是 PostgreSQL，配置方式相同"
            )
            db_type = "postgresql"

        logger.info(f"创建数据库连接: {db_type}")

        # 根据类型创建实例
        if db_type == "mysql":
            from crawler.database_mysql import MySQLManager

            cfg = config or DatabaseFactory._load_mysql_config()
            return MySQLManager(cfg)

        elif db_type in ("postgresql", "postgres"):
            from crawler.database_postgresql import PostgreSQLManager

            cfg = config or DatabaseFactory._load_postgresql_config()
            return PostgreSQLManager(cfg)

        else:
            raise ValueError(
                f"不支持的数据库类型: {db_type}\n"
                f"支持的类型: mysql, postgresql (Supabase 使用 postgresql)"
            )

    @staticmethod
    def _load_mysql_config() -> dict:
        """从环境变量加载 MySQL 配置"""
        # 优先使用完整 URI
        uri = os.getenv("MYSQL_URI")
        if uri:
            return {"uri": uri}

        return {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "username": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "crawler_db"),
            "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
            "ssl_disabled": os.getenv("MYSQL_SSL_DISABLED", "false").lower() == "true",
            "ssl_ca": os.getenv("MYSQL_SSL_CA"),
            "ssl_cert": os.getenv("MYSQL_SSL_CERT"),
            "ssl_key": os.getenv("MYSQL_SSL_KEY"),
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        }

    @staticmethod
    def _load_postgresql_config() -> dict:
        """从环境变量加载 PostgreSQL 配置"""
        # 优先使用完整 URI
        uri = os.getenv("POSTGRESQL_URI") or os.getenv("PG_URI")
        if uri:
            return {"uri": uri}

        return {
            "host": os.getenv("PG_HOST", "localhost"),
            "port": int(os.getenv("PG_PORT", "5432")),
            "username": os.getenv("PG_USER", "postgres"),
            "password": os.getenv("PG_PASSWORD", ""),
            "database": os.getenv("PG_DATABASE", "postgres"),
            "ssl_mode": os.getenv("PG_SSL_MODE", "prefer"),
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        }


# 便捷函数
def get_database(db_type: str | None = None, config: dict | None = None) -> SQLDatabaseInterface:
    """
    获取数据库实例（便捷函数）

    Args:
        db_type: 数据库类型
        config: 数据库配置

    Returns:
        数据库管理器实例
    """
    return DatabaseFactory.create_sql_database(db_type, config)
