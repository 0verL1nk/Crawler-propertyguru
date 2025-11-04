"""
数据库操作模块
封装PropertyGuru爬虫的数据库操作，支持批量插入
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert

from utils.logger import get_logger

from .database import DatabaseManager, MySQLManager
from .orm_models import (
    FAQORM,
    AmenityORM,
    ListingInfoORM,
    MediaItemORM,
    MortgageInfoORM,
)

if TYPE_CHECKING:
    from .models import FAQ, Amenity, ListingInfo, MediaItem, MortgageInfo, PropertyDetails

logger = get_logger("DBOperations")


class DBOperations:
    """数据库操作封装类"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化数据库操作

        Args:
            db_manager: DatabaseManager实例
        """
        self.db_manager = db_manager
        self.db = db_manager.get_db()

        # 数据缓冲队列（用于批量插入）
        self.listing_buffer: deque = deque(maxlen=100)
        self.media_buffer: deque = deque(maxlen=100)
        self.faq_buffer: deque = deque(maxlen=100)
        self.mortgage_buffer: deque = deque(maxlen=100)
        self.amenities_buffer: deque = deque(maxlen=100)

        # 检查是否是MySQL
        if not isinstance(self.db, MySQLManager):
            raise ValueError("当前只支持MySQL数据库")

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
            assert isinstance(self.db, MySQLManager)
            with self.db.get_session() as session:
                # 准备数据
                data_list = []
                for listing in listings:
                    data = listing.to_dict()
                    # 确保is_completed字段存在
                    if "is_completed" not in data:
                        data["is_completed"] = False
                    data_list.append(data)

                # 使用 MySQL 的 INSERT ... ON DUPLICATE KEY UPDATE
                stmt = insert(ListingInfoORM).values(data_list)
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
                    listed_date=stmt.inserted.listed_date,
                    listed_age=stmt.inserted.listed_age,
                    green_score_value=stmt.inserted.green_score_value,
                    green_score_max=stmt.inserted.green_score_max,
                    url=stmt.inserted.url,
                    # 注意：is_completed字段不在ON DUPLICATE KEY UPDATE中更新
                    # 只有通过mark_listing_completed方法才设置为true
                )
                session.execute(stmt)
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
            assert isinstance(self.db, MySQLManager)
            with self.db.get_session() as session:
                stmt = select(ListingInfoORM).where(ListingInfoORM.listing_id == details.listing_id)
                listing = session.scalar(stmt)
                if listing:
                    listing.property_details = (
                        details.property_details if details.property_details else None
                    )
                    listing.description = details.description
                    listing.description_title = details.description_title
                    # commit 由上下文管理器自动处理
                    logger.debug(f"更新房源详细信息: {details.listing_id}")
                    return True
                else:
                    logger.warning(f"房源不存在: {details.listing_id}")
                    return False

        except Exception as e:
            logger.error(f"保存房产详细信息失败: {e}")
            return False

    def save_mortgage_info(self, mortgage: MortgageInfo, flush: bool = False) -> bool:
        """
        保存房贷信息

        Args:
            mortgage: MortgageInfo对象
            flush: 是否立即刷新缓冲区

        Returns:
            是否成功
        """
        try:
            if not flush:
                self.mortgage_buffer.append(mortgage)
                if (
                    self.mortgage_buffer.maxlen is not None
                    and len(self.mortgage_buffer) >= self.mortgage_buffer.maxlen
                ):
                    return self._flush_mortgage_buffer()
                return True

            return self._flush_mortgage_buffer([mortgage])

        except Exception as e:
            logger.error(f"保存房贷信息失败: {e}")
            return False

    def _flush_mortgage_buffer(self, mortgages: list[MortgageInfo] | None = None) -> bool:
        """刷新房贷信息缓冲区"""
        if mortgages is None:
            if not self.mortgage_buffer:
                return True
            mortgages = list(self.mortgage_buffer)
            self.mortgage_buffer.clear()

        if not mortgages:
            return True

        try:
            assert isinstance(self.db, MySQLManager)
            with self.db.get_session() as session:
                # 准备数据
                data_list = [mortgage.to_dict() for mortgage in mortgages]

                # 使用 MySQL 的 INSERT ... ON DUPLICATE KEY UPDATE
                stmt = insert(MortgageInfoORM).values(data_list)
                stmt = stmt.on_duplicate_key_update(
                    monthly_repayment=stmt.inserted.monthly_repayment,
                    principal=stmt.inserted.principal,
                    interest=stmt.inserted.interest,
                    downpayment=stmt.inserted.downpayment,
                    loan_amount=stmt.inserted.loan_amount,
                    loan_to_value_percent=stmt.inserted.loan_to_value_percent,
                    property_price=stmt.inserted.property_price,
                    interest_rate=stmt.inserted.interest_rate,
                    loan_tenure_years=stmt.inserted.loan_tenure_years,
                    data_extracted_at=stmt.inserted.data_extracted_at,
                )
                session.execute(stmt)
                # commit 由上下文管理器自动处理

            logger.info(f"批量保存 {len(mortgages)} 条房贷信息")
            return True

        except Exception as e:
            logger.error(f"批量保存房贷信息失败: {e}")
            return False

    def save_faqs(self, faqs: list[FAQ], flush: bool = False) -> bool:
        """
        保存FAQs

        Args:
            faqs: FAQ对象列表
            flush: 是否立即刷新缓冲区

        Returns:
            是否成功
        """
        try:
            if not flush:
                self.faq_buffer.extend(faqs)
                if (
                    self.faq_buffer.maxlen is not None
                    and len(self.faq_buffer) >= self.faq_buffer.maxlen
                ):
                    return self._flush_faq_buffer()
                return True

            return self._flush_faq_buffer(faqs)

        except Exception as e:
            logger.error(f"保存FAQs失败: {e}")
            return False

    def _flush_faq_buffer(self, faqs: list[FAQ] | None = None) -> bool:
        """刷新FAQ缓冲区"""
        if faqs is None:
            if not self.faq_buffer:
                return True
            faqs = list(self.faq_buffer)
            self.faq_buffer.clear()

        if not faqs:
            return True

        try:
            assert isinstance(self.db, MySQLManager)
            with self.db.get_session() as session:
                # 准备数据
                data_list = [faq.to_dict() for faq in faqs]

                # 使用 MySQL 的 INSERT ... ON DUPLICATE KEY UPDATE
                # 注意：需要根据 listing_id + question 来判断唯一性
                stmt = insert(FAQORM).values(data_list)
                stmt = stmt.on_duplicate_key_update(
                    answer=stmt.inserted.answer,
                    updated_at=stmt.inserted.updated_at,
                )
                session.execute(stmt)
                # commit 由上下文管理器自动处理

            logger.info(f"批量保存 {len(faqs)} 条FAQ")
            return True

        except Exception as e:
            logger.error(f"批量保存FAQ失败: {e}")
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
        """刷新媒体缓冲区"""
        if media_items is None:
            if not self.media_buffer:
                return True
            media_items = list(self.media_buffer)
            self.media_buffer.clear()

        if not media_items:
            return True

        try:
            assert isinstance(self.db, MySQLManager)
            with self.db.get_session() as session:
                # 准备数据
                data_list = [media.to_dict() for media in media_items]

                # 使用 MySQL 的 INSERT ... ON DUPLICATE KEY UPDATE
                stmt = insert(MediaItemORM).values(data_list)
                stmt = stmt.on_duplicate_key_update(
                    media_url=stmt.inserted.media_url,
                    s3_key=stmt.inserted.s3_key,
                    original_url=stmt.inserted.original_url,
                    watermark_removed=stmt.inserted.watermark_removed,
                    position=stmt.inserted.position,
                )
                session.execute(stmt)
                # commit 由上下文管理器自动处理

            logger.info(f"批量保存 {len(media_items)} 条媒体记录")
            return True

        except Exception as e:
            logger.error(f"批量保存媒体记录失败: {e}")
            return False

    def save_amenities(self, amenities: list[Amenity], flush: bool = False) -> bool:
        """
        保存Amenities和Facilities

        Args:
            amenities: Amenity对象列表
            flush: 是否立即刷新缓冲区

        Returns:
            是否成功
        """
        try:
            if not flush:
                self.amenities_buffer.extend(amenities)
                if (
                    self.amenities_buffer.maxlen is not None
                    and len(self.amenities_buffer) >= self.amenities_buffer.maxlen
                ):
                    return self._flush_amenities_buffer()
                return True

            return self._flush_amenities_buffer(amenities)

        except Exception as e:
            logger.error(f"保存Amenities失败: {e}")
            return False

    def _flush_amenities_buffer(self, amenities: list[Amenity] | None = None) -> bool:
        """刷新Amenities缓冲区"""
        if amenities is None:
            if not self.amenities_buffer:
                return True
            amenities = list(self.amenities_buffer)
            self.amenities_buffer.clear()

        if not amenities:
            return True

        try:
            assert isinstance(self.db, MySQLManager)
            with self.db.get_session() as session:
                # 准备数据
                data_list = [amenity.to_dict() for amenity in amenities]

                # 使用 MySQL 的 INSERT ... ON DUPLICATE KEY UPDATE
                # 注意：表中有 UNIQUE KEY uk_listing_amenity (listing_id, amenity_type, name)
                stmt = insert(AmenityORM).values(data_list)
                stmt = stmt.on_duplicate_key_update(
                    listing_id=stmt.inserted.listing_id,
                )
                session.execute(stmt)
                # commit 由上下文管理器自动处理

            logger.info(f"批量保存 {len(amenities)} 条Amenities")
            return True

        except Exception as e:
            logger.error(f"批量保存Amenities失败: {e}")
            return False

    def flush_all(self):
        """刷新所有缓冲区"""
        self._flush_listing_buffer()
        self._flush_mortgage_buffer()
        self._flush_faq_buffer()
        self._flush_media_buffer()
        self._flush_amenities_buffer()
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
            # 类型断言：已在 __init__ 中检查只支持 MySQL
            assert isinstance(self.db, MySQLManager)
            with self.db.get_session() as session:
                stmt = select(ListingInfoORM).where(ListingInfoORM.listing_id == listing_id)
                listing = session.scalar(stmt)
                if listing:
                    listing.is_completed = True
                    # get_session 上下文管理器会自动 commit
                    logger.debug(f"标记房源为已完成: {listing_id}")
                    return True
                else:
                    logger.warning(f"房源不存在: {listing_id}")
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
            # 类型断言：已在 __init__ 中检查只支持 MySQL
            assert isinstance(self.db, MySQLManager)
            with self.db.get_session() as session:
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
            # 类型断言：已在 __init__ 中检查只支持 MySQL
            assert isinstance(self.db, MySQLManager)
            with self.db.get_session() as session:
                stmt = select(ListingInfoORM).where(ListingInfoORM.listing_id == listing_id)
                listing = session.scalar(stmt)
                if listing:
                    return listing.is_completed
                return False
        except Exception as e:
            logger.error(f"检查房源完成状态失败: {e}")
            return False
