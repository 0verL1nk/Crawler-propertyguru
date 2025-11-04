"""
数据模型定义
用于PropertyGuru爬虫的数据结构
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal


@dataclass
class ListingInfo:
    """房源基本信息"""

    listing_id: int
    title: str | None = None
    price: Decimal | None = None
    price_per_sqft: Decimal | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    area_sqft: Decimal | None = None
    unit_type: str | None = None
    tenure: str | None = None
    build_year: int | None = None
    mrt_station: str | None = None
    mrt_distance_m: int | None = None
    location: str | None = None
    listed_date: date | None = None
    listed_age: str | None = None
    green_score_value: Decimal | None = None
    green_score_max: Decimal | None = None
    url: str | None = None
    is_completed: bool = False  # 是否完成（整个流程成功后才为true）

    def to_dict(self) -> dict:
        """转换为字典，用于数据库插入"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None or key == "is_completed":  # is_completed即使是False也要包含
                result[key] = value
        return result


@dataclass
class PropertyDetails:
    """房产详细信息（从详情页提取）"""

    listing_id: int
    property_details: dict = field(default_factory=dict)  # 存储所有Property details字段（字典格式）
    description: str | None = None  # About this property的描述
    description_title: str | None = None  # About this property的标题

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result: dict[str, Any] = {"listing_id": self.listing_id}
        if self.property_details:
            result["property_details"] = self.property_details
        if self.description is not None:
            result["description"] = self.description
        if self.description_title is not None:
            result["description_title"] = self.description_title
        return result


@dataclass
class MortgageInfo:
    """房贷计算信息"""

    listing_id: int
    monthly_repayment: Decimal | None = None
    principal: Decimal | None = None
    interest: Decimal | None = None
    downpayment: Decimal | None = None
    loan_amount: Decimal | None = None
    loan_to_value_percent: Decimal | None = None
    property_price: Decimal | None = None
    interest_rate: Decimal | None = None
    loan_tenure_years: int | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {"listing_id": self.listing_id}
        for key, value in self.__dict__.items():
            if key != "listing_id" and value is not None:
                result[key] = value
        return result


@dataclass
class FAQ:
    """FAQ数据"""

    listing_id: int
    question: str
    answer: str | None = None
    position: int | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "listing_id": self.listing_id,
            "question": self.question,
        }
        if self.answer is not None:
            result["answer"] = self.answer
        if self.position is not None:
            result["position"] = self.position
        return result


@dataclass
class MediaItem:
    """媒体数据（图片/视频）"""

    listing_id: int
    media_type: str  # 'image' or 'video'
    original_url: str  # 原始URL（网站抓取的URL，用于后续回溯补偿去水印）
    media_url: str | None = None  # S3 URL（去水印成功时才有值）
    s3_key: str | None = None  # S3 key（去水印成功时才有值）
    watermark_removed: bool = False  # 是否去水印成功
    position: int | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "listing_id": self.listing_id,
            "media_type": self.media_type,
            "original_url": self.original_url,
            "watermark_removed": self.watermark_removed,
        }
        if self.media_url is not None:
            result["media_url"] = self.media_url
        if self.s3_key is not None:
            result["s3_key"] = self.s3_key
        if self.position is not None:
            result["position"] = self.position
        return result


@dataclass
class Amenity:
    """设施/便利设施"""

    listing_id: int
    amenity_type: str  # 'amenity' or 'facility'
    name: str

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "listing_id": self.listing_id,
            "amenity_type": self.amenity_type,
            "name": self.name,
        }
