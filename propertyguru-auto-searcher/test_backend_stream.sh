#!/bin/bash

echo "🧪 Testing Backend Stream Output"
echo "================================"
echo ""

# Test the backend stream endpoint
echo "Sending request to backend..."
curl -N -X POST http://localhost:8080/api/v1/search/stream \
  -H "Content-Type: application/json" \
  -d '{"query":"I want a 3-bedroom condo near MRT, budget under S$1.2M","options":{"top_k":5,"semantic":true}}' 2>&1 | \
  grep -E "event: (thinking|content)" | head -30

echo ""
echo "================================"
echo "If you see 'event: thinking' above, the backend is working correctly."
echo "If not, there's an issue with the backend streaming logic."

