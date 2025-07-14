from playwright.sync_api import sync_playwright
import time

def test_scan_reports_simple():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # Login
            print("=== LOGIN ===")
            page.goto("http://localhost:4405/auth/login/")
            page.wait_for_selector('input[name="username"]', timeout=10000)
            page.fill('input[name="username"]', "admin")
            page.fill('input[name="password"]', "temppass123")
            page.click('button[type="submit"]')
            page.wait_for_url("**/core/dashboard/**", timeout=10000)
            print("✓ Login successful")
            
            # Navigate to equipment detail
            print("\n=== NAVIGATING TO EQUIPMENT ===")
            page.goto("http://localhost:4405/equipment/17/")
            page.wait_for_load_state('networkidle', timeout=15000)
            print("✓ Equipment page loaded")
            
            # Click on "Maintenance Reports" tab using specific selector
            print("\n=== ACTIVATING MAINTENANCE REPORTS TAB ===")
            maintenance_reports_tab = page.locator('[role="tab"][href="#reports"]')
            if maintenance_reports_tab.count() > 0:
                print("✓ Found Maintenance Reports tab, clicking...")
                maintenance_reports_tab.click()
                page.wait_for_timeout(2000)  # Wait for tab to activate
                print("✓ Maintenance Reports tab activated")
            else:
                print("✗ Maintenance Reports tab not found")
                return
            
            # Now click Scan Reports button
            print("\n=== CLICKING SCAN REPORTS ===")
            scan_button = page.locator('text=Scan Reports')
            if scan_button.count() > 0 and scan_button.is_visible():
                print("✓ Scan Reports button is visible, clicking...")
                scan_button.click()
                print("✓ Scan Reports button clicked")
                
                # Wait for AJAX request to complete
                page.wait_for_timeout(3000)
                
                # Check for results
                print("\n=== CHECKING RESULTS ===")
                report_section = page.locator('#reportAnalysis')
                if report_section.count() > 0:
                    print("✓ Report analysis section found!")
                    
                    # Get content
                    content = report_section.inner_text()
                    print(f"Content: {content}")
                    
                    # Take screenshot
                    report_section.screenshot(path="scan_report_analysis.png")
                    print("✓ Screenshot saved: scan_report_analysis.png")
                    
                    # Check if there are any findings
                    findings = page.locator('#reportAnalysis .finding, #reportAnalysis .result, #reportAnalysis .card')
                    print(f"Found {findings.count()} findings/result cards")
                    
                    if findings.count() > 0:
                        print("Findings:")
                        for i in range(findings.count()):
                            finding_text = findings.nth(i).inner_text()
                            print(f"  {i+1}. {finding_text}")
                    else:
                        print("No findings displayed - this might be normal if no documents are available")
                        
                else:
                    print("✗ Report analysis section not found")
            else:
                print("✗ Scan Reports button not found or not visible")
            
            # Take final screenshot
            page.screenshot(path="final_page.png")
            print("✓ Final page screenshot saved")
            
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path="error_debug.png")
            print("Error screenshot saved: error_debug.png")
            
        finally:
            print("\n=== TEST COMPLETED ===")
            print("Browser will close in 5 seconds...")
            time.sleep(5)
            browser.close()

if __name__ == "__main__":
    test_scan_reports_simple() 