# Proxy Network Configuration Guide

This guide explains how to configure the maintenance dashboard to join an external proxy network (like Traefik) on startup.

## Overview

All Docker Compose files have been updated to support joining an external proxy network. The configuration includes:

- **Internal network**: `maintenance_network` - for communication between services
- **External network**: `proxy-network` - for reverse proxy access
- **Traefik labels** - for automatic service discovery and routing

## Prerequisites

1. **Create the proxy network** (if it doesn't exist):
   ```bash
   docker network create proxy-network
   ```

2. **Configure your environment** (copy `.env.example` to `.env`):
   ```bash
   cp .env.example .env
   ```

3. **Set your domain** in the `.env` file:
   ```bash
   DOMAIN=yourdomain.com
   ```

## Using with Traefik

### 1. Basic Traefik Setup

Create a `traefik.yml` configuration:

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v3.0
    command:
      - --api.dashboard=true
      - --api.insecure=true
      - --providers.docker=true
      - --providers.docker.network=proxy-network
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.letsencrypt.acme.tlschallenge=true
      - --certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com
      - --certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./letsencrypt:/letsencrypt
    networks:
      - proxy-network

networks:
  proxy-network:
    external: true
```

### 2. Start Traefik

```bash
docker-compose -f traefik.yml up -d
```

### 3. Start the Maintenance Dashboard

```bash
# Using the enhanced version with proxy support
docker-compose -f docker-compose.enhanced.yml up -d

# Or using Portainer stack
docker-compose -f portainer-stack.yml up -d
```

## Configuration Files

### Updated Files

All these files now include proxy network support:

- `docker-compose.yml` - Basic configuration
- `docker-compose.enhanced.yml` - Enhanced with monitoring
- `docker-compose.prod.yml` - Production configuration
- `portainer-stack.yml` - Portainer stack configuration

### Network Configuration

Each file includes:

```yaml
networks:
  maintenance_network:
    driver: bridge
  proxy-network:
    external: true  # Joins existing proxy network
```

### Service Labels

The web service includes Traefik labels:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.maintenance-web.rule=Host(`maintenance.${DOMAIN:-localhost}`)"
  - "traefik.http.routers.maintenance-web.entrypoints=websecure"
  - "traefik.http.routers.maintenance-web.tls.certresolver=letsencrypt"
  - "traefik.http.services.maintenance-web.loadbalancer.server.port=8000"
  - "traefik.docker.network=proxy-network"
```

## Environment Variables

Set these in your `.env` file:

```bash
# Domain for routing
DOMAIN=maintenance.yourdomain.com

# Proxy network name (if different)
PROXY_NETWORK=proxy-network

# Traefik configuration
TRAEFIK_ENABLE=true
TRAEFIK_ROUTER_RULE=Host(`maintenance.${DOMAIN}`)
TRAEFIK_ENTRYPOINTS=websecure
TRAEFIK_CERTRESOLVER=letsencrypt
TRAEFIK_SERVICE_PORT=8000
```

## Troubleshooting

### Common Issues

1. **Network not found**:
   ```bash
   docker network create proxy-network
   ```

2. **Domain not resolving**:
   - Check DNS records
   - Verify DOMAIN environment variable
   - Test with localhost first

3. **SSL Certificate issues**:
   - Verify email in Traefik configuration
   - Check Let's Encrypt rate limits
   - Ensure ports 80/443 are accessible

### Debugging Commands

```bash
# Check network status
docker network ls
docker network inspect proxy-network

# Check container logs
docker-compose logs traefik
docker-compose logs web

# Verify labels
docker inspect maintenance_web | grep -A 20 Labels
```

## Using with Other Reverse Proxies

### Nginx Proxy Manager

For Nginx Proxy Manager, remove Traefik labels and configure manually:

1. Remove or comment out Traefik labels
2. Set up proxy host in Nginx Proxy Manager UI
3. Point to `maintenance_web:8000`

### Caddy

For Caddy, update labels:

```yaml
labels:
  - "caddy=maintenance.yourdomain.com"
  - "caddy.reverse_proxy={{upstreams 8000}}"
```

## Security Considerations

1. **Remove direct port exposure** in production:
   ```yaml
   # Remove this in production
   ports:
     - "4405:8000"
   ```

2. **Use strong passwords** in `.env`
3. **Enable HTTPS** with proper certificates
4. **Restrict network access** as needed

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs`
2. Verify network connectivity
3. Test with simple HTTP first, then HTTPS
4. Check proxy configuration

The database initialization issue has also been fixed to handle existing tables properly.