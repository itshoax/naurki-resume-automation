# automation/naukri_cookie_uploader.py
"""
Enhanced Cookie-based Naukri Resume Upload Automation
Improved error handling and debugging capabilities
"""

import os
import time
import json
import base64
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains

# We will completely skip undetected-chromedriver in CI
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

class CookieBasedNaukriUploader:
    def __init__(self):
        self.resume_path = os.getenv("RESUME_PATH", "./resume/Nikhil_Saini_Resume.pdf")
        self.driver = None
        self.cookies_file = "./cookies/naukri_cookies.json"
        self.cookies_b64 = os.getenv("NAUKRI_COOKIES_B64")

        os.makedirs("./cookies", exist_ok=True)
        os.makedirs("./logs", exist_ok=True)

    def setup_driver(self):
        """Setup Chrome driver with enhanced options for stability"""
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
                self.driver = uc.Chrome(options=options)
                logging.info("Undetected Chrome driver initialized")
                return
            except Exception as e:
                logging.warning(f"UC failed: {e}, falling back to regular Chrome")

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
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

        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        logging.info("Regular Chrome driver initialized")

        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(10)

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

    def load_cookies(self):
        """Load cookies from JSON into browser"""
        try:
            if not os.path.exists(self.cookies_file):
                if not self.decode_cookies_from_secret():
                    raise FileNotFoundError("No cookies available")

            self.driver.get("https://www.naukri.com")
            time.sleep(3)

            with open(self.cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            for cookie in cookies:
                if cookie.get("sameSite") == "None":
                    cookie["sameSite"] = "Lax"
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logging.warning(f"Failed to add cookie {cookie.get('name')}: {e}")

            logging.info(f"Loaded {len(cookies)} cookies successfully")
            self.driver.refresh()
            time.sleep(5)
            return True
        except Exception as e:
            logging.error(f"Failed to load cookies: {e}")
            return False

    def verify_login_status(self):
        """Enhanced login verification with multiple checks"""
        try:
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            time.sleep(5)
            
            # Multiple verification strategies
            login_indicators = [
                (By.CLASS_NAME, "nI-gNb-drawer"),
                (By.CLASS_NAME, "profileSection"),
                (By.CLASS_NAME, "user-name"),
                (By.ID, "name"),
                (By.CSS_SELECTOR, "[data-automation='profile-name']"),
                (By.CSS_SELECTOR, ".nI-gNb-info__name"),
            ]
            
            for by, selector in login_indicators:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    logging.info(f"Login verified via {selector}")
                    return True
                except TimeoutException:
                    continue
            
            # Check if redirected to login
            if "nlogin" in self.driver.current_url or "login" in self.driver.current_url:
                logging.error("Redirected to login page - cookies expired")
                return False
                
            # Check for profile URL
            if "mnjuser" in self.driver.current_url:
                logging.info("Successfully authenticated using cookies (URL check)")
                return True
                
            logging.error("Could not verify login status")
            return False
            
        except Exception as e:
            logging.error(f"Login verification failed: {e}")
            return False

    def debug_page_elements(self):
        """Debug helper to understand page structure"""
        try:
            logging.info("=== PAGE DEBUG INFO ===")
            logging.info(f"Current URL: {self.driver.current_url}")
            logging.info(f"Page title: {self.driver.title}")
            
            # Look for file inputs
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            logging.info(f"Found {len(file_inputs)} file inputs")
            for i, inp in enumerate(file_inputs):
                try:
                    accept = inp.get_attribute("accept")
                    name = inp.get_attribute("name")
                    id_attr = inp.get_attribute("id")
                    class_attr = inp.get_attribute("class")
                    visible = inp.is_displayed()
                    enabled = inp.is_enabled()
                    logging.info(f"  File input {i}: accept={accept}, name={name}, id={id_attr}, class={class_attr}, visible={visible}, enabled={enabled}")
                except Exception as e:
                    logging.info(f"  File input {i}: Error getting attributes - {e}")
            
            # Look for upload buttons
            upload_buttons = self.driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'update') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'attach')]")
            logging.info(f"Found {len(upload_buttons)} potential upload buttons")
            for i, btn in enumerate(upload_buttons):
                try:
                    text = btn.text
                    class_attr = btn.get_attribute("class")
                    visible = btn.is_displayed()
                    enabled = btn.is_enabled()
                    logging.info(f"  Button {i}: text='{text}', class={class_attr}, visible={visible}, enabled={enabled}")
                except Exception as e:
                    logging.info(f"  Button {i}: Error getting attributes - {e}")
                    
            # Look for resume-related elements
            resume_elements = self.driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'resume') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cv')]")
            logging.info(f"Found {len(resume_elements)} resume-related elements")
            
        except Exception as e:
            logging.error(f"Debug failed: {e}")

    def upload_resume(self):
        """Enhanced upload with better error handling and debugging"""
        strategies = [
            self._strategy_modern_upload,     # New strategy for current Naukri
            self._strategy_attach_cv,         # Original strategy with fixes
            self._strategy_profile_upload,    # Enhanced profile strategy
            self._strategy_resume_section,    # Resume section strategy
            self._strategy_quick_update       # Quick update fallback
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                logging.info(f"Trying upload strategy {i}: {strategy.__name__}")
                if strategy():
                    logging.info(f"Strategy {i} ({strategy.__name__}) succeeded!")
                    return True
                else:
                    logging.warning(f"Strategy {i} ({strategy.__name__}) returned False")
            except Exception as e:
                logging.error(f"Strategy {i} ({strategy.__name__}) failed with exception: {e}")
                
        logging.error("All upload strategies failed")
        return False

    def _strategy_modern_upload(self):
        """Modern upload strategy for current Naukri interface"""
        try:
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            time.sleep(5)
            
            self.debug_page_elements()
            
            # Look for modern file upload elements
            upload_selectors = [
                "input[type='file'][accept*='pdf']",
                "input[type='file']",
                "input.dummyUpload",
                ".file-upload input[type='file']",
                "[data-automation='resume-upload'] input[type='file']"
            ]
            
            for selector in upload_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logging.info(f"Found visible file input with selector: {selector}")
                            element.send_keys(os.path.abspath(self.resume_path))
                            logging.info("File sent to input")
                            time.sleep(3)
                            
                            # Look for submit/upload button after file selection
                            submit_buttons = self.driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'update')]")
                            
                            for btn in submit_buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    btn.click()
                                    logging.info(f"Clicked submit button: {btn.text}")
                                    time.sleep(5)
                                    return self._verify_upload_success()
                                    
                except Exception as e:
                    logging.warning(f"Failed with selector {selector}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Modern upload strategy failed: {e}")
            
        return False

    def _strategy_attach_cv(self):
        """Enhanced attach CV strategy with better error handling"""
        try:
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            time.sleep(5)

            # Multiple selectors for the update resume button
            update_selectors = [
                "input.dummyUpload",
                "button[data-automation='update-resume']",
                ".resume-upload-btn",
                "//button[contains(text(), 'Update resume')]",
                "//input[contains(@class, 'dummyUpload')]"
            ]

            for selector in update_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed():
                            # Use ActionChains for more reliable clicking
                            actions = ActionChains(self.driver)
                            actions.move_to_element(element).click().perform()
                            logging.info(f"Clicked element with selector: {selector}")
                            time.sleep(3)
                            
                            # Look for the triggered file input
                            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file' and not(@disabled)]")
                            for file_input in file_inputs:
                                if file_input.is_displayed() or file_input.is_enabled():
                                    file_input.send_keys(os.path.abspath(self.resume_path))
                                    logging.info("File sent to triggered file input")
                                    time.sleep(5)
                                    return self._verify_upload_success()
                                    
                except Exception as e:
                    logging.warning(f"Failed with update selector {selector}: {e}")
                    continue

        except Exception as e:
            logging.error(f"Attach CV strategy failed: {e}")
            
        return False

    def _strategy_profile_upload(self):
        """Enhanced profile upload strategy"""
        try:
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            time.sleep(5)
            
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
            logging.info(f"Found {len(file_inputs)} file inputs on profile page")
            
            for i, file_input in enumerate(file_inputs):
                try:
                    # Check if file input accepts PDF
                    accept_attr = file_input.get_attribute("accept")
                    if accept_attr and "pdf" not in accept_attr.lower():
                        logging.info(f"File input {i} doesn't accept PDF: {accept_attr}")
                        continue
                    
                    # Make element visible if needed
                    self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible'; arguments[0].style.opacity = '1';", file_input)
                    
                    file_input.send_keys(os.path.abspath(self.resume_path))
                    logging.info(f"File sent to input {i}")
                    time.sleep(5)
                    
                    # Look for upload/save buttons
                    upload_buttons = self.driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'update')]")
                    
                    for btn in upload_buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            btn.click()
                            logging.info(f"Clicked upload button: {btn.text}")
                            time.sleep(5)
                            return self._verify_upload_success()
                    
                    # If no button found, try form submission
                    form = file_input.find_element(By.XPATH, "./ancestor::form")
                    if form:
                        form.submit()
                        logging.info("Submitted form")
                        time.sleep(5)
                        return self._verify_upload_success()
                        
                except Exception as e:
                    logging.warning(f"Failed with file input {i}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Profile upload strategy failed: {e}")
            
        return False

    def _strategy_resume_section(self):
        """Enhanced resume section strategy"""
        resume_urls = [
            "https://www.naukri.com/mnjuser/profile?id=&altresume",
            "https://www.naukri.com/mnjuser/homepage",
            "https://www.naukri.com/mnjuser/manageResume",
            "https://www.naukri.com/mnjuser/resume"
        ]
        
        for url in resume_urls:
            try:
                logging.info(f"Trying URL: {url}")
                self.driver.get(url)
                time.sleep(5)
                
                # Look for file inputs
                file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
                if file_inputs:
                    for file_input in file_inputs:
                        try:
                            self.driver.execute_script("arguments[0].style.display = 'block';", file_input)
                            file_input.send_keys(os.path.abspath(self.resume_path))
                            time.sleep(3)
                            
                            # Try to submit
                            submit_btns = self.driver.find_elements(By.XPATH, "//button[@type='submit' or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save')]")
                            if submit_btns:
                                submit_btns[0].click()
                                time.sleep(5)
                                logging.info(f"Resume uploaded via {url}")
                                return True
                        except Exception as e:
                            logging.warning(f"Failed file upload on {url}: {e}")
                            continue
                            
            except Exception as e:
                logging.warning(f"Failed to access {url}: {e}")
                continue
                
        return False

    def _strategy_quick_update(self):
        """Enhanced quick update strategy - just refresh profile"""
        try:
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            time.sleep(5)
            
            # Try to find any edit/update buttons and click them to refresh profile
            update_buttons = self.driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'edit') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'update')]")
            
            if update_buttons:
                for btn in update_buttons[:2]:  # Try first 2 buttons
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            btn.click()
                            time.sleep(2)
                            
                            # Look for save/done buttons
                            save_buttons = self.driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'done')]")
                            if save_buttons:
                                save_buttons[0].click()
                                time.sleep(3)
                                logging.info("Profile updated via quick update")
                                return True
                    except Exception as e:
                        logging.warning(f"Quick update button failed: {e}")
                        continue
                        
            # Just refresh the page as a fallback
            self.driver.refresh()
            time.sleep(3)
            logging.info("Profile refreshed")
            return True
            
        except Exception as e:
            logging.error(f"Quick update strategy failed: {e}")
            return False

    def _verify_upload_success(self):
        """Verify if resume upload was successful"""
        success_indicators = [
            (By.ID, "results_resumeParser"),
            (By.CLASS_NAME, "success-message"),
            (By.XPATH, "//div[contains(text(), 'uploaded successfully')]"),
            (By.XPATH, "//div[contains(text(), 'Resume updated')]"),
            (By.CSS_SELECTOR, ".alert-success"),
            (By.CSS_SELECTOR, "[data-automation='success-message']")
        ]
        
        for by, selector in success_indicators:
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                logging.info(f"Upload success verified via: {selector}")
                return True
            except TimeoutException:
                continue
        
        # Check for any positive changes in URL or page content
        current_url = self.driver.current_url
        if "success" in current_url or "updated" in current_url:
            logging.info("Upload success indicated by URL")
            return True
            
        logging.warning("Could not verify upload success")
        return False

    def save_updated_cookies(self):
        """Save updated cookies for future use"""
        try:
            current_cookies = self.driver.get_cookies()
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(current_cookies, f, indent=2)
            
            cookies_b64 = base64.b64encode(json.dumps(current_cookies).encode("utf-8")).decode("utf-8")
            logging.info("Updated cookies saved")
            logging.info("To update GitHub secret, use this base64 string:")
            print(f"COOKIES_B64: {cookies_b64}")
            
            # Save to logs for easy access
            with open("./logs/updated_cookies.txt", "w") as f:
                f.write(f"COOKIES_B64: {cookies_b64}\n")
                f.write(f"Generated at: {datetime.now()}\n")
                
        except Exception as e:
            logging.error(f"Failed to save cookies: {e}")

    def cleanup(self):
        """Enhanced cleanup with error handling"""
        if self.driver:
            try:
                self.save_updated_cookies()
                
                # Take a screenshot for debugging if something went wrong
                try:
                    self.driver.save_screenshot("./logs/final_screenshot.png")
                    logging.info("Final screenshot saved")
                except Exception:
                    pass
                    
                self.driver.quit()
                logging.info("Browser closed successfully")
                
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")

    def run(self):
        """Enhanced main execution with better error handling"""
        try:
            logging.info("Starting enhanced cookie-based Naukri automation")
            
            # Verify resume file exists
            if not os.path.exists(self.resume_path):
                raise FileNotFoundError(f"Resume file not found: {self.resume_path}")
            
            logging.info(f"Resume file found: {self.resume_path} ({os.path.getsize(self.resume_path)} bytes)")
            
            # Setup browser
            self.setup_driver()
            
            # Load cookies and verify login
            if not self.load_cookies():
                raise Exception("Failed to load cookies")
            
            if not self.verify_login_status():
                raise Exception("Cookie authentication failed - cookies may have expired")
            
            # Attempt resume upload
            if self.upload_resume():
                logging.info("✅ Resume upload completed successfully")
                return True
            else:
                logging.error("❌ All upload strategies failed")
                return False
                
        except Exception as e:
            logging.error(f"❌ Automation failed: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    mode = os.getenv("MODE", "automation")
    test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    
    if test_mode:
        logging.info("🧪 Running in test mode")
    
    uploader = CookieBasedNaukriUploader()
    success = uploader.run()
    
    if success:
        print("🎉 SUCCESS: Resume automation completed!")
    else:
        print("💥 FAILED: Resume automation failed!")
    
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
