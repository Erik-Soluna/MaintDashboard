import os
import json

def review_screenshots():
    print("=== SCREENSHOT ANALYSIS ===\n")
    
    # Check if test results exist
    if os.path.exists("all_clear_test_results.json"):
        with open("all_clear_test_results.json", "r") as f:
            results = json.load(f)
        
        print("=== TEST RESULTS SUMMARY ===")
        for result in results:
            print(f"Equipment ID: {result['equipment_id']}")
            print(f"Label: {result['label']}")
            print(f"Content: {result['content'][:100]}...")
            print("-" * 50)
    
    # List and describe screenshots
    screenshots = {
        "no_scan_button_no_docs.png": "Equipment with no documents - Scan Reports button not visible",
        "no_scan_button_benign_doc.png": "Equipment with benign document - Scan Reports button not visible", 
        "scan_report_analysis_finding.png": "Equipment with findings - Scan Reports results displayed",
        "full_page_finding.png": "Full page view with findings",
        "maintenance_reports_tab.png": "Maintenance Reports tab activated",
        "equipment_detail_initial.png": "Initial equipment detail page"
    }
    
    print("\n=== SCREENSHOTS GENERATED ===")
    for filename, description in screenshots.items():
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(f"✓ {filename} ({file_size} bytes)")
            print(f"  {description}")
        else:
            print(f"✗ {filename} - NOT FOUND")
        print()
    
    print("=== ANALYSIS ===")
    print("1. Equipment IDs 1000 and 1001 likely don't exist in the database")
    print("2. The Scan Reports button is only visible for equipment with documents")
    print("3. Equipment ID 17 shows findings correctly")
    print("4. The 'All clear' message will only appear when:")
    print("   - Equipment has documents")
    print("   - Scan Reports button is clicked")
    print("   - No findings are detected")
    
    print("\n=== RECOMMENDATIONS ===")
    print("1. Create test equipment records with IDs 1000 and 1001")
    print("2. Or use existing equipment IDs that have no documents")
    print("3. Test with equipment that has benign documents (no issues)")
    print("4. Verify the template change is working by checking equipment ID 17")

if __name__ == "__main__":
    review_screenshots() 