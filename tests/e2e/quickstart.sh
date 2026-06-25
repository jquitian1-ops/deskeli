#!/bin/bash
# Quick Start script para E2E tests de TicketDesk Enterprise
# Uso: bash tests/e2e/quickstart.sh [options]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}TicketDesk Enterprise - E2E Tests${NC}"
echo -e "${GREEN}Quick Start${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python found: $(python3 --version)${NC}"
echo ""

# Step 1: Install dependencies
echo -e "${YELLOW}[1/5]${NC} Installing dependencies..."
if pip install -r tests/e2e/requirements-e2e.txt > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}✗ Failed to install dependencies${NC}"
    exit 1
fi
echo ""

# Step 2: Install Playwright browsers
echo -e "${YELLOW}[2/5]${NC} Installing Playwright browsers..."
if playwright install chromium > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Chromium browser installed${NC}"
else
    echo -e "${RED}✗ Failed to install Playwright browsers${NC}"
    exit 1
fi
echo ""

# Step 3: Check TicketDesk server
echo -e "${YELLOW}[3/5]${NC} Checking TicketDesk server..."
BASE_URL="${TEST_BASE_URL:-http://localhost:5050}"
if curl -s -m 5 "$BASE_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Server running at $BASE_URL${NC}"
else
    echo -e "${YELLOW}⚠ Server not responding at $BASE_URL${NC}"
    echo "  Make sure TicketDesk is running:"
    echo "  python app.py"
fi
echo ""

# Step 4: Create reports directory
echo -e "${YELLOW}[4/5]${NC} Setting up directories..."
mkdir -p tests/e2e/reports tests/e2e/screenshots tests/e2e/videos
echo -e "${GREEN}✓ Directories ready${NC}"
echo ""

# Step 5: Run smoke tests
echo -e "${YELLOW}[5/5]${NC} Running smoke tests..."
echo ""

# Ask user which tests to run
echo "What would you like to run?"
echo "1) Smoke tests (quick validation)"
echo "2) All E2E tests"
echo "3) Employee create ticket flow"
echo "4) Technician resolve ticket flow"
echo "5) Admin metrics flow"
echo "6) Custom pytest command"
echo ""
read -p "Choose [1-6]: " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}Running smoke tests...${NC}"
        pytest tests/e2e/ -m smoke -v --headed
        ;;
    2)
        echo ""
        echo -e "${GREEN}Running all E2E tests...${NC}"
        pytest tests/e2e/ -v --html=tests/e2e/reports/report.html --self-contained-html
        ;;
    3)
        echo ""
        echo -e "${GREEN}Running employee create ticket flow...${NC}"
        pytest tests/e2e/test_employee_create_ticket.py -v --headed
        ;;
    4)
        echo ""
        echo -e "${GREEN}Running technician resolve ticket flow...${NC}"
        pytest tests/e2e/test_technician_resolve_ticket.py -v --headed
        ;;
    5)
        echo ""
        echo -e "${GREEN}Running admin metrics flow...${NC}"
        pytest tests/e2e/test_admin_dashboard_metrics.py -v --headed
        ;;
    6)
        read -p "Enter pytest command: " cmd
        eval "pytest $cmd"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Tests completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Reports and artifacts:"
echo "  HTML Report: tests/e2e/reports/report.html"
echo "  Screenshots: tests/e2e/screenshots/"
echo "  Videos: tests/e2e/videos/"
echo "  Logs: tests/e2e/reports/test_run.log"
echo ""
