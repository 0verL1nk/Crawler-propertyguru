# 地理编码功能

## 概述

地理编码（Geocoding）功能可以将新加坡地址转换为地理坐标（纬度和经度），便于进行地图可视化、空间分析和基于位置的查询。

## 功能特性

- ✅ 自动将 `location` 字段转换为 `latitude` 和 `longitude`
- ✅ 使用 OpenStreetMap Nominatim API（免费，无需 API Key）
- ✅ 专门针对新加坡地址优化
- ✅ 自动遵守 API 速率限制（每秒最多1次请求）
- ✅ 错误处理和日志记录

## 数据库字段

在 `listing_info` 表中新增了两个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `latitude` | DECIMAL(10,7) | 纬度（7位小数精度约1.1cm） |
| `longitude` | DECIMAL(10,7) | 经度（7位小数精度约1.1cm） |

## 数据库迁移

### 对于新项目

运行初始化脚本，它已经包含了地理坐标字段：

```bash
mysql -u root -p < sql/init.sql
```

### 对于现有数据库

运行迁移脚本添加地理坐标字段：

```bash
mysql -u root -p crawler_data < sql/add_geocoding_columns.sql
```

## 使用示例

### 基本用法

地理编码会在解析房产信息时自动执行：

```python
from crawler.parsers import ListPageParser

parser = ListPageParser()
listing_info = parser.parse_listing_card(card_element)

# listing_info 现在包含地理坐标
print(f"地址: {listing_info.location}")
print(f"坐标: ({listing_info.latitude}, {listing_info.longitude})")
```

### 手动调用

也可以单独使用地理编码功能：

```python
from utils.geocoding import geocode_address

# 单个地址
lat, lon = geocode_address("32 Lentor Hills Road")
print(f"纬度: {lat}, 经度: {lon}")

# 批量地址
from utils.geocoding import batch_geocode_addresses

addresses = [
    "32 Lentor Hills Road",
    "619D Punggol Drive",
    "123 Orchard Road"
]

results = batch_geocode_addresses(addresses)
for address, (lat, lon) in results.items():
    print(f"{address} -> ({lat}, {lon})")
```

## API 说明

### geocode_address()

将单个地址转换为地理坐标。

**参数：**
- `address` (str): 地址字符串，如 "32 Lentor Hills Road"
- `country` (str): 国家名称，默认为 "Singapore"
- `timeout` (int): 请求超时时间（秒），默认为 10

**返回：**
- `tuple[Decimal | None, Decimal | None]`: (纬度, 经度)，失败时返回 (None, None)

**示例：**
```python
lat, lon = geocode_address("32 Lentor Hills Road")
```

### batch_geocode_addresses()

批量地理编码多个地址。

**参数：**
- `addresses` (list[str]): 地址列表
- `country` (str): 国家名称，默认为 "Singapore"
- `delay` (float): 每次请求之间的延迟（秒），默认为 1.0

**返回：**
- `dict[str, tuple[Decimal | None, Decimal | None]]`: 地址到坐标的映射

**示例：**
```python
addresses = ["32 Lentor Hills Road", "619D Punggol Drive"]
results = batch_geocode_addresses(addresses)
```

## 地理坐标精度

- 使用 `DECIMAL(10,7)` 类型存储坐标
- 7位小数精度约为 1.1cm
- 适合新加坡的坐标范围（纬度 1.2-1.5°，经度 103.6-104.0°）

## 性能考虑

### 速率限制

Nominatim API 要求：
- 最多每秒1次请求
- 必须设置合适的 User-Agent
- 本工具已自动实现速率限制

### 优化建议

1. **缓存结果**：相同地址不需要重复查询
2. **批量处理**：使用 `batch_geocode_addresses()` 处理多个地址
3. **异步处理**：对于大量数据，考虑后台异步处理

### 示例：缓存实现

```python
from functools import lru_cache
from utils.geocoding import geocode_address

@lru_cache(maxsize=1000)
def cached_geocode(address: str) -> tuple[Decimal | None, Decimal | None]:
    """带缓存的地理编码"""
    return geocode_address(address)
```

## 空间查询

有了地理坐标后，可以进行各种空间查询：

### 查找附近的房产

```sql
-- 查找坐标 (1.3521, 103.8198) 附近 1km 内的房产
SELECT
    listing_id,
    location,
    latitude,
    longitude,
    (
        6371 * acos(
            cos(radians(1.3521))
            * cos(radians(latitude))
            * cos(radians(longitude) - radians(103.8198))
            + sin(radians(1.3521))
            * sin(radians(latitude))
        )
    ) AS distance_km
FROM listing_info
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL
HAVING distance_km <= 1
ORDER BY distance_km;
```

### 查找特定区域内的房产

```sql
-- 查找新加坡市中心区域的房产（示例范围）
SELECT
    listing_id,
    location,
    latitude,
    longitude
FROM listing_info
WHERE latitude BETWEEN 1.26 AND 1.32
  AND longitude BETWEEN 103.82 AND 103.88;
```

## 故障排查

### 地理编码失败

如果地理编码失败（返回 None），可能的原因：

1. **网络问题**：检查网络连接和防火墙设置
2. **API 超时**：增加 `timeout` 参数
3. **地址格式错误**：确保地址格式正确且完整
4. **速率限制**：确保没有超过 API 速率限制

### 查看日志

地理编码过程会记录详细日志：

```python
# 日志示例
# DEBUG: 开始地理编码: 32 Lentor Hills Road, Singapore
# DEBUG: 地理编码成功: 32 Lentor Hills Road, Singapore -> (1.3827540, 103.8338790)
```

## 注意事项

1. **隐私**：地理坐标可能泄露精确位置，注意数据安全
2. **准确性**：Nominatim 的精度取决于 OpenStreetMap 数据质量
3. **使用政策**：遵守 Nominatim 的使用政策和限制
4. **备选方案**：如果需要更高精度或更快速度，可以考虑付费服务（如 Google Maps API）

## 替换为其他服务

如果需要使用其他地理编码服务（如 Google Maps），只需修改 `utils/geocoding.py` 中的实现：

```python
# 示例：使用 Google Maps API
import googlemaps

def geocode_address_google(address: str, api_key: str) -> tuple[Decimal | None, Decimal | None]:
    """使用 Google Maps API 进行地理编码"""
    gmaps = googlemaps.Client(key=api_key)

    try:
        result = gmaps.geocode(f"{address}, Singapore")
        if result:
            location = result[0]['geometry']['location']
            return Decimal(str(location['lat'])), Decimal(str(location['lng']))
    except Exception as e:
        logger.error(f"Google 地理编码失败: {e}")

    return None, None
```

## 相关资源

- [OpenStreetMap Nominatim Documentation](https://nominatim.org/release-docs/latest/)
- [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)
- [MySQL Spatial Functions](https://dev.mysql.com/doc/refman/8.0/en/spatial-function-reference.html)
