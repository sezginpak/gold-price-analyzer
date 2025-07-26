#!/bin/bash
# Deploy Guard - Pre-deployment validation script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛡️  Deploy Guard - Pre-deployment Validation${NC}"
echo "==========================================="

ERRORS=0
WARNINGS=0

# Check Python syntax
echo -e "\n${YELLOW}1. Python Syntax Check${NC}"
echo -n "   Checking all Python files... "

syntax_errors=0
while IFS= read -r file; do
    if ! python3 -m py_compile "$file" 2>/dev/null; then
        if [ $syntax_errors -eq 0 ]; then
            echo -e "${RED}❌${NC}"
        fi
        echo -e "   ${RED}✗ Syntax error in: $file${NC}"
        syntax_errors=$((syntax_errors + 1))
    fi
done < <(find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" -not -path "./tests/*")

if [ $syntax_errors -eq 0 ]; then
    echo -e "${GREEN}✓ All files OK${NC}"
else
    ERRORS=$((ERRORS + syntax_errors))
fi

# Check for sensitive data
echo -e "\n${YELLOW}2. Security Check${NC}"
echo -n "   Scanning for exposed credentials... "

sensitive_found=0
patterns=(
    "password\s*=\s*['\"][^'\"]+['\"]"
    "api_key\s*=\s*['\"][^'\"]+['\"]"
    "secret\s*=\s*['\"][^'\"]+['\"]"
    "token\s*=\s*['\"][^'\"]+['\"]"
)

for pattern in "${patterns[@]}"; do
    results=$(grep -r -i -E "$pattern" --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude="quick_deploy.sh" --exclude="config.py" . 2>/dev/null | grep -v "os.getenv" | grep -v "os.environ" | grep -v "getenv")
    if [ -n "$results" ]; then
        if [ $sensitive_found -eq 0 ]; then
            echo -e "${RED}❌${NC}"
            sensitive_found=1
        fi
        echo -e "   ${RED}✗ Sensitive data found:${NC}"
        echo "$results" | while IFS= read -r line; do
            echo "     $line"
        done
        ERRORS=$((ERRORS + 1))
    fi
done

if [ $sensitive_found -eq 0 ]; then
    echo -e "${GREEN}✓ No exposed credentials${NC}"
fi

# Check critical imports
echo -e "\n${YELLOW}3. Import Validation${NC}"
echo "   Testing critical module imports..."

python3 << 'EOF' 2>&1 | while IFS= read -r line; do echo "   $line"; done
import sys
sys.path.append('.')

modules_to_check = [
    ("main", "Main application"),
    ("web_server", "Web server"),
    ("collectors.harem_price_collector", "Price collector"),
    ("analyzers.gram_altin_analyzer", "Gram analyzer"),
    ("strategies.hybrid_strategy", "Hybrid strategy"),
    ("storage.sqlite_storage", "Database storage")
]

import_errors = 0
for module_name, description in modules_to_check:
    try:
        __import__(module_name)
        print(f"   ✓ {description} ({module_name})")
    except ImportError as e:
        print(f"   ✗ {description} - {e}")
        import_errors += 1

if import_errors > 0:
    sys.exit(import_errors)
EOF

if [ $? -ne 0 ]; then
    ERRORS=$((ERRORS + $?))
fi

# Check configuration
echo -e "\n${YELLOW}4. Configuration Check${NC}"

if [ -f "config.py" ]; then
    echo -e "   ${GREEN}✓ config.py exists${NC}"
    
    # Check for unused configs
    unused_configs=$(grep -E "(mongodb|redis)" config.py | wc -l)
    if [ $unused_configs -gt 0 ]; then
        echo -e "   ${YELLOW}⚠ Found $unused_configs unused MongoDB/Redis configurations${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "   ${RED}✗ config.py not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check database
echo -e "\n${YELLOW}5. Database Check${NC}"

if [ -f "gold_prices.db" ]; then
    size=$(du -h gold_prices.db | cut -f1)
    echo -e "   ${GREEN}✓ Database exists (size: $size)${NC}"
    
    # Check if database is accessible
    if python3 -c "import sqlite3; conn = sqlite3.connect('gold_prices.db'); conn.close()" 2>/dev/null; then
        echo -e "   ${GREEN}✓ Database is accessible${NC}"
    else
        echo -e "   ${RED}✗ Database is corrupted or locked${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "   ${YELLOW}⚠ Database not found (will be created on first run)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Check services
echo -e "\n${YELLOW}6. Service Port Check${NC}"

if lsof -i :8080 >/dev/null 2>&1; then
    echo -e "   ${YELLOW}⚠ Port 8080 is in use (service will be restarted)${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "   ${GREEN}✓ Port 8080 is available${NC}"
fi

# Run tests if available
echo -e "\n${YELLOW}7. Test Suite${NC}"

if [ -d "tests" ] && command -v pytest &> /dev/null; then
    echo "   Running test suite..."
    test_output=$(pytest tests/ -q --tb=short 2>&1)
    test_exit_code=$?
    
    if [ $test_exit_code -eq 0 ]; then
        test_count=$(echo "$test_output" | grep -E "passed" | grep -oE "[0-9]+ passed" | cut -d' ' -f1)
        echo -e "   ${GREEN}✓ All tests passed ($test_count tests)${NC}"
    else
        echo -e "   ${RED}✗ Some tests failed${NC}"
        echo "$test_output" | grep -E "(FAILED|ERROR)" | while IFS= read -r line; do
            echo "     $line"
        done
        ERRORS=$((ERRORS + 1))
    fi
elif [ -d "tests" ]; then
    echo -e "   ${YELLOW}⚠ Tests found but pytest not installed${NC}"
    echo "     Install with: pip install pytest pytest-asyncio"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "   ${YELLOW}⚠ No test directory found${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Final report
echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Deploy Guard Summary${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Ready to deploy.${NC}"
    echo -e "\n${GREEN}Run: ./quick_deploy.sh --skip-guard${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $WARNINGS warning(s) found${NC}"
    echo -e "${GREEN}✅ No critical errors. Can proceed with deployment.${NC}"
    echo -e "\n${GREEN}Run: ./quick_deploy.sh --skip-guard${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS error(s) found${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  $WARNINGS warning(s) found${NC}"
    fi
    echo -e "\n${RED}Fix the errors before deploying!${NC}"
    exit 1
fi