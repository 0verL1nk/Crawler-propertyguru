#!/bin/bash
# PropertyGuru 搜索引擎 - Docker 部署脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查必要的命令
check_requirements() {
    log_info "检查环境要求..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    log_info "✓ Docker 版本: $(docker --version)"
    log_info "✓ Docker Compose 版本: $(docker compose version)"
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."
    
    if [ ! -f "config.example.env" ]; then
        log_error "config.example.env 文件不存在"
        exit 1
    fi
    
    if [ ! -f ".env" ]; then
        log_warn ".env 文件不存在，使用示例配置"
        cp config.example.env .env
        log_info "已创建 .env 文件，请根据需要修改配置"
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p data/postgres
    mkdir -p backups
    mkdir -p logs
    mkdir -p config/ssl
    
    log_info "✓ 目录创建完成"
}

# 构建镜像
build_images() {
    log_info "构建 Docker 镜像..."
    
    docker compose build --no-cache
    
    log_info "✓ 镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    docker compose up -d
    
    log_info "✓ 服务启动完成"
    
    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 10
    
    # 检查服务状态
    docker compose ps
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查 PostgreSQL
    if docker exec property-postgres pg_isready -U property_user &> /dev/null; then
        log_info "✓ PostgreSQL 运行正常"
    else
        log_error "✗ PostgreSQL 未就绪"
        return 1
    fi
    
    # 检查搜索引擎
    sleep 5
    if curl -f http://localhost:8080/health &> /dev/null; then
        log_info "✓ 搜索引擎运行正常"
    else
        log_error "✗ 搜索引擎未就绪"
        return 1
    fi
}

# 显示访问信息
show_info() {
    echo ""
    echo "=================================================="
    echo "  🎉 PropertyGuru 搜索引擎部署完成！"
    echo "=================================================="
    echo ""
    echo "📝 访问地址:"
    echo "  - Web UI:  http://localhost:8080"
    echo "  - API:     http://localhost:8080/api/v1"
    echo "  - Health:  http://localhost:8080/health"
    echo ""
    echo "🗄️  数据库信息:"
    echo "  - Host:     localhost"
    echo "  - Port:     5432"
    echo "  - Database: property_search"
    echo ""
    echo "📊 管理命令:"
    echo "  - 查看日志:    docker compose logs -f"
    echo "  - 停止服务:    docker compose stop"
    echo "  - 重启服务:    docker compose restart"
    echo "  - 删除服务:    docker compose down"
    echo ""
    echo "  或使用 Makefile:"
    echo "  - make logs      # 查看日志"
    echo "  - make stop      # 停止服务"
    echo "  - make restart   # 重启服务"
    echo "  - make down      # 删除服务"
    echo ""
    echo "=================================================="
}

# 主函数
main() {
    log_info "开始部署 PropertyGuru 搜索引擎..."
    echo ""
    
    check_requirements
    check_config
    create_directories
    build_images
    start_services
    
    if health_check; then
        show_info
    else
        log_error "部署失败，请检查日志"
        docker compose logs
        exit 1
    fi
}

# 处理命令行参数
case "${1:-}" in
    --prod)
        log_info "使用生产环境配置"
        export COMPOSE_FILE="docker-compose.prod.yml"
        ;;
    --dev)
        log_info "使用开发环境配置"
        ;;
    --help|-h)
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --prod    使用生产环境配置"
        echo "  --dev     使用开发环境配置（默认）"
        echo "  --help    显示此帮助信息"
        exit 0
        ;;
esac

# 运行主函数
main

