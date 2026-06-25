# Quick Start script para E2E tests de TicketDesk Enterprise (Windows)
# Uso: .\tests\e2e\quickstart.ps1

param(
    [string]$TestType = "interactive",
    [switch]$Headless,
    [switch]$SkipBrowserInstall
)

# Colors and formatting
function Write-Success {
    Write-Host "✓ $args" -ForegroundColor Green
}

function Write-Error-Custom {
    Write-Host "✗ $args" -ForegroundColor Red
}

function Write-Warning-Custom {
    Write-Host "⚠ $args" -ForegroundColor Yellow
}

function Write-Step {
    Write-Host "[Step $args]" -ForegroundColor Cyan
}

# Banner
Write-Host "========================================" -ForegroundColor Green
Write-Host "TicketDesk Enterprise - E2E Tests" -ForegroundColor Green
Write-Host "Quick Start (Windows)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check Python
Write-Step "1/5"
Write-Host "Checking Python..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python found: $pythonVersion"
} catch {
    Write-Error-Custom "Python not found. Install Python 3.10+ and add to PATH"
    exit 1
}
Write-Host ""

# Install dependencies
Write-Step "2/5"
Write-Host "Installing dependencies..."
try {
    pip install -q -r tests/e2e/requirements-e2e.txt
    Write-Success "Dependencies installed"
} catch {
    Write-Error-Custom "Failed to install dependencies"
    exit 1
}
Write-Host ""

# Install Playwright browsers
if (-not $SkipBrowserInstall) {
    Write-Step "3/5"
    Write-Host "Installing Playwright browser (chromium)..."
    try {
        playwright install chromium --quiet | Out-Null
        Write-Success "Chromium browser installed"
    } catch {
        Write-Error-Custom "Failed to install Playwright browsers"
        exit 1
    }
} else {
    Write-Step "3/5"
    Write-Success "Skipping browser installation"
}
Write-Host ""

# Check server
Write-Step "4/5"
Write-Host "Checking TicketDesk server..."
$baseUrl = $env:TEST_BASE_URL
if (-not $baseUrl) {
    $baseUrl = "http://localhost:5050"
}

try {
    $response = Invoke-WebRequest -Uri $baseUrl -TimeoutSec 5 -ErrorAction Stop
    Write-Success "Server running at $baseUrl"
} catch {
    Write-Warning-Custom "Server not responding at $baseUrl"
    Write-Host "Make sure TicketDesk is running:"
    Write-Host "  python app.py"
}
Write-Host ""

# Create directories
Write-Step "5/5"
Write-Host "Setting up directories..."
$dirs = @(
    "tests\e2e\reports",
    "tests\e2e\screenshots",
    "tests\e2e\videos"
)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Success "Directories ready"
Write-Host ""

# Set TEST_HEADLESS if needed
if ($Headless) {
    $env:TEST_HEADLESS = "true"
    Write-Success "Headless mode enabled"
} else {
    $env:TEST_HEADLESS = "false"
    Write-Success "Headed mode (browser visible)"
}
Write-Host ""

# Run tests based on type
if ($TestType -eq "interactive") {
    Write-Host "What would you like to run?" -ForegroundColor Yellow
    Write-Host "1) Smoke tests (quick validation)"
    Write-Host "2) All E2E tests"
    Write-Host "3) Employee create ticket flow"
    Write-Host "4) Technician resolve ticket flow"
    Write-Host "5) Admin metrics flow"
    Write-Host "6) Exit"
    Write-Host ""

    $choice = Read-Host "Choose [1-6]"

    Write-Host ""

    switch ($choice) {
        "1" {
            Write-Host "Running smoke tests..." -ForegroundColor Green
            pytest tests/e2e/ -m smoke -v
        }
        "2" {
            Write-Host "Running all E2E tests..." -ForegroundColor Green
            pytest tests/e2e/ -v --html=tests/e2e/reports/report.html --self-contained-html
        }
        "3" {
            Write-Host "Running employee create ticket flow..." -ForegroundColor Green
            if (-not $Headless) {
                pytest tests/e2e/test_employee_create_ticket.py -v --headed
            } else {
                pytest tests/e2e/test_employee_create_ticket.py -v
            }
        }
        "4" {
            Write-Host "Running technician resolve ticket flow..." -ForegroundColor Green
            if (-not $Headless) {
                pytest tests/e2e/test_technician_resolve_ticket.py -v --headed
            } else {
                pytest tests/e2e/test_technician_resolve_ticket.py -v
            }
        }
        "5" {
            Write-Host "Running admin metrics flow..." -ForegroundColor Green
            if (-not $Headless) {
                pytest tests/e2e/test_admin_dashboard_metrics.py -v --headed
            } else {
                pytest tests/e2e/test_admin_dashboard_metrics.py -v
            }
        }
        "6" {
            Write-Host "Exiting..."
            exit 0
        }
        default {
            Write-Error-Custom "Invalid choice"
            exit 1
        }
    }
} else {
    # Non-interactive mode based on $TestType parameter
    Write-Host "Running $TestType..." -ForegroundColor Green

    switch ($TestType) {
        "smoke" {
            pytest tests/e2e/ -m smoke -v
        }
        "all" {
            pytest tests/e2e/ -v --html=tests/e2e/reports/report.html --self-contained-html
        }
        "employee" {
            pytest tests/e2e/test_employee_create_ticket.py -v
        }
        "technician" {
            pytest tests/e2e/test_technician_resolve_ticket.py -v
        }
        "admin" {
            pytest tests/e2e/test_admin_dashboard_metrics.py -v
        }
        default {
            Write-Error-Custom "Unknown test type: $TestType"
            exit 1
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Tests completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Reports and artifacts:" -ForegroundColor Cyan
Write-Host "  HTML Report: tests\e2e\reports\report.html"
Write-Host "  Screenshots: tests\e2e\screenshots\"
Write-Host "  Videos: tests\e2e\videos\"
Write-Host "  Logs: tests\e2e\reports\test_run.log"
Write-Host ""

# Open HTML report if available
$reportPath = "tests\e2e\reports\report.html"
if (Test-Path $reportPath) {
    Write-Host "Opening HTML report in browser..." -ForegroundColor Cyan
    Start-Process $reportPath
}
