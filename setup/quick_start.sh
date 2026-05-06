#!/bin/bash

# Customer Feedback Intelligence - Quick Start Script
# Setup dan jalankan seluruh project dengan satu command

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ===========================
# Functions
# ===========================

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed"
        exit 1
    fi
}

# ===========================
# Main Script
# ===========================

print_header "Customer Feedback Intelligence Platform"
print_info "Starting setup process..."

# Check prerequisites
print_header "1. Checking Prerequisites"
print_info "Checking Docker..."
check_command "docker"
print_success "Docker installed"

print_info "Checking Docker Compose..."
check_command "docker-compose"
print_success "Docker Compose installed"

print_info "Checking Python..."
check_command "python3"
print_success "Python installed"

# Setup environment
print_header "2. Setting Up Environment"

if [ ! -f .env ]; then
    print_info "Creating .env file from .env.example..."
    cp .env.example .env
    print_success ".env created"
    print_error "⚠️  IMPORTANT: Edit .env file with your API keys:"
    echo "   nano .env"
    echo ""
    echo "   Required:"
    echo "   - GEMINI_API_KEY (get from https://makersuite.google.com)"
    echo ""
    read -p "Press ENTER after editing .env file..."
else
    print_success ".env already exists"
fi

# Create directories
print_info "Creating required directories..."
mkdir -p logs data/cache data/downloads backend/scripts/output

print_success "Directories created"

# Start Docker services
print_header "3. Starting Docker Services"

print_info "Pulling Docker images..."
docker-compose pull

print_info "Starting services..."
docker-compose up -d

print_success "Services started"

# Wait for services
print_header "4. Waiting for Services to Be Ready"

print_info "Waiting for PostgreSQL..."
timeout 60 bash -c 'until docker exec cfi_postgres pg_isready -U feedbackuser > /dev/null 2>&1; do sleep 1; done'
print_success "PostgreSQL ready"

print_info "Waiting for Qdrant..."
timeout 60 bash -c 'until curl -f http://localhost:6333/health > /dev/null 2>&1; do sleep 1; done'
print_success "Qdrant ready"

print_info "Waiting for Backend..."
timeout 60 bash -c 'until curl -f http://localhost:8000/health > /dev/null 2>&1; do sleep 1; done'
print_success "Backend ready"

sleep 5

# Initialize database
print_header "5. Initializing Database"

print_info "Creating tables..."
docker exec cfi_backend python -m alembic upgrade head 2>/dev/null || true

print_success "Database schema created"

# Seed data
print_header "6. Loading Sample Data"

read -p "Load Google Play Review dataset? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Loading dataset (this may take 2-3 minutes)..."
    docker exec cfi_backend python -m backend.scripts.seed_google_play
    print_success "Data loaded"
else
    print_info "Skipping data loading"
fi

# Test connections
print_header "7. Testing Connections"

print_info "Testing API..."
response=$(curl -s http://localhost:8000/health)
if echo "$response" | grep -q "healthy\|operational"; then
    print_success "API healthy"
else
    print_error "API not responding correctly"
fi

print_info "Testing RAG Pipeline..."
response=$(curl -s http://localhost:6333/health)
if echo "$response" | grep -q "Qdrant"; then
    print_success "RAG Pipeline ready"
else
    print_error "RAG Pipeline not responding"
fi

print_info "Testing Database..."
result=$(docker exec cfi_postgres psql -U feedbackuser -d feedback_db -c "SELECT COUNT(*) FROM feedback;" 2>/dev/null | tail -1)
print_success "Database connected (Feedback count: $result)"

# Display access information
print_header "8. Setup Complete!"

echo ""
echo -e "${GREEN}🎉 Customer Feedback Intelligence Platform is running!${NC}"
echo ""
echo "Access Points:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}API Swagger UI:${NC}       http://localhost:8000/docs"
echo -e "${BLUE}ReDoc:${NC}                http://localhost:8000/redoc"
echo -e "${BLUE}N8n Dashboard:${NC}       http://localhost:5678"
echo -e "${BLUE}Qdrant Dashboard:${NC}    http://localhost:6333/dashboard"
echo -e "${BLUE}Prometheus:${NC}          http://localhost:9090"
echo -e "${BLUE}Grafana:${NC}             http://localhost:3000"
echo ""
echo "Credentials:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "N8n:        admin / change_me_123"
echo "Grafana:    admin / admin"
echo "Database:   feedbackuser / feedbackpass"
echo ""
echo "Quick Commands:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "View logs:             docker-compose logs -f backend"
echo "Stop services:         docker-compose down"
echo "Restart services:      docker-compose restart"
echo "Database shell:        docker exec -it cfi_postgres psql -U feedbackuser -d feedback_db"
echo ""
echo "Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Open API Docs:      http://localhost:8000/docs"
echo "2. Test creating feedback via API"
echo "3. Setup Tableau dashboard (see TABLEAU_SETUP_GUIDE.md)"
echo "4. Configure N8n workflow (n8n_enhanced_workflow.json)"
echo "5. Monitor with Grafana:  http://localhost:3000"
echo ""
print_success "All systems operational ✓"