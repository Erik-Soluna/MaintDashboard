from playwright.sync_api import sync_playwright
import time

def test_scan_reports_fix():
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
            
            # Take initial screenshot
            page.screenshot(path="initial_page.png")
            print("Initial page screenshot saved")
            
            # Try to find and activate tabs or sections
            print("\n=== LOOKING FOR TABS/SECTIONS ===")
            
            # Method 1: Look for Bootstrap tabs
            tab_buttons = page.locator('.nav-tabs a, .nav-pills a, [role="tab"]')
            print(f"Found {tab_buttons.count()} tab buttons")
            
            for i in range(tab_buttons.count()):
                try:
                    tab_text = tab_buttons.nth(i).inner_text().strip()
                    print(f"  Tab {i}: '{tab_text}'")
                    
                    # Click on tabs that might contain reports
                    if any(keyword in tab_text.lower() for keyword in ['report', 'scan', 'analysis', 'document', 'file']):
                        print(f"    Clicking tab: {tab_text}")
                        tab_buttons.nth(i).click()
                        page.wait_for_timeout(2000)
                        
                        # Check if Scan Reports button is now visible
                        scan_button = page.locator('text=Scan Reports')
                        if scan_button.count() > 0 and scan_button.is_visible():
                            print(f"    ✓ Scan Reports button is now visible!")
                            break
                except Exception as e:
                    print(f"    Error with tab {i}: {e}")
            
            # Method 2: Look for accordion or collapsible sections
            print("\n=== LOOKING FOR COLLAPSIBLE SECTIONS ===")
            collapsible = page.locator('.accordion-button, .collapse-toggle, [data-toggle="collapse"], [data-bs-toggle="collapse"]')
            print(f"Found {collapsible.count()} collapsible elements")
            
            for i in range(collapsible.count()):
                try:
                    collapsible_text = collapsible.nth(i).inner_text().strip()
                    print(f"  Collapsible {i}: '{collapsible_text}'")
                    
                    # Click on collapsible sections that might contain reports
                    if any(keyword in collapsible_text.lower() for keyword in ['report', 'scan', 'analysis', 'document', 'file']):
                        print(f"    Clicking collapsible: {collapsible_text}")
                        collapsible.nth(i).click()
                        page.wait_for_timeout(2000)
                        
                        # Check if Scan Reports button is now visible
                        scan_button = page.locator('text=Scan Reports')
                        if scan_button.count() > 0 and scan_button.is_visible():
                            print(f"    ✓ Scan Reports button is now visible!")
                            break
                except Exception as e:
                    print(f"    Error with collapsible {i}: {e}")
            
            # Method 3: Look for any buttons that might expand sections
            print("\n=== LOOKING FOR EXPAND BUTTONS ===")
            expand_buttons = page.locator('button:has-text("expand"), button:has-text("show"), button:has-text("more"), a:has-text("expand"), a:has-text("show"), a:has-text("more")')
            print(f"Found {expand_buttons.count()} expand buttons")
            
            for i in range(expand_buttons.count()):
                try:
                    expand_text = expand_buttons.nth(i).inner_text().strip()
                    print(f"  Expand button {i}: '{expand_text}'")
                    
                    print(f"    Clicking expand button: {expand_text}")
                    expand_buttons.nth(i).click()
                    page.wait_for_timeout(2000)
                    
                    # Check if Scan Reports button is now visible
                    scan_button = page.locator('text=Scan Reports')
                    if scan_button.count() > 0 and scan_button.is_visible():
                        print(f"    ✓ Scan Reports button is now visible!")
                        break
                except Exception as e:
                    print(f"    Error with expand button {i}: {e}")
            
            # Method 4: Try clicking on any visible buttons that might reveal more content
            print("\n=== TRYING VISIBLE BUTTONS ===")
            visible_buttons = page.locator('button:visible, a.btn:visible')
            print(f"Found {visible_buttons.count()} visible buttons")
            
            for i in range(min(visible_buttons.count(), 5)):  # Try first 5 visible buttons
                try:
                    button_text = visible_buttons.nth(i).inner_text().strip()
                    print(f"  Visible button {i}: '{button_text}'")
                    
                    # Skip navigation buttons
                    if any(keyword in button_text.lower() for keyword in ['edit', 'delete', 'system', 'admin']):
                        print(f"    Skipping navigation button: {button_text}")
                        continue
                    
                    print(f"    Clicking visible button: {button_text}")
                    visible_buttons.nth(i).click()
                    page.wait_for_timeout(2000)
                    
                    # Check if Scan Reports button is now visible
                    scan_button = page.locator('text=Scan Reports')
                    if scan_button.count() > 0 and scan_button.is_visible():
                        print(f"    ✓ Scan Reports button is now visible!")
                        break
                except Exception as e:
                    print(f"    Error with visible button {i}: {e}")
            
            # Now try to click Scan Reports button if it's visible
            print("\n=== ATTEMPTING SCAN REPORTS CLICK ===")
            scan_button = page.locator('text=Scan Reports')
            if scan_button.count() > 0:
                if scan_button.is_visible():
                    print("✓ Scan Reports button is visible, clicking...")
                    scan_button.click()
                    print("✓ Click successful!")
                    
                    # Wait for AJAX
                    page.wait_for_timeout(3000)
                    
                    # Check for report analysis section
                    report_section = page.locator('#reportAnalysis')
                    if report_section.count() > 0:
                        print("✓ Report analysis section found!")
                        report_section.screenshot(path="scan_report_analysis.png")
                        print("Screenshot saved: scan_report_analysis.png")
                        
                        # Get content
                        content = report_section.inner_text()
                        print(f"Content length: {len(content)}")
                        if content.strip():
                            print(f"Content: {content[:200]}...")
                        else:
                            print("Section is empty")
                    else:
                        print("✗ Report analysis section not found")
                else:
                    print("✗ Scan Reports button is still not visible")
                    
                    # Try to force click even if not visible
                    print("Attempting force click...")
                    try:
                        scan_button.click(force=True)
                        print("✓ Force click successful!")
                        
                        # Wait for AJAX
                        page.wait_for_timeout(3000)
                        
                        # Check for report analysis section
                        report_section = page.locator('#reportAnalysis')
                        if report_section.count() > 0:
                            print("✓ Report analysis section found!")
                            report_section.screenshot(path="scan_report_analysis.png")
                            print("Screenshot saved: scan_report_analysis.png")
                        else:
                            print("✗ Report analysis section not found")
                    except Exception as e:
                        print(f"✗ Force click failed: {e}")
            else:
                print("✗ Scan Reports button not found")
            
            # Take final screenshot
            page.screenshot(path="final_page.png")
            print("Final page screenshot saved")
            
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
    test_scan_reports_fix() 