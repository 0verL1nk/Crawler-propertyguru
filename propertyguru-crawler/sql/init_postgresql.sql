-- =========================================================
-- 🏠 房产爬虫数据库初始化脚本 - PostgreSQL 版本
-- =========================================================
-- 支持：本地 PostgreSQL、Supabase、AWS RDS、Azure Database 等
-- =========================================================

-- 1️⃣ 创建数据库（如果需要）
-- 注意：在 Supabase 等托管服务中，数据库通常已存在，直接使用即可
-- CREATE DATABASE crawler_data WITH ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8';

-- 连接到目标数据库
-- \c crawler_data;

-- =========================================================
-- 2️⃣ 创建枚举类型
-- =========================================================
DO $$ BEGIN
    CREATE TYPE media_type_enum AS ENUM ('image', 'video');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- =========================================================
-- 3️⃣ 房源基本信息表
-- =========================================================
CREATE TABLE IF NOT EXISTS listing_info (
    -- 主键
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL UNIQUE,

    -- 基础信息
    title VARCHAR(255) DEFAULT NULL,
    price DECIMAL(15,2) DEFAULT NULL,
    price_per_sqft DECIMAL(10,2) DEFAULT NULL,
    bedrooms INTEGER DEFAULT NULL,
    bathrooms INTEGER DEFAULT NULL,
    area_sqft DECIMAL(10,2) DEFAULT NULL,
    unit_type VARCHAR(100) DEFAULT NULL,
    tenure VARCHAR(100) DEFAULT NULL,
    build_year INTEGER DEFAULT NULL,

    -- 位置信息
    mrt_station VARCHAR(255) DEFAULT NULL,
    mrt_distance_m INTEGER DEFAULT NULL,
    location VARCHAR(255) DEFAULT NULL,
    latitude DECIMAL(10,7) DEFAULT NULL,
    longitude DECIMAL(10,7) DEFAULT NULL,

    -- 列表信息
    listed_date DATE DEFAULT NULL,
    listed_age VARCHAR(50) DEFAULT NULL,

    -- 附加信息
    green_score_value DECIMAL(3,1) DEFAULT NULL,
    green_score_max DECIMAL(3,1) DEFAULT 5.0,
    url VARCHAR(500) DEFAULT NULL,

    -- PropertyDetails详细信息（JSONB格式存储，因为字段不固定）
    property_details JSONB DEFAULT NULL,
    description TEXT DEFAULT NULL,
    description_title VARCHAR(255) DEFAULT NULL,
    amenities JSONB DEFAULT NULL,
    facilities JSONB DEFAULT NULL,
    is_completed BOOLEAN DEFAULT FALSE,

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 为 listing_info 表添加注释
COMMENT ON TABLE listing_info IS '房源基本信息表';
COMMENT ON COLUMN listing_info.id IS '自增主键ID';
COMMENT ON COLUMN listing_info.listing_id IS '网站唯一房源ID，例如60157325';
COMMENT ON COLUMN listing_info.title IS '房源标题，例如 "619D Punggol Drive"';
COMMENT ON COLUMN listing_info.price IS '房产价格（单位S$）';
COMMENT ON COLUMN listing_info.price_per_sqft IS '每平方英尺价格 (S$ psf)';
COMMENT ON COLUMN listing_info.bedrooms IS '卧室数量';
COMMENT ON COLUMN listing_info.bathrooms IS '浴室数量';
COMMENT ON COLUMN listing_info.area_sqft IS '面积 (平方英尺)';
COMMENT ON COLUMN listing_info.unit_type IS '单位类型，例如 HDB Flat, Condo';
COMMENT ON COLUMN listing_info.tenure IS '租赁类型，例如 "99-year Leasehold"';
COMMENT ON COLUMN listing_info.build_year IS '建造年份';
COMMENT ON COLUMN listing_info.mrt_station IS '最近地铁站，例如 "PE6 Oasis LRT Station"';
COMMENT ON COLUMN listing_info.mrt_distance_m IS '距离最近地铁站的距离（米）';
COMMENT ON COLUMN listing_info.location IS '地址';
COMMENT ON COLUMN listing_info.latitude IS '纬度（7位小数精度约1.1cm）';
COMMENT ON COLUMN listing_info.longitude IS '经度（7位小数精度约1.1cm）';
COMMENT ON COLUMN listing_info.listed_date IS '房源上架日期';
COMMENT ON COLUMN listing_info.listed_age IS '上架时长（例如 "18m ago"）';
COMMENT ON COLUMN listing_info.green_score_value IS '绿色节能评分值，例如 5.0';
COMMENT ON COLUMN listing_info.green_score_max IS '绿色评分满分，通常为5';
COMMENT ON COLUMN listing_info.url IS '详情页URL';
COMMENT ON COLUMN listing_info.property_details IS '房产详细信息（JSONB格式，包含所有动态字段）';
COMMENT ON COLUMN listing_info.description IS '房产描述（About this property）';
COMMENT ON COLUMN listing_info.description_title IS '房产描述标题';
COMMENT ON COLUMN listing_info.amenities IS '便利设施列表（Amenities）';
COMMENT ON COLUMN listing_info.facilities IS '公共设施列表（Common facilities）';
COMMENT ON COLUMN listing_info.is_completed IS '是否完成（整个流程成功后才为true）';
COMMENT ON COLUMN listing_info.created_at IS '记录创建时间';
COMMENT ON COLUMN listing_info.updated_at IS '最后更新时间';

-- =========================================================
-- 4️⃣ 房源多媒体表（图片/视频）
-- =========================================================
CREATE TABLE IF NOT EXISTS listing_media (
    -- 主键
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL,

    -- 媒体信息
    media_type media_type_enum NOT NULL,
    media_url VARCHAR(500) DEFAULT NULL,
    s3_key VARCHAR(255) DEFAULT NULL,
    original_url VARCHAR(500) NOT NULL,
    watermark_removed BOOLEAN DEFAULT FALSE,
    position INTEGER DEFAULT NULL,

    -- 时间戳
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    CONSTRAINT fk_listing_media_listing_id
        FOREIGN KEY (listing_id)
        REFERENCES listing_info(listing_id)
        ON DELETE CASCADE,

    -- 唯一约束
    CONSTRAINT uk_listing_media_url
        UNIQUE (listing_id, original_url)
);

-- 为 listing_media 表添加注释
COMMENT ON TABLE listing_media IS '房源多媒体资源表（图片和视频）';
COMMENT ON COLUMN listing_media.id IS '自增主键ID';
COMMENT ON COLUMN listing_media.listing_id IS '对应 listing_info 的 listing_id';
COMMENT ON COLUMN listing_media.media_type IS '媒体类型: image / video';
COMMENT ON COLUMN listing_media.media_url IS '媒体在S3中的完整URL（去水印成功时才有值）';
COMMENT ON COLUMN listing_media.s3_key IS '媒体在S3存储桶中的路径Key（去水印成功时才有值）';
COMMENT ON COLUMN listing_media.original_url IS '原始URL（网站抓取的URL，用于后续回溯补偿去水印）';
COMMENT ON COLUMN listing_media.watermark_removed IS '是否去水印成功';
COMMENT ON COLUMN listing_media.position IS '媒体展示顺序';
COMMENT ON COLUMN listing_media.uploaded_at IS '上传S3时间';

-- =========================================================
-- 5️⃣ 创建自动更新 updated_at 的触发器函数
-- =========================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为 listing_info 表创建触发器
DROP TRIGGER IF EXISTS update_listing_info_updated_at ON listing_info;
CREATE TRIGGER update_listing_info_updated_at
    BEFORE UPDATE ON listing_info
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =========================================================
-- 6️⃣ 创建索引
-- =========================================================

-- listing_info 表索引
CREATE INDEX IF NOT EXISTS idx_listing_id ON listing_info (listing_id);
CREATE INDEX IF NOT EXISTS idx_listing_completed ON listing_info (is_completed);
CREATE INDEX IF NOT EXISTS idx_listing_price ON listing_info (price);
CREATE INDEX IF NOT EXISTS idx_listing_bedrooms ON listing_info (bedrooms);
CREATE INDEX IF NOT EXISTS idx_listing_unit_type ON listing_info (unit_type);
CREATE INDEX IF NOT EXISTS idx_listing_created_at ON listing_info (created_at);

-- 地理坐标索引（支持空间查询）
CREATE INDEX IF NOT EXISTS idx_listing_info_latitude ON listing_info(latitude);
CREATE INDEX IF NOT EXISTS idx_listing_info_longitude ON listing_info(longitude);
CREATE INDEX IF NOT EXISTS idx_listing_info_lat_lng ON listing_info(latitude, longitude);

-- JSONB 字段索引（使用 GIN 索引支持 JSONB 查询）
CREATE INDEX IF NOT EXISTS idx_listing_property_details ON listing_info USING GIN (property_details);
CREATE INDEX IF NOT EXISTS idx_listing_amenities ON listing_info USING GIN (amenities);
CREATE INDEX IF NOT EXISTS idx_listing_facilities ON listing_info USING GIN (facilities);

-- listing_media 表索引
CREATE INDEX IF NOT EXISTS idx_media_listing ON listing_media (listing_id);
CREATE INDEX IF NOT EXISTS idx_media_type ON listing_media (media_type);
CREATE INDEX IF NOT EXISTS idx_media_watermark ON listing_media (watermark_removed);

-- =========================================================
-- 7️⃣ 创建 PostGIS 扩展（可选，用于高级地理空间查询）
-- =========================================================
-- 如果需要高级地理查询功能，取消下面的注释：
-- CREATE EXTENSION IF NOT EXISTS postgis;
--
-- 然后可以添加地理空间列和索引：
-- ALTER TABLE listing_info ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);
--
-- 创建触发器自动从经纬度生成 geometry
-- CREATE OR REPLACE FUNCTION update_geom_from_lat_lng()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
--         NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
--     END IF;
--     RETURN NEW;
-- END;
-- $$ language 'plpgsql';
--
-- DROP TRIGGER IF EXISTS update_listing_geom ON listing_info;
-- CREATE TRIGGER update_listing_geom
--     BEFORE INSERT OR UPDATE ON listing_info
--     FOR EACH ROW
--     EXECUTE FUNCTION update_geom_from_lat_lng();
--
-- 创建空间索引（大幅提升地理查询性能）
-- CREATE INDEX IF NOT EXISTS idx_listing_geom ON listing_info USING GIST (geom);

