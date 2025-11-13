# API 使用指南

## 基础信息

- **Base URL**: `http://localhost:8080/api/v1`
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

## 接口列表

### 1. 健康检查

检查服务是否正常运行。

**请求:**

```http
GET /health HTTP/1.1
```

**响应:**

```json
{
  "status": "healthy",
  "service": "property-search-engine"
}
```

---

### 2. 搜索房源

使用自然语言或结构化条件搜索房源。

**请求:**

```http
POST /api/v1/search HTTP/1.1
Content-Type: application/json

{
  "query": "我想找靠近地铁的三房公寓，预算120万以内",
  "filters": {
    "price_min": 1000000,
    "price_max": 1200000,
    "bedrooms": 3,
    "bathrooms": 2,
    "unit_type": "Condo",
    "mrt_distance_max": 1000,
    "location": "Punggol",
    "is_completed": true
  },
  "options": {
    "top_k": 20,
    "offset": 0,
    "semantic": true
  }
}
```

**参数说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 自然语言查询 |
| filters | object | 否 | 结构化过滤条件 |
| filters.price_min | number | 否 | 最低价格 (S$) |
| filters.price_max | number | 否 | 最高价格 (S$) |
| filters.bedrooms | integer | 否 | 卧室数量 |
| filters.bathrooms | integer | 否 | 浴室数量 |
| filters.unit_type | string | 否 | 房型 (HDB/Condo/Landed) |
| filters.mrt_distance_max | integer | 否 | 最大地铁距离 (米) |
| filters.location | string | 否 | 地点关键词 |
| filters.is_completed | boolean | 否 | 是否只返回完整数据 (默认 true) |
| options.top_k | integer | 否 | 返回结果数量 (默认 20, 最大 100) |
| options.offset | integer | 否 | 分页偏移量 (默认 0) |
| options.semantic | boolean | 否 | 是否启用语义搜索 (默认 true) |

**响应:**

```json
{
  "results": [
    {
      "id": 1,
      "listing_id": 60157325,
      "title": "619D Punggol Drive",
      "price": 1150000,
      "price_per_sqft": 800,
      "bedrooms": 3,
      "bathrooms": 2,
      "area_sqft": 1200,
      "unit_type": "Condo",
      "tenure": "99-year Leasehold",
      "build_year": 2015,
      "mrt_station": "PE6 Oasis LRT Station",
      "mrt_distance_m": 500,
      "location": "Punggol",
      "latitude": 1.3984,
      "longitude": 103.9078,
      "listed_date": "2024-11-01",
      "listed_age": "6 days ago",
      "green_score_value": 4.5,
      "green_score_max": 5.0,
      "url": "https://www.propertyguru.com.sg/listing/60157325",
      "description": "Beautiful 3-bedroom condo...",
      "amenities": ["Swimming Pool", "Gym", "Playground"],
      "facilities": ["24hr Security", "Covered Parking"],
      "is_completed": true,
      "score": 0.92,
      "matched_reasons": ["Bedrooms match", "Near MRT", "Price within budget", "Newly listed"]
    }
  ],
  "total": 45,
  "intent": {
    "slots": {
      "price_max": 1200000,
      "bedrooms": 3,
      "mrt_distance_max": 1000,
      "unit_type": "Condo"
    },
    "semantic_keywords": ["靠近地铁", "公寓"],
    "confidence": 0.85
  },
  "took_ms": 125
}
```

**状态码:**

- `200 OK`: 搜索成功
- `400 Bad Request`: 请求参数错误
- `500 Internal Server Error`: 服务器内部错误

---

### 3. 获取房源详情

根据房源ID获取完整信息。

**请求:**

```http
GET /api/v1/listings/60157325 HTTP/1.1
```

**响应:**

```json
{
  "id": 1,
  "listing_id": 60157325,
  "title": "619D Punggol Drive",
  "price": 1150000,
  "price_per_sqft": 800,
  "bedrooms": 3,
  "bathrooms": 2,
  "area_sqft": 1200,
  "unit_type": "Condo",
  "tenure": "99-year Leasehold",
  "build_year": 2015,
  "mrt_station": "PE6 Oasis LRT Station",
  "mrt_distance_m": 500,
  "location": "Punggol",
  "latitude": 1.3984,
  "longitude": 103.9078,
  "listed_date": "2024-11-01",
  "listed_age": "6 days ago",
  "green_score_value": 4.5,
  "green_score_max": 5.0,
  "url": "https://www.propertyguru.com.sg/listing/60157325",
  "property_details": {
    "floor_level": "High Floor",
    "furnishing": "Fully Furnished"
  },
  "description": "Beautiful 3-bedroom condo with great view...",
  "description_title": "Spacious Family Home",
  "amenities": ["Swimming Pool", "Gym", "Playground"],
  "facilities": ["24hr Security", "Covered Parking"],
  "is_completed": true,
  "created_at": "2024-11-01T10:00:00Z",
  "updated_at": "2024-11-01T10:00:00Z"
}
```

**状态码:**

- `200 OK`: 查询成功
- `404 Not Found`: 房源不存在
- `500 Internal Server Error`: 服务器内部错误

