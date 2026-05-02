#!/bin/bash
# Run script for Content Automation System
# Usage: ./run.sh [command]

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

# Print step
print_step() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# Print warning
print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Print error
print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if virtual environment exists
check_venv() {
    if [ ! -d "venv" ]; then
        print_warning "Virtual environment not found. Running setup..."
        python3 setup.py
    fi
}

# Activate virtual environment
activate_venv() {
    source venv/bin/activate
}

# Default command
case "${1:-run}" in
    setup)
        print_header "Setting up Content Automation System"
        python3 setup.py
        ;;
    
    run)
        print_header "Starting Content Automation System"
        check_venv
        activate_venv
        
        if [ ! -f ".env" ]; then
            print_warning ".env file not found. Creating from template..."
            cp .env.example .env
            print_warning "Please edit .env to configure your settings"
        fi
        
        print_step "Starting web server on http://localhost:8000"
        print_step "Dashboard: http://localhost:8000/"
        print_step "API Docs:  http://localhost:8000/docs"
        echo ""
        
        uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
        ;;
    
    cli)
        check_venv
        activate_venv
        python -m src.cli "${@:2}"
        ;;
    
    status)
        check_venv
        activate_venv
        python -m src.cli status
        ;;
    
    generate)
        check_venv
        activate_venv
        python -m src.cli generate "${@:2}"
        ;;
    
    post)
        check_venv
        activate_venv
        python -m src.cli post "${@:2}"
        ;;
    
    test)
        check_venv
        activate_venv
        print_header "Running Tests"
        pytest tests/ -v
        ;;
    
    docker)
        print_header "Starting with Docker Compose"
        docker-compose up -d
        print_step "Service started on http://localhost:8000"
        ;;
    
    docker-logs)
        docker-compose logs -f
        ;;
    
    docker-stop)
        docker-compose down
        print_step "Docker services stopped"
        ;;
    
    help|--help|-h)
        print_header "Content Automation System - Usage"
        echo "Commands:"
        echo "  ./run.sh setup          - Run setup wizard"
        echo "  ./run.sh run            - Start the web server (default)"
        echo "  ./run.sh cli [args]     - Run CLI commands"
        echo "  ./run.sh status         - Show system status"
        echo "  ./run.sh generate       - Generate content manually"
        echo "  ./run.sh post           - Post scheduled content"
        echo "  ./run.sh test           - Run tests"
        echo "  ./run.sh docker         - Start with Docker Compose"
        echo "  ./run.sh docker-logs    - View Docker logs"
        echo "  ./run.sh docker-stop    - Stop Docker services"
        echo "  ./run.sh help           - Show this help message"
        echo ""
        echo "CLI Commands:"
        echo "  python -m src.cli status        - Show system status"
        echo "  python -m src.cli generate      - Generate content"
        echo "  python -m src.cli post          - Post content"
        echo "  python -m src.cli topics        - List supported topics"
        echo "  python -m src.cli recent        - Show recent content"
        ;;
    
    *)
        print_error "Unknown command: $1"
        echo "Run './run.sh help' for usage information"
        exit 1
        ;;
esac