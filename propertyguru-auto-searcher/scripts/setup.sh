#!/bin/bash

# PropertyGuru Search Engine - 快速安装脚本

set -e

echo "🏠 PropertyGuru 智能搜索引擎 - 安装脚本"
echo "================================================"

# 检查 Go 版本
echo "📦 检查 Go 环境..."
if ! command -v go &> /dev/null; then
    echo "❌ 未找到 Go，请先安装 Go 1.21+"
    exit 1
fi

GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')
echo "✅ Go 版本: $GO_VERSION"

# 检查 PostgreSQL
echo ""
echo "🐘 检查 PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "⚠️  未找到 PostgreSQL，请手动安装："
    echo "   Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
    echo "   MacOS: brew install postgresql"
else
    PG_VERSION=$(psql --version | awk '{print $3}')
    echo "✅ PostgreSQL 版本: $PG_VERSION"
fi

# 安装 Go 依赖
echo ""
echo "📥 安装 Go 依赖..."
go mod download
go mod tidy

echo "✅ Go 依赖安装完成"

# 检查配置文件
echo ""
echo "⚙️  检查配置文件..."
if [ ! -f ".env" ]; then
    if [ -f "config.example.env" ]; then
        echo "📝 复制配置示例文件..."
        cp config.example.env .env
        echo "⚠️  请编辑 .env 文件，配置数据库连接信息"
    else
        echo "❌ 未找到配置示例文件"
        exit 1
    fi
else
    echo "✅ 配置文件已存在"
fi

# 提示下一步
echo ""
echo "================================================"
echo "✅ 安装完成！"
echo ""
echo "📋 接下来的步骤："
echo ""
echo "1. 配置 PostgreSQL："
echo "   sudo -u postgres psql"
echo "   CREATE USER property_user WITH PASSWORD 'your_password';"
echo "   CREATE DATABASE property_search OWNER property_user;"
echo "   \\q"
echo ""
echo "2. 初始化数据库："
echo "   psql -U property_user -d property_search -f sql/init.sql"
echo ""
echo "3. 编辑配置文件："
echo "   vim .env"
echo ""
echo "4. 启动服务："
echo "   go run cmd/server/main.go"
echo ""
echo "5. 访问服务："
echo "   http://localhost:8080"
echo ""
echo "================================================"
echo "📚 更多信息请查看 README.md"

