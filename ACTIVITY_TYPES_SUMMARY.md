# Activity Types Organization Summary

## 📊 **Current Problems You're Experiencing**

Based on your feedback: "a bunch of them and several are repeats/confusing as it's under the same thing"

### Likely Issues:
1. Types scattered across too many categories
2. Similar types with different names (Oil Testing vs Oil Analysis)
3. Unclear which type to pick for specific tasks
4. Duplicates from multiple populate scripts

---

## ✅ **Clean Solution - 6 Categories, 20 Types**

### **Quick Reference Guide**

| I Need To... | Category | Activity Type |
|--------------|----------|---------------|
| Do a quick visual check | **Inspection** | Routine Inspection |
| Check safety compliance | **Inspection** | Safety Inspection |
| Do thermal imaging | **Inspection** | Thermal Inspection |
| Test transformer oil for gases | **Testing** | DGA Analysis |
| Test oil quality | **Testing** | Oil Analysis |
| Test insulation | **Testing** | Insulation Testing |
| Load test equipment | **Testing** | Load Testing |
| Test all functions work | **Testing** | Functional Testing |
| Add grease/oil | **Preventive Maintenance** | Lubrication |
| Replace filters | **Preventive Maintenance** | Filter Replacement |
| Clean equipment | **Preventive Maintenance** | Cleaning |
| Torque check bolts | **Preventive Maintenance** | Tightening & Adjustment |
| Check belts/couplings | **Preventive Maintenance** | Belt & Coupling Inspection |
| Something broke (urgent!) | **Corrective Maintenance** | Emergency Repair |
| Replace a broken part | **Corrective Maintenance** | Component Replacement |
| Fix an identified problem | **Corrective Maintenance** | Fault Correction |
| Restore after major failure | **Corrective Maintenance** | System Restoration |
| Calibrate instruments | **Calibration** | Instrument Calibration |
| Calibrate relays | **Calibration** | Protection Relay Calibration |
| Regulatory inspection | **Compliance** | Regulatory Inspection |
| Internal audit | **Compliance** | Compliance Audit |
| Update documentation | **Compliance** | Documentation Review |

---

## 🎯 **How to Apply the Clean Structure**

### Step 1: Review the Cleanup Document
See `ACTIVITY_TYPES_CLEANUP.md` for full details

### Step 2: Run in Portainer Console
Once code deploys (already pushed), run in your container:

```bash
# Preview what will change
python manage.py reorganize_activity_types --dry-run

# Apply the clean structure
python manage.py reorganize_activity_types --force
```

### Step 3: Verify
- Go to Maintenance → Activity Types
- Should see 20 well-organized types in 6 categories
- No duplicates or confusion

---

## 📋 **What Gets Removed**

### Duplicates & Confusing Types:
- ~~Visual Inspection~~ → **Routine Inspection** (clearer name)
- ~~Thermal Imaging~~ → **Thermal Inspection** (consistent naming)
- ~~Oil Testing~~ → **Oil Analysis** (matches DGA terminology)
- ~~Electrical Testing~~ → Covered by **Functional Testing**
- ~~Performance Testing~~ → Covered by **Load Testing** or **Functional Testing**
- ~~Reliability Testing~~ → Covered by **Load Testing**
- ~~Environmental Inspection~~ → Covered by **Safety Inspection**
- ~~System Repair~~ → **System Restoration** (clearer purpose)
- ~~Area Cleaning~~ → Merged into **Cleaning**
- ~~Equipment Cleaning~~ → Just **Cleaning**

---

## 💡 **Category Logic**

### Clear Decision Tree:

```
Is it scheduled or as-needed?
├─ Scheduled regularly
│  ├─ Just looking? → INSPECTION
│  ├─ Testing/analyzing? → TESTING
│  ├─ Performing maintenance? → PREVENTIVE MAINTENANCE
│  ├─ Calibrating? → CALIBRATION
│  └─ Compliance work? → COMPLIANCE
└─ As-needed (reactive)
   └─ CORRECTIVE MAINTENANCE
```

### Category Purposes:

1. **INSPECTION** = Look at it (visual, thermal)
2. **TESTING** = Analyze it (lab tests, diagnostics)
3. **PREVENTIVE MAINTENANCE** = Maintain it (lube, clean, adjust)
4. **CORRECTIVE MAINTENANCE** = Fix it (repairs, replacements)
5. **CALIBRATION** = Calibrate it (accuracy, settings)
6. **COMPLIANCE** = Document it (audits, regulations)

---

## ⏱️ **Frequency Guidelines**

| Frequency | Types |
|-----------|-------|
| **Weekly (7 days)** | Routine Inspection |
| **Monthly (30 days)** | Safety Inspection, Lubrication, Cleaning |
| **Quarterly (90 days)** | Thermal Inspection, DGA Analysis, Tightening, Belts |
| **Semi-Annual (180 days)** | Oil Analysis, Filter Replacement, Functional Testing |
| **Annual (365 days)** | Insulation Testing, Load Testing, Calibrations, Compliance |
| **As-Needed (0 days)** | All Corrective Maintenance |

---

## 🎯 **Example: DGA for Transformer**

**Before:** Confusing to find
- Could be under "Testing"?
- Or "Preventive Maintenance"?
- Or is it "Oil Testing" or "DGA Analysis"?

**After:** Crystal clear
- Category: **Testing** (it's diagnostic analysis)
- Type: **DGA Analysis**
- Description: "Dissolved Gas Analysis for transformers - tests oil for fault gases"
- Frequency: 90 days (Quarterly)
- Duration: 3 hours

---

**Once the container restarts with the new code, you can run the reorganization command!** 🚀

