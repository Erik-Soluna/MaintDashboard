# Security Configuration Guide

This guide provides comprehensive security configuration for the Maintenance Dashboard deployed behind a reverse proxy at `maintenance.errorlog.app`.

## SSL/TLS Configuration

### Automatic SSL with Let's Encrypt

The Portainer stack is configured to automatically obtain and renew SSL certificates using Let's Encrypt through Traefik.

#### Prerequisites

1. **Traefik Configuration**: Ensure Traefik is configured with Let's Encrypt
2. **Domain Verification**: Your domain `maintenance.errorlog.app` must be publicly accessible
3. **DNS Configuration**: Point your domain to your server's IP address

#### Traefik Labels Configuration

The stack includes comprehensive Traefik labels for SSL/TLS:

```yaml
labels:
  # SSL/TLS Configuration
  - "traefik.enable=true"
  - "traefik.http.routers.maintenance-web.rule=Host(`maintenance.errorlog.app`)"
  - "traefik.http.routers.maintenance-web.entrypoints=websecure"
  - "traefik.http.routers.maintenance-web.tls.certresolver=letsencrypt"
  - "traefik.http.routers.maintenance-web.tls.domains[0].main=maintenance.errorlog.app"
  - "traefik.http.routers.maintenance-web.tls.domains[0].sans=www.maintenance.errorlog.app"
```

### Manual SSL Configuration (Alternative)

If you're not using Traefik, configure your reverse proxy (Nginx, Apache, etc.) with SSL:

#### Nginx Example

```nginx
server {
    listen 80;
    server_name maintenance.errorlog.app www.maintenance.errorlog.app;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name maintenance.errorlog.app www.maintenance.errorlog.app;
    
    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';" always;
    
    # Proxy Configuration
    location / {
        proxy_pass http://localhost:4405;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Server $host;
    }
}
```

## Security Headers

### Traefik Security Headers

The stack includes comprehensive security headers via Traefik middleware:

```yaml
# Security Headers
- "traefik.http.middlewares.maintenance-security.headers.sslredirect=true"
- "traefik.http.middlewares.maintenance-security.headers.forcestsheader=X-Forwarded-Proto:https"
- "traefik.http.middlewares.maintenance-security.headers.customrequestheaders.X-Forwarded-Proto=https"
- "traefik.http.middlewares.maintenance-security.headers.customrequestheaders.X-Forwarded-Host=maintenance.errorlog.app"
- "traefik.http.middlewares.maintenance-security.headers.customrequestheaders.X-Forwarded-Server=maintenance.errorlog.app"
- "traefik.http.middlewares.maintenance-security.headers.customresponseheaders.X-Content-Type-Options=nosniff"
- "traefik.http.middlewares.maintenance-security.headers.customresponseheaders.X-Frame-Options=DENY"
- "traefik.http.middlewares.maintenance-security.headers.customresponseheaders.X-XSS-Protection=1; mode=block"
- "traefik.http.middlewares.maintenance-security.headers.customresponseheaders.Referrer-Policy=strict-origin-when-cross-origin"
- "traefik.http.middlewares.maintenance-security.headers.customresponseheaders.Permissions-Policy=geolocation=(), microphone=(), camera=()"
- "traefik.http.middlewares.maintenance-security.headers.customresponseheaders.Strict-Transport-Security=max-age=31536000; includeSubDomains; preload"
- "traefik.http.middlewares.maintenance-security.headers.customresponseheaders.Content-Security-Policy=default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';"
```

### Security Header Explanations

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` | Forces HTTPS connections |
| `X-Frame-Options` | `DENY` | Prevents clickjacking attacks |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME type sniffing |
| `X-XSS-Protection` | `1; mode=block` | Enables XSS protection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer information |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Restricts browser features |
| `Content-Security-Policy` | Complex policy | Prevents XSS and injection attacks |

## Django Security Settings

### Environment Variables

Configure these security-related environment variables in your `stack.env`:

```bash
# Security Settings (SSL/TLS)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
CSRF_TRUSTED_ORIGINS=https://maintenance.errorlog.app,https://www.maintenance.errorlog.app
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https

