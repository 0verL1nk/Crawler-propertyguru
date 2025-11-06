"""
数据库管理模块
支持 MySQL, MongoDB, Redis（可选）
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

import pymongo
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

# Redis 为可选依赖
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger("DatabaseManager")


class MongoDBManager:
    """MongoDB管理器"""

    def __init__(self, config: dict):
        """
        初始化MongoDB连接

        Args:
            config: MongoDB配置
        """
        self.config = config
        self.client: pymongo.MongoClient | None = None
        self.db: Any | None = None
        self._connect()

    def _connect(self):
        """建立连接"""
        try:
            # 构建连接URI
            username = self.config.get("username", "")
            password = self.config.get("password", "")
            host = self.config.get("host", "localhost")
            port = self.config.get("port", 27017)
            database = self.config.get("database", "crawler_db")

            if username and password:
                uri = f"mongodb://{username}:{password}@{host}:{port}/"
            else:
                uri = f"mongodb://{host}:{port}/"

            # 如果配置中有完整URI，使用它
            uri = self.config.get("uri", uri)

            self.client = pymongo.MongoClient(
                uri, maxPoolSize=50, minPoolSize=10, serverSelectionTimeoutMS=5000
            )
            self.db = self.client[database]

            # 测试连接
            self.client.server_info()
            logger.info(f"MongoDB连接成功: {database}")
        except Exception as e:
            logger.error(f"MongoDB连接失败: {e}")
            raise

    def get_collection(self, collection_name: str):
        """
        获取集合

        Args:
            collection_name: 集合名称

        Returns:
            MongoDB集合对象
        """
        if self.db is None:
            raise RuntimeError("数据库未初始化")
        return self.db[collection_name]

    def insert_one(self, collection: str, document: dict) -> str:
        """
        插入单条文档

        Args:
            collection: 集合名称
            document: 文档数据

        Returns:
            插入的文档ID
        """
        try:
            if self.db is None:
                raise RuntimeError("数据库未初始化")
            result = self.db[collection].insert_one(document)
            logger.debug(f"插入文档成功: {collection}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"插入文档失败: {e}")
            raise

    def insert_many(self, collection: str, documents: list[dict]) -> list[str]:
        """
        批量插入文档

        Args:
            collection: 集合名称
            documents: 文档列表

        Returns:
            插入的文档ID列表
        """
        try:
            if self.db is None:
                raise RuntimeError("数据库未初始化")
            result = self.db[collection].insert_many(documents)
            logger.debug(f"批量插入 {len(documents)} 条文档: {collection}")
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            logger.error(f"批量插入文档失败: {e}")
            raise

    def find_one(self, collection: str, query: dict) -> dict | None:
        """
        查询单条文档

        Args:
            collection: 集合名称
            query: 查询条件

        Returns:
            文档数据或None
        """
        try:
            if self.db is None:
                raise RuntimeError("数据库未初始化")
            return self.db[collection].find_one(query)  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"查询文档失败: {e}")
            raise

    def find_many(
        self, collection: str, query: dict | None = None, limit: int = 0, skip: int = 0
    ) -> list[dict]:
        """
        查询多条文档

        Args:
            collection: 集合名称
            query: 查询条件
            limit: 限制数量
            skip: 跳过数量

        Returns:
            文档列表
        """
        try:
            if self.db is None:
                raise RuntimeError("数据库未初始化")
            query = query or {}
            cursor = self.db[collection].find(query).skip(skip)
            if limit > 0:
                cursor = cursor.limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"查询文档失败: {e}")
            raise

    def update_one(self, collection: str, query: dict, update: dict) -> int:
        """
        更新单条文档

        Args:
            collection: 集合名称
            query: 查询条件
            update: 更新内容

        Returns:
            更新的文档数
        """
        try:
            if self.db is None:
                raise RuntimeError("数据库未初始化")
            result = self.db[collection].update_one(query, {"$set": update})
            return int(result.modified_count)
        except Exception as e:
            logger.error(f"更新文档失败: {e}")
            raise

    def delete_one(self, collection: str, query: dict) -> int:
        """
        删除单条文档

        Args:
            collection: 集合名称
            query: 查询条件

        Returns:
            删除的文档数
        """
        try:
            if self.db is None:
                raise RuntimeError("数据库未初始化")
            result = self.db[collection].delete_one(query)
            return int(result.deleted_count)
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise

    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()
            logger.info("MongoDB连接已关闭")


class MySQLManager:
    """MySQL管理器"""

    def __init__(self, config: dict):
        """
        初始化MySQL连接

        Args:
            config: MySQL配置
        """
        self.config = config
        self.engine: Engine | None = None
        self.Session: sessionmaker[Session] | None = None
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

    def _connect(self):
        """建立连接"""
        try:
            uri = self._build_connection_uri()
            connect_args = self._build_ssl_config()

            if not uri:
                raise ValueError("数据库URI不能为空")

            self.engine = create_engine(
                uri,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_recycle=3600,
                echo=False,
                connect_args=connect_args,
            )

            # 创建Session工厂
            self.Session = sessionmaker(bind=self.engine)

            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            database_name = self.config.get("database", "crawler_db")
            logger.info(f"MySQL连接成功: {database_name}")
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            raise

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取数据库会话（上下文管理器）

        Yields:
            SQLAlchemy Session
        """
        if self.Session is None:
            raise RuntimeError("数据库未初始化")
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()

    def execute(self, sql: str, params: dict | None = None) -> Any:
        """
        执行SQL语句

        Args:
            sql: SQL语句
            params: 参数（支持 pymysql 的 %(name)s 格式）

        Returns:
            执行结果：
            - SELECT 查询：返回一个 CursorWrapper 对象（支持 fetchone/fetchall）
            - 其他查询：返回受影响的行数
        """
        try:
            if self.engine is None:
                raise RuntimeError("数据库未初始化")
            # 使用原始连接执行SQL，这样可以正确处理 %(param)s 格式的参数
            raw_conn = self.engine.raw_connection()
            cursor = raw_conn.cursor()
            try:
                # PyMySQL 支持 %(param)s 格式的命名参数
                cursor.execute(sql, params or {})
                raw_conn.commit()

                # 如果是 SELECT 查询，返回包装后的 cursor
                if sql.strip().upper().startswith("SELECT"):
                    # 返回一个包装类，在关闭时自动清理连接和cursor
                    return _CursorWrapper(cursor, raw_conn)
                else:
                    rowcount = cursor.rowcount
                    cursor.close()
                    raw_conn.close()
                    return rowcount
            except Exception:
                # 发生异常时确保资源被清理
                cursor.close()
                raw_conn.close()
                raise
        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            raise

    def execute_many(self, sql: str, params_list: list[dict]) -> Any:
        """
        批量执行SQL

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            执行结果
        """
        try:
            if self.engine is None:
                raise RuntimeError("数据库未初始化")
            # 使用原始连接执行批量SQL，这样可以正确处理 %(param)s 格式的参数
            raw_conn = self.engine.raw_connection()
            cursor = raw_conn.cursor()
            try:
                # PyMySQL 的 executemany 支持 %(param)s 格式
                cursor.executemany(sql, params_list)
                raw_conn.commit()
                result = cursor.rowcount
                return result
            finally:
                cursor.close()
                raw_conn.close()
        except Exception as e:
            logger.error(f"批量SQL执行失败: {e}")
            raise

    def close(self):
        """关闭连接"""
        if self.engine:
            self.engine.dispose()
            logger.info("MySQL连接已关闭")


