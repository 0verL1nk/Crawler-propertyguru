.PHONY: all clean build build-frontend build-backend dev test install help

# 项目信息
APP_NAME=searcher
VERSION?=$(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
BUILD_TIME=$(shell date -u '+%Y-%m-%d_%H:%M:%S')
GIT_COMMIT=$(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# 构建目录
BUILD_DIR=build
FRONTEND_DIR=web
FRONTEND_DIST=$(FRONTEND_DIR)/dist
BACKEND_MAIN=cmd/server/main.go

# Go 编译参数
GOOS?=$(shell go env GOOS)
GOARCH?=$(shell go env GOARCH)
LDFLAGS=-ldflags "\
	-s -w \
	-X main.Version=$(VERSION) \
	-X main.BuildTime=$(BUILD_TIME) \
	-X main.GitCommit=$(GIT_COMMIT)"

# 默认目标
all: clean build

## help: 显示帮助信息
help:
	@echo "PropertyGuru Auto Searcher - Build Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  all              - 清理并构建完整应用（默认）"
	@echo "  build            - 构建前端和后端，生成单一二进制文件"
	@echo "  build-frontend   - 仅构建前端（Vite build）"
	@echo "  build-backend    - 仅构建后端（Go build with embed）"
	@echo "  dev              - 开发模式（前端 Vite dev + 后端 Go run）"
	@echo "  clean            - 清理构建产物"
	@echo "  test             - 运行测试"
	@echo "  install          - 安装前端依赖"
	@echo "  help             - 显示此帮助信息"
	@echo ""
	@echo "Examples:"
	@echo "  make build                    # 构建生产版本"
	@echo "  make build GOOS=linux         # 交叉编译 Linux 版本"
	@echo "  make build VERSION=v1.0.0     # 指定版本号"
	@echo ""

## build: 构建完整应用（前端 + 后端）
build: build-frontend build-backend
	@echo "✅ Build completed: $(BUILD_DIR)/$(APP_NAME)"
	@echo "📦 Version: $(VERSION)"
	@echo "🕒 Build Time: $(BUILD_TIME)"
	@echo "📝 Git Commit: $(GIT_COMMIT)"
	@ls -lh $(BUILD_DIR)/$(APP_NAME)

## build-frontend: 构建前端静态资源
build-frontend:
	@echo "🎨 Building frontend..."
	@if [ ! -d "$(FRONTEND_DIR)/node_modules" ]; then \
		echo "📦 Installing frontend dependencies..."; \
		cd $(FRONTEND_DIR) && npm install; \
	fi
	@cd $(FRONTEND_DIR) && npm run build
	@echo "✅ Frontend build completed: $(FRONTEND_DIST)"

## build-backend: 构建后端二进制文件（嵌入前端）
build-backend:
	@echo "🔨 Building backend with embedded frontend..."
	@mkdir -p $(BUILD_DIR)
	@if [ ! -d "$(FRONTEND_DIST)" ]; then \
		echo "⚠️  Frontend dist not found, building frontend first..."; \
		$(MAKE) build-frontend; \
	fi
	@echo "📦 Embedding frontend assets..."
	@mkdir -p cmd/server/web/dist
	@cp -r web/dist/* cmd/server/web/dist/
	@GOOS=$(GOOS) GOARCH=$(GOARCH) go build $(LDFLAGS) -tags embed \
		-o $(BUILD_DIR)/$(APP_NAME) ./cmd/server
	@rm -rf cmd/server/web
	@echo "✅ Backend build completed"

## install: 安装前端依赖
install:
	@echo "📦 Installing frontend dependencies..."
	@cd $(FRONTEND_DIR) && npm install
	@echo "✅ Dependencies installed"

## dev: 开发模式（不嵌入前端）
dev:
	@echo "🚀 Starting development mode..."
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8080"
	@echo ""
	@echo "Start backend with: go run cmd/server/main.go"
	@echo "Start frontend with: cd web && npm run dev"

## clean: 清理构建产物
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf $(BUILD_DIR)
	@rm -rf $(FRONTEND_DIST)
	@rm -rf $(FRONTEND_DIR)/node_modules
	@rm -rf cmd/server/web
	@echo "✅ Clean completed"

## test: 运行测试
test:
	@echo "🧪 Running tests..."
	@go test -v -race -coverprofile=coverage.out ./...
	@echo "✅ Tests completed"

# 交叉编译目标
## build-linux: 构建 Linux amd64 版本
build-linux:
	@$(MAKE) build GOOS=linux GOARCH=amd64

## build-linux-arm64: 构建 Linux arm64 版本
build-linux-arm64:
	@$(MAKE) build GOOS=linux GOARCH=arm64

## build-darwin: 构建 macOS amd64 版本
build-darwin:
	@$(MAKE) build GOOS=darwin GOARCH=amd64

## build-darwin-arm64: 构建 macOS arm64 版本
build-darwin-arm64:
	@$(MAKE) build GOOS=darwin GOARCH=arm64

## build-windows: 构建 Windows amd64 版本
build-windows:
	@$(MAKE) build GOOS=windows GOARCH=amd64

## build-all: 构建所有平台版本
build-all: clean
	@echo "🌍 Building for all platforms..."
	@$(MAKE) build-frontend
	@$(MAKE) build-linux
	@mv $(BUILD_DIR)/$(APP_NAME) $(BUILD_DIR)/$(APP_NAME)-linux-amd64
	@$(MAKE) build-linux-arm64
	@mv $(BUILD_DIR)/$(APP_NAME) $(BUILD_DIR)/$(APP_NAME)-linux-arm64
	@$(MAKE) build-darwin
	@mv $(BUILD_DIR)/$(APP_NAME) $(BUILD_DIR)/$(APP_NAME)-darwin-amd64
	@$(MAKE) build-darwin-arm64
	@mv $(BUILD_DIR)/$(APP_NAME) $(BUILD_DIR)/$(APP_NAME)-darwin-arm64
	@$(MAKE) build-windows
	@mv $(BUILD_DIR)/$(APP_NAME) $(BUILD_DIR)/$(APP_NAME)-windows-amd64.exe
	@echo "✅ All platforms built"
	@ls -lh $(BUILD_DIR)/

# Docker 构建
## docker-build: 构建 Docker 镜像
docker-build:
	@echo "🐳 Building Docker image..."
	@docker build -t $(APP_NAME):$(VERSION) .
	@docker tag $(APP_NAME):$(VERSION) $(APP_NAME):latest
	@echo "✅ Docker image built: $(APP_NAME):$(VERSION)"

## docker-run: 运行 Docker 容器
docker-run:
	@docker run --rm -p 8080:8080 --env-file .env $(APP_NAME):latest
