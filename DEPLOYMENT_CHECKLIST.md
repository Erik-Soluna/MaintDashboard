# Production Deployment Checklist

## Pre-Deployment
- [ ] Version information updated (v.)
- [ ] All tests passing
- [ ] Database migrations reviewed
- [ ] Security settings verified
- [ ] Environment variables configured

## Portainer Configuration
- [ ] Stack file uploaded (portainer-stack.yml)
- [ ] Environment variables set:
  - [ ] GIT_COMMIT_COUNT=
  - [ ] GIT_COMMIT_HASH=
  - [ ] GIT_BRANCH=
  - [ ] GIT_COMMIT_DATE=
  - [ ] Database credentials configured
  - [ ] Admin credentials configured
  - [ ] Domain settings configured

## Deployment
- [ ] Stack deployed successfully
- [ ] All containers showing as healthy
- [ ] No error messages in logs

## Post-Deployment Verification
- [ ] Health endpoint responding: /health/simple/
- [ ] Version endpoint working: /version/
- [ ] Admin panel accessible: /admin/
- [ ] Application fully functional
- [ ] SSL certificate working (if applicable)
- [ ] Database connectivity verified
- [ ] Redis connectivity verified
- [ ] Celery workers running
- [ ] Celery beat scheduler running

## Monitoring
- [ ] Container resource usage normal
- [ ] Application logs clean
- [ ] Error rates within acceptable limits
- [ ] Performance metrics satisfactory

---
**Deployment Date**: 09/02/2025 09:38:19
**Version**: v.
**Branch**: 
