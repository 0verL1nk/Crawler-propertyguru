-- =========================================================
-- 更新 Embedding 维度：1536 -> 1024
-- =========================================================
-- 用途：将数据库中的 embedding 字段从 1536 维修改为 1024 维
-- 执行方式：psql -U property_user -d property_search -f update_embedding_dimension.sql
-- =========================================================

\echo '🔄 开始更新 embedding 维度...'

-- 1. 删除旧的向量索引（如果存在）
\echo '1️⃣ 删除旧的向量索引...'
DROP INDEX IF EXISTS idx_listing_embedding;

-- 2. 删除旧的 embedding 列
\echo '2️⃣ 删除旧的 embedding 列...'
ALTER TABLE listing_info DROP COLUMN IF EXISTS embedding;

-- 3. 添加新的 1024 维 embedding 列
\echo '3️⃣ 添加新的 1024 维 embedding 列...'
ALTER TABLE listing_info ADD COLUMN embedding vector(1024) DEFAULT NULL;

-- 4. 添加列注释
\echo '4️⃣ 更新列注释...'
COMMENT ON COLUMN listing_info.embedding IS 'AI向量嵌入（1024维，用于语义搜索）';

-- 5. 重新创建向量索引（HNSW 索引）
\echo '5️⃣ 重新创建向量索引...'
CREATE INDEX idx_listing_embedding ON listing_info
    USING hnsw (embedding vector_cosine_ops);

-- 6. 查看更新结果
\echo '6️⃣ 验证更新结果...'
SELECT 
    column_name,
    data_type,
    udt_name,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'listing_info' AND column_name = 'embedding';

\echo ''
\echo '✅ Embedding 维度更新完成！'
\echo '   旧维度: 1536'
\echo '   新维度: 1024'
\echo ''
\echo '⚠️  注意：'
\echo '   - 所有旧的 embedding 数据已被清空'
\echo '   - 需要重新生成 1024 维的 embedding'
\echo '   - 使用 POST /api/v1/embeddings/batch 接口批量更新'
\echo ''

