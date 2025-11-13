i# 🚀 Build & Deployment Guide

完整的构建和部署指南，包括前端嵌入后端的单一二进制文件部署方案。

## 📋 目录

- [快速开始](#快速开始)
- [构建方式](#构建方式)
- [部署方案](#部署方案)
- [测试验证](#测试验证)
- [故障排查](#故障排查)

---

## 🎯 快速开始

### 最简单的方式：一键构建

```bash
make build
```

这会：
1. ✅ 构建前端 React 应用（Ant Design X）
2. ✅ 将前端嵌入 Go 二进制文件
3. ✅ 生成单一可执行文件：`build/searcher`

### 运行构建的二进制文件

```bash
# 1. 设置环境变量（或使用 .env 文件）
export DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"
export OPENAI_API_KEY="your-api-key"

# 2. 运行
./build/searcher
```

就是这么简单！🎉

---

## 🏗️ 构建方式

### 1. 完整构建（推荐）

```bash
make build
```

**输出：**
- `build/searcher` - 单一二进制文件（前端已嵌入）
- 大小约 15-25 MB（包含完整 React 应用）

**适用场景：**
- ✅ 生产环境部署
- ✅ Docker 容器
- ✅ 云服务器
- ✅ 无需 Node.js 环境

### 2. 仅构建前端

```bash
make build-frontend
```

**输出：**
- `web/dist/` - 前端静态文件

**适用场景：**
- 🔧 前端开发测试
- 🔧 Nginx 独立部署
- 🔧 CDN 部署

### 3. 仅构建后端

```bash
make build-backend
```

**前提：** 前端已构建（`web/dist/` 存在）

**输出：**
- `build/searcher` - 嵌入前端的二进制文件

### 4. 开发模式（不嵌入）

```bash
# 终端 1：启动后端
go run cmd/server/main.go

# 终端 2：启动前端
cd web && npm run dev
```

**特点：**
- 🔧 热重载
- 🔧 前端 http://localhost:3000
- 🔧 后端 http://localhost:8080
- 🔧 API 自动代理

---

## 🌍 交叉编译

### Linux (amd64)

```bash
make build-linux
# 输出: build/searcher-linux-amd64
```

### Linux (arm64)

```bash
make build-linux-arm64
# 输出: build/searcher-linux-arm64
```

### macOS (Intel)

```bash
make build-darwin
# 输出: build/searcher-darwin-amd64
```

### macOS (Apple Silicon)

```bash
make build-darwin-arm64
# 输出: build/searcher-darwin-arm64
```

### Windows

```bash
make build-windows
# 输出: build/searcher-windows-amd64.exe
```

### 构建所有平台

```bash
make build-all
```

会生成所有平台的二进制文件。

---

## 📦 部署方案

### 方案 1：单一二进制部署（最简单）

**优点：**
- ✅ 无需安装 Node.js
- ✅ 无需安装 Nginx
- ✅ 一个文件搞定
- ✅ 容器镜像最小

**步骤：**

```bash
# 1. 构建
make build

# 2. 复制到服务器
scp build/searcher user@server:/opt/searcher/

# 3. 配置环境变量
scp config.example.env user@server:/opt/searcher/.env

# 4. SSH 到服务器并运行
ssh user@server
cd /opt/searcher
chmod +x searcher
./searcher
```

### 方案 2：Systemd 服务

创建 `/etc/systemd/system/searcher.service`:

```ini
[Unit]
Description=PropertyGuru Auto Searcher
After=network.target postgresql.service

[Service]
Type=simple
User=searcher
WorkingDirectory=/opt/searcher
EnvironmentFile=/opt/searcher/.env
ExecStart=/opt/searcher/searcher
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable searcher
sudo systemctl start searcher
sudo systemctl status searcher
```

### 方案 3：Docker 部署

#### 创建 Dockerfile

```dockerfile
FROM node:18-alpine AS frontend-builder
WORKDIR /build/web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

FROM golang:1.21-alpine AS backend-builder
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
COPY --from=frontend-builder /build/web/dist ./web/dist
RUN CGO_ENABLED=0 go build -tags=embed \
    -ldflags="-s -w -X main.Version=docker" \
    -o searcher cmd/server/main.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=backend-builder /build/searcher .
EXPOSE 8080
CMD ["./searcher"]
```

#### 构建和运行

```bash
# 构建镜像
docker build -t searcher:latest .

# 运行容器
docker run -d \
  -p 8080:8080 \
  --env-file .env \
  --name searcher \
  searcher:latest
```

#### 使用 docker-compose

```yaml
version: '3.8'
services:
  searcher:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env
    depends_on:
      - postgres
    restart: unless-stopped
```

```bash
docker-compose up -d
```

### 方案 4：Nginx 反向代理（可选）

如果需要 HTTPS 或负载均衡：

```nginx
server {
    listen 80;
    server_name property-search.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
    }
}
```

---

## 🧪 测试验证

### 1. 健康检查

```bash
curl http://localhost:8080/health
```

**预期输出：**
```json
{
  "status": "healthy",
  "service": "property-search-engine",
  "version": "v1.0.0",
  "build_time": "2025-11-07_10:30:00",
  "git_commit": "abc1234"
}
```

### 2. 版本信息

```bash
curl http://localhost:8080/version
```

### 3. 测试搜索 API（非流式）

```bash
curl -X POST http://localhost:8080/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "3 bedroom condo near MRT under 1.2M",
    "options": {
      "top_k": 10,
      "semantic": true
    }
  }'
```

### 4. 测试流式搜索（SSE）

```bash
curl -N -X POST http://localhost:8080/api/v1/search/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "3 bedroom condo near MRT under 1.2M",
    "options": {
      "top_k": 10,
      "semantic": true
    }
  }'
```

**预期输出：**
```
event: start
data: {"message":"Starting search"}

event: parsing
data: {"message":"Parsing query"}

event: thinking
data: {"content":"Let me analyze..."}

event: intent
data: {"slots":{"bedrooms":3,...}}

event: results
data: {"results":[...],"total":42,"took":123}

event: done
data: {"message":"Search completed"}
```

### 5. 测试前端界面

浏览器访问：
```
http://localhost:8080
```

**应该看到：**
- ✅ Ant Design X 界面
- ✅ 输入框和搜索按钮
- ✅ 能够输入查询
- ✅ 实时显示 AI 思考过程
- ✅ 显示搜索结果卡片

### 6. 测试流式 UI

在前端输入查询并观察：
1. 🔍 Starting search...
2. 🤖 Parsing your query with AI...
3. 💭 AI is thinking: ...（实时流式显示）
4. ✅ Understood: bedrooms: 3, ...
5. 🔎 Searching database...
6. 📊 Found 42 properties in 123ms
7. 📋 显示房源卡片列表

---

## 🔧 故障排查

### 问题 1：前端 404

**症状：** 访问 `http://localhost:8080` 返回 404

**原因：** 前端未嵌入或路径错误

**解决：**
```bash
# 确认前端已构建
ls -la web/dist/

# 重新构建
make clean
make build

# 检查构建标签
strings build/searcher | grep -i "embedded"
```

### 问题 2：API CORS 错误

**症状：** 浏览器控制台显示 CORS 错误

**原因：** 开发模式下前端和后端端口不同

**解决：**
```bash
# 生产模式（前端已嵌入）：无此问题

# 开发模式：确保 Vite 代理配置正确
cat web/vite.config.ts
```

### 问题 3：SSE 连接中断

**症状：** 流式搜索中途断开

**原因：** Nginx 缓冲或超时

**解决：**
```nginx
# Nginx 配置添加
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 300s;
```

### 问题 4：嵌入文件过大

**症状：** 二进制文件 > 50MB

**原因：** 前端未压缩或包含多余文件

**解决：**
```bash
# 检查 dist 大小
du -sh web/dist

# 清理并重建
cd web
rm -rf node_modules dist
npm install --production
npm run build

# 检查 Vite 配置是否启用压缩
cat vite.config.ts
```

### 问题 5：数据库连接失败

**症状：** `Failed to connect to database`

**解决：**
```bash
# 检查环境变量
env | grep -E "DATABASE|PG_|POSTGRESQL"

# 测试连接
psql "$DATABASE_URL"

# 检查配置优先级
# 1. DATABASE_URL
# 2. POSTGRESQL_URI  
# 3. PG_DSN
# 4. PG_HOST + PG_PORT + ...
```

### 问题 6：AI 功能不工作

**症状：** 搜索返回空结果或错误

**解决：**
```bash
# 检查 OpenAI 配置
env | grep OPENAI

# 测试 API 密钥
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://integrate.api.nvidia.com/v1/models

# 检查日志
journalctl -u searcher -f
```

---

## 📊 性能优化

### 1. 二进制文件大小

```bash
# 当前大小
ls -lh build/searcher

# 优化：使用 upx 压缩
upx --best --lzma build/searcher

# 通常可减少 50-70% 大小
```

### 2. 启动速度

```bash
# 预编译模板
go build -ldflags="-s -w" -trimpath

# 禁用符号表
go build -ldflags="-s -w"
```

### 3. 内存使用

```bash
# 设置 GOGC 环境变量
export GOGC=50  # 更激进的 GC

# 或在代码中设置
debug.SetGCPercent(50)
```

---

## 📝 部署检查清单

部署前确认：

- [ ] ✅ 前端已构建（`web/dist/` 存在）
- [ ] ✅ 后端编译成功（`build/searcher` 存在）
- [ ] ✅ 环境变量已配置（`.env` 文件）
- [ ] ✅ 数据库连接正常（`psql $DATABASE_URL`）
- [ ] ✅ OpenAI API 密钥有效
- [ ] ✅ 健康检查通过（`/health`）
- [ ] ✅ 前端界面可访问
- [ ] ✅ 搜索功能正常
- [ ] ✅ 流式传输工作
- [ ] ✅ 防火墙规则配置（端口 8080）
- [ ] ✅ 日志收集配置
- [ ] ✅ 监控告警配置

---

## 🎉 完成！

现在你有一个：
- ✅ 单一二进制可执行文件
- ✅ 前端完全嵌入
- ✅ 无需 Node.js 运行时
- ✅ 支持流式 AI 对话
- ✅ 专业的 Ant Design X 界面
- ✅ 跨平台支持

部署就像复制一个文件一样简单！🚀

