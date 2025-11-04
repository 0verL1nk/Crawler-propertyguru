-- =========================================================
-- 🏠 房产爬虫数据库初始化脚本（支持图片/视频 + FAQ）
-- =========================================================

-- 1️⃣ 创建数据库
CREATE DATABASE IF NOT EXISTS crawler_data
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE crawler_data;

-- =========================================================
-- 2️⃣ 房源基本信息表
-- =========================================================
CREATE TABLE IF NOT EXISTS listing_info (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键ID',
    listing_id BIGINT NOT NULL UNIQUE COMMENT '网站唯一房源ID，例如60157325',

    -- 基础信息
    title VARCHAR(255) DEFAULT NULL COMMENT '房源标题，例如 "619D Punggol Drive"',
    price DECIMAL(15,2) DEFAULT NULL COMMENT '房产价格（单位S$）',
    price_per_sqft DECIMAL(10,2) DEFAULT NULL COMMENT '每平方英尺价格 (S$ psf)',
    bedrooms INT DEFAULT NULL COMMENT '卧室数量',
    bathrooms INT DEFAULT NULL COMMENT '浴室数量',
    area_sqft DECIMAL(10,2) DEFAULT NULL COMMENT '面积 (平方英尺)',
    unit_type VARCHAR(100) DEFAULT NULL COMMENT '单位类型，例如 HDB Flat, Condo',
    tenure VARCHAR(100) DEFAULT NULL COMMENT '租赁类型，例如 "99-year Leasehold"',
    build_year INT DEFAULT NULL COMMENT '建造年份',

    -- 位置信息
    mrt_station VARCHAR(255) DEFAULT NULL COMMENT '最近地铁站，例如 "PE6 Oasis LRT Station"',
    mrt_distance_m INT DEFAULT NULL COMMENT '距离最近地铁站的距离（米）',
    location VARCHAR(255) DEFAULT NULL COMMENT '地址',

    -- 列表信息
    listed_date DATE DEFAULT NULL COMMENT '房源上架日期',
    listed_age VARCHAR(50) DEFAULT NULL COMMENT '上架时长（例如 "18m ago"）',

    -- 附加信息
    green_score_value DECIMAL(3,1) DEFAULT NULL COMMENT '绿色节能评分值，例如 5.0',
    green_score_max DECIMAL(3,1) DEFAULT 5.0 COMMENT '绿色评分满分，通常为5',
    url VARCHAR(500) DEFAULT NULL COMMENT '详情页URL',

    -- PropertyDetails详细信息（JSON格式存储，因为字段不固定）
    property_details JSON DEFAULT NULL COMMENT '房产详细信息（JSON格式，包含所有动态字段）',
    description TEXT DEFAULT NULL COMMENT '房产描述（About this property）',
    description_title VARCHAR(255) DEFAULT NULL COMMENT '房产描述标题',
    amenities JSON DEFAULT NULL COMMENT '便利设施列表（Amenities）',
    facilities JSON DEFAULT NULL COMMENT '公共设施列表（Common facilities）',
    is_completed BOOLEAN DEFAULT FALSE COMMENT '是否完成（整个流程成功后才为true）',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间'
) ENGINE=InnoDB COMMENT='房源基本信息表';

-- =========================================================
-- 3️⃣ 房源多媒体表（图片/视频）
-- =========================================================
CREATE TABLE IF NOT EXISTS listing_media (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键ID',
    listing_id BIGINT NOT NULL COMMENT '对应 listing_info 的 listing_id',
    media_type ENUM('image','video') NOT NULL COMMENT '媒体类型: image / video',
    media_url VARCHAR(500) DEFAULT NULL COMMENT '媒体在S3中的完整URL（去水印成功时才有值）',
    s3_key VARCHAR(255) DEFAULT NULL COMMENT '媒体在S3存储桶中的路径Key（去水印成功时才有值）',
    original_url VARCHAR(500) NOT NULL COMMENT '原始URL（网站抓取的URL，用于后续回溯补偿去水印）',
    watermark_removed BOOLEAN DEFAULT FALSE COMMENT '是否去水印成功',
    position INT DEFAULT NULL COMMENT '媒体展示顺序',
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传S3时间',
    FOREIGN KEY (listing_id) REFERENCES listing_info(listing_id) ON DELETE CASCADE,
    UNIQUE KEY uk_listing_media_url (listing_id, original_url) COMMENT '同一房源同一原始URL只能有一条记录，防止重复存储'
) ENGINE=InnoDB COMMENT='房源多媒体资源表（图片和视频）';



-- =========================================================
-- 6️⃣ 房源设施表（Amenities和Facilities）
-- =========================================================
CREATE TABLE IF NOT EXISTS listing_amenities (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键ID',
    listing_id BIGINT NOT NULL COMMENT '对应 listing_info 的 listing_id',
    amenity_type ENUM('amenity', 'facility') NOT NULL COMMENT '类型: amenity(便利设施) / facility(公共设施)',
    name VARCHAR(255) NOT NULL COMMENT '设施名称',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    FOREIGN KEY (listing_id) REFERENCES listing_info(listing_id) ON DELETE CASCADE,
    UNIQUE KEY uk_listing_amenity (listing_id, amenity_type, name)
) ENGINE=InnoDB COMMENT='房源设施表';

-- =========================================================
-- 7️⃣ 索引
-- =========================================================
CREATE INDEX idx_listing_id ON listing_info (listing_id);
CREATE INDEX idx_listing_completed ON listing_info (is_completed);
CREATE INDEX idx_media_listing ON listing_media (listing_id);