-- =========================================================
-- 8️⃣ 创建全文搜索索引（可选，用于搜索引擎）
-- =========================================================
-- 添加全文搜索列
ALTER TABLE listing_info ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- 创建触发器自动更新全文搜索向量
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector =
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.unit_type, '')), 'B');
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_listing_search_vector ON listing_info;
CREATE TRIGGER update_listing_search_vector
    BEFORE INSERT OR UPDATE ON listing_info
    FOR EACH ROW
    EXECUTE FUNCTION update_search_vector();

-- 创建 GIN 索引支持全文搜索
CREATE INDEX IF NOT EXISTS idx_listing_search_vector ON listing_info USING GIN (search_vector);

-- =========================================================
-- 9️⃣ 创建性能优化视图（可选）
-- =========================================================
CREATE OR REPLACE VIEW listing_summary AS
SELECT
    listing_id,
    title,
    price,
    bedrooms,
    bathrooms,
    area_sqft,
    unit_type,
    location,
    mrt_station,
    mrt_distance_m,
    is_completed,
    created_at,
    updated_at,
    -- 统计媒体数量
    (SELECT COUNT(*) FROM listing_media WHERE listing_media.listing_id = listing_info.listing_id) AS media_count,
    (SELECT COUNT(*) FROM listing_media WHERE listing_media.listing_id = listing_info.listing_id AND media_type = 'image') AS image_count,
    (SELECT COUNT(*) FROM listing_media WHERE listing_media.listing_id = listing_info.listing_id AND media_type = 'video') AS video_count
