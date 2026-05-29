# Cursor AI Git Workflow Guide

**Purpose:** Guide for AI assistants working on this codebase  
**Branch:** `latest`  
**Deployment:** Docker/Portainer (auto-deploy via webhook)

---

## 📋 **Standard Git Workflow**

### **Every Single Commit Follows This Pattern:**

```bash
# Step 1: Stage changes
git add <files>
# or
git add -A  # for multiple files

# Step 2: Commit with descriptive message
git commit -m "type: Brief description

Detailed explanation of changes
- Bullet points for key changes
- Impact and benefits
- Any breaking changes"

# Step 3: ALWAYS pull with rebase before pushing
git pull --rebase

# Step 4: Push to latest branch
git push
```

---

## ⚠️ **Critical Rules**

### **ALWAYS Do:**
1. ✅ Use `git pull --rebase` before EVERY push
2. ✅ Stage changes before committing (`git add`)
3. ✅ Write clear, descriptive commit messages
4. ✅ Push to `latest` branch
5. ✅ Handle rebase conflicts if they occur
6. ✅ Test changes after deployment

### **NEVER Do:**
1. ❌ `git push --force` (especially to main/latest)
2. ❌ `git reset --hard` without explicit user request
3. ❌ `--no-verify` or skip hooks
4. ❌ Commit without user explicitly asking
5. ❌ Push without `git pull --rebase` first
6. ❌ Update git config

---

## 🔄 **Handling Push Rejections**

### **When You See: "Updates were rejected (non-fast-forward)"**

This is NORMAL and happens frequently. The pattern is:

```bash
git push
# Error: rejected (non-fast-forward)

git pull --rebase
# Rebasing (1/1)...
# Successfully rebased and updated refs/heads/latest.

git push
# Success!
```

**What's Happening:**
- Someone else pushed while you were working
- Git requires you to rebase your changes on top of theirs
- `--rebase` keeps history clean (vs merge commits)
- Very common in active development

**Pattern You'll See:**
```bash
git commit -m "..."
git push
# ❌ rejected

git pull --rebase
# ✅ rebased

git push
# ✅ success
```

---

## 📝 **Commit Message Format**

### **Structure:**
```
type: Brief one-line summary (50 chars)

Detailed Description:
- What changed
- Why it changed
- Impact/benefits
- Any important notes

Technical Details:
- Specific changes
- Files affected
- Performance impact
```

### **Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `perf:` - Performance improvement
- `docs:` - Documentation
- `refactor:` - Code restructuring
- `test:` - Test additions/changes
- `chore:` - Maintenance tasks

### **Good Example:**
```bash
git commit -m "feat: Add quick schedule buttons for maintenance activities

Features:
- Add 'In 2 Hours', 'In 4 Hours', 'This Afternoon' buttons
- Auto-populate scheduled_start and scheduled_end fields
- 3-hour default duration
- Visual toast confirmation

UX Improvements:
- Makes scheduling for same-day much faster
- Eliminates manual date/time entry
- Streamlines urgent maintenance workflow

Files: templates/maintenance/add_activity.html"
```

### **Bad Example:**
```bash
git commit -m "updated file"
# ❌ Too vague, no details
```

---

## 🚀 **Deployment Process**

### **Code → Deployment Flow:**

```
1. Make changes locally
2. git add / commit / pull --rebase / push
3. GitHub webhook triggers (if configured)
4. Portainer pulls latest image
5. Container restarts (~2-3 minutes)
6. Changes are live
```

### **Important Notes:**

- **Container restart required** - Code changes don't take effect until restart
- **Webhook auto-deploy** - Usually deploys within 5-10 minutes
- **Manual restart** - User can restart container in Portainer for immediate deployment
- **No local Docker** - User only runs Docker via Portainer (not local Docker daemon)

### **Testing Deployment:**

**Wait for Container Restart:**
```bash
# Check if new code is deployed by testing an endpoint
curl https://dev.maintenance.errorlog.app/api/database-stats/

# If returns 404 → Old code still running
# If returns JSON → New code is live
```

**Common Pattern:**
```bash
# After pushing code
echo "Waiting for container restart..."
# Try API endpoint to test if deployed
curl -X POST https://dev.maintenance.errorlog.app/api/clear-maintenance/ -d "dry_run=true"
# If works → container restarted
# If 404 → wait 1-2 more minutes
```

---

## 🔧 **Common Scenarios**

### **Scenario 1: Simple Single-File Change**
```bash
git add core/views.py
git commit -m "fix: Handle null values in health check"
git pull --rebase
git push
```

### **Scenario 2: Multiple Files Changed**
```bash
git add -A
git commit -m "feat: Add document deletion for admins"
git pull --rebase
git push
```

### **Scenario 3: Push Rejected (Very Common)**
```bash
git push
# Error: rejected (non-fast-forward)

# Just rebase and try again:
git pull --rebase
git push
# Success!
```

### **Scenario 4: Multiple Rapid Commits**
```bash
# Commit 1
git add file1.py
git commit -m "fix: Part 1"
git push

# Commit 2
git add file2.py
git commit -m "fix: Part 2"
git pull --rebase  # Always pull first!
git push

# Commit 3
git add file3.py
git commit -m "fix: Part 3"
git pull --rebase  # Always pull first!
git push
```

