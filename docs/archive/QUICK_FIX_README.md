# 🚨 QUICK DATABASE FIX

Your Django app is showing: **`database "maintenance_dashboard" does not exist`**

## ⚡ IMMEDIATE FIX (30 seconds)

**Run this command right now:**

```bash
./fix-database-now.sh
```

**That's it!** Your app will be working in under 30 seconds.

---

## 🛡️ PERMANENT FIX (5 minutes)

To prevent this from happening again:

1. **Stop your Portainer stack**
2. **Update stack configuration** with the modified `portainer-stack.yml`
3. **Start the stack** - it will now auto-fix database issues

**Files ready for deployment:**
- ✅ `portainer-stack.yml` - Updated with database auto-fix
- ✅ `Dockerfile` - Includes database scripts
- ✅ `ensure-database.sh` - Automatic database creation
- ✅ `docker-entrypoint.sh` - Enhanced startup handling

---

## 📚 Full Documentation

See `PORTAINER_DATABASE_PERMANENT_FIX.md` for complete technical details and troubleshooting.

---

## 🎯 What This Fixes

**Problem:** PostgreSQL Docker containers only create databases on first run. With persistent volumes, restarts skip database creation.

**Solution:** Automatic database verification and creation on every container startup.

**Result:** Zero-downtime, self-healing database setup for Portainer deployments.