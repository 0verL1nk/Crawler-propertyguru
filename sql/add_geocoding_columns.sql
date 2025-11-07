-- 添加地理坐标字段到 listing_info 表
-- 用于存储地址的经纬度信息

ALTER TABLE listing_info
ADD COLUMN latitude DECIMAL(10, 7) NULL COMMENT '纬度（7位小数精度约1.1cm）',
ADD COLUMN longitude DECIMAL(10, 7) NULL COMMENT '经度（7位小数精度约1.1cm）';

-- 为地理坐标字段添加索引以支持空间查询
CREATE INDEX idx_listing_info_latitude ON listing_info(latitude);
CREATE INDEX idx_listing_info_longitude ON listing_info(longitude);

-- 可选：如果需要更高效的空间查询，可以添加复合索引
CREATE INDEX idx_listing_info_lat_lng ON listing_info(latitude, longitude);
