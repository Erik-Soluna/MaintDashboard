# Git Rebase and Docker Compose Test Runner - Usage Guide

## Overview
This Python script helps you rebase specific commits and run tests using Docker Compose. It automates the process of rebasing onto/from specific commits and running your test suite.

## Prerequisites
- Git repository with commits
- Docker and Docker Compose installed
- Python 3.6+
- A `docker-compose.yml` file in your project

## Basic Usage

### 1. Make the script executable
```bash
chmod +x rebase_and_test.py
```

### 2. Basic rebase onto a commit
```bash
python3 rebase_and_test.py <commit-hash>
```

### 3. View all options
```bash
python3 rebase_and_test.py --help
```

## Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `commit` | Commit hash to rebase onto/from | `abc123` |
| `--mode` | Rebase mode: `onto`, `from`, `interactive` | `--mode interactive` |
| `--branch` | Branch to work on | `--branch feature-branch` |
| `--compose-file` | Docker Compose file to use | `--compose-file docker-compose.test.yml` |
| `--test-service` | Specific service to run tests on | `--test-service web` |
| `--test-command` | Test command to run | `--test-command "pytest tests/"` |
| `--skip-build` | Skip building Docker services | `--skip-build` |
| `--cleanup` | Clean up after tests | `--cleanup` |

## Usage Examples

### Example 1: Basic Rebase
```bash
# Rebase current branch onto commit abc123
python3 rebase_and_test.py abc123
```

### Example 2: Rebase Specific Branch
```bash
# Rebase feature-branch onto main
python3 rebase_and_test.py main --branch feature-branch
```

### Example 3: Interactive Rebase
```bash
# Start interactive rebase from commit abc123
python3 rebase_and_test.py abc123 --mode interactive
```

### Example 4: Run Specific Test Service
```bash
# Rebase and run tests on web service
python3 rebase_and_test.py abc123 --test-service web --test-command "pytest tests/"
```

### Example 5: Custom Docker Compose File
```bash
# Use custom compose file
python3 rebase_and_test.py abc123 --compose-file docker-compose.test.yml
```

### Example 6: Skip Build and Clean Up
```bash
# Skip building and clean up after tests
python3 rebase_and_test.py abc123 --skip-build --cleanup
```

## Rebase Modes

### 1. `onto` (default)
Rebases current branch onto the specified commit:
```bash
python3 rebase_and_test.py abc123 --mode onto
```

### 2. `from`
Rebases from the parent of the specified commit:
```bash
python3 rebase_and_test.py abc123 --mode from
```

### 3. `interactive`
Starts interactive rebase from the specified commit:
```bash
python3 rebase_and_test.py abc123 --mode interactive
```

## Safety Features

### Automatic Backup
The script automatically creates a backup branch before rebasing:
```
backup-<original-branch>-<timestamp>
```

### Conflict Handling
If conflicts occur during rebase:
1. The script will show the current status
2. You can resolve conflicts manually
3. Use `git add` and `git rebase --continue`
4. Or restore from backup if needed

### Restore from Backup
If something goes wrong:
```bash
git checkout backup-<branch>-<timestamp>
```

## Docker Compose Integration

### Default Behavior
- Uses `docker-compose.yml` by default
- Builds all services unless `--skip-build` is specified
- Runs `docker-compose up --abort-on-container-exit`

### Custom Service Testing
```bash
# Run tests on specific service
python3 rebase_and_test.py abc123 --test-service api --test-command "npm test"
```

### Cleanup
```bash
# Clean up containers and volumes after tests
python3 rebase_and_test.py abc123 --cleanup
```

## Logging
The script logs all operations to:
- Console (INFO level)
- `rebase_test.log` file

## Error Handling
- Automatic backup creation before operations
- Graceful handling of rebase conflicts
- Docker Compose error reporting
- Rollback options if operations fail

## Tips for Success

1. **Always work on feature branches** - Never rebase shared branches
2. **Keep commits small** - Easier to rebase and test
3. **Test early and often** - Use this script in your development workflow
4. **Use meaningful commit messages** - Helps during interactive rebases
5. **Keep Docker services fast** - Faster feedback during development

## Troubleshooting

### Git Issues
- Check `git status` if rebase fails
- Use `git rebase --abort` to cancel
- Restore from backup branch if needed

### Docker Issues
- Ensure Docker is running
- Check `docker-compose.yml` syntax
- Verify service names are correct

### Common Problems
- **Permission denied**: Make script executable with `chmod +x`
- **Docker not found**: Install Docker and Docker Compose
- **Git conflicts**: Resolve manually and continue rebase
- **Test failures**: Check service logs and fix issues

## Integration with CI/CD
This script can be integrated into CI/CD pipelines for automated testing of rebased branches.