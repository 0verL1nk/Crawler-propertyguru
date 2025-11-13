-- =========================================================
-- 🏠 房产爬虫 + AI 搜索引擎 统一数据库初始化脚本
-- =========================================================
-- 适用于：本地 PostgreSQL、Supabase、AWS RDS 等
--
-- 架构说明：
--   - 爬虫项目：写入 listing_info, listing_media
--   - 搜索引擎：读取 listing_info，写入 search_logs, user_feedback
--   - 共享同一个数据库，数据实时同步
-- =========================================================

-- 1️⃣ 创建数据库（如果需要）
-- 注意：Supabase 等托管服务通常数据库已存在
-- CREATE DATABASE property_data WITH ENCODING 'UTF8';

-- =========================================================
-- 2️⃣ 启用扩展
-- =========================================================

-- 向量搜索扩展（AI 搜索引擎需要）
CREATE EXTENSION IF NOT EXISTS vector;

-- 全文搜索扩展（默认已包含）
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 三元组相似度搜索（可选）

-- PostGIS 扩展（高级地理查询，可选）
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- =========================================================
-- 3️⃣ 创建枚举类型
-- =========================================================
DO $$ BEGIN
    CREATE TYPE media_type_enum AS ENUM ('image', 'video');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- =========================================================
-- 4️⃣ 核心表：房源基本信息（爬虫写入，搜索引擎读取）
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

    -- PropertyDetails详细信息（JSONB格式）
    property_details JSONB DEFAULT NULL,
    description TEXT DEFAULT NULL,
    description_title VARCHAR(255) DEFAULT NULL,
    amenities JSONB DEFAULT NULL,
    facilities JSONB DEFAULT NULL,

    -- 爬虫状态
    is_completed BOOLEAN DEFAULT FALSE,

    -- ========== AI 搜索引擎字段 ==========
    -- 向量嵌入（OpenAI text-embedding-ada-002: 1536维）
    embedding vector(1536) DEFAULT NULL,

    -- 全文搜索向量（自动生成）
    search_vector tsvector,

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 表注释
COMMENT ON TABLE listing_info IS '房源基本信息表（爬虫写入，搜索引擎读取）';
COMMENT ON COLUMN listing_info.id IS '自增主键ID';
COMMENT ON COLUMN listing_info.listing_id IS '网站唯一房源ID';
COMMENT ON COLUMN listing_info.title IS '房源标题';
COMMENT ON COLUMN listing_info.price IS '房产价格（单位S$）';
COMMENT ON COLUMN listing_info.price_per_sqft IS '每平方英尺价格 (S$ psf)';
COMMENT ON COLUMN listing_info.bedrooms IS '卧室数量';
COMMENT ON COLUMN listing_info.bathrooms IS '浴室数量';
COMMENT ON COLUMN listing_info.area_sqft IS '面积 (平方英尺)';
COMMENT ON COLUMN listing_info.unit_type IS '单位类型，例如 HDB Flat, Condo';
COMMENT ON COLUMN listing_info.tenure IS '租赁类型';
COMMENT ON COLUMN listing_info.build_year IS '建造年份';
COMMENT ON COLUMN listing_info.mrt_station IS '最近地铁站';
COMMENT ON COLUMN listing_info.mrt_distance_m IS '距离地铁站距离（米）';
COMMENT ON COLUMN listing_info.location IS '地址';
COMMENT ON COLUMN listing_info.latitude IS '纬度';
COMMENT ON COLUMN listing_info.longitude IS '经度';
COMMENT ON COLUMN listing_info.listed_date IS '房源上架日期';
COMMENT ON COLUMN listing_info.listed_age IS '上架时长';
COMMENT ON COLUMN listing_info.green_score_value IS '绿色节能评分';
COMMENT ON COLUMN listing_info.green_score_max IS '绿色评分满分';
COMMENT ON COLUMN listing_info.url IS '详情页URL';
COMMENT ON COLUMN listing_info.property_details IS '房产详细信息（JSONB）';
COMMENT ON COLUMN listing_info.description IS '房产描述';
COMMENT ON COLUMN listing_info.description_title IS '描述标题';
COMMENT ON COLUMN listing_info.amenities IS '便利设施';
COMMENT ON COLUMN listing_info.facilities IS '公共设施';
COMMENT ON COLUMN listing_info.is_completed IS '爬虫是否完成';
COMMENT ON COLUMN listing_info.embedding IS 'AI向量嵌入（1536维，用于语义搜索）';
COMMENT ON COLUMN listing_info.search_vector IS '全文搜索向量（自动生成）';
COMMENT ON COLUMN listing_info.created_at IS '创建时间';
COMMENT ON COLUMN listing_info.updated_at IS '更新时间';

