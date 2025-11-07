"""
MySQL 数据库管理器（基于 SQLAlchemy ORM）
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

from crawler.database_interface import SQLDatabaseInterface
from utils.logger import get_logger
from utils.retry import retry_on_error

logger = get_logger("MySQLManager")


class MySQLManager(SQLDatabaseInterface):
    """MySQL管理器（基于 ORM）"""

    def __init__(self, config: dict):
        """
        初始化MySQL连接

        Args:
            config: MySQL配置
                - uri: 完整连接URI
                - host: 主机名
                - port: 端口（默认3306）
                - username: 用户名
                - password: 密码
                - database: 数据库名
                - charset: 字符集（默认utf8mb4）
                - ssl_disabled: 是否禁用SSL（默认False）
                - ssl_ca: SSL CA证书路径
                - ssl_cert: SSL客户端证书路径
                - ssl_key: SSL客户端密钥路径
                - ssl_verify_cert: 是否验证证书（默认True）
                - ssl_verify_identity: 是否验证主机名（默认False）
                - pool_size: 连接池大小（默认10）
                - max_overflow: 最大溢出连接数（默认20）
        """
        self.config = config
        self._engine: Engine | None = None
        self._Session: sessionmaker[Session] | None = None
        self._connect()

    def _build_connection_uri(self) -> str:
        """构建数据库连接URI"""
        uri = self.config.get("uri")
        if uri:
            return str(uri)

        username = self.config.get("username", "root")
        password = self.config.get("password", "")
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 3306)
        database = self.config.get("database", "crawler_db")
        charset = self.config.get("charset", "utf8mb4")

        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset={charset}"

    def _build_ssl_config(self) -> dict:
        """构建SSL配置"""
        ssl_disabled = self.config.get("ssl_disabled", False)
        if ssl_disabled:
            logger.info("MySQL SSL 连接已禁用")
            return {}

        ssl_ca = self.config.get("ssl_ca")
        ssl_cert = self.config.get("ssl_cert")
        ssl_key = self.config.get("ssl_key")
        ssl_verify_cert = self.config.get("ssl_verify_cert", True)
        ssl_verify_identity = self.config.get("ssl_verify_identity", False)

        ssl_config = {}
        if ssl_ca:
            ssl_config["ca"] = ssl_ca
        if ssl_cert:
            ssl_config["cert"] = ssl_cert
        if ssl_key:
            ssl_config["key"] = ssl_key

        if ssl_config:
            if ssl_verify_cert and ssl_ca:
                ssl_config["check_hostname"] = ssl_verify_identity
            else:
                ssl_config["check_hostname"] = False
            logger.info(
                f"MySQL SSL 连接已启用（CA: {ssl_ca or '未提供'}, Cert: {ssl_cert or '未提供'}, Key: {ssl_key or '未提供'}）"
            )
            return {"ssl": ssl_config}

        logger.info("MySQL SSL 连接已启用（使用默认 SSL，不验证证书）")
        return {"ssl": {"check_hostname": False}}

    @retry_on_error(max_retries=3, retry_delay=5, logger_instance=logger)
    def _connect(self):
        """建立连接"""
        uri = self._build_connection_uri()
        connect_args = self._build_ssl_config()

        if not uri:
            raise ValueError("数据库URI不能为空")

        # 获取连接池配置
        pool_size = self.config.get("pool_size", 10)
        max_overflow = self.config.get("max_overflow", 20)

        self._engine = create_engine(
            uri,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=3600,
            pool_pre_ping=True,  # 自动检测连接是否有效
            echo=False,
            connect_args=connect_args,
        )

        # 创建Session工厂
        self._Session = sa_sessionmaker(bind=self._engine)

        # 测试连接
        if not self.test_connection():
            raise RuntimeError("数据库连接测试失败")

        database_name = self.config.get("database", "crawler_db")
        logger.info(f"MySQL 连接成功: {database_name}")

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
            logger.info("MySQL 连接已关闭")

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
        return "mysql"