---

## 🎯 **Efficient Workflow Tips**

### **Batch Related Changes:**
```bash
# Instead of 3 separate commits:
git add file1.py file2.py file3.py
git commit -m "feat: Complete feature X with all components"
git pull --rebase && git push
```

### **Use && for Chaining:**
```bash
# This is the pattern used throughout this chat:
git add -A && git commit -m "..." && git pull --rebase && git push

# If any step fails, the chain stops
# Very efficient for single operation
```

### **Check Status Before Operations:**
```bash
git status  # See what's changed
git add -A  # Stage everything
git status  # Verify staging
git commit -m "..."
git pull --rebase && git push
```

---

## 🐛 **Troubleshooting**

### **Issue: "Updates were rejected"**
**Solution:** `git pull --rebase` then `git push`

### **Issue: "Your branch is behind origin/latest by X commits"**
**Solution:** `git pull --rebase` or `git pull`

### **Issue: Rebase conflicts**
**Solution:** 
```bash
# View conflicts
git status

# Resolve conflicts in files
# Then:
git add <resolved-files>
git rebase --continue
git push
```

### **Issue: Changes not showing up on site**
**Solution:** Container needs restart. Wait 2-3 minutes or restart in Portainer.

### **Issue: "fatal: not a git repository"**
**Solution:** Already in repo. This shouldn't happen in this workspace.

---

## 🔍 **Verification Commands**

### **Check Status:**
```bash
git status                    # What's changed
git log --oneline -5         # Recent commits
git branch                   # Current branch (should be 'latest')
git remote -v                # Verify remote (GitHub)
```

### **Check Deployment:**
```bash
# Check if new code is deployed
curl https://dev.maintenance.errorlog.app/api/database-stats/

# Check version deployed
curl https://dev.maintenance.errorlog.app/version/
```

---

## 📦 **File Management**

### **Temporary Test Files:**
Always clean up temporary test files at the end:
```bash
# Created test file
test_something.py

# Clean up at end of session
git add -A  # This will show untracked files
# If you see test files, delete them:
rm test_something.py
```

### **Dev-Specific Files:**
Per user preference: Dev-specific files should not be pushed to main branch if avoidable.

Examples of dev-only files:
- `test_*.py` (unless they're actual test suite files)
- `debug_*.py` 
- `*.log` (already in .gitignore)
- IDE configs
- Local scripts for testing

---

## 🎯 **Quick Reference**

### **Standard Commit & Push:**
```bash
git add <files> && git commit -m "type: message" && git pull --rebase && git push
```

### **Check What Changed:**
```bash
git status
```

### **See Recent History:**
```bash
git log --oneline -10
```

### **Handle Rejection:**
```bash
git pull --rebase && git push
```

---

## 💡 **Memory Aid for AI Assistants**

**Every time you make code changes:**

1. Stage → `git add`
2. Commit → `git commit -m "clear message"`
3. **ALWAYS** pull → `git pull --rebase`
4. Push → `git push`
5. If rejected → Go back to step 3

**Think of it as:**
```
Make changes → add → commit → pull --rebase → push
                                    ↑
                            NEVER SKIP THIS
```

---

## 🚀 **Example from This Session**

### **Typical Successful Flow:**
```bash
$ git add equipment/views.py
$ git commit -m "fix: CSV export respects site selection from header"
$ git pull --rebase
Rebasing (1/1)...
Successfully rebased and updated refs/heads/latest.
$ git push
To https://github.com/Erik-Soluna/MaintDashboard.git
   6b2c808..e721d85  latest -> latest
```

### **Typical Rejection → Fix:**
```bash
$ git push
! [rejected] latest -> latest (non-fast-forward)
error: failed to push...

$ git pull --rebase
Rebasing (1/1)...
Successfully rebased and updated refs/heads/latest.

$ git push
To https://github.com/Erik-Soluna/MaintDashboard.git
   5c1e75b..d5c7f38  latest -> latest
# ✅ Success!
```

---

## 📚 **User Preferences (Important!)**

From user memories:

1. **Deployment:** Only runs Docker/Portainer version (not local Docker)
2. **Testing:** Run tests in Docker containers, not local PC
3. **Dev Files:** Don't push dev-specific files to main branch if avoidable
4. **Config Files:** Deployment configs only in root directory
5. **Branch:** Primary branch is `latest`

---

## ✅ **Success Indicators**

You've successfully completed the git workflow when you see:

```bash
To https://github.com/Erik-Soluna/MaintDashboard.git
   abc1234..def5678  latest -> latest
```

---

## 🎯 **Start of Chat Prompt**

When starting a new chat, user should say:

> "See CURSOR_GIT_WORKFLOW.md for git workflow. Always use: `git add → commit → pull --rebase → push`. Handle rejections by running `git pull --rebase` again."

This gives you the context without burning tokens on examples.

---

**This document should be referenced at the start of each Cursor chat session!** 📖

