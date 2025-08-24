FROM python:3.11-slim

# Build arguments for version information
ARG GIT_COMMIT_COUNT=0
ARG GIT_COMMIT_HASH=unknown
ARG GIT_BRANCH=unknown
ARG GIT_COMMIT_DATE=unknown

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT
ENV GIT_COMMIT_HASH=$GIT_COMMIT_HASH
ENV GIT_BRANCH=$GIT_BRANCH
ENV GIT_COMMIT_DATE=$GIT_COMMIT_DATE

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
        # Docker CLI
        ca-certificates \
        gnupg \
        lsb-release \
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

# Install Docker CLI
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
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

# Create a non-root user and add to docker group
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app \
    && groupadd -g 999 docker || true \
    && usermod -aG docker appuser

# For Docker access, we'll run as root but switch to appuser for the application
# USER appuser

# Expose port
EXPOSE 8000

# Enhanced health check that works with the new system
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/simple/ || python manage.py check --database default || exit 1

# Set the entrypoint
ENTRYPOINT ["./scripts/deployment/docker-entrypoint.sh"]

# Default command
CMD ["web"]