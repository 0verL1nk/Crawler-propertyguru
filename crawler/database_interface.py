"""
数据库接口抽象层
定义统一的数据库操作接口，支持多种数据库实现（基于 SQLAlchemy ORM）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session, sessionmaker


class SQLDatabaseInterface(ABC):
    """
    SQL数据库抽象接口（基于 SQLAlchemy ORM）

    所有数据库操作通过 ORM 进行，统一使用 Session 管理
    """

    @abstractmethod
    def _connect(self) -> None:
        """
        建立数据库连接

        Raises:
            Exception: 连接失败时抛出异常
        """
        pass

    @abstractmethod
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取数据库会话（上下文管理器）

        使用示例:
            with db.get_session() as session:
                listing = session.query(ListingInfoORM).filter_by(listing_id=123).first()
                session.add(new_listing)

        Yields:
            SQLAlchemy Session

        Raises:
            RuntimeError: 数据库未初始化
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭数据库连接池"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        测试数据库连接是否正常

        Returns:
            连接是否正常
        """
        pass

    @property
    @abstractmethod
    def engine(self) -> Engine | None:
        """
        获取SQLAlchemy engine对象

        Returns:
            SQLAlchemy Engine 或 None（未初始化时）
        """
        pass

    @property
    @abstractmethod
    def Session(self) -> sessionmaker[Session] | None:
        """
        获取SQLAlchemy Session工厂

        Returns:
            sessionmaker[Session] 或 None（未初始化时）
        """
        pass

    @property
    @abstractmethod
    def db_type(self) -> str:
        """
        获取数据库类型

        Returns:
            数据库类型名称（如 'mysql', 'postgresql', 'supabase'）
        """
        pass
