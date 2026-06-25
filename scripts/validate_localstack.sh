#!/bin/bash

# ========================================================================
# Validación de LocalStack + TicketDesk Infrastructure
# ========================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
LOCALSTACK_URL="http://localhost:4566"
AWS_REGION="us-east-1"
TIMEOUT=300
PASSED=0
FAILED=0

# Funciones helper
print_header() {
  echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

pass() {
  echo -e "${GREEN}✓ PASS${NC}: $1"
  ((PASSED++))
}

fail() {
  echo -e "${RED}✗ FAIL${NC}: $1"
  ((FAILED++))
}

warning() {
  echo -e "${YELLOW}⚠ WARNING${NC}: $1"
}

# ========================================================================
# Test 1: LocalStack Health
# ========================================================================
print_header "Test 1: LocalStack Health Check"

if curl -s "${LOCALSTACK_URL}/health" > /dev/null 2>&1; then
  health=$(curl -s "${LOCALSTACK_URL}/health" | jq '.' 2>/dev/null || echo "{}")
  echo "LocalStack health: $health"
  pass "LocalStack is running"
else
  fail "LocalStack is not responding"
  exit 1
fi

# ========================================================================
# Test 2: PostgreSQL Connectivity
# ========================================================================
print_header "Test 2: PostgreSQL Database Connectivity"

if command -v psql &> /dev/null; then
  if psql -h localhost -U ticketdesk -d ticketdesk -c "SELECT version();" > /dev/null 2>&1; then
    pg_version=$(psql -h localhost -U ticketdesk -d ticketdesk -c "SELECT version();" 2>/dev/null | tail -1)
    echo "PostgreSQL: $pg_version"
    pass "PostgreSQL connection successful"
  else
    fail "PostgreSQL connection failed"
  fi
else
  warning "psql not installed, skipping PostgreSQL direct test"
fi

# ========================================================================
# Test 3: Redis Connectivity
# ========================================================================
print_header "Test 3: Redis Cache Connectivity"

if command -v redis-cli &> /dev/null; then
  if redis-cli -h localhost -a ticketdesk123 ping > /dev/null 2>&1; then
    pass "Redis connection successful"
    redis_info=$(redis-cli -h localhost -a ticketdesk123 info server 2>/dev/null | grep redis_version || echo "version: unknown")
    echo "Redis: $redis_info"
  else
    fail "Redis connection failed"
  fi
else
  warning "redis-cli not installed, skipping Redis direct test"
fi

# ========================================================================
# Test 4: AWS RDS via LocalStack
# ========================================================================
print_header "Test 4: AWS RDS via LocalStack"

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=$AWS_REGION

if command -v aws &> /dev/null; then
  if aws --endpoint-url="${LOCALSTACK_URL}" rds describe-db-instances --query 'DBInstances[*].DBInstanceIdentifier' > /dev/null 2>&1; then
    db_instances=$(aws --endpoint-url="${LOCALSTACK_URL}" rds describe-db-instances --query 'DBInstances[*].DBInstanceIdentifier' --output text 2>/dev/null)
    if [ -z "$db_instances" ]; then
      warning "No RDS instances found (may need to run terraform apply)"
    else
      echo "RDS Instances: $db_instances"
      pass "RDS API accessible"
    fi
  else
    fail "RDS API not responding"
  fi
else
  warning "AWS CLI not installed, skipping RDS test"
fi

# ========================================================================
# Test 5: AWS S3 via LocalStack
# ========================================================================
print_header "Test 5: AWS S3 via LocalStack"

if command -v aws &> /dev/null; then
  if aws --endpoint-url="${LOCALSTACK_URL}" s3 ls 2>/dev/null > /dev/null; then
    buckets=$(aws --endpoint-url="${LOCALSTACK_URL}" s3 ls --output text 2>/dev/null)
    if [ -z "$buckets" ]; then
      warning "No S3 buckets found (may need to run terraform apply)"
    else
      echo -e "S3 Buckets:\n$buckets"
      pass "S3 API accessible"
    fi
  else
    fail "S3 API not responding"
  fi
else
  warning "AWS CLI not installed, skipping S3 test"
fi

# ========================================================================
# Test 6: AWS ECS via LocalStack
# ========================================================================
print_header "Test 6: AWS ECS via LocalStack"

if command -v aws &> /dev/null; then
  if aws --endpoint-url="${LOCALSTACK_URL}" ecs list-clusters --query 'clusterArns' > /dev/null 2>&1; then
    clusters=$(aws --endpoint-url="${LOCALSTACK_URL}" ecs list-clusters --query 'clusterArns' --output text 2>/dev/null)
    if [ -z "$clusters" ]; then
      warning "No ECS clusters found (may need to run terraform apply)"
    else
      echo "ECS Clusters: $clusters"
      pass "ECS API accessible"
    fi
  else
    fail "ECS API not responding"
  fi
else
  warning "AWS CLI not installed, skipping ECS test"
fi

# ========================================================================
# Test 7: AWS ALB/ELB via LocalStack
# ========================================================================
print_header "Test 7: AWS ALB/ELB via LocalStack"

if command -v aws &> /dev/null; then
  if aws --endpoint-url="${LOCALSTACK_URL}" elbv2 describe-load-balancers --query 'LoadBalancers[*].LoadBalancerArn' > /dev/null 2>&1; then
    albs=$(aws --endpoint-url="${LOCALSTACK_URL}" elbv2 describe-load-balancers --query 'LoadBalancers[*].LoadBalancerName' --output text 2>/dev/null)
    if [ -z "$albs" ]; then
      warning "No ALBs found (may need to run terraform apply)"
    else
      echo "Application Load Balancers: $albs"
      pass "ELBv2 API accessible"
    fi
  else
    fail "ELBv2 API not responding"
  fi
else
  warning "AWS CLI not installed, skipping ALB test"
fi

# ========================================================================
# Test 8: Terraform LocalStack Configuration
# ========================================================================
print_header "Test 8: Terraform Configuration"

TERRAFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/terraform/localstack"

if [ -d "$TERRAFORM_DIR" ]; then
  if [ -f "$TERRAFORM_DIR/provider.tf" ] && [ -f "$TERRAFORM_DIR/main.tf" ] && [ -f "$TERRAFORM_DIR/variables.tf" ]; then
    pass "Terraform files are present"

    # Validar sintaxis
    if command -v terraform &> /dev/null; then
      cd "$TERRAFORM_DIR"
      if terraform validate > /dev/null 2>&1; then
        pass "Terraform configuration is valid"
      else
        fail "Terraform validation failed"
      fi
      cd - > /dev/null
    else
      warning "Terraform not installed, skipping validation"
    fi
  else
    fail "Terraform files are missing"
  fi
else
  fail "Terraform directory not found at $TERRAFORM_DIR"
fi

# ========================================================================
# Test 9: Application Health Check
# ========================================================================
print_header "Test 9: TicketDesk Application Health"

if curl -s http://localhost:5050/health > /dev/null 2>&1; then
  health_status=$(curl -s http://localhost:5050/health | jq '.status' 2>/dev/null || echo "unknown")
  echo "Application health: $health_status"
  pass "TicketDesk application is running"
else
  warning "TicketDesk application not responding (may not be running)"
fi

# ========================================================================
# Test 10: Application API Test
# ========================================================================
print_header "Test 10: TicketDesk API Endpoints"

if curl -s http://localhost:5050/api/health > /dev/null 2>&1; then
  api_response=$(curl -s http://localhost:5050/api/health)
  echo "API Response: $api_response"
  pass "TicketDesk API is accessible"
else
  warning "TicketDesk API not responding"
fi

# ========================================================================
# Test 11: Database Initialization Check
# ========================================================================
print_header "Test 11: Database Schema Verification"

if command -v psql &> /dev/null; then
  table_count=$(psql -h localhost -U ticketdesk -d ticketdesk -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tail -1 | tr -d ' ')
  echo "Tables in database: $table_count"

  if [ "$table_count" -gt 0 ]; then
    pass "Database schema is initialized"

    # Listar tablas
    echo -e "\nTables:"
    psql -h localhost -U ticketdesk -d ticketdesk -c "\dt" 2>/dev/null
  else
    warning "Database is empty (may need manual initialization)"
  fi
else
  warning "psql not installed, skipping database schema check"
fi

# ========================================================================
# Test 12: Docker Services Status
# ========================================================================
print_header "Test 12: Docker Container Status"

if command -v docker &> /dev/null; then
  echo "Container Status:"
  docker ps --filter "name=ticketdesk" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || warning "Docker not running or no containers found"

  running_containers=$(docker ps --filter "name=ticketdesk" --quiet 2>/dev/null | wc -l)
  if [ "$running_containers" -ge 3 ]; then
    pass "Expected containers are running"
  else
    warning "Some expected containers may not be running"
  fi
else
  warning "Docker not installed, skipping container status check"
fi

# ========================================================================
# Summary
# ========================================================================
print_header "VALIDATION SUMMARY"

total=$((PASSED + FAILED))
echo -e "Tests Passed: ${GREEN}$PASSED${NC}/$total"
echo -e "Tests Failed: ${RED}$FAILED${NC}/$total"

if [ $FAILED -eq 0 ]; then
  echo -e "\n${GREEN}✓ All tests passed!${NC}"
  exit 0
else
  echo -e "\n${RED}✗ Some tests failed. Please review the output above.${NC}"
  exit 1
fi
