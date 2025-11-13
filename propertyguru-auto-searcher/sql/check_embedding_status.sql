-- =========================================================
-- 检查 Embedding 状态
-- =========================================================
-- 用途：检查数据库中 embedding 字段的维度和数据状态
-- 执行方式：psql -U property_user -d property_search -f check_embedding_status.sql
-- =========================================================

\echo '🔍 检查 Embedding 状态...'
\echo ''

-- 1. 检查 embedding 列信息
\echo '1️⃣ Embedding 列信息：'
SELECT 
    column_name,
    data_type,
    udt_name,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'listing_info' AND column_name = 'embedding';

\echo ''

-- 2. 检查 embedding 数据统计
\echo '2️⃣ Embedding 数据统计：'
SELECT 
    COUNT(*) as total_listings,
    COUNT(embedding) as has_embedding,
    COUNT(*) - COUNT(embedding) as missing_embedding,
    ROUND(100.0 * COUNT(embedding) / NULLIF(COUNT(*), 0), 2) as embedding_coverage_percent
FROM listing_info;

\echo ''

-- 3. 检查向量索引
\echo '3️⃣ 向量索引信息：'
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'listing_info' 
  AND indexname LIKE '%embedding%';

\echo ''

-- 4. 示例：查看第一条有 embedding 的记录
\echo '4️⃣ 示例记录（有 embedding 的第一条）：'
SELECT 
    listing_id,
    title,
    location,
    CASE 
        WHEN embedding IS NOT NULL THEN 'Yes (dimension: ' || array_length(embedding::float[], 1)::text || ')'
        ELSE 'No'
    END as has_embedding,
    created_at,
    updated_at
FROM listing_info
WHERE embedding IS NOT NULL
LIMIT 1;

\echo ''

-- 5. 检查 pgvector 扩展版本
\echo '5️⃣ pgvector 扩展信息：'
SELECT 
    extname as extension_name,
    extversion as version,
    extrelocatable as relocatable
FROM pg_extension
WHERE extname = 'vector';

\echo ''
\echo '✅ 检查完成！'
\echo ''

