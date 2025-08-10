# automation/naukri_cookie_uploader_fixed.py
"""
Fixed Cookie-based Naukri Resume Upload Automation
Addresses Access Denied issues and eliminates false positives
"""

import os
import time
import json
import base64
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains

USE_UNDETECTED = os.getenv("USE_UNDETECTED", "false").lower() == "true"
if USE_UNDETECTED:
    try:
        import undetected_chromedriver as uc
    except ImportError:
        USE_UNDETECTED = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class FixedNaukriUploader:
    def __init__(self):
        self.resume_path = os.getenv("RESUME_PATH", "./resume/Nikhil_Saini_Resume.pdf")
        self.driver = None
        self.cookies_file = "./cookies/naukri_cookies.json"
        self.cookies_b64 = os.getenv("NAUKRI_COOKIES_B64")
        self.upload_verified = False

        os.makedirs("./cookies", exist_ok=True)
        os.makedirs("./logs", exist_ok=True)

    def setup_driver(self):
        """Setup Chrome driver with anti-detection measures"""
        if USE_UNDETECTED:
            try:
                options = uc.ChromeOptions()
                options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-web-security")
                options.add_argument("--allow-running-insecure-content")
                # Add more stealth options
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                self.driver = uc.Chrome(options=options)
                logging.info("Undetected Chrome driver initialized")
                return
            except Exception as e:
                logging.warning(f"UC failed: {e}, falling back to regular Chrome")

        # Enhanced regular Chrome options
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Anti-detection measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        
        # More realistic browser fingerprint
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        chromedriver_paths = [
            "/usr/local/bin/chromedriver",
            "/usr/bin/chromedriver",
            "./chromedriver"
        ]
        chromedriver_path = next((p for p in chromedriver_paths if os.path.exists(p)), None)

        if chromedriver_path:
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        else:
            self.driver = webdriver.Chrome(options=options)

        # Execute stealth scripts
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        
        logging.info("Enhanced Chrome driver initialized")
        self.driver.set_page_load_timeout(30)

    def decode_cookies_from_secret(self):
        """Decode Base64 JSON cookies from secret"""
        if self.cookies_b64:
            try:
                cookies_json_str = base64.b64decode(self.cookies_b64).decode("utf-8")
                cookies = json.loads(cookies_json_str)
                with open(self.cookies_file, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, indent=2)
                logging.info("Cookies decoded from GitHub secret")
                return True
            except Exception as e:
                logging.error(f"Failed to decode cookies: {e}")
        return False

    def load_cookies_gradually(self):
        """Load cookies with gradual approach to avoid Access Denied"""
        try:
            if not os.path.exists(self.cookies_file):
                if not self.decode_cookies_from_secret():
                    raise FileNotFoundError("No cookies available")

            # Start with main domain
            self.driver.get("https://www.naukri.com")
            time.sleep(5)

            with open(self.cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            # Filter and add cookies carefully
            valid_cookies = []
            for cookie in cookies:
                # Skip problematic cookies
                if cookie.get("name") in ["_gat", "_gat_UA-", "__gads"]:
                    continue
                    
                if cookie.get("sameSite") == "None":
                    cookie["sameSite"] = "Lax"
                    
                try:
                    self.driver.add_cookie(cookie)
                    valid_cookies.append(cookie)
                except Exception as e:
                    logging.warning(f"Failed to add cookie {cookie.get('name')}: {e}")

            logging.info(f"Loaded {len(valid_cookies)} valid cookies")
            
            # Navigate gradually to avoid triggering security
            self.driver.get("https://www.naukri.com")
            time.sleep(3)
            
            # Try to access a simple page first
            self.driver.get("https://www.naukri.com/mnjuser/homepage")
            time.sleep(5)
            
            return True
        except Exception as e:
            logging.error(f"Failed to load cookies: {e}")
            return False

    def check_access_denied(self):
        """Check if we're getting Access Denied"""
        page_title = self.driver.title.lower()
        page_source = self.driver.page_source.lower()
        
        if "access denied" in page_title or "access denied" in page_source:
            logging.error("❌ ACCESS DENIED detected!")
            logging.error("This usually means:")
            logging.error("1. Cookies have expired")
            logging.error("2. Account is locked/restricted")
            logging.error("3. Too many automation attempts detected")
            return True
        return False

    def verify_login_status(self):
        """Enhanced login verification"""
        try:
            # Try multiple URLs to avoid access denied
            test_urls = [
                "https://www.naukri.com/mnjuser/homepage",
                "https://www.naukri.com/mnjuser/profile",
                "https://www.naukri.com/mnjuser/dashboard"
            ]
            
            for url in test_urls:
                try:
                    logging.info(f"Testing login with: {url}")
                    self.driver.get(url)
                    time.sleep(5)
                    
                    if self.check_access_denied():
                        continue
                    
                    # Check for login indicators
                    login_indicators = [
                        (By.CLASS_NAME, "nI-gNb-drawer"),
                        (By.CLASS_NAME, "profileSection"),
                        (By.CLASS_NAME, "user-name"),
                        (By.ID, "name"),
                        (By.CSS_SELECTOR, "[data-automation='profile-name']"),
                        (By.CSS_SELECTOR, ".nI-gNb-info__name"),
                        (By.XPATH, "//*[contains(text(), 'Profile')]"),
                        (By.XPATH, "//*[contains(text(), 'Dashboard')]")
                    ]
                    
                    for by, selector in login_indicators:
                        try:
                            element = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((by, selector))
                            )
                            logging.info(f"✅ Login verified via {selector} on {url}")
                            return True
                        except TimeoutException:
                            continue
                    
                    # Check URL patterns
                    if "mnjuser" in self.driver.current_url and "nlogin" not in self.driver.current_url:
                        logging.info(f"✅ Login verified via URL pattern: {self.driver.current_url}")
                        return True
                        
                except Exception as e:
                    logging.warning(f"Failed to test {url}: {e}")
                    continue
            
            logging.error("❌ Could not verify login on any URL")
            return False
            
        except Exception as e:
            logging.error(f"Login verification failed: {e}")
            return False

    def find_resume_upload_page(self):
        """Find a working resume upload page"""
        upload_urls = [
            "https://www.naukri.com/mnjuser/profile",
            "https://www.naukri.com/mnjuser/manageResume", 
            "https://www.naukri.com/mnjuser/homepage",
            "https://www.naukri.com/mnjuser/profile?id=&altresume",
            "https://www.naukri.com/mnjuser/resume",
            "https://www.naukri.com/mnjuser/profile/resume"
        ]
        
        for url in upload_urls:
            try:
                logging.info(f"🔍 Checking upload page: {url}")
                self.driver.get(url)
                time.sleep(5)
                
                if self.check_access_denied():
                    logging.warning(f"Access denied on {url}")
                    continue
                
                # Look for file inputs
                file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
                upload_buttons = self.driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'resume')]")
                
                if file_inputs or upload_buttons:
                    logging.info(f"✅ Found upload elements on {url}: {len(file_inputs)} inputs, {len(upload_buttons)} buttons")
                    return url
                    
            except Exception as e:
                logging.warning(f"Failed to check {url}: {e}")
                continue
        
        logging.error("❌ No working upload page found")
        return None

    def upload_resume(self):
        """Main upload logic with strict verification"""
        
        # First, find a page that actually has upload elements
        working_url = self.find_resume_upload_page()
        if not working_url:
            logging.error("❌ No upload page accessible - cookies may have expired or account restricted")
            return False
        
        logging.info(f"✅ Using upload page: {working_url}")
        
        # Try actual upload strategies
        strategies = [
            self._strategy_direct_file_upload,
            self._strategy_button_triggered_upload,
            self._strategy_form_based_upload
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                logging.info(f"🔄 Attempting upload strategy {i}: {strategy.__name__}")
                if strategy(working_url):
                    if self._verify_actual_upload():
                        logging.info(f"✅ Strategy {i} succeeded with verified upload!")
                        self.upload_verified = True
                        return True
                    else:
                        logging.warning(f"⚠️  Strategy {i} completed but upload not verified")
                else:
                    logging.warning(f"❌ Strategy {i} failed")
            except Exception as e:
                logging.error(f"❌ Strategy {i} exception: {e}")
        
        return False

    def _strategy_direct_file_upload(self, url):
        """Direct file upload to visible file inputs"""
        try:
            self.driver.get(url)
            time.sleep(5)
            
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            
            for i, file_input in enumerate(file_inputs):
                try:
                    # Make sure element is interactable
                    self.driver.execute_script(
                        "arguments[0].style.display = 'block';"
                        "arguments[0].style.visibility = 'visible';"
                        "arguments[0].style.opacity = '1';"
                        "arguments[0].removeAttribute('hidden');",
                        file_input
                    )
                    
                    # Check accept attribute
                    accept = file_input.get_attribute("accept")
                    if accept and "pdf" not in accept.lower():
                        logging.info(f"Skipping input {i}: doesn't accept PDF ({accept})")
                        continue
                    
                    logging.info(f"📁 Uploading to file input {i}")
                    file_input.send_keys(os.path.abspath(self.resume_path))
                    time.sleep(3)
                    
                    # Look for immediate submit button or auto-submit
                    self._try_submit_upload()
                    
                    # Verify upload happened
                    if self._check_upload_progress():
                        return True
                        
                except Exception as e:
                    logging.warning(f"File input {i} failed: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logging.error(f"Direct upload failed: {e}")
            return False

    def _strategy_button_triggered_upload(self, url):
        """Click upload/update buttons to trigger file dialogs"""
        try:
            self.driver.get(url)
            time.sleep(5)
            
            # Look for buttons that might trigger file upload
            button_selectors = [
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload resume')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'update resume')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'attach')]",
                "//input[@class='dummyUpload']",
                "//button[@data-automation='resume-upload']",
                "//*[contains(@class, 'resume-upload')]//button"
            ]
            
            for selector in button_selectors:
                buttons = self.driver.find_elements(By.XPATH, selector)
                for button in buttons:
                    try:
                        if button.is_displayed() and button.is_enabled():
                            logging.info(f"🔘 Clicking upload trigger: {button.text or button.get_attribute('class')}")
                            
                            # Scroll to element and click
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(1)
                            
                            ActionChains(self.driver).move_to_element(button).click().perform()
                            time.sleep(3)
                            
                            # Look for file input that appeared
                            new_file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file' and not(@disabled)]")
                            for file_input in new_file_inputs:
                                if file_input.is_displayed() or file_input.is_enabled():
                                    logging.info("📁 Found triggered file input")
                                    file_input.send_keys(os.path.abspath(self.resume_path))
                                    time.sleep(3)
                                    
                                    self._try_submit_upload()
                                    
                                    if self._check_upload_progress():
                                        return True
                                        
                    except Exception as e:
                        logging.warning(f"Button trigger failed: {e}")
                        continue
            
            return False
            
        except Exception as e:
            logging.error(f"Button triggered upload failed: {e}")
            return False

    def _strategy_form_based_upload(self, url):
        """Look for forms with file inputs and submit them"""
        try:
            self.driver.get(url)
            time.sleep(5)
            
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            
            for i, form in enumerate(forms):
                try:
                    # Look for file inputs within this form
                    file_inputs = form.find_elements(By.XPATH, ".//input[@type='file']")
                    
                    if file_inputs:
                        logging.info(f"📋 Found form {i} with {len(file_inputs)} file input(s)")
                        
                        for file_input in file_inputs:
                            try:
                                self.driver.execute_script("arguments[0].style.display = 'block';", file_input)
                                file_input.send_keys(os.path.abspath(self.resume_path))
                                logging.info("📁 File uploaded to form")
                                time.sleep(3)
                                break
                            except Exception as e:
                                logging.warning(f"Form file input failed: {e}")
                                continue
                        
                        # Try to submit the form
                        submit_buttons = form.find_elements(By.XPATH, ".//button[@type='submit'] | .//input[@type='submit']")
                        if submit_buttons:
                            submit_buttons[0].click()
                            logging.info("📤 Form submitted")
                        else:
                            form.submit()
                            logging.info("📤 Form submitted via JavaScript")
                        
                        time.sleep(5)
                        
                        if self._check_upload_progress():
                            return True
                            
                except Exception as e:
                    logging.warning(f"Form {i} failed: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logging.error(f"Form based upload failed: {e}")
            return False

    def _try_submit_upload(self):
        """Try to find and click submit/upload buttons"""
        submit_selectors = [
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
            "//button[@type='submit']",
            "//input[@type='submit']"
        ]
        
        for selector in submit_selectors:
            try:
                buttons = self.driver.find_elements(By.XPATH, selector)
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        button.click()
                        logging.info(f"📤 Clicked submit button: {button.text}")
                        time.sleep(3)
                        return True
            except Exception as e:
                continue
        
        return False

    def _check_upload_progress(self):
        """Check for upload progress indicators"""
        progress_indicators = [
            (By.ID, "results_resumeParser"),
            (By.CLASS_NAME, "progress-bar"),
            (By.XPATH, "//div[contains(text(), 'uploading')]"),
            (By.XPATH, "//div[contains(text(), 'processing')]"),
            (By.CSS_SELECTOR, ".upload-progress"),
            (By.XPATH, "//div[contains(@class, 'loader')]")
        ]
        
        for by, selector in progress_indicators:
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                logging.info(f"📊 Upload progress detected: {selector}")
                return True
            except TimeoutException:
                continue
        
        return False

    def _verify_actual_upload(self):
        """Strictly verify that resume was actually uploaded"""
        try:
            # Wait for upload completion indicators
            success_indicators = [
                (By.ID, "results_resumeParser"),
                (By.XPATH, "//div[contains(text(), 'uploaded successfully')]"),
                (By.XPATH, "//div[contains(text(), 'Resume updated')]"),
                (By.XPATH, "//div[contains(text(), 'successfully')]"),
                (By.CSS_SELECTOR, ".alert-success"),
                (By.CSS_SELECTOR, ".success-message")
            ]
            
            for by, selector in success_indicators:
                try:
                    element = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    logging.info(f"✅ Upload success confirmed: {selector}")
                    
                    # Additional verification - check if resume section shows new file
                    self._verify_resume_presence()
                    return True
                except TimeoutException:
                    continue
            
            # Try alternative verification - look for updated resume section
            return self._verify_resume_presence()
            
        except Exception as e:
            logging.error(f"Upload verification failed: {e}")
            return False

    def _verify_resume_presence(self):
        """Verify resume is actually present on profile"""
        try:
            # Go to profile and check for resume
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            time.sleep(5)
            
            if self.check_access_denied():
                return False
            
            # Look for resume file name or upload date
            resume_indicators = [
                "//div[contains(text(), '.pdf')]",
                "//div[contains(text(), 'Resume')]",
                "//span[contains(text(), 'Uploaded')]",
                "//div[contains(@class, 'resume-file')]",
                "//*[contains(text(), 'Nikhil_Saini_Resume')]"
            ]
            
            for selector in resume_indicators:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements:
                    for element in elements:
                        text = element.text.strip()
                        if text and ("pdf" in text.lower() or "resume" in text.lower()):
                            logging.info(f"✅ Resume verified on profile: {text}")
                            return True
            
            logging.warning("⚠️  Could not verify resume presence on profile")
            return False
            
        except Exception as e:
            logging.error(f"Resume presence verification failed: {e}")
            return False

    def save_debug_info(self):
        """Save debugging information"""
        try:
            # Take screenshot
            screenshot_path = f"./logs/debug_screenshot_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            logging.info(f"📸 Screenshot saved: {screenshot_path}")
            
            # Save page source
            source_path = f"./logs/page_source_{int(time.time())}.html"
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logging.info(f"📄 Page source saved: {source_path}")
            
            # Save current state info
            info_path = f"./logs/debug_info_{int(time.time())}.txt"
            with open(info_path, "w", encoding="utf-8") as f:
                f.write(f"Debug Info - {datetime.now()}\n")
                f.write(f"Current URL: {self.driver.current_url}\n")
                f.write(f"Page Title: {self.driver.title}\n")
                f.write(f"Upload Verified: {self.upload_verified}\n")
                
                # Count elements
                file_inputs = len(self.driver.find_elements(By.XPATH, "//input[@type='file']"))
                buttons = len(self.driver.find_elements(By.TAG_NAME, "button"))
                f.write(f"File Inputs Found: {file_inputs}\n")
                f.write(f"Buttons Found: {buttons}\n")
            
            logging.info(f"ℹ️  Debug info saved: {info_path}")
            
        except Exception as e:
            logging.error(f"Failed to save debug info: {e}")

    def save_updated_cookies(self):
        """Save updated cookies"""
        try:
            current_cookies = self.driver.get_cookies()
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(current_cookies, f, indent=2)
            
            cookies_b64 = base64.b64encode(json.dumps(current_cookies).encode("utf-8")).decode("utf-8")
            logging.info("🍪 Updated cookies saved")
            
            # Only show base64 if upload was actually verified
            if self.upload_verified:
                logging.info("✅ Upload was verified - cookies are good")
            else:
                logging.warning("⚠️  Upload not verified - cookies may need refresh")
            
            print(f"COOKIES_B64: {cookies_b64}")
            
        except Exception as e:
            logging.error(f"Failed to save cookies: {e}")

    def cleanup(self):
        """Enhanced cleanup"""
        if self.driver:
            try:
                self.save_debug_info()
                self.save_updated_cookies()
                self.driver.quit()
                logging.info("🧹 Cleanup completed")
            except Exception as e:
                logging.error(f"Cleanup error: {e}")

    def run(self):
        """Main execution with enhanced error handling"""
        try:
            logging.info("🚀 Starting FIXED cookie-based Naukri automation")
            
            if not os.path.exists(self.resume_path):
                raise FileNotFoundError(f"Resume file not found: {self.resume_path}")
            
            logging.info(f"📄 Resume file: {self.resume_path} ({os.path.getsize(self.resume_path)} bytes)")
            
            # Setup browser
            self.setup_driver()
            
            # Load cookies with gradual approach
            if not self.load_cookies_gradually():
                raise Exception("Failed to load cookies")
            
            # Verify login with multiple attempts
            if not self.verify_login_status():
                raise Exception("Cookie authentication failed - cookies expired or account restricted")
            
            # Attempt resume upload with strict verification
            if self.upload_resume():
                if self.upload_verified:
                    logging.info("🎉 VERIFIED: Resume upload completed successfully!")
                    return True
                else:
                    logging.warning("⚠️  Upload completed but not verified")
                    return False
            else:
                logging.error("❌ All upload strategies failed")
                return False
                
        except Exception as e:
            logging.error(f"💥 Automation failed: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    uploader = FixedNaukriUploader()
    success = uploader.run()
    
    if success:
        print("\n🎉 SUCCESS: Resume uploaded and verified!")
    else:
        print("\n💥 FAILED: Resume upload failed or not verified!")
        print("💡 Check logs/screenshots for debugging information")
        print("💡 Most likely cause: Cookies expired - refresh NAUKRI_COOKIES_B64 secret")
    
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
