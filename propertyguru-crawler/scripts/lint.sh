#!/bin/bash
# Lint脚本 - 运行所有代码质量检查

set -e

echo "🔍 开始代码质量检查..."
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查ruff
echo -e "${YELLOW}[1/4] 运行 ruff 检查...${NC}"
if ruff check .; then
    echo -e "${GREEN}✓ Ruff 检查通过${NC}"
else
    echo -e "${RED}✗ Ruff 检查失败${NC}"
    exit 1
fi
echo ""

# 检查flake8
echo -e "${YELLOW}[2/4] 运行 flake8 检查...${NC}"
if flake8 .; then
    echo -e "${GREEN}✓ Flake8 检查通过${NC}"
else
    echo -e "${RED}✗ Flake8 检查失败${NC}"
    exit 1
fi
echo ""

# 类型检查
echo -e "${YELLOW}[3/4] 运行 mypy 类型检查...${NC}"
if mypy crawler utils --ignore-missing-imports; then
    echo -e "${GREEN}✓ Mypy 类型检查通过${NC}"
else
    echo -e "${RED}✗ Mypy 类型检查失败${NC}"
    exit 1
fi
echo ""

# 导入排序检查
echo -e "${YELLOW}[4/4] 检查导入排序...${NC}"
if isort --check-only --profile black .; then
    echo -e "${GREEN}✓ 导入排序检查通过${NC}"
else
    echo -e "${YELLOW}⚠ 导入排序需要调整，运行 'make format' 自动修复${NC}"
fi
echo ""

echo -e "${GREEN}✅ 所有检查完成！${NC}"

