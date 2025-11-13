"""
数据库操作模块
封装PropertyGuru爬虫的数据库操作，支持批量插入
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from sqlalchemy import func, insert, select

from utils.logger import get_logger

from .legacy import DatabaseManager, MySQLManager
from .interface import SQLDatabaseInterface
from .orm_models import ListingInfoORM, MediaItemORM

if TYPE_CHECKING:
    from ..models import ListingInfo, MediaItem, PropertyDetails

logger = get_logger("DBOperations")


class DBOperations:
    """数据库操作封装类"""

    def __init__(self, db_manager: DatabaseManager | SQLDatabaseInterface):
        """
        初始化数据库操作

        Args:
            db_manager: DatabaseManager实例或SQLDatabaseInterface实例
        """
        # 兼容新旧接口
        if isinstance(db_manager, SQLDatabaseInterface):
            # 新接口：直接使用 SQLDatabaseInterface
            self.sql_db: SQLDatabaseInterface | None = db_manager
            self.db_manager: DatabaseManager | None = None
            self.db: MySQLManager | None = None
            logger.debug(f"使用新的 SQL 数据库接口: {db_manager.db_type}")
        else:
            # 旧接口：使用 DatabaseManager
            self.db_manager = db_manager
            self.sql_db = None
            self.db = db_manager.get_db()  # type: ignore[assignment]

            # 检查是否是MySQL
            if not isinstance(self.db, MySQLManager):
                raise ValueError("旧接口当前只支持MySQL数据库")
            logger.debug("使用旧的 DatabaseManager 接口")

        # 数据缓冲队列（用于批量插入）
        self.listing_buffer: deque = deque(maxlen=100)
        self.media_buffer: deque = deque(maxlen=100)

    def _get_session(self):
        """获取数据库 session 上下文管理器（兼容新旧接口）"""
        if self.sql_db:
            return self.sql_db.get_session()
        else:
            assert self.db is not None
            return self.db.get_session()

    def _get_db_type(self) -> str:
        """获取数据库类型"""
        if self.sql_db:
            return self.sql_db.db_type
        elif isinstance(self.db, MySQLManager):
            return "mysql"
        else:
            return "unknown"

    def save_listing_info(self, listing: ListingInfo, flush: bool = False) -> bool:
        """
        保存房源基本信息

        Args:
            listing: ListingInfo对象
            flush: 是否立即刷新缓冲区

        Returns:
            是否成功
        """
        try:
            if not flush:
                self.listing_buffer.append(listing)
                # 如果缓冲区满了，自动刷新
                if (
                    self.listing_buffer.maxlen is not None
                    and len(self.listing_buffer) >= self.listing_buffer.maxlen
                ):
                    return self._flush_listing_buffer()
                return True

            return self._flush_listing_buffer([listing])

        except Exception as e:
            logger.error(f"保存房源信息失败: {e}")
            return False

    def _flush_listing_buffer(self, listings: list[ListingInfo] | None = None) -> bool:
        """刷新房源信息缓冲区"""
        if listings is None:
            if not self.listing_buffer:
                return True
            listings = list(self.listing_buffer)
            self.listing_buffer.clear()

        if not listings:
            return True

        try:
            with self._get_session() as session:
                # 准备数据
                data_list = []
                for listing in listings:
                    data = listing.to_dict()
                    # 确保is_completed字段存在
                    if "is_completed" not in data:
                        data["is_completed"] = False
                    data_list.append(data)

                db_type = self._get_db_type()

                if db_type == "mysql":
                    # 使用 MySQL 的 INSERT ... ON DUPLICATE KEY UPDATE
                    from sqlalchemy.dialects.mysql import insert as mysql_insert

                    stmt = mysql_insert(ListingInfoORM).values(data_list)
                    stmt = stmt.on_duplicate_key_update(
                        title=stmt.inserted.title,
                        price=stmt.inserted.price,
                        price_per_sqft=stmt.inserted.price_per_sqft,
                        bedrooms=stmt.inserted.bedrooms,
                        bathrooms=stmt.inserted.bathrooms,
                        area_sqft=stmt.inserted.area_sqft,
                        unit_type=stmt.inserted.unit_type,
                        tenure=stmt.inserted.tenure,
                        build_year=stmt.inserted.build_year,
                        mrt_station=stmt.inserted.mrt_station,
                        mrt_distance_m=stmt.inserted.mrt_distance_m,
                        location=stmt.inserted.location,
                        latitude=stmt.inserted.latitude,
                        longitude=stmt.inserted.longitude,
                        listed_date=stmt.inserted.listed_date,
                        listed_age=stmt.inserted.listed_age,
                        green_score_value=stmt.inserted.green_score_value,
                        green_score_max=stmt.inserted.green_score_max,
                        url=stmt.inserted.url,
                        # 注意：is_completed字段不在ON DUPLICATE KEY UPDATE中更新
                        # 只有通过mark_listing_completed方法才设置为true
                    )
                    session.execute(stmt)

                elif db_type == "postgresql":
                    # 使用 PostgreSQL 的 INSERT ... ON CONFLICT DO UPDATE
                    from sqlalchemy.dialects.postgresql import insert as pg_insert

                    pg_stmt = pg_insert(ListingInfoORM).values(data_list)
                    pg_stmt = pg_stmt.on_conflict_do_update(
                        index_elements=["listing_id"],
                        set_={
                            "title": pg_stmt.excluded.title,
                            "price": pg_stmt.excluded.price,
                            "price_per_sqft": pg_stmt.excluded.price_per_sqft,
                            "bedrooms": pg_stmt.excluded.bedrooms,
                            "bathrooms": pg_stmt.excluded.bathrooms,
                            "area_sqft": pg_stmt.excluded.area_sqft,
                            "unit_type": pg_stmt.excluded.unit_type,
                            "tenure": pg_stmt.excluded.tenure,
                            "build_year": pg_stmt.excluded.build_year,
                            "mrt_station": pg_stmt.excluded.mrt_station,
                            "mrt_distance_m": pg_stmt.excluded.mrt_distance_m,
                            "location": pg_stmt.excluded.location,
                            "latitude": pg_stmt.excluded.latitude,
                            "longitude": pg_stmt.excluded.longitude,
                            "listed_date": pg_stmt.excluded.listed_date,
                            "listed_age": pg_stmt.excluded.listed_age,
                            "green_score_value": pg_stmt.excluded.green_score_value,
                            "green_score_max": pg_stmt.excluded.green_score_max,
                            "url": pg_stmt.excluded.url,
                            # 注意：is_completed字段不更新
                        },
                    )
                    session.execute(pg_stmt)
                else:
                    raise ValueError(f"不支持的数据库类型: {db_type}")

                # commit 由上下文管理器自动处理

            logger.info(f"批量保存 {len(listings)} 条房源信息")
            return True

        except Exception as e:
            logger.error(f"批量保存房源信息失败: {e}")
            return False

    def save_property_details(self, details: PropertyDetails) -> bool:
        """
        保存房产详细信息（更新到listing_info表）

        Args:
            details: PropertyDetails对象

        Returns:
            是否成功
        """
        try:
            logger.debug(
                f"开始保存PropertyDetails - listing_id: {details.listing_id}, "
                f"property_details: {bool(details.property_details)}, "
                f"description: {bool(details.description)}, "
                f"description_title: {bool(details.description_title)}, "
                f"amenities: {bool(details.amenities)}, "
                f"facilities: {bool(details.facilities)}"
            )
            with self._get_session() as session:
                stmt = select(ListingInfoORM).where(ListingInfoORM.listing_id == details.listing_id)
                listing = session.scalar(stmt)
                if listing:
                    listing.property_details = (
                        details.property_details if details.property_details else None
                    )
                    listing.description = details.description
                    listing.description_title = details.description_title
                    listing.amenities = details.amenities if details.amenities else None
                    listing.facilities = details.facilities if details.facilities else None
                    # commit 由上下文管理器自动处理
                    logger.info(
                        f"更新房源详细信息成功: {details.listing_id}, "
                        f"property_details字段数: {len(details.property_details) if details.property_details else 0}, "
                        f"description: {len(details.description) if details.description else 0} chars, "
                        f"amenities: {len(details.amenities) if details.amenities else 0} 项, "
                        f"facilities: {len(details.facilities) if details.facilities else 0} 项"
                    )
                    return True
                else:
                    logger.warning(f"房源不存在，无法保存PropertyDetails: {details.listing_id}")
                    return False

        except Exception as e:
            logger.error(f"保存房产详细信息失败: {e}", exc_info=True)
            return False

    def save_media(self, media_items: list[MediaItem], flush: bool = False) -> bool:
        """
        保存媒体记录

        Args:
            media_items: MediaItem对象列表
            flush: 是否立即刷新缓冲区

        Returns:
            是否成功
        """
        try:
            if not flush:
                self.media_buffer.extend(media_items)
                if (
                    self.media_buffer.maxlen is not None
                    and len(self.media_buffer) >= self.media_buffer.maxlen
                ):
                    return self._flush_media_buffer()
                return True

            return self._flush_media_buffer(media_items)

        except Exception as e:
            logger.error(f"保存媒体记录失败: {e}")
            return False

    def _flush_media_buffer(self, media_items: list[MediaItem] | None = None) -> bool:
        """
        刷新媒体缓冲区

        注意：为避免auto_increment跳变，先查询已存在的记录，只插入不存在的记录
        """
        if media_items is None:
            if not self.media_buffer:
                return True
            media_items = list(self.media_buffer)
            self.media_buffer.clear()

        if not media_items:
            return True

        try:
            with self._get_session() as session:
                data_list = [media.to_dict() for media in media_items]
                to_insert, to_update = self._separate_media_items(session, data_list)
                self._insert_new_media(session, to_insert)
                self._update_existing_media(session, to_update)
                logger.info(
                    f"批量保存媒体记录完成 - 新增: {len(to_insert)}, 更新: {len(to_update)}"
                )
            return True

        except Exception as e:
            logger.error(f"批量保存媒体记录失败: {e}", exc_info=True)
            return False

    def _separate_media_items(
        self, session, data_list: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        """分离需要插入和更新的媒体记录"""
        if not data_list:
            return [], []

        # 先去重：对于相同的 (listing_id, original_url) 组合，只保留第一个
        seen_keys: set[tuple[int, str]] = set()
        unique_data_list = []
        for item in data_list:
            key = (item["listing_id"], item["original_url"])
            if key not in seen_keys:
                seen_keys.add(key)
                unique_data_list.append(item)
            else:
                logger.debug(
                    f"跳过重复的媒体URL: listing_id={item['listing_id']}, url={item['original_url']}"
                )

        listing_ids = list({item["listing_id"] for item in unique_data_list})
        original_urls = [item["original_url"] for item in unique_data_list]

        existing_records = session.execute(
            select(MediaItemORM.listing_id, MediaItemORM.original_url).where(
                MediaItemORM.listing_id.in_(listing_ids),
                MediaItemORM.original_url.in_(original_urls),
            )
        ).all()

        existing_set = {(r.listing_id, r.original_url) for r in existing_records}
        to_insert = []
        to_update = []

        for item in unique_data_list:
            key = (item["listing_id"], item["original_url"])
            if key in existing_set:
                to_update.append(item)
            else:
                to_insert.append(item)

        return to_insert, to_update

    def _insert_new_media(self, session, to_insert: list[dict]):
        """插入新媒体记录"""
        if to_insert:
            stmt = insert(MediaItemORM).values(to_insert)
            session.execute(stmt)
            logger.debug(f"插入 {len(to_insert)} 条新媒体记录")

    def _update_existing_media(self, session, to_update: list[dict]):
        """更新已存在的媒体记录"""
        if to_update:
            for item in to_update:
                existing_record = session.scalar(
                    select(MediaItemORM).where(
                        MediaItemORM.listing_id == item["listing_id"],
                        MediaItemORM.original_url == item["original_url"],
                    )
                )
                if existing_record:
                    existing_record.media_url = item.get("media_url")
                    existing_record.s3_key = item.get("s3_key")
                    existing_record.watermark_removed = item.get("watermark_removed", False)
                    existing_record.position = item.get("position")
            logger.debug(f"更新 {len(to_update)} 条已存在的媒体记录")

    def flush_all(self):
        """刷新所有缓冲区"""
        self._flush_listing_buffer()
        self._flush_media_buffer()
        logger.info("所有缓冲区已刷新")

    def mark_listing_completed(self, listing_id: int) -> bool:
        """
        标记房源为已完成（使用 ORM）

        Args:
            listing_id: 房源ID

        Returns:
            是否成功
        """
        try:
            # 第一次尝试：查询并标记
            with self._get_session() as session:
                stmt = select(ListingInfoORM).where(ListingInfoORM.listing_id == listing_id)
                listing = session.scalar(stmt)
                if listing:
                    listing.is_completed = True
                    # get_session 上下文管理器会自动 commit
                    logger.debug(f"标记房源为已完成: {listing_id}")
                    return True

            # 如果房源不存在，可能是缓冲区还没刷新，尝试刷新后再查询
            # 这种情况不应该报warning，因为可能是正常的时序问题
            logger.debug(f"房源不存在，可能是缓冲区未刷新: {listing_id}，将尝试刷新缓冲区")
            # 刷新listing缓冲区（这会创建新的session）
            self._flush_listing_buffer()

            # 第二次尝试：刷新缓冲区后重新查询
            with self._get_session() as session:
                stmt = select(ListingInfoORM).where(ListingInfoORM.listing_id == listing_id)
                listing = session.scalar(stmt)
                if listing:
                    listing.is_completed = True
                    logger.debug(f"刷新缓冲区后成功标记房源为已完成: {listing_id}")
                    return True
                else:
                    # 如果刷新后还是不存在，说明确实有问题
                    logger.warning(f"房源不存在（刷新缓冲区后仍不存在）: {listing_id}")
                    return False
        except Exception as e:
            logger.error(f"标记房源完成状态失败: {e}")
            return False

    def check_listing_exists(self, listing_id: int) -> bool:
        """
        检查房源是否已存在（包括是否完成）（使用 ORM）

        Args:
            listing_id: 房源ID

        Returns:
            是否存在
        """
        try:
            with self._get_session() as session:
                stmt = select(ListingInfoORM).where(ListingInfoORM.listing_id == listing_id)
                result = session.scalar(stmt)
                return result is not None
        except Exception as e:
            logger.error(f"检查房源是否存在失败: {e}")
            return False

    def check_listing_completed(self, listing_id: int) -> bool:
        """
        检查房源是否已完成（使用 ORM）

        Args:
            listing_id: 房源ID

        Returns:
            是否完成
        """
        try:
            with self._get_session() as session:
                stmt = select(ListingInfoORM).where(ListingInfoORM.listing_id == listing_id)
                listing = session.scalar(stmt)
                if listing:
                    return bool(listing.is_completed)
                return False
        except Exception as e:
            logger.error(f"检查房源完成状态失败: {e}")
            return False

    def batch_check_listings_status(self, listing_ids: list[int]) -> dict[int, dict[str, bool]]:
        """
        批量检查多个房源的状态（使用 ORM）

        Args:
            listing_ids: 房源ID列表

        Returns:
            字典，key为listing_id，value为包含exists和is_completed的字典
            例如: {123: {"exists": True, "is_completed": True}, ...}
        """
        try:
            if not listing_ids:
                return {}

            with self._get_session() as session:
                stmt = select(ListingInfoORM).where(ListingInfoORM.listing_id.in_(listing_ids))
                results = session.scalars(stmt).all()

                # 构建结果字典
                status_dict: dict[int, dict[str, bool]] = {}
                found_ids = set()
                for listing in results:
                    status_dict[listing.listing_id] = {
                        "exists": True,
                        "is_completed": listing.is_completed,
                    }
                    found_ids.add(listing.listing_id)

                # 对于未找到的房源，标记为不存在
                for listing_id in listing_ids:
                    if listing_id not in found_ids:
                        status_dict[listing_id] = {
                            "exists": False,
                            "is_completed": False,
                        }

                return status_dict
        except Exception as e:
            logger.error(f"批量检查房源状态失败: {e}")
            # 返回空字典，外部可以用默认值处理
            return {}

    def count_completed_listings(self) -> int:
        """
        统计数据库中已完成房源的数量

        Returns:
            已完成房源数量
        """
        try:
            with self._get_session() as session:
                stmt = select(func.count(ListingInfoORM.listing_id)).where(
                    ListingInfoORM.is_completed == True  # noqa: E712
                )
                count = session.scalar(stmt)
                return int(count) if count is not None else 0
        except Exception as e:
            logger.error(f"统计已完成房源数量失败: {e}")
            return 0
