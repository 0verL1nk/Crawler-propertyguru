#!/bin/bash

echo "=== Test 1: 2-bedroom condo ==="
curl -s -X POST http://localhost:8080/api/v1/search/stream \
  -H "Content-Type: application/json" \
  -d '{"query":"I want a 2-bedroom condo near MRT, budget under S$1.2M","options":{"top_k":3,"offset":0,"semantic":true}}' \
  | grep -E "event: (results|intent)" | head -4

echo ""
echo ""
echo "=== Test 2: 3-bedroom HDB ==="
curl -s -X POST http://localhost:8080/api/v1/search/stream \
  -H "Content-Type: application/json" \
  -d '{"query":"3-bedroom HDB near Jurong, budget 500k","options":{"top_k":3,"offset":0,"semantic":true}}' \
  | grep -E "event: (results|intent)" | head -4

echo ""
echo ""
echo "=== Test 3: Same as Test 1 (should be same result) ==="
curl -s -X POST http://localhost:8080/api/v1/search/stream \
  -H "Content-Type: application/json" \
  -d '{"query":"I want a 2-bedroom condo near MRT, budget under S$1.2M","options":{"top_k":3,"offset":0,"semantic":true}}' \
  | grep -E "event: (results|intent)" | head -4

