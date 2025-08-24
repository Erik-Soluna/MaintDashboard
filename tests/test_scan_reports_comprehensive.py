from playwright.sync_api import sync_playwright
import time
import json

def test_scan_reports_comprehensive():
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
            
            # Analyze page structure
            print("\n=== PAGE ANALYSIS ===")
            
            # Check for tabs or sections
            tabs = page.locator('[role="tab"], .nav-tabs a, .tab-content, .accordion')
            print(f"Found {tabs.count()} potential tab/accordion elements")
            
            # Check for any elements containing "scan" or "report"
            scan_elements = page.locator('*:has-text("scan"), *:has-text("report")')
            print(f"Found {scan_elements.count()} elements containing 'scan' or 'report'")
            
            # List all buttons and their states
            print("\n=== BUTTON ANALYSIS ===")
            buttons = page.locator('button, a.btn, input[type="button"], input[type="submit"]')
            print(f"Total buttons found: {buttons.count()}")
            
            button_info = []
            for i in range(buttons.count()):
                try:
                    text = buttons.nth(i).inner_text().strip()
                    visible = buttons.nth(i).is_visible()
                    enabled = buttons.nth(i).is_enabled()
                    button_info.append({
                        'index': i,
                        'text': text,
                        'visible': visible,
                        'enabled': enabled
                    })
                    print(f"  Button {i}: '{text}' (visible: {visible}, enabled: {enabled})")
                except Exception as e:
                    print(f"  Button {i}: Error reading - {e}")
            
            # Find the Scan Reports button specifically
            print("\n=== SCAN REPORTS BUTTON ===")
            scan_button = page.locator('text=Scan Reports')
            if scan_button.count() > 0:
                print("✓ Scan Reports button found")
                print(f"  Visible: {scan_button.is_visible()}")
                print(f"  Enabled: {scan_button.is_enabled()}")
                
                # Get button details
                button_rect = scan_button.bounding_box()
                print(f"  Position: {button_rect}")
                
                # Check if button is in viewport
                is_in_viewport = scan_button.is_visible()
                print(f"  In viewport: {is_in_viewport}")
                
                # Scroll to button if needed
                if not is_in_viewport:
                    print("  Scrolling to button...")
                    scan_button.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000)
                
                # Take screenshot before click
                page.screenshot(path="before_scan_click.png")
                print("  Screenshot saved: before_scan_click.png")
                
                # Click the button
                print("  Clicking Scan Reports button...")
                scan_button.click()
                print("  ✓ Click successful")
                
                # Wait for any AJAX requests
                print("  Waiting for AJAX requests...")
                page.wait_for_timeout(3000)
                
                # Check for report analysis section
                print("\n=== REPORT ANALYSIS SECTION ===")
                report_section = page.locator('#reportAnalysis')
                if report_section.count() > 0:
                    print("✓ Report analysis section found")
                    
                    # Get section content
                    section_html = report_section.inner_html()
                    section_text = report_section.inner_text()
                    
                    print(f"  Section text length: {len(section_text)}")
                    print(f"  Section HTML length: {len(section_html)}")
                    
                    if section_text.strip():
                        print("  Section content:")
                        print(f"    {section_text[:200]}...")
                    else:
                        print("  Section appears to be empty")
                    
                    # Take screenshot of the section
                    report_section.screenshot(path="scan_report_analysis.png")
                    print("  Screenshot saved: scan_report_analysis.png")
                    
                    # Check for any findings or results
                    findings = page.locator('#reportAnalysis .finding, #reportAnalysis .result, #reportAnalysis .card')
                    print(f"  Found {findings.count()} findings/result cards")
                    
                    if findings.count() > 0:
                        for i in range(findings.count()):
                            finding_text = findings.nth(i).inner_text()
                            print(f"    Finding {i}: {finding_text[:100]}...")
                    
                else:
                    print("✗ Report analysis section not found")
                    
                    # Look for similar elements
                    similar = page.locator('[id*="report"], [id*="analysis"], [class*="report"], [class*="analysis"]')
                    print(f"  Found {similar.count()} similar elements")
                    
                    for i in range(similar.count()):
                        try:
                            element_id = similar.nth(i).get_attribute('id') or similar.nth(i).get_attribute('class')
                            print(f"    Similar element {i}: {element_id}")
                        except Exception:
                            pass
                
                # Take full page screenshot after click
                page.screenshot(path="after_scan_click.png")
                print("  Screenshot saved: after_scan_click.png")
                
            else:
                print("✗ Scan Reports button not found")
                
                # Look for any buttons with similar text
                similar_buttons = page.locator('button:has-text("scan"), button:has-text("report"), a:has-text("scan"), a:has-text("report")')
                print(f"  Found {similar_buttons.count()} buttons with similar text")
                
                for i in range(similar_buttons.count()):
                    text = similar_buttons.nth(i).inner_text()
                    print(f"    Similar button {i}: '{text}'")
            
            # Check for any JavaScript errors
            print("\n=== JAVASCRIPT ERRORS ===")
            errors = page.evaluate("() => window.console.errors || []")
            if errors:
                print(f"Found {len(errors)} JavaScript errors:")
                for error in errors:
                    print(f"  {error}")
            else:
                print("✓ No JavaScript errors found")
            
            # Check network requests
            print("\n=== NETWORK REQUESTS ===")
            # This would require setting up request/response listeners
            print("Network monitoring not implemented in this test")
            
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path="error_debug.png")
            print("Error screenshot saved: error_debug.png")
            
        finally:
            print("\n=== TEST COMPLETED ===")
            print("Browser will close in 10 seconds...")
            time.sleep(10)
            browser.close()

if __name__ == "__main__":
    test_scan_reports_comprehensive() 