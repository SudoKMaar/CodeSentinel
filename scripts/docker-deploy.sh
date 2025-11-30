#!/bin/bash
# Quick deployment script for Docker
# Usage: ./docker-deploy.sh [start|stop|restart|logs|status]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

# Function to check if .env file exists
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f "$ENV_EXAMPLE" ]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            print_info "Please edit .env file with your configuration before starting."
            print_info "At minimum, configure your LLM provider credentials."
            exit 0
        else
            print_error ".env.example file not found. Cannot create .env file."
            exit 1
        fi
    fi
}

# Function to start services
start_services() {
    print_info "Starting Code Review Agent services..."
    
    # Check if services are already running
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        print_warning "Services are already running."
        read -p "Do you want to restart them? (y/N): " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            exit 0
        fi
        stop_services
    fi
    
    # Build and start services
    docker-compose -f "$COMPOSE_FILE" up -d --build
    
    if [ $? -eq 0 ]; then
        print_success "Services started successfully!"
        echo ""
        print_info "API is available at: http://localhost:8000"
        print_info "API documentation: http://localhost:8000/docs"
        print_info "Health check: http://localhost:8000/health"
        echo ""
        print_info "View logs with: $0 logs"
        print_info "Check status with: $0 status"
    else
        print_error "Failed to start services"
        exit 1
    fi
}

# Function to stop services
stop_services() {
    print_info "Stopping Code Review Agent services..."
    docker-compose -f "$COMPOSE_FILE" down
    
    if [ $? -eq 0 ]; then
        print_success "Services stopped successfully!"
    else
        print_error "Failed to stop services"
        exit 1
    fi
}

# Function to restart services
restart_services() {
    print_info "Restarting Code Review Agent services..."
    stop_services
    sleep 2
    start_services
}

# Function to show logs
show_logs() {
    print_info "Showing logs (Ctrl+C to exit)..."
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# Function to show status
show_status() {
    print_info "Service Status:"
    echo ""
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    
    # Check health endpoint
    print_info "Checking health endpoint..."
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        HEALTH=$(curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || echo "Unable to parse health response")
        print_success "API is healthy"
        echo "$HEALTH"
    else
        print_warning "API is not responding"
    fi
}

# Function to clean up (remove volumes)
cleanup() {
    print_warning "This will remove all data including Memory Bank and sessions!"
    read -p "Are you sure? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        print_info "Stopping services and removing volumes..."
        docker-compose -f "$COMPOSE_FILE" down -v
        print_success "Cleanup complete!"
    else
        print_info "Cleanup cancelled."
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Start the services"
    echo "  stop      - Stop the services"
    echo "  restart   - Restart the services"
    echo "  logs      - Show service logs"
    echo "  status    - Show service status"
    echo "  cleanup   - Stop services and remove all data"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start          # Start services"
    echo "  $0 logs           # View logs"
    echo "  $0 status         # Check status"
}

# Main script
main() {
    # Check prerequisites
    check_docker
    
    # Parse command
    COMMAND=${1:-help}
    
    case $COMMAND in
        start)
            check_env_file
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            check_env_file
            restart_services
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        cleanup)
            cleanup
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