-- =========================================================
-- 5️⃣ 核心表：房源多媒体（爬虫写入）
-- =========================================================
CREATE TABLE IF NOT EXISTS listing_media (
    id BIGSERIAL PRIMARY KEY,
    listing_id BIGINT NOT NULL,

    -- 媒体信息
    media_type media_type_enum NOT NULL,
    media_url VARCHAR(500) DEFAULT NULL,
    s3_key VARCHAR(255) DEFAULT NULL,
    original_url VARCHAR(500) NOT NULL,
    watermark_removed BOOLEAN DEFAULT FALSE,
    position INTEGER DEFAULT NULL,

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

COMMENT ON TABLE listing_media IS '房源多媒体资源表（爬虫写入）';
COMMENT ON COLUMN listing_media.id IS '自增主键';
COMMENT ON COLUMN listing_media.listing_id IS '关联房源ID';
COMMENT ON COLUMN listing_media.media_type IS '媒体类型';
COMMENT ON COLUMN listing_media.media_url IS 'S3存储URL';
COMMENT ON COLUMN listing_media.s3_key IS 'S3路径Key';
COMMENT ON COLUMN listing_media.original_url IS '原始URL';
COMMENT ON COLUMN listing_media.watermark_removed IS '是否去水印';
COMMENT ON COLUMN listing_media.position IS '展示顺序';

-- =========================================================
-- 6️⃣ 搜索引擎表：搜索日志（搜索引擎写入）
-- =========================================================
CREATE TABLE IF NOT EXISTS search_logs (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    user_id VARCHAR(100),

    -- 解析后的过滤条件（JSONB存储）
    filters JSONB,

    -- 搜索结果
    result_count INTEGER DEFAULT 0,
    result_ids BIGINT[] DEFAULT '{}',

    -- 性能指标
    duration_ms INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE search_logs IS '搜索日志表（搜索引擎写入）';
COMMENT ON COLUMN search_logs.query IS '用户搜索查询';
COMMENT ON COLUMN search_logs.user_id IS '用户ID（可选）';
COMMENT ON COLUMN search_logs.filters IS '解析后的过滤条件';
COMMENT ON COLUMN search_logs.result_count IS '结果数量';
COMMENT ON COLUMN search_logs.result_ids IS '返回的房源ID列表';
COMMENT ON COLUMN search_logs.duration_ms IS '搜索耗时（毫秒）';

-- =========================================================
-- 7️⃣ 搜索引擎表：用户反馈（搜索引擎写入）
-- =========================================================
CREATE TABLE IF NOT EXISTS user_feedback (
    id BIGSERIAL PRIMARY KEY,
    search_log_id BIGINT,
    listing_id BIGINT NOT NULL,
    user_id VARCHAR(100),

    -- 反馈类型：click（点击）, like（喜欢）, dislike（不喜欢）
    feedback_type VARCHAR(20) NOT NULL,

    -- 额外信息
    comment TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 外键
    CONSTRAINT fk_feedback_search_log
        FOREIGN KEY (search_log_id)
        REFERENCES search_logs(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_feedback_listing
        FOREIGN KEY (listing_id)
        REFERENCES listing_info(listing_id)
        ON DELETE CASCADE
);

COMMENT ON TABLE user_feedback IS '用户反馈表（搜索引擎写入）';
COMMENT ON COLUMN user_feedback.search_log_id IS '关联的搜索日志ID';
COMMENT ON COLUMN user_feedback.listing_id IS '反馈的房源ID';
COMMENT ON COLUMN user_feedback.user_id IS '用户ID';
COMMENT ON COLUMN user_feedback.feedback_type IS '反馈类型：click/like/dislike';
COMMENT ON COLUMN user_feedback.comment IS '用户评论';

-- =========================================================
-- 8️⃣ 自动更新触发器
-- =========================================================

-- 自动更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_listing_info_updated_at ON listing_info;
CREATE TRIGGER update_listing_info_updated_at
    BEFORE UPDATE ON listing_info
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 自动更新全文搜索向量
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector =
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.unit_type, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.mrt_station, '')), 'B');
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_listing_search_vector ON listing_info;
CREATE TRIGGER update_listing_search_vector
    BEFORE INSERT OR UPDATE ON listing_info
    FOR EACH ROW
    EXECUTE FUNCTION update_search_vector();

