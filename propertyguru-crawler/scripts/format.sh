#!/bin/bash
# 格式化脚本 - 自动格式化代码

set -e

echo "🎨 开始格式化代码..."
echo ""

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 运行black
echo -e "${YELLOW}[1/4] 运行 black...${NC}"
black .
echo -e "${GREEN}✓ Black 完成${NC}"
echo ""

# 运行isort
echo -e "${YELLOW}[2/4] 运行 isort...${NC}"
isort --profile black .
echo -e "${GREEN}✓ Isort 完成${NC}"
echo ""

# 运行ruff format
echo -e "${YELLOW}[3/4] 运行 ruff format...${NC}"
ruff format .
echo -e "${GREEN}✓ Ruff format 完成${NC}"
echo ""

# 运行ruff fix
echo -e "${YELLOW}[4/4] 运行 ruff fix...${NC}"
ruff check --fix .
echo -e "${GREEN}✓ Ruff fix 完成${NC}"
echo ""

echo -e "${GREEN}✅ 代码格式化完成！${NC}"

