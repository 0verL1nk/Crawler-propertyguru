# ============================================
# 阶段 1: 构建阶段
# ============================================
FROM node:18-alpine AS frontend-builder

# 设置工作目录
WORKDIR /app

# 复制前端依赖文件
COPY web/package.json web/package-lock.json ./web/

# 安装前端依赖
RUN cd web && npm ci

# 复制前端源代码
COPY web ./web

# 构建前端
RUN cd web && npm run build

# ============================================
# 阶段 2: 后端构建阶段
# ============================================
FROM golang:1.21-alpine AS backend-builder

# 获取构建信息
ARG VERSION=dev
ARG BUILD_TIME=unknown
ARG GIT_COMMIT=unknown

# 设置工作目录
WORKDIR /app

# 安装编译依赖
RUN apk add --no-cache git gcc musl-dev

# 复制 go mod 文件并下载依赖
COPY go.mod go.sum ./
RUN go mod download

# 复制源代码
COPY . .

# 复制前端构建产物到后端目录
COPY --from=frontend-builder /app/web/dist ./cmd/server/web/dist

# 编译应用（启用 CGO 支持 PostgreSQL 驱动，使用 embed 标签）
RUN CGO_ENABLED=1 GOOS=linux go build \
    -tags embed \
    -ldflags="-s -w -X main.Version=${VERSION} -X main.BuildTime=${BUILD_TIME} -X main.GitCommit=${GIT_COMMIT}" \
    -o server ./cmd/server

# ============================================
# 阶段 3: 运行阶段
# ============================================
FROM alpine:latest

# 安装运行时依赖
RUN apk --no-cache add ca-certificates tzdata

# 设置时区为新加坡时间
ENV TZ=Asia/Singapore
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 创建非 root 用户
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# 设置工作目录
WORKDIR /home/appuser/app

# 从构建阶段复制编译好的二进制文件
COPY --from=backend-builder /app/server .

# 修改文件所有者
RUN chown -R appuser:appuser /home/appuser/app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# 运行应用
CMD ["./server"]

