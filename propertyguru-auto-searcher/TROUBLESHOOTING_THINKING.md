# 🐛 DeepSeek 思考过程故障排除

## 问题诊断

经过诊断发现，虽然 `.env` 文件中配置了 `OPENAI_CHAT_EXTRA_BODY`，但是：

1. ❌ 项目**没有自动加载 .env 文件**（没有使用 godotenv）
2. ❌ .env 文件中的行内注释可能干扰环境变量值

## 解决方案

### 方案 1：使用启动脚本（推荐）

```bash
chmod +x start_server.sh
./start_server.sh
```

这个脚本会：
- 自动加载 .env 文件（并移除注释）
- 显示 AI 配置信息
- 重启服务器

### 方案 2：手动导出环境变量

在启动服务器前，手动导出关键环境变量：

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE="https://integrate.api.nvidia.com/v1"
export OPENAI_CHAT_MODEL="deepseek-ai/deepseek-v3.1-terminus"
export OPENAI_CHAT_EXTRA_BODY='{"chat_template_kwargs":{"thinking":true}}'
export OPENAI_EMBEDDING_MODEL="baai/bge-m3"

# 然后启动服务器
./build/searcher
```

### 方案 3：修改 .env 文件格式

将 .env 文件中的行内注释移到单独的行：

**之前（可能有问题）：**
```
OPENAI_CHAT_EXTRA_BODY={"chat_template_kwargs":{"thinking":true}}  # Extra body for API
```

**之后（正确格式）：**
```
# Extra body for API (JSON string)
OPENAI_CHAT_EXTRA_BODY={"chat_template_kwargs":{"thinking":true}}
```

然后使用方案 1 或方案 2 加载环境变量。

## 验证配置

启动服务器后，查看日志应该能看到：

```
✅ OpenAI client initialized
   - API Base: https://integrate.api.nvidia.com/v1
   - Chat model: deepseek-ai/deepseek-v3.1-terminus
   - Chat ExtraBody: {"chat_template_kwargs":{"thinking":true}}
```

然后运行测试脚本：

```bash
./test_ai_thinking.sh
```

应该看到：
```
✅ SUCCESS! Thinking process is working!
   - Thinking events: 10+
   - Content events: 30+
```

## 前端调试

打开浏览器控制台（F12），搜索时应该看到：

```
[DEBUG] Thinking accumulated: ...
[DEBUG] Content accumulated: ...
```

## 还是不行？

如果仍然没有思考过程，检查后端日志中的 DEBUG 消息：

```bash
# 查看最近的请求日志
grep "DEBUG" searcher.log | tail -50
```

关键信息：
- `[DEBUG] 🔧 Applying ChatExtraBody from config` - 确认 extra_body 被应用
- `[DEBUG] 📤 Streaming request body` - 查看实际发送的请求
- `[DEBUG] 💭 Thinking chunk` - 确认收到思考内容

