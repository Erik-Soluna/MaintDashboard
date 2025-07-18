# Webhook Integration with Portainer

This feature allows you to automatically update your Docker stack via webhooks triggered from Portainer. This enables seamless deployment updates without manual intervention.

## Overview

The webhook integration provides:
- **Automated Stack Updates**: Trigger stack updates via HTTP webhooks
- **Security**: HMAC signature verification for webhook authenticity
- **Testing Tools**: Built-in connection testing and configuration validation
- **Management Interface**: Web-based settings page for configuration

## Setup Instructions

### 1. Environment Configuration

Add these environment variables to your Django settings:

```bash
# Portainer API Configuration
PORTAINER_URL=http://your-portainer:9000
PORTAINER_USER=your-username
PORTAINER_PASSWORD=your-password
PORTAINER_STACK_NAME=your-stack-name

# Webhook Security
PORTAINER_WEBHOOK_SECRET=your-secure-secret
```

### 2. Generate Webhook Secret

Use the management command to generate a secure webhook secret:

```bash
python manage.py setup_webhook --generate-secret
```

This will output a secure 32-character secret. Add it to your environment variables as `PORTAINER_WEBHOOK_SECRET`.

### 3. Configure Portainer Webhook

1. Log into your Portainer instance
2. Navigate to **Settings > Webhooks**
3. Click **Add Webhook**
4. Configure with these settings:

```
Webhook URL: http://your-domain/webhook/update/
HTTP Method: POST
Content Type: application/json
Secret: [Your generated secret]
Events: Stack Update, Image Update
```

### 4. Test Configuration

Test your setup using the management command:

```bash
python manage.py setup_webhook --test-connection
```

Or use the web interface at `/settings/webhooks/` to test the connection.

## Web Interface

### Accessing Webhook Settings

1. Navigate to **Settings** in the main menu
2. Click **Webhook Settings** in the quick actions
3. Or go directly to `/settings/webhooks/`

### Features Available

- **Webhook URL Display**: Shows the webhook endpoint URL with copy functionality
- **Configuration Status**: Displays current Portainer configuration
- **Connection Testing**: Test Portainer API connectivity
- **Manual Stack Updates**: Trigger stack updates manually
- **Setup Instructions**: Step-by-step configuration guide

## Security Features

### HMAC Signature Verification

All webhook requests are verified using HMAC-SHA256 signatures:

1. **Request Header**: `X-Portainer-Signature` contains the signature
2. **Secret**: Configured via `PORTAINER_WEBHOOK_SECRET` environment variable
3. **Verification**: Django validates the signature before processing

### Example Signature Generation

```python
import hmac
import hashlib

def generate_signature(payload, secret):
    return hmac.new(
        secret.encode(), 
        payload.encode(), 
        hashlib.sha256
    ).hexdigest()
```

## API Endpoints

### Webhook Handler

**URL**: `/webhook/update/`
**Method**: POST
**Headers**: 
- `Content-Type: application/json`
- `X-Portainer-Signature: [signature]`

**Response**:
```json
{
    "success": true,
    "message": "Stack update triggered",
    "update_result": "Stack updated successfully"
}
```

### Webhook Settings

**URL**: `/settings/webhooks/`
**Method**: GET/POST
**Access**: Staff/Superuser only

## Management Commands

### setup_webhook

Comprehensive webhook management command:

```bash
# Generate a new webhook secret
python manage.py setup_webhook --generate-secret

# Test Portainer connection
python manage.py setup_webhook --test-connection

# Show current configuration
python manage.py setup_webhook --show-config
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify `PORTAINER_USER` and `PORTAINER_PASSWORD`
   - Check Portainer API accessibility

2. **Stack Not Found**
   - Verify `PORTAINER_STACK_NAME` matches exactly
   - Use `--test-connection` to list available stacks

3. **Webhook Signature Invalid**
   - Ensure `PORTAINER_WEBHOOK_SECRET` is set correctly
   - Verify Portainer is using the same secret

4. **Network Errors**
   - Check firewall settings
   - Verify Portainer URL is accessible from Django

### Debug Information

Enable debug logging to troubleshoot webhook issues:

```python
LOGGING = {
    'loggers': {
        'core.views': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

## Use Cases

### Automated Deployment

1. **Git Push Trigger**: Configure Git webhooks to trigger Portainer updates
2. **CI/CD Pipeline**: Integrate with Jenkins, GitHub Actions, or GitLab CI
3. **Scheduled Updates**: Use cron jobs to trigger regular updates

### Example GitLab CI Integration

```yaml
deploy:
  stage: deploy
  script:
    - curl -X POST $WEBHOOK_URL \
      -H "Content-Type: application/json" \
      -H "X-Portainer-Signature: $WEBHOOK_SECRET" \
      -d '{"event": "deployment", "branch": "$CI_COMMIT_REF_NAME"}'
```

## Best Practices

1. **Secure Secrets**: Use strong, unique secrets for webhook authentication
2. **Network Security**: Ensure webhook endpoints are only accessible from trusted sources
3. **Monitoring**: Monitor webhook success/failure rates
4. **Backup**: Keep configuration backups for disaster recovery
5. **Testing**: Test webhook functionality in staging environments first

## Advanced Configuration

### Custom Webhook Payloads

You can extend the webhook handler to process custom payloads:

```python
def webhook_handler(request):
    data = json.loads(request.body)
    
    # Handle different event types
    event_type = data.get('event')
    if event_type == 'stack_update':
        # Trigger stack update
        pass
    elif event_type == 'image_update':
        # Handle image updates
        pass
```

### Multiple Stack Support

Configure multiple stacks by extending the environment variables:

```bash
PORTAINER_STACK_NAME_APP=app-stack
PORTAINER_STACK_NAME_DB=db-stack
```

## Support

For issues or questions about webhook integration:

1. Check the troubleshooting section above
2. Review Django logs for error messages
3. Test with the management commands
4. Verify Portainer API documentation for compatibility 