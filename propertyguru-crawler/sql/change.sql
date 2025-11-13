-- =========================================================
-- 数据库结构变更脚本
-- 用于更新现有数据库，添加去水印相关字段
-- =========================================================

USE crawler_data;

-- =========================================================
-- 修改 listing_media 表
-- =========================================================

-- 1. 添加 original_url 字段（原始URL，用于后续回溯补偿去水印）
ALTER TABLE listing_media
ADD COLUMN original_url VARCHAR(500) DEFAULT NULL COMMENT '原始URL（网站抓取的URL，用于后续回溯补偿去水印）' AFTER s3_key;

-- 2. 添加 watermark_removed 字段（是否去水印成功）
ALTER TABLE listing_media
ADD COLUMN watermark_removed BOOLEAN DEFAULT FALSE COMMENT '是否去水印成功' AFTER original_url;

-- 3. 修改 media_url 和 s3_key 为可空（去水印失败时可能为空）
ALTER TABLE listing_media
MODIFY COLUMN media_url VARCHAR(500) DEFAULT NULL COMMENT '媒体在S3中的完整URL（去水印成功时才有值）';

ALTER TABLE listing_media
MODIFY COLUMN s3_key VARCHAR(255) DEFAULT NULL COMMENT '媒体在S3存储桶中的路径Key（去水印成功时才有值）';

-- 4. 将 existing original_url 数据设置为 media_url（如果有的话）
-- 注意：这个操作是可选的，如果表中已有数据且 original_url 字段已存在，可以跳过
-- UPDATE listing_media SET original_url = media_url WHERE original_url IS NULL;

-- 5. 添加唯一约束，防止同一房源同一原始URL重复插入图片
-- 注意：如果表中已有重复数据，需要先清理重复数据
-- 可以先查询重复数据：
-- SELECT listing_id, original_url, COUNT(*) as cnt
-- FROM listing_media
-- WHERE original_url IS NOT NULL
-- GROUP BY listing_id, original_url
-- HAVING cnt > 1;
--
-- 然后删除重复数据（保留最新的）：
-- DELETE t1 FROM listing_media t1
-- INNER JOIN listing_media t2
-- WHERE t1.id < t2.id
-- AND t1.listing_id = t2.listing_id
-- AND t1.original_url = t2.original_url;
ALTER TABLE listing_media
ADD UNIQUE KEY uk_listing_media_url (listing_id, original_url) COMMENT '同一房源同一原始URL只能有一条记录，防止重复存储';

-- =========================================================
-- 完成
-- =========================================================