FROM listing_info;

COMMENT ON VIEW listing_summary IS '房源摘要视图（包含媒体统计）';

-- =========================================================
-- 🎉 初始化完成！
-- =========================================================
--
-- 使用示例：
--
-- 1. 本地 PostgreSQL:
--    psql -U postgres -d crawler_data -f init_postgresql.sql
--
-- 2. Supabase:
--    在 SQL Editor 中粘贴并执行此脚本
--
-- 3. 通过 Python:
--    from crawler.database_factory import get_database
--    db = get_database(db_type='postgresql')
--    with open('sql/init_postgresql.sql', 'r') as f:
--        sql = f.read()
--        with db.get_session() as session:
--            session.execute(text(sql))
--
-- =========================================================

-- 显示表结构信息
DO $$
DECLARE
    listing_count INTEGER;
    media_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO listing_count FROM listing_info;
    SELECT COUNT(*) INTO media_count FROM listing_media;

    RAISE NOTICE '✅ 数据库初始化完成！';
    RAISE NOTICE '📊 当前统计：';
    RAISE NOTICE '   - 房源数量: %', listing_count;
    RAISE NOTICE '   - 媒体数量: %', media_count;
    RAISE NOTICE '';
    RAISE NOTICE '📋 已创建的表：';
    RAISE NOTICE '   - listing_info (房源基本信息)';
    RAISE NOTICE '   - listing_media (多媒体资源)';
    RAISE NOTICE '';
    RAISE NOTICE '🔍 已创建的索引：';
    RAISE NOTICE '   - 基础索引（listing_id, is_completed 等）';
    RAISE NOTICE '   - 地理坐标索引（支持位置查询）';
    RAISE NOTICE '   - JSONB 索引（支持 JSON 字段查询）';
    RAISE NOTICE '   - 全文搜索索引（支持文本搜索）';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 可以开始使用了！';
END $$;
