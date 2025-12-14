#!/bin/bash

# Test script for Template API - cURL version
# Usage: ./test_api.sh <template_url> <api_key>

if [ $# -lt 2 ]; then
    echo "Usage: ./test_api.sh <template_url> <api_key>"
    echo ""
    echo "Example:"
    echo '  ./test_api.sh "https://example.artworksdigital.fr" "sk-1234567890abcdef"'
    exit 1
fi

BASE_URL=$1
API_KEY=$2

echo "================================================================================"
echo "🧪 Template API Test Suite (cURL)"
echo "================================================================================"
echo "Target: $BASE_URL"
echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

test_count=0
pass_count=0
fail_count=0

test_endpoint() {
    local name=$1
    local endpoint=$2
    
    test_count=$((test_count + 1))
    
    echo -e "${BLUE}[${test_count}/7] Testing $name...${NC}"
    echo "📍 GET /api/export/$endpoint"
    
    response=$(curl -s -w "\n%{http_code}" \
        -H "X-API-Key: $API_KEY" \
        "$BASE_URL/api/export/$endpoint")
    
    # Extract HTTP status code (last line)
    http_code=$(echo "$response" | tail -n1)
    # Extract response body (all lines except last)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" == "200" ]; then
        echo -e "   ${GREEN}✅ 200 OK${NC}"
        
        # Try to count items if JSON response
        count=$(echo "$body" | grep -o '"count":[0-9]*' | cut -d':' -f2 | head -1)
        if [ ! -z "$count" ]; then
            echo "   📦 $count items returned"
        fi
        
        pass_count=$((pass_count + 1))
    else
        echo -e "   ${RED}❌ $http_code ERROR${NC}"
        # Try to extract error message
        error=$(echo "$body" | grep -o '"error":"[^"]*' | cut -d'"' -f4)
        if [ ! -z "$error" ]; then
            echo "   Error: $error"
        fi
        fail_count=$((fail_count + 1))
    fi
    echo ""
}

# Run all tests
test_endpoint "Settings" "settings"
test_endpoint "Users" "users"
test_endpoint "Paintings" "paintings"
test_endpoint "Orders" "orders?limit=10"
test_endpoint "Exhibitions" "exhibitions"
test_endpoint "Custom Requests" "custom-requests"
test_endpoint "Stats" "stats"

# Summary
echo "================================================================================"
echo "📊 Test Summary"
echo "================================================================================"
echo -e "✅ Successful: ${GREEN}${pass_count}${NC}/${test_count}"
echo -e "❌ Failed: ${RED}${fail_count}${NC}/${test_count}"
echo "================================================================================"

if [ $fail_count -gt 0 ]; then
    echo ""
    echo "💡 Troubleshooting Tips:"
    echo ""
    echo "1. 401 Unauthorized:"
    echo "   • Verify TEMPLATE_MASTER_API_KEY is set on the Template server"
    echo "   • Check that the API key value is correct"
    echo "   • Try generating a new key with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
    echo ""
    echo "2. Connection Refused:"
    echo "   • Ensure the Template server is running and accessible"
    echo "   • Verify the URL: $BASE_URL"
    echo "   • Check network connectivity: ping ${BASE_URL#https://}"
    echo ""
    echo "3. Timeout:"
    echo "   • Check if the server is responding: curl -v $BASE_URL"
    echo "   • Increase timeout if needed (edit script)"
    echo ""
    exit 1
else
    echo ""
    echo -e "${GREEN}✨ All tests passed! Your API connection is working correctly.${NC}"
    echo ""
    exit 0
fi
