#!/bin/bash
# Local Development Startup Script
# Usage: ./scripts/dev.sh

set -e

echo "================================"
echo "Hackathon Platform - Dev Mode"
echo "================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker first."
    exit 1
fi

echo "Docker is running ✓"

# Check for .env file
if [ ! -f .env ]; then
    echo "WARNING: No .env file found. Creating minimal one..."
    cat > .env << 'EOF'
# Required for Clerk auth
HACKVERIFY_CLERK_SECRET_KEY=your_clerk_secret_key_here
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key_here

# Optional - for AI features
HACKVERIFY_LLM_API_KEY=your_poolside_or_openai_key_here
EOF
    echo "Created .env file. Please edit it with your actual API keys."
fi

echo ""
echo "Starting services..."
echo ""

# Start all services
docker-compose -f docker-compose.dev.yml up -d --build

echo ""
echo "================================"
echo "Services started!"
echo "================================"
echo ""
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Hot reload enabled for both frontend and backend"
echo ""
echo "Commands:"
echo "  docker-compose -f docker-compose.dev.yml logs -f"
echo "  docker-compose -f docker-compose.dev.yml down"
echo ""
