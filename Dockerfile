FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        gettext \
        curl \
        procps \
        netcat-traditional \
        # Playwright dependencies
        libglib2.0-0 \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libdbus-1-3 \
        libxcb1 \
        libxkbcommon0 \
        libx11-6 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 \
        libatspi2.0-0 \
        libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create directories for static and media files
RUN mkdir -p /app/staticfiles /app/media

# Make all scripts executable in one layer
RUN chmod +x /app/scripts/deployment/docker-entrypoint.sh \
    && chmod +x /app/scripts/celery/start_celery_beat.sh \
    && chmod +x /app/scripts/celery/start_celery.sh \
    && chmod +x /app/scripts/celery/start_celery_beat_prod.sh \
    && chmod +x /app/scripts/celery/start_celery_prod.sh \
    && chmod +x /app/scripts/database/init_database.sh \
    && chmod +x /app/scripts/database/auto_init_database.py \
    && chmod +x /app/scripts/database/ensure-database.sh \
    && chmod +x /app/scripts/database/ensure_database.sh

# Collect static files (but allow override via environment variable)
RUN python manage.py collectstatic --noinput || echo "Static files collection failed, will retry at runtime"

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Enhanced health check that works with the new system
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || python manage.py check --database default || exit 1

# Set the entrypoint
ENTRYPOINT ["./scripts/deployment/docker-entrypoint.sh"]

# Default command
CMD ["web"]