# Reverse Proxy Settings
USE_X_FORWARDED_HOST=True
USE_X_FORWARDED_PORT=True
```

### Django Security Features

The application includes these security features:

1. **HTTPS Redirect**: Automatically redirects HTTP to HTTPS
2. **Secure Cookies**: Session and CSRF cookies are secure-only
3. **HSTS**: HTTP Strict Transport Security headers
4. **XSS Protection**: Browser XSS protection enabled
5. **Content Type Sniffing**: Disabled for security
6. **Frame Options**: Prevents clickjacking
7. **CSRF Protection**: Cross-Site Request Forgery protection
8. **SQL Injection Protection**: Django ORM protection
9. **Password Validation**: Strong password requirements

## Network Security

### Docker Network Configuration

```yaml
networks:
  maintenance_network:
    driver: bridge
    # Internal network for service communication
  proxy-network:
    external: true
    # External network for Traefik integration
```

### Port Configuration

- **Web Service**: Internal port 8000, external port 4405
- **Database**: Internal port 5432, external port configurable
- **Redis**: Internal port 6379, external port configurable

### Firewall Recommendations

Configure your server firewall to allow only necessary ports:

```bash
# Allow SSH
ufw allow 22

# Allow HTTP/HTTPS (if not using reverse proxy)
ufw allow 80
ufw allow 443

# Allow Portainer (if needed)
ufw allow 9000

# Block all other incoming traffic
ufw default deny incoming
```

## Authentication Security

### Admin User Setup

1. **Strong Password**: Use a complex password for the admin user
2. **Unique Email**: Use a dedicated email for admin notifications
3. **Regular Rotation**: Change admin password regularly

### Session Security

- **Session Timeout**: 24 hours (configurable)
- **Secure Cookies**: Session cookies are HTTPS-only
- **Redis Storage**: Sessions stored in Redis for scalability

### Password Policy

Django enforces strong password requirements:
- Minimum length validation
- Common password prevention
- Numeric password prevention
- User attribute similarity validation

## Database Security

### PostgreSQL Security

1. **Strong Passwords**: Use complex database passwords
2. **Limited Access**: Database only accessible from Docker network
3. **Connection Pooling**: Optimized connection management
4. **Regular Backups**: Automated backup procedures

### Redis Security

1. **Network Isolation**: Redis only accessible from Docker network
2. **No Authentication**: Redis runs without authentication (internal network)
3. **Memory Limits**: Configured memory limits prevent DoS

## Monitoring and Logging

### Security Logging

The application logs security-related events:
- Failed login attempts
- CSRF violations
- Permission denied errors
- System health issues

### Health Checks

All services include health checks:
- Database connectivity
- Redis connectivity
- Web application health
- Celery worker status

## Backup and Recovery

### Database Backups

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
docker exec maintenance_db_prod pg_dump -U maintenance_user maintenance_dashboard_prod > $BACKUP_DIR/backup_$DATE.sql
```

### Volume Backups

```bash
# Backup Docker volumes
docker run --rm -v maintenance-dashboard_postgres_data:/data -v /backups:/backup alpine tar czf /backup/postgres_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

## Compliance and Standards

### Security Standards

This configuration follows:
- **OWASP Top 10**: Addresses common web vulnerabilities
- **NIST Cybersecurity Framework**: Risk management approach
- **GDPR**: Data protection compliance
- **SOC 2**: Security controls framework

### Regular Security Updates

1. **Docker Images**: Keep base images updated
2. **Dependencies**: Regular security updates
3. **SSL Certificates**: Automatic renewal with Let's Encrypt
4. **Security Patches**: Apply OS and application patches

## Troubleshooting

### SSL Issues

1. **Certificate Not Found**: Check Let's Encrypt configuration
2. **Mixed Content**: Ensure all resources use HTTPS
3. **HSTS Errors**: Clear browser cache and cookies

### Security Header Issues

1. **CSP Violations**: Check browser console for violations
2. **Frame Loading**: Ensure external frames are allowed if needed
3. **XSS Protection**: Verify browser compatibility

### Reverse Proxy Issues

1. **Headers Not Forwarded**: Check proxy configuration
2. **SSL Termination**: Verify SSL certificate chain
3. **Health Check Failures**: Check internal service health

## Security Checklist

- [ ] SSL/TLS certificates configured and valid
- [ ] Security headers properly set
- [ ] Django security settings enabled
- [ ] Strong passwords configured
- [ ] Firewall rules applied
- [ ] Regular backups scheduled
- [ ] Monitoring and logging enabled
- [ ] Security updates automated
- [ ] Access controls implemented
- [ ] Network isolation configured

## Support

For security-related issues:
1. Check application logs for errors
2. Verify SSL certificate status
3. Test security headers with online tools
4. Review Django security documentation
5. Contact system administrator for network issues 