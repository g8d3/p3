#!/bin/bash

echo "🔍 AI Scraper Application - Complete Diagnostic Report"
echo "======================================================"
echo "Run once to get full status of all components"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Results tracking
declare -A RESULTS
ISSUES_FOUND=0

# Log to file
log_to_file() {
  local level=$1
  local message=$2
  local timestamp=$(date -Iseconds)
  echo "[$timestamp] [$level] $message" >> diagnostic.log
}

# Function to print colored output
print_header() {
  echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
  echo -e "${GREEN}✅ $1${NC}"
  RESULTS["$1"]="PASS"
  log_to_file "SUCCESS" "$1"
}

print_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
  RESULTS["$1"]="WARN"
  ((ISSUES_FOUND++))
  log_to_file "WARNING" "$1"
}

print_error() {
  echo -e "${RED}❌ $1${NC}"
  RESULTS["$1"]="FAIL"
  ((ISSUES_FOUND++))
  log_to_file "ERROR" "$1"
}

print_info() {
  echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if service is running
check_service() {
  local name=$1
  local url=$2

  if curl -s --max-time 3 "$url" > /dev/null 2>&1; then
    print_success "$name is accessible"
    return 0
  else
    print_error "$name is not accessible"
    return 1
  fi
}

# Run a test and capture result
run_test() {
  local test_name=$1
  local test_command=$2

  echo ""
  print_info "Testing: $test_name"

  if eval "$test_command" 2>&1; then
    print_success "$test_name"
    return 0
  else
    print_error "$test_name"
    return 1
  fi
}

# Main diagnostic
main() {

  print_header "SERVICE AVAILABILITY CHECK"

  # Check PocketBase
  check_service "PocketBase Database" "http://localhost:8090/api/health"

  # Check Application
  check_service "Web Application" "http://localhost:3000/"

  # Check Chrome CDP
  if curl -s --max-time 3 "http://localhost:9222/json/version" > /dev/null 2>&1; then
    print_success "Chrome CDP is available"
    CDP_AVAILABLE=true
  else
    print_warning "Chrome CDP not available (optional for full testing)"
    CDP_AVAILABLE=false
  fi

  print_header "SERVER FUNCTIONALITY TESTS"

  # Test PocketBase collections (with auth)
  run_test "PocketBase Collections" "curl -s -H \"Authorization: Bearer \$(curl -s -X POST http://localhost:8090/api/admins/auth-with-password -H 'Content-Type: application/json' -d '{\"identity\": \"admin@example.com\", \"password\": \"admin123123\"}' | grep -o '\"token\":\"[^\"]*\"' | cut -d'\"' -f4)\" 'http://localhost:8090/api/collections' | grep -q 'name'"

  # Test Application HTML
  run_test "Application HTML Serving" "curl -s 'http://localhost:3000/' | grep -q '<!DOCTYPE html>'"

  # Test API endpoints
  run_test "API Endpoints Response" "curl -s 'http://localhost:3000/api/discover' -X POST -H 'Content-Type: application/json' -d '{}' | grep -q 'error'"

  print_header "BROWSER AUTOMATION TESTS"

  if [ "$CDP_AVAILABLE" = true ]; then
    # Test CDP connection
    run_test "CDP Browser Connection" "node -e \"
const puppeteer = require('puppeteer-core');
async function test() {
  try {
    const browser = await puppeteer.connect({
      browserWSEndpoint: 'ws://localhost:9222/devtools/browser/' +
        (await (await fetch('http://localhost:9222/json/version')).json()).webSocketDebuggerUrl.split('/').pop()
    });
    await browser.disconnect();
    console.log('SUCCESS');
  } catch(e) {
    console.error('FAILED:', e.message);
    process.exit(1);
  }
}
test();
\""

  # Test actual browser page loading and console errors
  run_test "Browser Page Loading & Console Errors" "node test-browser-page.cjs"

  else
    print_warning "Skipping browser tests (CDP not available)"
  fi

  print_header "CONFIGURATION VALIDATION"

  # Check if admin is set up
  if curl -s "http://localhost:8090/api/admins" -H "Authorization: Bearer $(curl -s -X POST http://localhost:8090/api/admins/auth-with-password -H 'Content-Type: application/json' -d '{"identity": "admin@example.com", "password": "admin123123"}' 2>/dev/null | grep -o '"token":"[^"]*"' | cut -d'"' -f4)" > /dev/null 2>&1; then
    print_success "PocketBase Admin configured"
  else
    print_error "PocketBase Admin not configured"
  fi

  # Check if collections exist (with auth)
  COLLECTIONS=$(curl -s -H "Authorization: Bearer $(curl -s -X POST http://localhost:8090/api/admins/auth-with-password -H 'Content-Type: application/json' -d '{"identity": "admin@example.com", "password": "admin123123"}' | grep -o '"token":"[^"]*"' | cut -d'"' -f4)" "http://localhost:8090/api/collections" 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | wc -l)
  if [ "$COLLECTIONS" -gt 3 ]; then
    print_success "Database collections created ($COLLECTIONS found)"
  else
    print_error "Database collections missing (only $COLLECTIONS found)"
  fi

  print_header "DETAILED TEST RESULTS"

  echo "Summary of all checks:"
  for test in "${!RESULTS[@]}"; do
    status="${RESULTS[$test]}"
    case $status in
      "PASS") echo -e "  ${GREEN}✅${NC} $test" ;;
      "WARN") echo -e "  ${YELLOW}⚠️ ${NC} $test" ;;
      "FAIL") echo -e "  ${RED}❌${NC} $test" ;;
    esac
  done

  print_header "NEXT STEPS"

  if [ $ISSUES_FOUND -eq 0 ]; then
    echo ""
    print_success "🎉 ALL SYSTEMS OPERATIONAL!"
    log_to_file "SUCCESS" "DIAGNOSTIC COMPLETE: All systems operational - $TOTAL_CHECKS checks passed"
    echo ""
    print_success "Your AI Scraper application is fully functional!"
    echo ""
    echo "You can now:"
    echo "• Run the application: bun run dev"
    echo "• Access the UI: http://localhost:3000"
    echo "• Run tests anytime: bun run test"
    echo "• Monitor logs: tail -f server.log"
    echo "• View browser errors: tail -f browser-console.log"
    echo "• View diagnostics: tail -f diagnostic.log"
    exit 0
  fi

  echo ""
  echo "Issues found: $ISSUES_FOUND"
  log_to_file "ERROR" "DIAGNOSTIC COMPLETE: $ISSUES_FOUND issues found that need fixing"
  echo ""
  echo "🔧 FIX THE FOLLOWING ISSUES:"
  echo ""

  # Provide specific fix instructions
  if ! curl -s "http://localhost:8090/api/health" > /dev/null 2>&1; then
    echo "1. Start PocketBase:"
    echo "   ./pocketbase serve --http 0.0.0.0:8090 &"
    echo ""
  fi

  if ! curl -s "http://localhost:3000/" > /dev/null 2>&1; then
    echo "2. Start the Application:"
    echo "   bun run dev"
    echo ""
  fi

  if ! curl -s "http://localhost:9222/json/version" > /dev/null 2>&1; then
    echo "3. Start Chrome CDP (optional but recommended):"
    echo "   /usr/bin/google-chrome --headless --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 &"
    echo ""
  fi

  # Check admin setup
  if ! curl -s -X POST http://localhost:8090/api/admins/auth-with-password -H "Content-Type: application/json" -d '{"identity": "admin@example.com", "password": "admin123123"}' | grep -q '"token"'; then
    echo "4. Setup PocketBase Admin:"
    echo "   • Open http://localhost:8090/_/"
    echo "   • Create admin user: admin@example.com / admin123123"
    echo "   • Run: ./setup.sh"
    echo ""
  fi

  # Check collections
  if [ "$COLLECTIONS" -le 3 ]; then
    echo "5. Create Database Collections:"
    echo "   ./setup.sh"
    echo ""
  fi

  echo "After fixing issues, run this diagnostic again:"
  echo "  ./diagnose.sh"

  exit 1
}

# Run main function
main