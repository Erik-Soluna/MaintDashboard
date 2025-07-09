#!/bin/bash

# Maintenance Dashboard Launch Script

set -e

echo "🔧 Starting Maintenance Dashboard..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before proceeding."
    echo "   Important: Change the default passwords!"
    read -p "Press Enter to continue after editing .env file..."
fi

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up -d --build

# Wait a moment for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
docker-compose ps

# Show logs for web service
echo ""
echo "📋 Web Service Logs:"
docker-compose logs --tail=20 web

echo ""
echo "✅ Maintenance Dashboard is starting up!"
echo ""
echo "🌐 Access the application at:"
echo "   - Web Application: http://localhost:8000"
echo "   - Django Admin: http://localhost:8000/admin/"
echo ""
echo "🔑 Default login credentials:"
echo "   - Username: admin (or your ADMIN_USERNAME from .env)"
echo "   - Password: admin123 (or your ADMIN_PASSWORD from .env)"
echo ""
echo "⚠️  IMPORTANT: Change the default password immediately!"
echo ""
echo "📚 Useful commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Stop services: docker-compose down"
echo "   - Restart: docker-compose restart"
echo "   - Shell access: docker-compose exec web bash"
echo ""