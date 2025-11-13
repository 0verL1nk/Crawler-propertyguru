#!/bin/bash

echo "🔍 AI Configuration Checker"
echo "=========================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY is NOT set${NC}"
    echo "   Set it with: export OPENAI_API_KEY='your-api-key'"
else
    KEY_LEN=${#OPENAI_API_KEY}
    echo -e "${GREEN}✅ OPENAI_API_KEY is set${NC} (length: $KEY_LEN)"
    echo "   Preview: ${OPENAI_API_KEY:0:10}..."
fi
echo ""

# Check OPENAI_API_BASE
if [ -z "$OPENAI_API_BASE" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_API_BASE is NOT set${NC}"
    echo "   Defaulting to: https://api.openai.com/v1"
else
    echo -e "${GREEN}✅ OPENAI_API_BASE is set${NC}"
    echo "   Value: $OPENAI_API_BASE"
fi
echo ""

# Check OPENAI_CHAT_MODEL
if [ -z "$OPENAI_CHAT_MODEL" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_CHAT_MODEL is NOT set${NC}"
    echo "   Defaulting to: gpt-3.5-turbo"
else
    echo -e "${GREEN}✅ OPENAI_CHAT_MODEL is set${NC}"
    echo "   Value: $OPENAI_CHAT_MODEL"
fi
echo ""

# Check OPENAI_CHAT_EXTRA_BODY
if [ -z "$OPENAI_CHAT_EXTRA_BODY" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_CHAT_EXTRA_BODY is NOT set${NC}"
    echo "   No extra body parameters (thinking mode disabled)"
else
    echo -e "${GREEN}✅ OPENAI_CHAT_EXTRA_BODY is set${NC}"
    echo "   Value: $OPENAI_CHAT_EXTRA_BODY"
fi
echo ""

# Check OPENAI_EMBEDDING_MODEL
if [ -z "$OPENAI_EMBEDDING_MODEL" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_EMBEDDING_MODEL is NOT set${NC}"
else
    echo -e "${GREEN}✅ OPENAI_EMBEDDING_MODEL is set${NC}"
    echo "   Value: $OPENAI_EMBEDDING_MODEL"
fi
echo ""

echo "=========================="
echo ""

# Summary
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}⛔ AI功能无法使用 - 缺少 API Key${NC}"
    echo ""
    echo "请在 .env 文件中配置或导出环境变量："
    echo ""
    echo "export OPENAI_API_KEY='your-nvidia-api-key'"
    echo "export OPENAI_API_BASE='https://integrate.api.nvidia.com/v1'"
    echo "export OPENAI_CHAT_MODEL='deepseek-ai/deepseek-v3.1-terminus'"
    echo "export OPENAI_CHAT_EXTRA_BODY='{\"chat_template_kwargs\":{\"thinking\":true}}'"
    echo "export OPENAI_EMBEDDING_MODEL='baai/bge-m3'"
else
    echo -e "${GREEN}✅ 基本配置完成 - AI 功能应该可以工作${NC}"
    echo ""
    echo "如果仍然没有思考过程，请："
    echo "1. 重启服务器"
    echo "2. 查看启动日志确认 '🔧 Detected NVIDIA API provider'"
    echo "3. 运行 ./test_streaming.sh 测试流式 API"
fi