class _CursorWrapper:
    """Cursor包装类，用于延迟关闭连接和cursor"""

    def __init__(self, cursor, connection):
        self.cursor = cursor
        self.connection = connection
        self._closed = False

    def fetchone(self):
        """获取一行"""
        if self._closed:
            raise RuntimeError("Cursor已经关闭")
        return self.cursor.fetchone()

    def fetchall(self):
        """获取所有行"""
        if self._closed:
            raise RuntimeError("Cursor已经关闭")
        return self.cursor.fetchall()

    def fetchmany(self, size=None):
        """获取多行"""
        if self._closed:
            raise RuntimeError("Cursor已经关闭")
        return self.cursor.fetchmany(size)

    def close(self):
        """关闭cursor和连接"""
        if not self._closed:
            self.cursor.close()
            self.connection.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        """析构时自动关闭"""
        if not self._closed:
            import contextlib

            with contextlib.suppress(Exception):
                self.close()


class RedisManager:
    """Redis管理器（需要安装 redis 包）"""

    def __init__(self, config: dict):
        """
        初始化Redis连接

        Args:
            config: Redis配置

        Raises:
            ImportError: 如果 redis 包未安装
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis support requires 'redis' package. Install it with: pip install redis>=5.0.0"
            )

        self.config = config
        self.client: redis.Redis | None = None
        self._connect()

    def _connect(self):
        """建立连接"""
        try:
            host = self.config.get("host", "localhost")
            port = self.config.get("port", 6379)
            db = self.config.get("db", 0)
            password = self.config.get("password")

            # 如果配置中有URL，使用它
            url = self.config.get("url")

            if url:
                self.client = redis.from_url(url, decode_responses=True, max_connections=50)
            else:
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=True,
                    max_connections=50,
                )

            # 测试连接
            self.client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise

    def get(self, key: str) -> str | None:
        """获取值"""
        try:
            if self.client is None:
                raise RuntimeError("Redis未初始化")
            result = self.client.get(key)
            if isinstance(result, str):
                return result
            return None
        except Exception as e:
            logger.error(f"Redis GET失败: {e}")
            raise

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """
        设置值

        Args:
            key: 键
            value: 值
            ex: 过期时间（秒）

        Returns:
            是否成功
        """
        try:
            if self.client is None:
                raise RuntimeError("Redis未初始化")
            result = self.client.set(key, value, ex=ex)
            if isinstance(result, bool):
                return result
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET失败: {e}")
            raise

    def delete(self, *keys: str) -> int:
        """删除键"""
        try:
            if self.client is None:
                raise RuntimeError("Redis未初始化")
            result = self.client.delete(*keys)
            # redis-py 同步客户端返回 int
            return int(result)
        except Exception as e:
            logger.error(f"Redis DELETE失败: {e}")
            raise

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            if self.client is None:
                raise RuntimeError("Redis未初始化")
            result = self.client.exists(key)
            if isinstance(result, bool):
                return result
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXISTS失败: {e}")
            raise

    def lpush(self, key: str, *values: str) -> int:
        """列表左侧推入"""
        try:
            if self.client is None:
                raise RuntimeError("Redis未初始化")
            result = self.client.lpush(key, *values)
            # redis-py 同步客户端返回 int
            return int(result)
        except Exception as e:
            logger.error(f"Redis LPUSH失败: {e}")
            raise

    def rpop(self, key: str) -> str | None:
        """列表右侧弹出"""
        try:
            if self.client is None:
                raise RuntimeError("Redis未初始化")
            result = self.client.rpop(key)
            if isinstance(result, str):
                return result
            return None
        except Exception as e:
            logger.error(f"Redis RPOP失败: {e}")
            raise

    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()
            logger.info("Redis连接已关闭")


class DatabaseManager:
    """统一数据库管理器"""

    def __init__(self, config: dict):
        """
        初始化数据库管理器

        Args:
            config: 数据库配置
        """
        self.config = config
        self.db_type = config.get("type", "mongodb")
        self.db: MongoDBManager | MySQLManager | None = None
        self.redis: RedisManager | None = None

        # 初始化主数据库
        if self.db_type == "mongodb":
            mongodb_config = config.get("mongodb", {})
            self.db = MongoDBManager(mongodb_config)
        elif self.db_type == "mysql":
            mysql_config = config.get("mysql", {})
            self.db = MySQLManager(mysql_config)
        else:
            logger.warning(f"不支持的数据库类型: {self.db_type}")

        # 初始化Redis（如果配置了）
        redis_config = config.get("redis")
        if redis_config:
            try:
                self.redis = RedisManager(redis_config)
            except ImportError as e:
                logger.warning(f"Redis不可用: {e}")
                logger.info("如需使用Redis，请安装: pip install redis>=5.0.0")
            except Exception as e:
                logger.warning(f"Redis初始化失败: {e}")

    def get_db(self) -> MongoDBManager | MySQLManager:
        """获取数据库实例"""
        if self.db is None:
            raise RuntimeError("数据库未初始化")
        return self.db

    def get_redis(self) -> RedisManager | None:
        """获取Redis实例"""
        return self.redis

    def close(self):
        """关闭所有连接"""
        if self.db:
            self.db.close()
        if self.redis:
            self.redis.close()
