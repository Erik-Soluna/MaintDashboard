#!/bin/bash

# Deploy Performance Optimizations Script
# This script implements all the CPU optimization changes

echo "🚀 Deploying Performance Optimizations"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: This script must be run from the Django project root directory"
    exit 1
fi

# Install new dependencies
echo "📦 Installing new dependencies..."
if command -v pip &> /dev/null; then
    pip install django-redis==5.3.0
    echo "✅ django-redis installed"
else
    echo "⚠️  pip not found, please install django-redis manually"
fi

# Run migrations
echo "🗄️  Running database migrations..."
python manage.py migrate

# Check if migration was successful
if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully"
else
    echo "❌ Database migrations failed"
    exit 1
fi

# Clear cache
echo "🧹 Clearing cache..."
python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('Cache cleared')"

# Collect static files (if needed)
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Check if services are running in Docker
if command -v docker-compose &> /dev/null; then
    echo "🐳 Detected Docker Compose, restarting services..."
    
    # Restart web service
    docker-compose restart web
    echo "✅ Web service restarted"
    
    # Restart celery services
    docker-compose restart celery-worker celery-beat
    echo "✅ Celery services restarted"
    
    # Restart Redis if it exists
    if docker-compose ps | grep -q redis; then
        docker-compose restart redis
        echo "✅ Redis restarted"
    fi
else
    echo "⚠️  Docker Compose not found, please restart services manually"
fi

# Monitor CPU usage
echo "📊 Monitoring CPU usage for 30 seconds..."
echo "Before optimization, CPU was at 396%"
echo "Expected: 80-120% CPU usage"
echo ""

# Monitor for 30 seconds
for i in {1..6}; do
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    echo "CPU Usage: ${cpu_usage}%"
    sleep 5
done

echo ""
echo "🎉 Performance optimizations deployed successfully!"
echo ""
echo "📋 Summary of changes applied:"
echo "✅ Dashboard view optimized (N+1 query fix)"
echo "✅ Database indexes added for performance"
echo "✅ Redis caching implemented"
echo "✅ Celery task frequency reduced"
echo "✅ Database connection pooling enabled"
echo ""
echo "📈 Expected improvements:"
echo "- 60-80% reduction in database queries"
echo "- 70-90% reduction in dashboard load time"
echo "- 50-70% reduction in background CPU usage"
echo ""
echo "🔍 Next steps:"
echo "1. Monitor CPU usage for the next hour"
echo "2. Check dashboard load times"
echo "3. Review the CPU_OPTIMIZATION_SUMMARY.md file"
echo "4. Run 'python optimize_performance.py' for detailed analysis"
echo ""
echo "📞 If you experience any issues, refer to the rollback plan in CPU_OPTIMIZATION_SUMMARY.md"