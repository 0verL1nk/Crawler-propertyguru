# HTTP爬虫升级指南

## 概述
本次升级为PropertyGuru爬虫添加了HTTP基础的列表页爬取功能，可以在无需浏览器的情况下快速爬取列表页数据，显著提升爬取效率。

## 新增功能

### 1. HTTP列表页爬虫
- 支持直接HTTP请求爬取列表页（无需JavaScript渲染）
- 比浏览器爬虫速度快10倍以上
- 资源消耗更低（无需启动浏览器进程）

### 2. ZenRows集成
- 集成ZenRows服务以绕过CloudFlare等防护
- 支持高级代理和请求头伪装
- 提高爬取成功率

### 3. 配置选项
- 可通过环境变量灵活控制功能启用
- 保持完全向后兼容性

## 配置说明

### 启用HTTP爬虫
在 `.env` 文件中设置：
```bash
USE_HTTP_CRAWLER=true
```

### 启用ZenRows服务
在 `.env` 文件中设置：
```bash
USE_ZENROWS=true
ZENROWS_APIKEY=your_actual_api_key_here
```

## 使用场景

### 适用场景
1. **列表页爬取** - 无需JavaScript渲染的内容
2. **高频次爬取** - 需要快速获取大量列表数据
3. **资源受限环境** - 无法运行完整浏览器的服务器

### 不适用场景
1. **详情页爬取** - 仍需JavaScript渲染
2. **动态内容** - 需要执行JavaScript才能获取的数据
3. **交互操作** - 需要点击、输入等用户交互的操作

## 性能对比

| 方案 | 速度 | 资源消耗 | 适用页面 |
|------|------|----------|----------|
| HTTP爬虫 | 快（~1秒/页） | 低 | 列表页 |
| 浏览器爬虫 | 慢（~5-10秒/页） | 高 | 所有页面 |

## 架构说明

### 核心组件
1. `crawler/http/client.py` - HTTP客户端封装
2. `crawler/pages/listing_http.py` - HTTP列表页爬虫实现
3. `crawler/pages/parsing_utils.py` - 共享解析工具
4. `crawler/pages/factory.py` - 爬虫工厂

### 工作流程
1. 检查是否启用HTTP爬虫
2. 如启用且为列表页，使用HTTP爬虫
3. 如失败或未启用，回退到浏览器爬虫
4. 详情页始终使用浏览器爬虫

## 注意事项

### 兼容性
- 现有配置无需更改即可正常使用
- 浏览器爬虫作为后备方案确保功能完整性

### 成本考虑
- ZenRows服务需要付费订阅
- HTTP请求比浏览器资源消耗更低

### 错误处理
- HTTP爬虫失败时自动回退到浏览器爬虫
- 详细的日志记录便于问题排查

## 测试验证

### 单元测试
```bash
python -m pytest tests/test_http_crawler.py
```

### 功能测试
```bash
# 启用HTTP爬虫
export USE_HTTP_CRAWLER=true

# 运行测试
python main.py --test-page
```

## 故障排除

### 常见问题
1. **HTTP爬虫失败** - 检查网络连接和防火墙设置
2. **ZenRows配额用完** - 检查账户余额和服务状态
3. **解析错误** - 网站结构变化时需要更新解析逻辑

### 日志查看
```bash
# 查看详细日志
export LOG_LEVEL=DEBUG
```

## 未来扩展

### 可能的改进
1. 添加更多HTTP服务提供商支持
2. 实现智能爬虫选择（根据页面类型自动选择）
3. 增加请求缓存机制
4. 支持更多网站的HTTP爬取