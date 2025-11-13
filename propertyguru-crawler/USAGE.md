# 使用指南

## 动态代理配置指南

### 为什么使用动态住宅代理？

本项目**强烈推荐使用动态住宅代理**（Bright Data Residential Proxy），原因如下：

#### ✅ 适合大规模处理
- **批量爬取**: 每次请求自动切换IP，不会因为频繁请求被封禁
- **图片处理**: 大规模图片去水印等操作需要大量API调用，动态代理避免IP限流
- **数据采集**: 长时间运行的任务不会因为单IP使用过多而被封禁

#### ✅ 自动IP轮换
- 每次HTTP请求自动使用不同的住宅IP
- 无需手动管理IP切换
- 系统自动处理IP分配

#### ✅ 真实网络环境
- IP来自真实用户的住宅网络
- 不像数据中心IP容易被识别
- 请求成功率高

### 配置方法

1. **复制环境变量模板**
   ```bash
   cp env.example .env
   ```

2. **编辑 .env 文件**
   ```bash
   # 动态住宅代理（必需，用于所有大规模任务）
   PROXY_URL=http://brd-customer-xxx-zone-residential_proxy1:your_password@brd.superproxy.io:33335
   
   # 图片去水印配置（可选）
   WATERMARK_REMOVER_PRODUCT_SERIAL=your_serial
   WATERMARK_REMOVER_PRODUCT_CODE=067003
   ```

3. **验证配置**
   ```bash
   # 运行测试示例
   uv run python examples/residential_proxy_example.py
   ```

### 使用场景

#### 场景1: 批量爬取网站数据
```python
from crawler import Spider
from dotenv import load_dotenv
import os

load_dotenv()

# 配置会自动从 .env 读取 PROXY_URL
config = {
    'crawler': {
        'concurrency': 10,
        'delay': 1,
        'use_proxy': True,  # 使用动态代理
    }
}

spider = Spider(config)
urls = ['url1', 'url2', ...]  # 大量URL
spider.crawl(urls, callback=parse_function)
```

#### 场景2: 大规模图片处理
```python
from crawler.watermark_remover import WatermarkRemover
import os

# 自动从环境变量读取代理配置
remover = WatermarkRemover()

# 批量处理图片
image_list = ['image1.jpg', 'image2.jpg', ...]  # 大量图片
for image in image_list:
    result = remover.remove_watermark(image)
    # 每次请求使用不同的IP，避免被封
```

#### 场景3: 长时间运行的任务
```python
# 动态代理自动轮换IP，即使运行数小时也不会被封禁
while True:
    # 执行爬取任务
    spider.crawl(urls, callback=parse)
    time.sleep(3600)  # 每小时执行一次
```

### 常见问题

#### Q: 动态代理和静态代理有什么区别？

**动态代理（推荐）**:
- ✅ 每次请求自动切换IP
- ✅ 适合大规模处理
- ✅ 不易被封禁
- ✅ 配置: `zone-residential_proxy1`

**静态代理（不推荐）**:
- ❌ 固定IP
- ❌ 容易被限流
- ❌ 不适合大规模任务
- ❌ 配置: `zone-isp_proxy1`

#### Q: 如何验证IP是否在轮换？

运行测试示例：
```bash
uv run python examples/residential_proxy_example.py
```

查看输出，每次请求的IP应该不同。

#### Q: 代理连接失败怎么办？

1. 检查 `.env` 文件中的 `PROXY_URL` 是否正确
2. 确认代理服务商账户是否有效
3. 检查网络连接
4. 运行代理测试：`examples/residential_proxy_example.py`

#### Q: 大规模处理时需要注意什么？

1. **请求频率**: 建议设置合理的延迟（`delay` 参数）
2. **并发数**: 不要设置过高，建议 5-10
3. **错误处理**: 实现重试机制
4. **日志记录**: 监控任务执行情况

### 最佳实践

1. ✅ **始终使用动态代理**进行大规模处理
2. ✅ **配置合理的延迟**，避免过快请求
3. ✅ **监控日志**，及时发现异常
4. ✅ **实现错误重试**，提高成功率
5. ✅ **定期检查代理状态**，确保服务正常

### 相关示例

- `examples/residential_proxy_example.py` - 动态代理使用示例
- `examples/watermark_remover_example.py` - 图片处理示例（含代理配置）
- `examples/batch_crawl_example.py` - 批量爬取示例

