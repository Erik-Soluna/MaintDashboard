from playwright.sync_api import sync_playwright
import time

def test_scan_reports_and_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to False to see what's happening
        page = browser.new_page()
        
        try:
            # Login with correct URL
            print("Navigating to login page...")
            page.goto("http://localhost:4405/auth/login/")
            
            # Wait for login form and fill credentials
            print("Waiting for login form...")
            page.wait_for_selector('input[name="username"]', timeout=10000)
            page.fill('input[name="username"]', "admin")
            page.fill('input[name="password"]', "temppass123")
            
            print("Submitting login form...")
            page.click('button[type="submit"]')
            
            # Wait for login to complete (redirect to dashboard)
            print("Waiting for login to complete...")
            page.wait_for_url("**/core/dashboard/**", timeout=10000)
            print("Login successful!")
            
            # Go to equipment detail
            print("Navigating to equipment detail page...")
            page.goto("http://localhost:4405/equipment/17/")
            
            # Wait for page to load completely
            print("Waiting for page to load...")
            page.wait_for_load_state('networkidle', timeout=15000)
            page.wait_for_timeout(2000)  # Extra wait for any dynamic content
            
            # Debug: Check what buttons are available on the page
            print("Checking for available buttons...")
            buttons = page.locator('button, a.btn, input[type="button"], input[type="submit"]')
            print(f"Found {buttons.count()} buttons/links on the page")
            
            for i in range(min(buttons.count(), 10)):  # Show first 10 buttons
                try:
                    text = buttons.nth(i).inner_text()
                    print(f"Button {i}: '{text}'")
                except Exception:
                    print(f"Button {i}: [no text]")
            
            # Try different selectors for the Scan Reports button
            print("Looking for Scan Reports button with different selectors...")
            
            # Method 1: Text selector
            scan_button = page.locator('text=Scan Reports')
            if scan_button.count() > 0:
                print("Found 'Scan Reports' button by text")
                print("Button is visible:", scan_button.is_visible())
                print("Button is enabled:", scan_button.is_enabled())
                
                # Scroll to button if needed
                scan_button.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                
                print("Attempting to click Scan Reports button...")
                scan_button.click()
                print("Click successful!")
            else:
                print("'Scan Reports' text not found, trying other selectors...")
                
                # Method 2: Look for buttons with "scan" or "report" in text
                scan_variants = page.locator('button:has-text("scan"), button:has-text("report"), a:has-text("scan"), a:has-text("report")')
                if scan_variants.count() > 0:
                    print(f"Found {scan_variants.count()} buttons with 'scan' or 'report' in text")
                    for i in range(scan_variants.count()):
                        text = scan_variants.nth(i).inner_text()
                        print(f"  Variant {i}: '{text}'")
                
                # Method 3: Look for any button that might be related
                all_buttons = page.locator('button, a.btn')
                print(f"Total buttons found: {all_buttons.count()}")
                
                # Take a screenshot to see what's on the page
                page.screenshot(path="before_scan_click.png")
                print("Screenshot saved as before_scan_click.png")
                
                # Try to find the button by looking at the page content
                page_content = page.content()
                if "Scan Reports" in page_content:
                    print("'Scan Reports' text found in page content")
                else:
                    print("'Scan Reports' text NOT found in page content")
                
                # Look for any JavaScript errors
                console_logs = page.evaluate("() => window.console.logs || []")
                if console_logs:
                    print("Console logs:", console_logs)
            
            # Wait for any AJAX requests to complete
            print("Waiting for any AJAX requests...")
            page.wait_for_timeout(5000)
            
            # Check if report analysis section appeared
            print("Checking for report analysis section...")
            report_section = page.locator('#reportAnalysis')
            if report_section.count() > 0:
                print("Report analysis section found!")
                report_section.screenshot(path="scan_report_analysis.png")
                print("Screenshot saved as scan_report_analysis.png")
            else:
                print("Report analysis section not found!")
                # Take full page screenshot for debugging
                page.screenshot(path="after_scan_attempt.png")
                print("Full page screenshot saved as after_scan_attempt.png")
                
                # Check if there are any elements with similar IDs
                similar_elements = page.locator('[id*="report"], [id*="analysis"], [class*="report"], [class*="analysis"]')
                print(f"Found {similar_elements.count()} elements with 'report' or 'analysis' in ID/class")
                
        except Exception as e:
            print(f"Error occurred: {e}")
            import traceback
            traceback.print_exc()
            # Take screenshot for debugging
            page.screenshot(path="error_debug.png")
            print("Error screenshot saved as error_debug.png")
            
        finally:
            # Keep browser open for a moment to see what happened
            print("Script completed. Browser will close in 5 seconds...")
            time.sleep(5)
            browser.close()

if __name__ == "__main__":
    test_scan_reports_and_screenshot() 