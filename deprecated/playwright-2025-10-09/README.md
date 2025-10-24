# Playwright Scripts - Deprecated

**Date Deprecated**: October 9, 2025  
**Reason**: Playwright testing functionality is no longer needed

## What Was Here

This directory contains the deprecated Playwright testing infrastructure that was used for:
- Automated browser testing
- Natural language test execution
- RBAC suite testing
- Admin page exploration

## Why Deprecated

1. **Complexity**: Playwright added unnecessary complexity to the deployment
2. **Maintenance Overhead**: Test scripts required constant updates
3. **Boot Time**: Playwright installation slowed down container builds
4. **Better Alternatives**: Django's built-in testing and the improved debug page provide better development tools

## Removed Components

- `playwright/` - TypeScript test specifications
- `core/playwright_actions.py` - Playwright action handlers
- `core/playwright_orchestrator.py` - Test orchestration logic
- `core/playwright_parser.py` - Natural language parsing
- Playwright API endpoints (6 endpoints removed from core/urls.py)
- `playwright==1.48.0` package from requirements.txt

## Migration Path

If you need similar functionality:
- Use Django's built-in `TestCase` for unit tests
- Use `pytest-django` for advanced testing
- Use the improved Debug page for system diagnostics
- Use browser DevTools for frontend debugging

## Files Archived

All playwright-related files are preserved in this directory for reference:
- Original test specs (.ts files)
- Configuration files (package.json, playwright.config.ts)
- Python integration files
- Test results and reports

To restore (not recommended), copy files back to their original locations and uncomment the requirements.txt entry.

