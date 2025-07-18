#!/bin/bash

# Environment Setup Script for Maintenance Dashboard
# This script helps you set up your .env file from templates

set -e

echo "🔧 Maintenance Dashboard Environment Setup"
echo "=========================================="

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled. Your existing .env file was preserved."
        exit 1
    fi
fi

# Show environment options
echo ""
echo "Choose your environment:"
echo "1) Development (DEBUG=True, safe defaults)"
echo "2) Production (DEBUG=False, secure settings)"
echo "3) Custom (manual setup)"
echo ""

read -p "Enter your choice (1-3): " -n 1 -r
echo

case $REPLY in
    1)
        echo "📝 Setting up development environment..."
        if [ -f "env.development" ]; then
            cp env.development .env
            echo "✅ Development environment configured!"
            echo "   - DEBUG=True"
            echo "   - Database: maintenance_dashboard_dev"
            echo "   - Admin password: temppass123"
        else
            echo "❌ env.development template not found!"
            exit 1
        fi
        ;;
    2)
        echo "🔒 Setting up production environment..."
        if [ -f "env.production" ]; then
            cp env.production .env
            echo "✅ Production environment configured!"
            echo "   - DEBUG=False"
            echo "   - Database: maintenance_dashboard_prod"
            echo "   - Secure passwords generated"
            echo ""
            echo "⚠️  IMPORTANT: Please review and update the following in .env:"
            echo "   - SECRET_KEY (generate a new one)"
            echo "   - DB_PASSWORD (use a strong password)"
            echo "   - ADMIN_PASSWORD (use a strong password)"
            echo "   - ALLOWED_HOSTS (update with your domain)"
        else
            echo "❌ env.production template not found!"
            exit 1
        fi
        ;;
    3)
        echo "📝 Manual setup selected."
        echo "Please create a .env file manually or copy from one of the templates:"
        echo "   - env.development (for development)"
        echo "   - env.production (for production)"
        echo ""
        echo "Then run: cp env.development .env (or env.production)"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "🎉 Environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Review your .env file: cat .env"
echo "2. Start the application: docker-compose up -d"
echo "3. Check logs: docker-compose logs -f"
echo ""
echo "For production deployments:"
echo "1. Update passwords in .env"
echo "2. Use portainer-stack.yml in Portainer"
echo "3. Configure your domain and SSL" 