-- =========================================================
-- 9️⃣ 创建索引
-- =========================================================

-- listing_info 基础索引
CREATE INDEX IF NOT EXISTS idx_listing_id ON listing_info (listing_id);
CREATE INDEX IF NOT EXISTS idx_listing_completed ON listing_info (is_completed);
CREATE INDEX IF NOT EXISTS idx_listing_price ON listing_info (price);
CREATE INDEX IF NOT EXISTS idx_listing_bedrooms ON listing_info (bedrooms);
CREATE INDEX IF NOT EXISTS idx_listing_bathrooms ON listing_info (bathrooms);
CREATE INDEX IF NOT EXISTS idx_listing_unit_type ON listing_info (unit_type);
CREATE INDEX IF NOT EXISTS idx_listing_created_at ON listing_info (created_at);

-- 地理坐标索引
CREATE INDEX IF NOT EXISTS idx_listing_latitude ON listing_info(latitude);
CREATE INDEX IF NOT EXISTS idx_listing_longitude ON listing_info(longitude);
CREATE INDEX IF NOT EXISTS idx_listing_lat_lng ON listing_info(latitude, longitude);

-- JSONB 字段索引（使用 GIN）
CREATE INDEX IF NOT EXISTS idx_listing_property_details ON listing_info USING GIN (property_details);
CREATE INDEX IF NOT EXISTS idx_listing_amenities ON listing_info USING GIN (amenities);
CREATE INDEX IF NOT EXISTS idx_listing_facilities ON listing_info USING GIN (facilities);

-- ========== AI 搜索引擎索引 ==========
-- 向量相似度搜索索引（HNSW 算法，速度快）
CREATE INDEX IF NOT EXISTS idx_listing_embedding ON listing_info
    USING hnsw (embedding vector_cosine_ops);

-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_listing_search_vector ON listing_info
    USING GIN (search_vector);

-- listing_media 索引
CREATE INDEX IF NOT EXISTS idx_media_listing ON listing_media (listing_id);
CREATE INDEX IF NOT EXISTS idx_media_type ON listing_media (media_type);
CREATE INDEX IF NOT EXISTS idx_media_watermark ON listing_media (watermark_removed);

-- search_logs 索引
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON search_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON search_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_filters ON search_logs USING GIN (filters);

