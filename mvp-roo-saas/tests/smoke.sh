#!/bin/bash
set -e

echo "🧪 Running Roo SaaS MVP smoke tests..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test functions
test_backend_health() {
    echo -n "🔧 Testing backend health... "
    if curl -s -f http://localhost:5000/health > /dev/null; then
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        return 1
    fi
}

test_frontend_accessible() {
    echo -n "🌐 Testing frontend accessibility... "
    if curl -s -f http://localhost:3000 > /dev/null; then
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        return 1
    fi
}

test_k3d_cluster() {
    echo -n "☸️  Testing k3d cluster... "
    if kubectl get nodes > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        return 1
    fi
}

test_create_project() {
    echo -n "🚀 Testing project creation... "

    # Create a project
    RESPONSE=$(curl -s -X POST http://localhost:5000/api/projects \
        -H "Content-Type: application/json" \
        -d '{}')

    if echo "$RESPONSE" | grep -q "namespace"; then
        NAMESPACE=$(echo "$RESPONSE" | grep -o '"namespace":"[^"]*"' | cut -d'"' -f4)
        echo -e "${GREEN}✅ PASS${NC} (Created: $NAMESPACE)"

        # Wait for deployment to be ready (max 2 minutes)
        echo -n "⏳ Waiting for workspace to be ready... "
        for i in {1..24}; do
            if kubectl get deployment vscode-server -n "$NAMESPACE" > /dev/null 2>&1; then
                if kubectl wait --for=condition=available deployment/vscode-server -n "$NAMESPACE" --timeout=5s > /dev/null 2>&1; then
                    echo -e "${GREEN}✅ READY${NC}"

                    # Test if workspace is accessible
                    echo -n "🌐 Testing workspace accessibility... "
                    sleep 5  # Give ingress a moment
                    if curl -s -f "http://localhost/$NAMESPACE/" > /dev/null; then
                        echo -e "${GREEN}✅ PASS${NC}"
                    else
                        echo -e "${YELLOW}⚠️  PARTIAL${NC} (Deployment ready but ingress not accessible)"
                    fi

                    # Cleanup
                    echo -n "🧹 Cleaning up test workspace... "
                    kubectl delete namespace "$NAMESPACE" > /dev/null 2>&1
                    echo -e "${GREEN}✅ DONE${NC}"
                    return 0
                fi
            fi
            sleep 5
        done
        echo -e "${RED}❌ TIMEOUT${NC}"
        return 1
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "Response: $RESPONSE"
        return 1
    fi
}

test_list_projects() {
    echo -n "📋 Testing project listing... "
    RESPONSE=$(curl -s http://localhost:5000/api/projects)
    if echo "$RESPONSE" | grep -q "\[\]" || echo "$RESPONSE" | grep -q "namespace"; then
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "Response: $RESPONSE"
        return 1
    fi
}

# Main test execution
main() {
    echo "Starting smoke tests at $(date)"
    echo "=================================="

    FAILED_TESTS=0

    # Basic connectivity tests
    test_backend_health || ((FAILED_TESTS++))
    test_frontend_accessible || ((FAILED_TESTS++))
    test_k3d_cluster || ((FAILED_TESTS++))

    # API functionality tests
    test_list_projects || ((FAILED_TESTS++))
    test_create_project || ((FAILED_TESTS++))

    echo "=================================="
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed!${NC}"
        echo "✅ Roo SaaS MVP is working correctly"
        exit 0
    else
        echo -e "${RED}❌ $FAILED_TESTS test(s) failed${NC}"
        echo "🔍 Check the logs for more details:"
        echo "   make logs"
        exit 1
    fi
}

# Help function
show_help() {
    echo "Roo SaaS MVP Smoke Tests"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --quick        Run only basic connectivity tests"
    echo ""
    echo "This script tests:"
    echo "  ✓ Backend API health"
    echo "  ✓ Frontend accessibility"
    echo "  ✓ k3d cluster connectivity"
    echo "  ✓ Project creation and deployment"
    echo "  ✓ Project listing"
    echo ""
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    --quick)
        echo "🏃 Running quick tests only..."
        test_backend_health || exit 1
        test_frontend_accessible || exit 1
        test_k3d_cluster || exit 1
        echo -e "${GREEN}✅ Quick tests passed!${NC}"
        exit 0
        ;;
    *)
        main
        ;;
esac
