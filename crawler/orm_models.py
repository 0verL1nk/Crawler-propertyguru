"""
SQLAlchemy ORM 模型定义
用于 PropertyGuru 爬虫的数据库操作
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DECIMAL,
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

if TYPE_CHECKING:
    from datetime import date


class Base(DeclarativeBase):
    """ORM 基类"""

    pass


class ListingInfoORM(Base):
    """房源基本信息表 ORM 模型"""

    __tablename__ = "listing_info"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, comment="网站唯一房源ID"
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="房源标题")
    price: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True, comment="房产价格（单位S$）"
    )
    price_per_sqft: Mapped[Decimal | None] = mapped_column(
        DECIMAL(10, 2), nullable=True, comment="每平方英尺价格"
    )
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="卧室数量")
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="浴室数量")
    area_sqft: Mapped[Decimal | None] = mapped_column(
        DECIMAL(10, 2), nullable=True, comment="面积（平方英尺）"
    )
    unit_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="单位类型")
    tenure: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="租赁类型")
    build_year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="建造年份")
    mrt_station: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="最近地铁站"
    )
    mrt_distance_m: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="距离最近地铁站的距离（米）"
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="地址")
    listed_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="房源上架日期")
    listed_age: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="上架时长")
    green_score_value: Mapped[Decimal | None] = mapped_column(
        DECIMAL(3, 1), nullable=True, comment="绿色节能评分值"
    )
    green_score_max: Mapped[Decimal | None] = mapped_column(
        DECIMAL(3, 1), nullable=True, default=Decimal("5.0"), comment="绿色评分满分"
    )
    url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="详情页URL")
    property_details: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="房产详细信息（JSON格式）"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="房产描述")
    description_title: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="房产描述标题"
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否完成"
    )


class MediaItemORM(Base):
    """房源多媒体表 ORM 模型"""

    __tablename__ = "listing_media"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="对应 listing_info 的 listing_id"
    )
    media_type: Mapped[str] = mapped_column(
        Enum("image", "video", name="media_type_enum"),
        nullable=False,
        comment="媒体类型: image / video",
    )
    media_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="媒体在S3中的完整URL（去水印成功时才有值）"
    )
    s3_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="媒体在S3存储桶中的路径Key（去水印成功时才有值）"
    )
    original_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="原始URL（网站抓取的URL，用于后续回溯补偿去水印）"
    )
    watermark_removed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否去水印成功"
    )
    position: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="媒体展示顺序")
    uploaded_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), comment="上传S3时间"
    )


class MortgageInfoORM(Base):
    """房贷计算信息表 ORM 模型"""

    __tablename__ = "mortgage_calculator"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="对应 listing_info 的 listing_id"
    )
    monthly_repayment: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True, comment="每月预计还款额 (S$)"
    )
    principal: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True, comment="本金部分 (S$)"
    )
    interest: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True, comment="利息部分 (S$)"
    )
    downpayment: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True, comment="首付款 (S$)"
    )
    loan_amount: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True, comment="贷款金额 (S$)"
    )
    loan_to_value_percent: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="贷款成数 (如75%)"
    )
    property_price: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True, comment="房产价格 (S$)"
    )
    interest_rate: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 2), nullable=True, comment="贷款利率 (%)"
    )
    loan_tenure_years: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="贷款年限 (年)"
    )
    data_extracted_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), comment="数据采集时间"
    )


class FAQORM(Base):
    """房源 FAQ 表 ORM 模型"""

    __tablename__ = "listing_faqs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="对应 listing_info 的 listing_id"
    )
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="FAQ 问题")
    answer: Mapped[str | None] = mapped_column(Text, nullable=True, comment="FAQ 答案")
    position: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="在页面中顺序")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), comment="记录创建时间"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="最后更新时间"
    )


class AmenityORM(Base):
    """房源设施表 ORM 模型"""

    __tablename__ = "listing_amenities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="对应 listing_info 的 listing_id"
    )
    amenity_type: Mapped[str] = mapped_column(
        Enum("amenity", "facility", name="amenity_type_enum"),
        nullable=False,
        comment="类型: amenity(便利设施) / facility(公共设施)",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="设施名称")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), comment="记录创建时间"
    )