---

### 4. 批量更新 Embedding

批量更新房源的向量嵌入（用于语义搜索）。

**请求:**

```http
POST /api/v1/embeddings/batch HTTP/1.1
Content-Type: application/json

{
  "embeddings": [
    {
      "listing_id": 60157325,
      "embedding": [0.1, 0.2, 0.3, ..., 0.5],  // 1536维向量
      "text": "Beautiful 3-bedroom condo near MRT..."
    },
    {
      "listing_id": 60157326,
      "embedding": [0.2, 0.1, 0.4, ..., 0.6],
      "text": "Spacious HDB flat in Punggol..."
    }
  ]
}
```

**参数说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| embeddings | array | 是 | Embedding 列表 |
| embeddings[].listing_id | integer | 是 | 房源ID |
| embeddings[].embedding | array | 是 | 1536维向量数组 |
| embeddings[].text | string | 否 | 生成 embedding 的原始文本 |

**响应:**

```json
{
  "success": 98,
  "failed": 2,
  "errors": [
    "listing_id 12345: listing not found",
    "listing_id 67890: invalid embedding dimension"
  ]
}
```

**状态码:**

- `200 OK`: 全部成功
- `207 Multi-Status`: 部分成功
- `400 Bad Request`: 请求参数错误
- `500 Internal Server Error`: 服务器内部错误

---

### 5. 提交用户反馈

记录用户行为（点击、联系等），用于优化搜索排序。

**请求:**

```http
POST /api/v1/feedback HTTP/1.1
Content-Type: application/json

{
  "search_id": "550e8400-e29b-41d4-a716-446655440000",
  "listing_id": 60157325,
  "action": "click"
}
```

**参数说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| search_id | string | 是 | 搜索ID (UUID) |
| listing_id | integer | 是 | 房源ID |
| action | string | 是 | 行为类型: click/contact/view_details |

**响应:**

```json
{
  "success": true,
  "message": "Feedback logged successfully"
}
```

**状态码:**

- `200 OK`: 记录成功
- `400 Bad Request`: 请求参数错误
- `500 Internal Server Error`: 服务器内部错误

---

## 使用示例

### cURL

```bash
# 搜索房源
curl -X POST http://localhost:8080/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "我想找靠近地铁的三房公寓，预算120万以内",
    "options": {
      "top_k": 10
    }
  }'

# 获取房源详情
curl http://localhost:8080/api/v1/listings/60157325

# 提交反馈
curl -X POST http://localhost:8080/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "search_id": "search-123",
    "listing_id": 60157325,
    "action": "click"
  }'
```

### Python

```python
import requests

# 搜索房源
response = requests.post('http://localhost:8080/api/v1/search', json={
    'query': '我想找靠近地铁的三房公寓，预算120万以内',
    'options': {
        'top_k': 10
    }
})

data = response.json()
print(f"找到 {data['total']} 个房源")

for listing in data['results']:
    print(f"- {listing['title']}: S${listing['price']:,.0f}")
    print(f"  匹配原因: {', '.join(listing['matched_reasons'])}")
```

### JavaScript

```javascript
// 搜索房源
const response = await fetch('http://localhost:8080/api/v1/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: '我想找靠近地铁的三房公寓，预算120万以内',
    options: {
      top_k: 10
    }
  })
});

const data = await response.json();
console.log(`找到 ${data.total} 个房源`);

data.results.forEach(listing => {
  console.log(`- ${listing.title}: S$${listing.price.toLocaleString()}`);
  console.log(`  匹配原因: ${listing.matched_reasons.join(', ')}`);
});
```

---

## 错误处理

所有错误响应遵循统一格式：

```json
{
  "error": "错误描述信息"
}
```

常见错误码：

- `400 Bad Request`: 请求参数格式错误或缺少必填字段
- `404 Not Found`: 请求的资源不存在
- `500 Internal Server Error`: 服务器内部错误（数据库连接失败等）

---

## 性能建议

1. **分页查询**: 使用 `offset` 和 `top_k` 实现分页，避免一次请求过多数据
2. **精确过滤**: 优先使用结构化 `filters` 而非纯自然语言，可获得更精确的结果
3. **缓存结果**: 对于热门查询，建议在客户端缓存结果
4. **异步反馈**: 用户反馈可以异步提交，不影响用户体验

---

## 速率限制

当前 MVP 版本暂无速率限制。生产环境建议：

- 每个 IP 每分钟最多 60 次请求
- 每个 IP 每小时最多 1000 次请求
- Embedding 批量更新每次最多 1000 条

---

## 更新日志

### v1.0.0 (MVP) - 2024-11

- ✅ 基础搜索功能
- ✅ 自然语言意图解析
- ✅ 全文检索
- ✅ 混合排序
- ✅ Embedding 批量更新接口
- ✅ 用户反馈记录

### v2.0.0 (计划中)

- 🔜 向量语义搜索
- 🔜 Learning-to-Rank 排序优化
- 🔜 RAG 生成推荐理由
- 🔜 个性化推荐

