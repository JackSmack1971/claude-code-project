#!/bin/bash
# Start script for AgentFactory

set -e

echo "🚀 Starting AgentFactory..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your API keys before continuing."
    exit 1
fi

# Start with Docker Compose
echo "🐳 Starting services with Docker Compose..."
docker-compose up -d

echo ""
echo "✅ AgentFactory is starting up!"
echo ""
echo "Services:"
echo "  🗄️  PostgreSQL: localhost:5432"
echo "  ⚡ Backend API: http://localhost:8000"
echo "  🎨 Frontend UI: http://localhost:8501"
echo ""
echo "📊 View logs: docker-compose logs -f"
echo "🛑 Stop services: docker-compose down"
echo ""
