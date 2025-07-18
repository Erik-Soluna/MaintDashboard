from playwright.sync_api import sync_playwright
import time
import json

def run_all_clear_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        results = []

        def login():
            page.goto("http://localhost:4405/auth/login/")
            page.wait_for_selector('input[name="username"]', timeout=10000)
            page.fill('input[name="username"]', "admin")
            page.fill('input[name="password"]', "temppass123")
            page.click('button[type="submit"]')
            page.wait_for_url("**/core/dashboard/**", timeout=10000)

        def scan_and_screenshot(equipment_id, label):
            page.goto(f"http://localhost:4405/equipment/{equipment_id}/")
            page.wait_for_load_state('networkidle', timeout=15000)
            # Go to Maintenance Reports tab
            maintenance_reports_tab = page.locator('[role="tab"][href="#reports"]')
            if maintenance_reports_tab.count() > 0:
                maintenance_reports_tab.click()
                page.wait_for_timeout(2000)
            # Click Scan Reports
            scan_button = page.locator('text=Scan Reports')
            if scan_button.count() > 0 and scan_button.is_visible():
                scan_button.click()
                page.wait_for_timeout(3000)
                report_section = page.locator('#reportAnalysis')
                if report_section.count() > 0:
                    content = report_section.inner_text()
                    report_section.screenshot(path=f"scan_report_analysis_{label}.png")
                    page.screenshot(path=f"full_page_{label}.png")
                    results.append({"equipment_id": equipment_id, "label": label, "content": content})
                else:
                    page.screenshot(path=f"no_report_section_{label}.png")
                    results.append({"equipment_id": equipment_id, "label": label, "content": "No reportAnalysis section found"})
            else:
                page.screenshot(path=f"no_scan_button_{label}.png")
                results.append({"equipment_id": equipment_id, "label": label, "content": "Scan Reports button not found or not visible"})

        try:
            login()
            # 1. Test with equipment that has no documents
            # Assume equipment with ID 1000 is new and has no documents (or create via admin if needed)
            scan_and_screenshot(1000, "no_docs")
            # 2. Test with equipment that has only a benign document (ID 1001)
            scan_and_screenshot(1001, "benign_doc")
            # 3. Test with equipment that has a document that triggers a finding (ID 17)
            scan_and_screenshot(17, "finding")
            # Save results log
            with open("all_clear_test_results.json", "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print("Test results saved to all_clear_test_results.json")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("All tests completed. Browser will close in 10 seconds...")
            time.sleep(10)
            browser.close()

if __name__ == "__main__":
    run_all_clear_tests() 