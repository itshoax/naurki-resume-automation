# automation/naukri_stealth_uploader.py
"""
Stealth Naukri Resume Upload - Bypasses bot detection
The issue is not cookies, but automation detection by Naukri
"""

import os
import time
import json
import base64
import logging
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

# Force use of undetected-chromedriver for stealth
USE_UNDETECTED = True
try:
    import undetected_chromedriver as uc
    logging.info("✅ Undetected ChromeDriver available")
except ImportError:
    USE_UNDETECTED = False
    logging.warning("⚠️ Undetected ChromeDriver not available - may get detected")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class StealthNaukriUploader:
    def __init__(self):
        self.resume_path = os.getenv("RESUME_PATH", "./resume/Nikhil_Saini_Resume.pdf")
        self.driver = None
        self.cookies_file = "./cookies/naukri_cookies.json"
        self.cookies_b64 = os.getenv("NAUKRI_COOKIES_B64")

        os.makedirs("./cookies", exist_ok=True)
        os.makedirs("./logs", exist_ok=True)

    def setup_stealth_driver(self):
        """Setup maximum stealth browser"""
        if USE_UNDETECTED:
            try:
                # Undetected ChromeDriver with maximum stealth
                options = uc.ChromeOptions()
                
                # Basic options
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1366,768")  # Common resolution
                
                # Stealth options
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-features=VizDisplayCompositor")
                options.add_argument("--disable-web-security")
                options.add_argument("--allow-running-insecure-content")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-plugins")
                options.add_argument("--disable-default-apps")
                options.add_argument("--disable-background-timer-throttling")
                options.add_argument("--disable-backgrounding-occluded-windows")
                options.add_argument("--disable-renderer-backgrounding")
                options.add_argument("--disable-features=TranslateUI")
                
                # Realistic user agent
                options.add_argument(
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                # Hide automation flags
                options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Add realistic preferences
                prefs = {
                    "profile.default_content_setting_values": {
                        "notifications": 2,
                        "media_stream": 2,
                    },
                    "profile.default_content_settings.popups": 0,
                    "profile.managed_default_content_settings.images": 1
                }
                options.add_experimental_option("prefs", prefs)
                
                # Initialize with version detection disabled
                self.driver = uc.Chrome(options=options, version_main=None)
                
                # Execute stealth scripts
                stealth_js = """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'permissions', {get: () => ({
                    query: () => Promise.resolve({state: 'granted'})
                })});
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                """
                self.driver.execute_script(stealth_js)
                
                logging.info("✅ Stealth Undetected Chrome driver initialized")
                
            except Exception as e:
                logging.error(f"Failed to initialize Undetected Chrome: {e}")
                USE_UNDETECTED = False
        
        if not USE_UNDETECTED:
            # Fallback to regular Chrome with maximum stealth
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1366,768")
            
            # Maximum stealth for regular Chrome
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            self.driver = webdriver.Chrome(options=options)
            
            # Execute stealth scripts for regular Chrome
            stealth_js = """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
            """
            self.driver.execute_script(stealth_js)
            
            logging.info("✅ Stealth regular Chrome driver initialized")

        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(5)

    def human_like_delay(self, min_delay=1, max_delay=3):
        """Add human-like delays"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def human_like_typing(self, element, text):
        """Type like a human with random delays"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))

    def decode_cookies_from_secret(self):
        """Decode cookies from base64"""
        if self.cookies_b64:
            try:
                cookies_json_str = base64.b64decode(self.cookies_b64).decode("utf-8")
                cookies = json.loads(cookies_json_str)
                with open(self.cookies_file, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, indent=2)
                logging.info("🍪 Cookies decoded from secret")
                return True
            except Exception as e:
                logging.error(f"Cookie decode failed: {e}")
        return False

    def load_cookies_stealthily(self):
        """Load cookies with stealth approach"""
        try:
            if not os.path.exists(self.cookies_file):
                if not self.decode_cookies_from_secret():
                    raise FileNotFoundError("No cookies available")

            # Start with main domain and browse like human
            logging.info("🌐 Navigating to Naukri homepage...")
            self.driver.get("https://www.naukri.com")
            self.human_like_delay(3, 5)

            # Load cookies
            with open(self.cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            # Add cookies one by one with delays
            valid_cookies = []
            for cookie in cookies:
                try:
                    if cookie.get("sameSite") == "None":
                        cookie["sameSite"] = "Lax"
                    
                    self.driver.add_cookie(cookie)
                    valid_cookies.append(cookie)
                    time.sleep(0.1)  # Small delay between cookies
                except Exception as e:
                    logging.warning(f"Cookie {cookie.get('name')} failed: {e}")

            logging.info(f"🍪 Loaded {len(valid_cookies)} cookies")

            # Refresh and wait like human
            logging.info("🔄 Refreshing page...")
            self.driver.refresh()
            self.human_like_delay(3, 5)

            return True
        except Exception as e:
            logging.error(f"Cookie loading failed: {e}")
            return False

    def navigate_like_human(self):
        """Navigate to profile page like a human user"""
        try:
            # First, go to homepage and browse a bit
            logging.info("🏠 Starting from homepage...")
            self.driver.get("https://www.naukri.com")
            self.human_like_delay(2, 4)

            # Scroll a bit like human
            self.driver.execute_script("window.scrollTo(0, 300);")
            self.human_like_delay(1, 2)

            # Try to click on profile/dashboard links naturally
            profile_links = [
                "//a[contains(@href, 'mnjuser')]",
                "//a[contains(text(), 'Profile')]",
                "//a[contains(text(), 'My Profile')]",
                "//a[contains(@href, 'profile')]"
            ]

            for link_xpath in profile_links:
                try:
                    links = self.driver.find_elements(By.XPATH, link_xpath)
                    for link in links:
                        if link.is_displayed():
                            logging.info(f"🔗 Clicking profile link: {link.text}")
                            ActionChains(self.driver).move_to_element(link).click().perform()
                            self.human_like_delay(3, 5)
                            
                            # Check if we're on a user page
                            if "mnjuser" in self.driver.current_url:
                                logging.info(f"✅ Successfully navigated to: {self.driver.current_url}")
                                return True
                except Exception as e:
                    continue

            # If clicking links didn't work, try direct navigation
            logging.info("🔗 Trying direct navigation to profile...")
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            self.human_like_delay(3, 5)

            # Check for access denied
            if "Access Denied" not in self.driver.title and "access denied" not in self.driver.page_source.lower():
                logging.info("✅ Direct navigation successful")
                return True

            return False

        except Exception as e:
            logging.error(f"Navigation failed: {e}")
            return False

    def verify_login_status(self):
        """Verify login with multiple checks"""
        try:
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            logging.info(f"📍 Current URL: {current_url}")
            logging.info(f"📄 Page title: {page_title}")

            # Check for access denied first
            if "access denied" in page_title.lower() or "access denied" in self.driver.page_source.lower():
                logging.error("❌ ACCESS DENIED detected")
                
                # Try alternative approach - go back to homepage and try again
                logging.info("🔄 Trying alternative navigation...")
                self.driver.get("https://www.naukri.com")
                self.human_like_delay(3, 5)
                
                # Try jobs page first (less restricted)
                self.driver.get("https://www.naukri.com/mnjuser/homepage")
                self.human_like_delay(3, 5)
                
                if "access denied" not in self.driver.title.lower():
                    logging.info("✅ Alternative navigation worked")
                    return True
                else:
                    return False

            # Look for login indicators
            login_indicators = [
                "//div[contains(@class, 'nI-gNb-drawer')]",
                "//div[contains(@class, 'user-name')]",
                "//span[contains(@class, 'fullname')]",
                "//*[contains(text(), 'My Profile')]",
                "//*[contains(text(), 'Dashboard')]",
                "//a[contains(@href, 'logout')]"
            ]

            for indicator in login_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    if elements and elements[0].is_displayed():
                        logging.info(f"✅ Login verified via: {indicator}")
                        return True
                except Exception:
                    continue

            # Check URL pattern
            if "mnjuser" in current_url and "login" not in current_url:
                logging.info("✅ Login verified via URL pattern")
                return True

            logging.warning("⚠️ Could not verify login status")
            return False

        except Exception as e:
            logging.error(f"Login verification failed: {e}")
            return False

    def find_and_upload_resume(self):
        """Find upload elements and upload resume"""
        try:
            # Make sure we're on a profile-related page
            if not self.navigate_to_upload_page():
                return False

            # Look for file inputs with human-like behavior
            logging.info("🔍 Looking for upload elements...")
            
            # Scroll around the page like human
            self.driver.execute_script("window.scrollTo(0, 200);")
            self.human_like_delay(1, 2)
            self.driver.execute_script("window.scrollTo(0, 500);")
            self.human_like_delay(1, 2)

            # Find file inputs
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            logging.info(f"📄 Found {len(file_inputs)} file input(s)")

            if file_inputs:
                return self.upload_to_file_input(file_inputs[0])

            # Look for upload buttons that trigger file dialogs
            upload_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'resume')]"
            )
            
            logging.info(f"🔘 Found {len(upload_buttons)} upload button(s)")

            for button in upload_buttons:
                if self.try_button_upload(button):
                    return True

            logging.warning("⚠️ No upload elements found")
            return False

        except Exception as e:
            logging.error(f"Upload search failed: {e}")
            return False

    def navigate_to_upload_page(self):
        """Navigate to best page for upload"""
        upload_pages = [
            "https://www.naukri.com/mnjuser/profile",
            "https://www.naukri.com/mnjuser/homepage", 
            "https://www.naukri.com/mnjuser/manageResume"
        ]

        for page in upload_pages:
            try:
                logging.info(f"🌐 Trying page: {page}")
                self.driver.get(page)
                self.human_like_delay(3, 5)

                if "access denied" not in self.driver.title.lower():
                    # Look for upload elements
                    file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
                    upload_buttons = self.driver.find_elements(By.XPATH, 
                        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload')]"
                    )
                    
                    if file_inputs or upload_buttons:
                        logging.info(f"✅ Found upload page: {page}")
                        return True
                        
            except Exception as e:
                logging.warning(f"Page {page} failed: {e}")
                continue

        return False

    def upload_to_file_input(self, file_input):
        """Upload file to input element"""
        try:
            # Make element visible and interactable
            self.driver.execute_script(
                "arguments[0].style.display = 'block';"
                "arguments[0].style.visibility = 'visible';"
                "arguments[0].style.opacity = '1';"
                "arguments[0].removeAttribute('hidden');",
                file_input
            )

            # Scroll to element
            self.driver.execute_script("arguments[0].scrollIntoView(true);", file_input)
            self.human_like_delay(1, 2)

            logging.info("📁 Uploading resume file...")
            file_input.send_keys(os.path.abspath(self.resume_path))
            self.human_like_delay(2, 4)

            # Look for submit button
            submit_buttons = self.driver.find_elements(By.XPATH,
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]"
            )

            if submit_buttons:
                for button in submit_buttons:
                    if button.is_displayed() and button.is_enabled():
                        logging.info(f"🔘 Clicking submit: {button.text}")
                        ActionChains(self.driver).move_to_element(button).click().perform()
                        self.human_like_delay(3, 6)
                        break

            return self.verify_upload_success()

        except Exception as e:
            logging.error(f"File input upload failed: {e}")
            return False

    def try_button_upload(self, button):
        """Try clicking upload button to trigger file dialog"""
        try:
            if not button.is_displayed() or not button.is_enabled():
                return False

            button_text = button.text.strip()
            logging.info(f"🔘 Trying button: {button_text}")

            # Scroll to button
            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
            self.human_like_delay(1, 2)

            # Click button
            ActionChains(self.driver).move_to_element(button).click().perform()
            self.human_like_delay(2, 3)

            # Look for file input that appeared
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file' and not(@disabled)]")
            
            for file_input in file_inputs:
                if file_input.is_displayed() or file_input.is_enabled():
                    logging.info("📁 Found triggered file input")
                    file_input.send_keys(os.path.abspath(self.resume_path))
                    self.human_like_delay(2, 4)
                    return self.verify_upload_success()

            return False

        except Exception as e:
            logging.error(f"Button upload failed: {e}")
            return False

    def verify_upload_success(self):
        """Verify that upload was successful"""
        try:
            # Wait for upload indicators
            success_indicators = [
                (By.ID, "results_resumeParser"),
                (By.XPATH, "//div[contains(text(), 'successfully')]"),
                (By.XPATH, "//div[contains(text(), 'uploaded')]"),
                (By.CSS_SELECTOR, ".success"),
                (By.CSS_SELECTOR, ".alert-success")
            ]

            for by, selector in success_indicators:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    logging.info(f"✅ Upload success detected: {selector}")
                    return True
                except TimeoutException:
                    continue

            # Check for any positive change in page
            self.human_like_delay(3, 5)
            
            # Look for resume file name on page
            if "resume" in self.driver.page_source.lower() and ".pdf" in self.driver.page_source.lower():
                logging.info("✅ Resume detected on page")
                return True

            logging.warning("⚠️ Upload success not confirmed")
            return False

        except Exception as e:
            logging.error(f"Upload verification failed: {e}")
            return False

    def save_debug_info(self):
        """Save debug information"""
        try:
            timestamp = int(time.time())
            
            # Screenshot
            self.driver.save_screenshot(f"./logs/debug_{timestamp}.png")
            
            # Page source
            with open(f"./logs/page_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            
            logging.info(f"🐛 Debug info saved with timestamp {timestamp}")
            
        except Exception as e:
            logging.error(f"Debug save failed: {e}")

    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.driver:
                self.save_debug_info()
                
                # Save updated cookies
                cookies = self.driver.get_cookies()
                with open(self.cookies_file, "w") as f:
                    json.dump(cookies, f, indent=2)
                
                cookies_b64 = base64.b64encode(json.dumps(cookies).encode()).decode()
                logging.info("🍪 Updated cookies saved")
                print(f"COOKIES_B64: {cookies_b64}")
                
                self.driver.quit()
                logging.info("🧹 Cleanup completed")
                
        except Exception as e:
            logging.error(f"Cleanup error: {e}")

    def run(self):
        """Main execution"""
        try:
            logging.info("🚀 Starting STEALTH Naukri automation")
            
            if not os.path.exists(self.resume_path):
                raise FileNotFoundError(f"Resume not found: {self.resume_path}")
            
            logging.info(f"📄 Resume: {self.resume_path} ({os.path.getsize(self.resume_path)} bytes)")
            
            # Setup stealth browser
            self.setup_stealth_driver()
            
            # Load cookies stealthily
            if not self.load_cookies_stealthily():
                raise Exception("Cookie loading failed")
            
            # Navigate like human
            if not self.navigate_like_human():
                raise Exception("Navigation failed")
            
            # Verify login
            if not self.verify_login_status():
                raise Exception("Login verification failed")
            
            # Upload resume
            if self.find_and_upload_resume():
                logging.info("🎉 SUCCESS: Resume upload completed!")
                return True
            else:
                logging.error("❌ Resume upload failed")
                return False
                
        except Exception as e:
            logging.error(f"💥 Automation failed: {e}")
            return False
        finally:
            self.cleanup()

def main():
    uploader = StealthNaukriUploader()
    success = uploader.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
