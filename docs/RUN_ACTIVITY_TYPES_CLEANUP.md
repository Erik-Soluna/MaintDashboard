# Run Activity Types Cleanup

## ⏳ **Container Status**
The code is pushed but container needs to restart to pick up changes.

---

## 🚀 **When Container is Ready, Run:**

### Step 1: Dry Run (Preview Current State)
```bash
curl -X POST https://dev.maintenance.errorlog.app/api/reorganize-activity-types/ \
  -d "dry_run=true" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

**This will show you:**
- Current categories and activity types
- Duplicate detection
- What will be changed
- The proposed clean structure

---

### Step 2: Apply the Cleanup
```bash
curl -X POST https://dev.maintenance.errorlog.app/api/reorganize-activity-types/ \
  -d "dry_run=false&force=true" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

**This will:**
- Delete all existing activity types and categories
- Create 6 clean categories
- Create 20 well-organized activity types
- Return command output showing what was created

---

## 📋 **Alternative: Run in Portainer Console**

If API doesn't work, you can run directly in the container:

```bash
# Preview
python manage.py reorganize_activity_types --dry-run

# Apply
python manage.py reorganize_activity_types --force
```

---

## ✅ **Expected Result**

**Before:**
- Confusing mix of categories
- Duplicate types ("Oil Testing" vs "Oil Analysis")
- Unclear which type to use

**After:**
```
6 Categories:
1. Inspection (3 types) - Visual checks
2. Testing (5 types) - Diagnostic analysis (DGA here!)
3. Preventive Maintenance (5 types) - Scheduled PM
4. Corrective Maintenance (4 types) - Repairs
5. Calibration (2 types) - Accuracy
6. Compliance (3 types) - Regulatory

Total: 20 clear, non-duplicate types
```

---

## 🧪 **How to Know It's Ready**

The container is ready when this returns data (not 404):
```bash
curl https://dev.maintenance.errorlog.app/api/reorganize-activity-types/ \
  -X POST -d "dry_run=true"
```

If you get:
- ✅ JSON response → Container is ready!
- ❌ 404 error → Wait 1-2 more minutes for restart

---

## ⚠️ **Safety Notes**

- `force=true` will delete existing activity types
- Dry run is safe (no changes made)
- Completed maintenance activities won't be affected
- Equipment and users are preserved

---

**Ready to try once container restarts!** 🎯

