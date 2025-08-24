# Automated Version Management System

This document explains how to use the fully automated version management system for the Maintenance Dashboard project.

## 🚀 **Overview**

The automated version management system eliminates manual version updates by automatically:
- Capturing git information on every commit
- Updating version files automatically
- Providing deployment-ready artifacts
- Integrating with CI/CD pipelines

## 🔄 **Automation Levels**

### 1. **Local Automation** (Immediate)
- Scripts automatically update version files
- No manual intervention required
- Perfect for development workflows

### 2. **GitHub Actions** (Fully Automated)
- Runs on every push/PR
- Automatically commits version updates
- Creates deployment artifacts
- Zero manual work required

### 3. **Docker Build Automation**
- Version info embedded during build
- Environment variables automatically set
- Perfect for containerized deployments

## 📁 **Scripts Overview**

### **Core Scripts**
- **`version.py`** - Unified version management (Python)
- **`scripts/portainer_build.sh`** - Enhanced Portainer deployment
- **`scripts/build_with_version.sh`** - Automated Docker builds (Linux/Mac)
- **`scripts/build_with_version.ps1`** - Automated Docker builds (Windows)
- **`scripts/docker-build-hook.sh`** - Docker build automation

### **Legacy Scripts** (Updated to use unified system)
- **`scripts/set_version.ps1`** - PowerShell version setter
- **`scripts/set_version.bat`** - Batch version setter

## 🎯 **Usage Scenarios**

### **Scenario 1: Local Development**
```bash
# Just update version files
python version.py --update

# Build with automatic version management
./scripts/build_with_version.sh
```

### **Scenario 2: Portainer Deployment**
```bash
# Run enhanced build script
./scripts/portainer_build.sh

# Copy output to Portainer environment variables
# Deploy stack
```

### **Scenario 3: CI/CD Pipeline**
```bash
# GitHub Actions automatically runs
# Creates deployment artifacts
# Commits version updates
# Ready for deployment
```

## 🔧 **GitHub Actions Workflow**

### **Automatic Triggers**
- **Push** to `main`, `latest`, or `dev` branches
- **Pull Requests** to `main` or `latest` branches
- **Manual** triggering via workflow dispatch

### **What It Does**
1. Captures git version information
2. Updates `version.json` and `.env` files
3. Creates deployment artifacts
4. Commits and pushes changes
5. Provides deployment summary

### **Artifacts Generated**
- `version.json` - Version information
- `.env` - Environment variables
- `deployment-info.txt` - Human-readable deployment guide

## 🐳 **Docker Integration**

### **Build Arguments**
```bash
docker build \
  --build-arg GIT_COMMIT_COUNT=289 \
  --build-arg GIT_COMMIT_HASH=65462d3 \
  --build-arg GIT_BRANCH=latest \
  --build-arg GIT_COMMIT_DATE=2025-08-23 \
  -t maint-dashboard:v289.65462d3 \
  .
```

### **Environment Variables**
The Dockerfile automatically sets these environment variables:
```dockerfile
ENV GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT
ENV GIT_COMMIT_HASH=$GIT_COMMIT_HASH
ENV GIT_BRANCH=$GIT_BRANCH
ENV GIT_COMMIT_DATE=$GIT_COMMIT_DATE
```

## 📋 **Portainer Deployment**

### **Automatic Method (Recommended)**
1. Push code to GitHub
2. GitHub Actions automatically updates version files
3. Download deployment artifacts from Actions
4. Copy environment variables to Portainer
5. Deploy stack

### **Manual Method**
1. Run `./scripts/portainer_build.sh`
2. Copy environment variables to Portainer
3. Deploy stack

### **Environment Variables Required**
```
GIT_COMMIT_COUNT=289
GIT_COMMIT_HASH=65462d3
GIT_BRANCH=latest
GIT_COMMIT_DATE=2025-08-23
```

## 🌐 **Version Display**

### **API Endpoints**
- **JSON**: `/core/version/`
- **HTML**: `/core/version/html/`
- **Form**: `/core/version/form/`

### **Navigation**
- **Settings** → **Version Info**
- **Admin Dashboard** → **Version Information**

## 🔄 **Workflow Examples**

### **Daily Development**
```bash
# Make changes and commit
git add .
git commit -m "feat: add new feature"
git push

# GitHub Actions automatically:
# ✅ Updates version files
# ✅ Creates deployment artifacts
# ✅ Commits changes
# ✅ Ready for deployment
```

### **Production Deployment**
```bash
# 1. GitHub Actions has already prepared everything
# 2. Download artifacts from Actions
# 3. Copy environment variables to Portainer
# 4. Deploy stack
# 5. Version info automatically displays in app
```

### **Local Testing**
```bash
# Build with automatic version management
./scripts/build_with_version.sh

# Or PowerShell on Windows
.\scripts\build_with_version.ps1

# Version info automatically embedded in image
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **GitHub Actions Not Running**
- Check branch names in workflow file
- Ensure workflow file is in `.github/workflows/`
- Check Actions tab in GitHub repository

#### **Version Files Not Updating**
- Ensure Python is available
- Check git repository status
- Run `python version.py --update` manually

#### **Docker Build Fails**
- Verify build arguments are correct
- Check Docker daemon is running
- Ensure all required files exist

### **Debug Commands**
```bash
# Check current version
python version.py

# Force version update
python version.py --update

# Test Docker build
./scripts/build_with_version.sh

# Check git status
git status
git log --oneline -5
```

## 🎉 **Benefits**

### **For Developers**
- ✅ No manual version management
- ✅ Automatic file updates
- ✅ Consistent versioning
- ✅ Reduced human error

### **For Operations**
- ✅ Deployment-ready artifacts
- ✅ Clear environment variables
- ✅ Automated workflows
- ✅ Version tracking

### **For Users**
- ✅ Accurate version information
- ✅ Real-time updates
- ✅ Professional appearance
- ✅ Trust in system reliability

## 🔮 **Future Enhancements**

### **Planned Features**
- **Slack/Discord notifications** on version updates
- **Automatic Portainer deployment** via API
- **Version rollback** capabilities
- **Multi-environment** version management
- **Release notes** generation

### **Integration Opportunities**
- **Jira/Confluence** version tracking
- **Monitoring systems** version alerts
- **Backup systems** version verification
- **Security scanning** version correlation

## 📚 **Related Documentation**

- [Version Management](./VERSION_MANAGEMENT.md) - Basic version management
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Deployment instructions
- [Portainer Quickstart](./deployment/portainer-quickstart.md) - Portainer setup
- [Architecture](./architecture/architecture.md) - System architecture

---

**🎯 Goal**: Zero manual version management with full automation and reliability.
