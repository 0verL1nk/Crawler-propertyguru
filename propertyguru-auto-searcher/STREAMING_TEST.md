# 🔍 流式传输测试指南

## 问题排查

### 1. 检查 AI 是否正确初始化

运行服务器时应该看到：
```
✅ OpenAI client initialized
   - Chat model: deepseek-ai/deepseek-v3.1-terminus
   - Embedding model: baai/bge-m3
🔧 Detected NVIDIA API provider (supports reasoning/thinking)
```

### 2. 测试流式搜索 API

```bash
curl -N -X POST http://localhost:8080/api/v1/search/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I want a 3-bedroom condo near MRT, budget under S$1.2M",
    "options": {
      "top_k": 20,
      "semantic": true
    }
  }'
```

**预期输出：**
```
event: start
data: {"query":"..."}

event: parsing
data: {"status":"Parsing your query..."}

event: thinking
data: {"content":"Let me"}

event: thinking
data: {"content":" analyze"}

event: content
data: {"content":"{\"bedrooms\":"}}

event: intent
data: {"slots":{"bedrooms":3,"price_max":1200000,...}}

event: searching
data: {"status":"Searching database..."}

event: results
data: {"results":[...],"total":42,"took":123}

event: done
data: {}
```

### 3. 检查环境变量

必需的配置：
```bash
# 检查这些环境变量是否设置
echo $OPENAI_API_KEY
echo $OPENAI_API_BASE
echo $OPENAI_CHAT_MODEL
echo $OPENAI_CHAT_EXTRA_BODY
```

应该看到：
```
your-nvidia-api-key
https://integrate.api.nvidia.com/v1
deepseek-ai/deepseek-v3.1-terminus
{"chat_template_kwargs":{"thinking":true}}
```

### 4. 前端调试

打开浏览器开发者工具（F12），查看：

#### Network 标签
- 找到 `/api/v1/search/stream` 请求
- 查看 Response 是否有 SSE 事件流
- 检查是否有 `thinking` 事件

#### Console 标签
- 查看是否有 JavaScript 错误
- 查看是否有 "Failed to parse SSE data" 消息

### 5. 常见问题

#### 问题：没有 thinking 事件
**原因：** NVIDIA API 可能没有启用 thinking 模式
**解决：** 检查 `OPENAI_CHAT_EXTRA_BODY` 配置

```bash
export OPENAI_CHAT_EXTRA_BODY='{"chat_template_kwargs":{"thinking":true}}'
```

#### 问题：AI 返回空结果
**原因：** API 密钥无效或配额用尽
**解决：** 
1. 验证 API 密钥
2. 检查 NVIDIA API 配额
3. 查看服务器日志中的错误信息

#### 问题：前端不显示流式消息
**原因：** SSE 解析逻辑问题
**解决：** 
1. 检查浏览器控制台错误
2. 验证后端返回的 SSE 格式
3. 确认前端正确处理 `thinking` 事件

### 6. 日志级别

如需详细调试信息，修改代码临时添加日志：

```go
// internal/service/openai.go - ParseIntentWithAIStream
log.Printf("🔍 Starting streaming parse for query: %s", query)
log.Printf("📤 Request: %+v", req)

// In callback:
log.Printf("💭 Thinking: %s", thinking)
log.Printf("📝 Content: %s", content)
```

### 7. 手动测试 NVIDIA API

直接测试 NVIDIA API：

```bash
curl -X POST "https://integrate.api.nvidia.com/v1/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/deepseek-v3.1-terminus",
    "messages": [{"role":"user","content":"Hello"}],
    "stream": true,
    "extra_body": {"chat_template_kwargs": {"thinking":true}}
  }'
```

应该看到包含 `reasoning_content` 的流式响应。

## 预期工作流程

1. **用户输入查询** → 前端发送 POST 到 `/api/v1/search/stream`
2. **后端开始处理** → 发送 `start` 事件
3. **调用 AI 解析** → 发送 `parsing` 事件
4. **AI 开始思考** → 发送多个 `thinking` 事件（DeepSeek 特有）
5. **AI 生成内容** → 发送多个 `content` 事件
6. **解析完成** → 发送 `intent` 事件
7. **数据库查询** → 发送 `searching` 事件
8. **返回结果** → 发送 `results` 事件
9. **完成** → 发送 `done` 事件

每个事件都会实时显示在前端界面！