-- user_feedback 索引
CREATE INDEX IF NOT EXISTS idx_feedback_listing ON user_feedback (listing_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON user_feedback (user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON user_feedback (feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON user_feedback (created_at);

-- =========================================================
-- 🔟 创建视图
-- =========================================================

-- 房源摘要视图（包含媒体统计）
CREATE OR REPLACE VIEW listing_summary AS
SELECT
    l.listing_id,
    l.title,
    l.price,
    l.bedrooms,
    l.bathrooms,
    l.area_sqft,
    l.unit_type,
    l.location,
    l.mrt_station,
    l.mrt_distance_m,
    l.is_completed,
    l.embedding IS NOT NULL as has_embedding,
    l.created_at,
    l.updated_at,
    -- 媒体统计
    COUNT(m.id) AS media_count,
    COUNT(m.id) FILTER (WHERE m.media_type = 'image') AS image_count,
    COUNT(m.id) FILTER (WHERE m.media_type = 'video') AS video_count
FROM listing_info l
LEFT JOIN listing_media m ON l.listing_id = m.listing_id
GROUP BY l.id, l.listing_id, l.title, l.price, l.bedrooms, l.bathrooms,
         l.area_sqft, l.unit_type, l.location, l.mrt_station, l.mrt_distance_m,
         l.is_completed, l.embedding, l.created_at, l.updated_at;

COMMENT ON VIEW listing_summary IS '房源摘要视图（包含媒体统计和嵌入状态）';

-- 热门搜索查询视图
CREATE OR REPLACE VIEW popular_searches AS
SELECT
    query,
    COUNT(*) as search_count,
    AVG(result_count) as avg_results,
    AVG(duration_ms) as avg_duration_ms,
    MAX(created_at) as last_searched
FROM search_logs
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY query
ORDER BY search_count DESC
LIMIT 100;

COMMENT ON VIEW popular_searches IS '热门搜索查询（最近30天）';

-- =========================================================
-- 1️⃣1️⃣ 数据库统计函数
-- =========================================================

CREATE OR REPLACE FUNCTION get_database_stats()
RETURNS TABLE (
    table_name TEXT,
    row_count BIGINT,
    table_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        'listing_info'::TEXT,
        COUNT(*)::BIGINT,
        pg_size_pretty(pg_total_relation_size('listing_info'))
    FROM listing_info

    UNION ALL

    SELECT
        'listing_media'::TEXT,
        COUNT(*)::BIGINT,
        pg_size_pretty(pg_total_relation_size('listing_media'))
    FROM listing_media

    UNION ALL

    SELECT
        'search_logs'::TEXT,
        COUNT(*)::BIGINT,
        pg_size_pretty(pg_total_relation_size('search_logs'))
    FROM search_logs

    UNION ALL

    SELECT
        'user_feedback'::TEXT,
        COUNT(*)::BIGINT,
        pg_size_pretty(pg_total_relation_size('user_feedback'))
    FROM user_feedback;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_database_stats() IS '获取数据库统计信息';

-- =========================================================
-- 🎉 初始化完成！
-- =========================================================

DO $$
DECLARE
    listing_count INTEGER;
    media_count INTEGER;
    search_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO listing_count FROM listing_info;
    SELECT COUNT(*) INTO media_count FROM listing_media;
    SELECT COUNT(*) INTO search_count FROM search_logs;

    RAISE NOTICE '';
    RAISE NOTICE '✅ 统一数据库初始化完成！';
    RAISE NOTICE '';
    RAISE NOTICE '📊 当前统计：';
    RAISE NOTICE '   房源数量: %', listing_count;
    RAISE NOTICE '   媒体数量: %', media_count;
    RAISE NOTICE '   搜索日志: %', search_count;
    RAISE NOTICE '';
    RAISE NOTICE '📋 表结构：';
    RAISE NOTICE '   核心数据表（爬虫写入，搜索引擎读取）：';
    RAISE NOTICE '     - listing_info (房源基本信息 + AI嵌入)';
    RAISE NOTICE '     - listing_media (多媒体资源)';
    RAISE NOTICE '';
    RAISE NOTICE '   搜索引擎专用表（搜索引擎写入）：';
    RAISE NOTICE '     - search_logs (搜索日志)';
    RAISE NOTICE '     - user_feedback (用户反馈)';
    RAISE NOTICE '';
    RAISE NOTICE '🔍 已启用功能：';
    RAISE NOTICE '   ✅ 向量搜索 (pgvector)';
    RAISE NOTICE '   ✅ 全文搜索 (tsvector + GIN)';
    RAISE NOTICE '   ✅ 地理坐标索引';
    RAISE NOTICE '   ✅ JSONB 查询支持';
    RAISE NOTICE '   ✅ 自动触发器';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 使用方式：';
    RAISE NOTICE '   爬虫项目: 写入 listing_info, listing_media';
    RAISE NOTICE '   搜索引擎: 读取 listing_info, 写入 search_logs, user_feedback';
    RAISE NOTICE '';
    RAISE NOTICE '📈 查看统计: SELECT * FROM get_database_stats();';
    RAISE NOTICE '';
END $$;
