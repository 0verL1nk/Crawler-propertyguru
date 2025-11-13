#!/bin/bash

echo "🔍 Testing Streaming Search API"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if server is running
if ! curl -s http://localhost:8080/health > /dev/null; then
    echo -e "${RED}❌ Server is not running on localhost:8080${NC}"
    echo "Start the server with: ./build/searcher"
    exit 1
fi

echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Test health endpoint
echo "1️⃣  Testing /health endpoint..."
HEALTH=$(curl -s http://localhost:8080/health)
echo "$HEALTH" | jq .
echo ""

# Test streaming search
echo "2️⃣  Testing /api/v1/search/stream endpoint..."
echo "Query: 'I want a 3-bedroom condo near MRT, budget under S$1.2M'"
echo ""
echo -e "${YELLOW}Expected events: start → parsing → thinking → content → intent → searching → results → done${NC}"
echo ""

curl -N -X POST http://localhost:8080/api/v1/search/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I want a 3-bedroom condo near MRT, budget under S$1.2M",
    "options": {
      "top_k": 5,
      "semantic": true
    }
  }' 2>/dev/null | while IFS= read -r line; do
    if [[ $line == event:* ]]; then
        EVENT=$(echo "$line" | sed 's/event: //')
        case $EVENT in
            start)
                echo -e "${GREEN}📍 $line${NC}"
                ;;
            parsing)
                echo -e "${YELLOW}🤖 $line${NC}"
                ;;
            thinking)
                echo -e "${YELLOW}💭 $line${NC}"
                ;;
            content)
                echo -e "${YELLOW}📝 $line${NC}"
                ;;
            intent)
                echo -e "${GREEN}✅ $line${NC}"
                ;;
            searching)
                echo -e "${YELLOW}🔎 $line${NC}"
                ;;
            results)
                echo -e "${GREEN}📊 $line${NC}"
                ;;
            done)
                echo -e "${GREEN}🎉 $line${NC}"
                ;;
            error)
                echo -e "${RED}❌ $line${NC}"
                ;;
            *)
                echo "$line"
                ;;
        esac
    else
        echo "$line"
    fi
done

echo ""
echo -e "${GREEN}✅ Test completed${NC}"

