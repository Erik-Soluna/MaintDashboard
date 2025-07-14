from playwright.sync_api import sync_playwright
import time
import json

def debug_maintenance_reports():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        network_log = []

        # Log all network requests and responses
        def log_request(request):
            print(f"Request: {request.method} {request.url}")
            network_log.append({"type": "request", "method": request.method, "url": request.url})

        def log_response(response):
            print(f"Response: {response.status} {response.url}")
            try:
                content_type = response.headers.get("content-type", "")
                entry = {"type": "response", "status": response.status, "url": response.url}
                if "application/json" in content_type or "text/html" in content_type:
                    body = response.text()
                    entry["body"] = body[:1000]  # Log more content for debugging
                network_log.append(entry)
            except Exception as e:
                network_log.append({"type": "response", "status": response.status, "url": response.url, "error": str(e)})

        page.on("request", log_request)
        page.on("response", log_response)

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
            page.screenshot(path="equipment_detail_initial.png")
            print("✓ Initial equipment page screenshot saved")

            # Explore all tabs to understand the interface
            print("\n=== EXPLORING ALL TABS ===")
            tabs = page.locator('[role="tab"], .nav-tabs a, .nav-pills a')
            print(f"Found {tabs.count()} tabs")
            
            tab_info = []
            for i in range(tabs.count()):
                try:
                    tab_text = tabs.nth(i).inner_text().strip()
                    tab_href = tabs.nth(i).get_attribute('href') or tabs.nth(i).get_attribute('data-target')
                    tab_info.append({"index": i, "text": tab_text, "href": tab_href})
                    print(f"  Tab {i}: '{tab_text}' -> {tab_href}")
                except Exception as e:
                    print(f"  Tab {i}: Error reading - {e}")

            # Click on "Maintenance Reports" tab
            print("\n=== ACTIVATING MAINTENANCE REPORTS TAB ===")
            maintenance_reports_tab = page.locator('[role="tab"][href="#reports"]')
            if maintenance_reports_tab.count() > 0:
                print("✓ Found Maintenance Reports tab, clicking...")
                maintenance_reports_tab.click()
                page.wait_for_timeout(2000)
                print("✓ Maintenance Reports tab activated")
                
                # Take screenshot of maintenance reports tab
                page.screenshot(path="maintenance_reports_tab.png")
                print("✓ Maintenance reports tab screenshot saved")
                
                # Analyze the maintenance reports section
                print("\n=== ANALYZING MAINTENANCE REPORTS SECTION ===")
                
                # Check for any content in the reports section
                reports_section = page.locator('#reports, .tab-pane.active')
                if reports_section.count() > 0:
                    section_content = reports_section.inner_text()
                    print(f"Reports section content length: {len(section_content)}")
                    if section_content.strip():
                        print(f"Content: {section_content[:200]}...")
                    else:
                        print("Reports section appears empty")
                
                # Look for any buttons or controls in the reports section
                report_buttons = page.locator('#reports button, #reports .btn, .tab-pane.active button, .tab-pane.active .btn')
                print(f"Found {report_buttons.count()} buttons in reports section")
                
                for i in range(report_buttons.count()):
                    try:
                        button_text = report_buttons.nth(i).inner_text().strip()
                        button_visible = report_buttons.nth(i).is_visible()
                        print(f"  Button {i}: '{button_text}' (visible: {button_visible})")
                    except Exception as e:
                        print(f"  Button {i}: Error reading - {e}")
                
                # Look for any existing reports or status messages
                status_messages = page.locator('#reports .alert, #reports .message, #reports .status, .tab-pane.active .alert, .tab-pane.active .message, .tab-pane.active .status')
                print(f"Found {status_messages.count()} status messages")
                
                for i in range(status_messages.count()):
                    try:
                        message_text = status_messages.nth(i).inner_text().strip()
                        print(f"  Status {i}: '{message_text}'")
                    except Exception as e:
                        print(f"  Status {i}: Error reading - {e}")
                
                # Now test the Scan Reports functionality
                print("\n=== TESTING SCAN REPORTS FUNCTIONALITY ===")
                scan_button = page.locator('text=Scan Reports')
                if scan_button.count() > 0:
                    print("✓ Found Scan Reports button")
                    print(f"  Visible: {scan_button.is_visible()}")
                    print(f"  Enabled: {scan_button.is_enabled()}")
                    
                    if scan_button.is_visible():
                        print("  Clicking Scan Reports button...")
                        scan_button.click()
                        print("  ✓ Scan Reports button clicked")
                        
                        # Wait for AJAX request to complete
                        page.wait_for_timeout(5000)
                        
                        # Check for results
                        print("\n=== CHECKING SCAN RESULTS ===")
                        report_analysis = page.locator('#reportAnalysis')
                        if report_analysis.count() > 0:
                            print("✓ Report analysis section found!")
                            
                            # Get content
                            content = report_analysis.inner_text()
                            print(f"Analysis content: {content}")
                            
                            # Take screenshot
                            report_analysis.screenshot(path="report_analysis_after_scan.png")
                            print("✓ Report analysis screenshot saved")
                            
                            # Check for any findings or error messages
                            findings = page.locator('#reportAnalysis .finding, #reportAnalysis .result, #reportAnalysis .card, #reportAnalysis .alert')
                            print(f"Found {findings.count()} findings/result cards")
                            
                            if findings.count() > 0:
                                print("Findings:")
                                for i in range(findings.count()):
                                    finding_text = findings.nth(i).inner_text()
                                    print(f"  {i+1}. {finding_text}")
                            else:
                                print("No findings displayed")
                                
                                # Check if there are any error messages or status indicators
                                error_messages = page.locator('#reportAnalysis .error, #reportAnalysis .warning, #reportAnalysis .info')
                                print(f"Found {error_messages.count()} error/warning messages")
                                
                                for i in range(error_messages.count()):
                                    error_text = error_messages.nth(i).inner_text()
                                    print(f"  Error {i}: {error_text}")
                        else:
                            print("✗ Report analysis section not found")
                            
                            # Look for any other elements that might contain results
                            result_elements = page.locator('[id*="result"], [class*="result"], [id*="analysis"], [class*="analysis"]')
                            print(f"Found {result_elements.count()} potential result elements")
                            
                            for i in range(result_elements.count()):
                                try:
                                    element_id = result_elements.nth(i).get_attribute('id') or result_elements.nth(i).get_attribute('class')
                                    element_text = result_elements.nth(i).inner_text()
                                    print(f"  Result element {i}: {element_id} - {element_text[:100]}...")
                                except:
                                    pass
                    else:
                        print("✗ Scan Reports button is not visible")
                else:
                    print("✗ Scan Reports button not found")
                    
                    # Look for any similar buttons
                    similar_buttons = page.locator('button:has-text("scan"), button:has-text("report"), button:has-text("analyze")')
                    print(f"Found {similar_buttons.count()} similar buttons")
                    
                    for i in range(similar_buttons.count()):
                        button_text = similar_buttons.nth(i).inner_text()
                        print(f"  Similar button {i}: '{button_text}'")
            else:
                print("✗ Maintenance Reports tab not found")

            # Take final screenshot
            page.screenshot(path="final_maintenance_reports.png")
            print("✓ Final maintenance reports screenshot saved")

        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            page.screenshot(path="error_debug.png")
            print("Error screenshot saved: error_debug.png")

        finally:
            # Save network log
            with open("maintenance_reports_network_log.json", "w", encoding="utf-8") as f:
                json.dump(network_log, f, indent=2)
            print("Network log saved to maintenance_reports_network_log.json")
            print("\n=== DEBUG COMPLETED ===")
            print("Browser will close in 10 seconds...")
            time.sleep(10)
            browser.close()

if __name__ == "__main__":
    debug_maintenance_reports() 