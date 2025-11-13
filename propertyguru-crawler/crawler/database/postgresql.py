"""
PostgreSQL 数据库管理器（基于 SQLAlchemy ORM）
支持本地 PostgreSQL 和托管 PostgreSQL (Supabase 等)
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session, sessionmaker

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker as sa_sessionmaker
from sqlalchemy.pool import QueuePool

from utils.logger import get_logger
from utils.retry import retry_on_error

from .interface import SQLDatabaseInterface

logger = get_logger("PostgreSQLManager")


class PostgreSQLManager(SQLDatabaseInterface):
    """PostgreSQL管理器（支持本地和托管 PostgreSQL，如 Supabase）"""

    def __init__(self, config: dict):
        """
        初始化PostgreSQL连接

        Args:
            config: PostgreSQL配置
                - uri: 完整连接URI（推荐，支持所有 PostgreSQL 变体）
                - host: 主机名（如果没有 uri）
                - port: 端口（默认5432）
                - username: 用户名
                - password: 密码
                - database: 数据库名
                - ssl_mode: SSL模式（默认 prefer）
                - pool_size: 连接池大小（默认10）
                - max_overflow: 最大溢出连接数（默认20）

        示例:
            # 本地 PostgreSQL
            config = {'uri': 'postgresql://postgres:pass@localhost:5432/db'}

            # Supabase（托管 PostgreSQL）
            config = {'uri': 'postgresql://postgres.xxx:pass@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres'}
        """
        self.config = config
        self._engine: Engine | None = None
        self._Session: sessionmaker[Session] | None = None
        self._connect()

    def _build_connection_uri(self) -> str:
        """
        构建数据库连接URI

        优先使用完整 URI，如果没有则从配置组件构建。
        自动检测 Supabase 直连（仅 IPv6）并发出警告。
        """
        # 如果提供了完整 URI，直接使用
        uri = self.config.get("uri")
        if uri:
            uri_str = str(uri)
            # 检测 Supabase 直连（仅 IPv6）
            self._check_supabase_direct_connection(uri_str)
            return uri_str

        # 从配置组件构建 PostgreSQL URI
        username = self.config.get("username", "postgres")
        password = self.config.get("password", "")
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 5432)
        database = self.config.get("database", "postgres")

        # 构建连接字符串
        uri = f"postgresql://{username}:{password}@{host}:{port}/{database}"

        # 添加 SSL 模式
        ssl_mode = self.config.get("ssl_mode", "prefer")
        uri += f"?sslmode={ssl_mode}"

        # 检测 Supabase 直连
        self._check_supabase_direct_connection(uri)

        return uri

    def _check_supabase_direct_connection(self, uri: str) -> None:
        """
        检测并警告 Supabase 直连（仅支持 IPv6）

        Args:
            uri: 数据库连接 URI
        """
        if ".supabase.co" in uri and "pooler" not in uri:
            logger.warning(
                "⚠️ 警告：检测到 Supabase 直连地址 (db.*.supabase.co)\n"
                "   直连仅支持 IPv6，大多数 IPv4 环境无法连接\n"
                "   建议改用连接池地址：aws-*.pooler.supabase.com"
            )

    @retry_on_error(max_retries=3, retry_delay=5, logger_instance=logger)
    def _connect(self):
        """建立连接"""
        uri = self._build_connection_uri()

        if not uri:
            raise ValueError("数据库URI不能为空")

        # 获取连接池配置
        pool_size = self.config.get("pool_size", 10)
        max_overflow = self.config.get("max_overflow", 20)

        # 创建引擎
        self._engine = create_engine(
            uri,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=3600,
            pool_pre_ping=True,  # 自动检测连接是否有效
            echo=False,
        )

        # 创建Session工厂
        self._Session = sa_sessionmaker(bind=self._engine)

        # 测试连接
        if not self.test_connection():
            raise RuntimeError("数据库连接测试失败")

        database_name = self.config.get("database", "postgres")
        logger.info(f"PostgreSQL 连接成功: {database_name}")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取数据库会话（上下文管理器）- 基于 ORM

        使用示例:
            # 查询
            with db.get_session() as session:
                listing = session.query(ListingInfoORM).filter_by(listing_id=123).first()

                # 添加
                new_listing = ListingInfoORM(listing_id=456, title="Test")
                session.add(new_listing)

                # 批量添加
                session.add_all([listing1, listing2])

                # 更新
                listing.title = "Updated Title"
                session.flush()  # 立即写入但不提交

                # 删除
                session.delete(listing)

        Yields:
            SQLAlchemy Session（自动提交和回滚）
        """
        if self._Session is None:
            raise RuntimeError("数据库未初始化")
        session = self._Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """
        测试数据库连接是否正常

        Returns:
            连接是否正常
        """
        try:
            if self._engine is None:
                return False
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False

    def close(self):
        """关闭数据库连接池"""
        if self._engine:
            self._engine.dispose()
            logger.info("PostgreSQL 连接已关闭")

    @property
    def engine(self):
        """获取SQLAlchemy engine对象"""
        return self._engine

    @property
    def Session(self):
        """获取SQLAlchemy Session工厂"""
        return self._Session

    @property
    def db_type(self) -> str:
        """获取数据库类型"""
        return "postgresql"
