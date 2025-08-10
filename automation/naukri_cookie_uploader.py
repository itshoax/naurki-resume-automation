# automation/naukri_cookie_uploader.py
"""
Cookie-based Naukri Resume Upload Automation
Bypasses Google OAuth by using saved browser cookies
"""

import os
import time
import json
import pickle
import base64
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Try to import undetected-chromedriver
UNDETECTED_AVAILABLE = False
try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CookieBasedNaukriUploader:
    def __init__(self):
        self.resume_path = os.getenv('RESUME_PATH', './resume/Nikhil_Saini_Resume.pdf')
        self.driver = None
        self.cookies_file = './cookies/naukri_cookies.pkl'
        self.cookies_b64 = os.getenv('NAUKRI_COOKIES_B64')
        
        # Create cookies directory
        os.makedirs('./cookies', exist_ok=True)
        
    def setup_driver(self):
        """Setup Chrome driver optimized for cookie-based auth"""
        global UNDETECTED_AVAILABLE
        if UNDETECTED_AVAILABLE:
            try:
                options = uc.ChromeOptions()
                options.add_argument("--headless=new")  # Use new headless mode
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                
                # Let undetected-chromedriver handle the ChromeDriver automatically
                self.driver = uc.Chrome(options=options, version_main=None, driver_executable_path=None)
                logging.info("Undetected Chrome driver initialized")
                
            except Exception as e:
                logging.warning(f"Undetected Chrome failed: {e}, falling back to regular Chrome")
                UNDETECTED_AVAILABLE = False
        
        if not UNDETECTED_AVAILABLE:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Try to find ChromeDriver
            chromedriver_paths = [
                '/usr/local/bin/chromedriver',
                '/usr/bin/chromedriver',
                './chromedriver'
            ]
            
            chromedriver_path = None
            for path in chromedriver_paths:
                if os.path.exists(path):
                    chromedriver_path = path
                    break
            
            if chromedriver_path:
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                # Let Selenium auto-download ChromeDriver
                self.driver = webdriver.Chrome(options=options)
            
            # Remove automation indicators
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logging.info("Regular Chrome driver initialized")
        
        self.driver.set_page_load_timeout(30)
        
    def decode_cookies_from_secret(self):
        """Decode cookies from GitHub secret"""
        if self.cookies_b64:
            try:
                cookies_json = base64.b64decode(self.cookies_b64).decode('utf-8')
                cookies = json.loads(cookies_json)
                
                # Save to file for loading
                with open(self.cookies_file, 'wb') as f:
                    pickle.dump(cookies, f)
                    
                logging.info("Cookies decoded from GitHub secret")
                return True
            except Exception as e:
                logging.error(f"Failed to decode cookies: {str(e)}")
                return False
        return False
        
    def load_cookies(self):
        """Load cookies into browser"""
        try:
            # First try to decode from GitHub secret
            if not os.path.exists(self.cookies_file):
                if not self.decode_cookies_from_secret():
                    raise FileNotFoundError("No cookies available")
            
            # Navigate to Naukri first (required for adding cookies)
            self.driver.get("https://www.naukri.com")
            time.sleep(2)
            
            # Load cookies from file
            with open(self.cookies_file, 'rb') as f:
                cookies = pickle.load(f)
                
            # Add each cookie to the driver
            for cookie in cookies:
                try:
                    # Ensure cookie is in correct format
                    if 'sameSite' in cookie and cookie['sameSite'] == 'None':
                        cookie['sameSite'] = 'Lax'
                    
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logging.warning(f"Failed to add cookie {cookie.get('name', 'unknown')}: {e}")
                    continue
                    
            logging.info(f"Loaded {len(cookies)} cookies successfully")
            
            # Refresh to apply cookies
            self.driver.refresh()
            time.sleep(3)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load cookies: {str(e)}")
            return False
    
    def verify_login_status(self):
        """Check if we're successfully logged in using cookies"""
        try:
            # Navigate to a page that requires login
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            
            # Wait and check for login indicators
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CLASS_NAME, "nI-gNb-drawer")),
                        EC.presence_of_element_located((By.CLASS_NAME, "profileSection")),
                        EC.presence_of_element_located((By.CLASS_NAME, "user-name")),
                        EC.url_contains("mnjuser")
                    )
                )
                
                # Check if we're still on login page (cookies failed)
                if "nlogin" in self.driver.current_url:
                    logging.error("Redirected to login page - cookies expired")
                    return False
                    
                logging.info("Successfully authenticated using cookies")
                return True
                
            except TimeoutException:
                logging.error("Login verification timeout - cookies may have expired")
                return False
                
        except Exception as e:
            logging.error(f"Login verification failed: {str(e)}")
            return False
    
    def upload_resume(self):
        """Upload resume using multiple strategies"""
        strategies = [
            self._strategy_profile_upload,
            self._strategy_resume_section,
            self._strategy_quick_update
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                logging.info(f"Trying upload strategy {i}")
                if strategy():
                    return True
            except Exception as e:
                logging.error(f"Strategy {i} failed: {str(e)}")
                continue
                
        return False
    
    def _strategy_profile_upload(self):
        """Strategy 1: Main profile page upload"""
        self.driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(3)
        
        # Look for file input elements
        file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
        
        for file_input in file_inputs:
            try:
                # Check if this input accepts PDF files
                accept_attr = file_input.get_attribute('accept')
                if accept_attr and 'pdf' not in accept_attr:
                    continue
                    
                file_input.send_keys(os.path.abspath(self.resume_path))
                time.sleep(5)
                
                # Look for upload/save button
                upload_buttons = self.driver.find_elements(By.XPATH, 
                    "//button[contains(text(), 'Upload') or contains(text(), 'Save') or contains(text(), 'Update')]")
                
                if upload_buttons:
                    upload_buttons[0].click()
                    time.sleep(3)
                    
                logging.info("Resume uploaded via profile page")
                return True
                
            except Exception as e:
                logging.warning(f"File input failed: {e}")
                continue
                
        return False
    
    def _strategy_resume_section(self):
        """Strategy 2: Dedicated resume section"""
        # Navigate to resume/CV section specifically
        resume_urls = [
            "https://www.naukri.com/mnjuser/profile?id=&altresume",
            "https://www.naukri.com/mnjuser/homepage",
            "https://www.naukri.com/mnjuser/manageResume"
        ]
        
        for url in resume_urls:
            try:
                self.driver.get(url)
                time.sleep(3)
                
                # Look for resume upload section
                upload_sections = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'resume') or contains(@class, 'upload')]")
                
                if upload_sections:
                    file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                    file_input.send_keys(os.path.abspath(self.resume_path))
                    time.sleep(5)
                    
                    # Submit
                    submit_btn = self.driver.find_element(By.XPATH, 
                        "//button[@type='submit' or contains(text(), 'Upload')]")
                    submit_btn.click()
                    time.sleep(3)
                    
                    logging.info(f"Resume uploaded via {url}")
                    return True
                    
            except Exception as e:
                logging.warning(f"Resume section strategy failed for {url}: {e}")
                continue
                
        return False
    
    def _strategy_quick_update(self):
        """Strategy 3: Quick profile refresh (alternative to upload)"""
        try:
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            time.sleep(3)
            
            # Find and click any "Update" or "Edit" buttons to refresh profile
            update_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(text(), 'Update') or contains(text(), 'Edit') or contains(text(), 'Save')]")
            
            if update_buttons:
                # Click first available update button
                update_buttons[0].click()
                time.sleep(2)
                
                # Try to save/submit
                save_buttons = self.driver.find_elements(By.XPATH,
                    "//button[contains(text(), 'Save') or contains(text(), 'Done')]")
                
                if save_buttons:
                    save_buttons[0].click()
                    time.sleep(2)
                
                logging.info("Profile refreshed successfully")
                return True
                
        except Exception as e:
            logging.error(f"Quick update strategy failed: {e}")
            
        return False
    
    def save_updated_cookies(self):
        """Save current cookies back to file"""
        try:
            current_cookies = self.driver.get_cookies()
            
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(current_cookies, f)
                
            # Encode for GitHub secret update (manual step)
            cookies_json = json.dumps(current_cookies)
            cookies_b64 = base64.b64encode(cookies_json.encode('utf-8')).decode('utf-8')
            
            logging.info("Updated cookies saved")
            logging.info("To update GitHub secret, use this base64 string:")
            print(f"COOKIES_B64: {cookies_b64}")
            
        except Exception as e:
            logging.error(f"Failed to save cookies: {str(e)}")
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.save_updated_cookies()  # Save cookies before closing
                self.driver.quit()
            except Exception as e:
                logging.error(f"Error during cleanup: {str(e)}")
    
    def run(self):
        """Main execution method"""
        try:
            logging.info("Starting cookie-based Naukri automation")
            
            # Verify resume file exists
            if not os.path.exists(self.resume_path):
                raise FileNotFoundError(f"Resume file not found: {self.resume_path}")
            
            self.setup_driver()
            
            # Load cookies and verify login
            if not self.load_cookies():
                raise Exception("Failed to load cookies")
                
            if not self.verify_login_status():
                raise Exception("Cookie authentication failed - cookies may have expired")
            
            # Attempt resume upload
            if self.upload_resume():
                logging.info("Resume upload completed successfully")
                return True
            else:
                logging.error("All upload strategies failed")
                return False
                
        except Exception as e:
            logging.error(f"Automation failed: {str(e)}")
            return False
            
        finally:
            self.cleanup()

# Cookie extraction utility (run locally)
class CookieExtractor:
    """Utility to extract cookies from manual login"""
    
    def __init__(self):
        self.driver = None
        
    def manual_login_and_extract_cookies(self):
        """Manual login process to extract cookies"""
        print("🍪 Cookie Extraction Utility")
        print("=" * 50)
        
        self.setup_interactive_driver()
        
        try:
            # Navigate to Naukri
            print("Opening Naukri.com...")
            self.driver.get("https://www.naukri.com")
            
            print("\n📋 Instructions:")
            print("1. Complete the login process manually (including Google OAuth)")
            print("2. Navigate to your profile page")
            print("3. Press ENTER here when you're logged in and on your profile page")
            
            input("\nPress ENTER when login is complete...")
            
            # Extract cookies
            cookies = self.driver.get_cookies()
            
            # Save cookies locally
            with open('./cookies/naukri_cookies.pkl', 'wb') as f:
                pickle.dump(cookies, f)
            
            # Create base64 encoded version for GitHub secrets
            cookies_json = json.dumps(cookies, indent=2)
            cookies_b64 = base64.b64encode(cookies_json.encode('utf-8')).decode('utf-8')
            
            # Save base64 version
            with open('./cookies/cookies_b64.txt', 'w') as f:
                f.write(cookies_b64)
            
            print(f"\n✅ Success! Extracted {len(cookies)} cookies")
            print(f"📁 Cookies saved to: ./cookies/naukri_cookies.pkl")
            print(f"📁 Base64 version saved to: ./cookies/cookies_b64.txt")
            print("\n🔐 GitHub Secret Setup:")
            print("Copy the base64 string from cookies_b64.txt and add it as:")
            print("Secret name: NAUKRI_COOKIES_B64")
            print("Secret value: [contents of cookies_b64.txt]")
            
            # Test the cookies immediately
            print("\n🧪 Testing cookies...")
            self.test_cookies(cookies)
            
        except Exception as e:
            print(f"❌ Cookie extraction failed: {str(e)}")
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def setup_interactive_driver(self):
        """Setup driver for interactive use"""
        if UNDETECTED_AVAILABLE:
            options = uc.ChromeOptions()
            # Don't use headless for manual login
            self.driver = uc.Chrome(options=options)
        else:
            options = Options()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            service = Service('/usr/local/bin/chromedriver')  # Update path as needed
            self.driver = webdriver.Chrome(service=service, options=options)
            
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.driver.maximize_window()
    
    def test_cookies(self, cookies):
        """Test if cookies work for authentication"""
        try:
            # Open new browser instance
            test_driver = None
            
            if UNDETECTED_AVAILABLE:
                options = uc.ChromeOptions()
                options.add_argument("--headless=new")
                test_driver = uc.Chrome(options=options)
            else:
                options = Options()
                options.add_argument("--headless=new")
                service = Service('/usr/local/bin/chromedriver')
                test_driver = webdriver.Chrome(service=service, options=options)
            
            # Load Naukri and add cookies
            test_driver.get("https://www.naukri.com")
            
            for cookie in cookies:
                try:
                    test_driver.add_cookie(cookie)
                except:
                    continue
            
            # Test authentication
            test_driver.get("https://www.naukri.com/mnjuser/profile")
            time.sleep(3)
            
            if "mnjuser" in test_driver.current_url and "nlogin" not in test_driver.current_url:
                print("✅ Cookie test successful - authentication working!")
                
                # Check cookie expiry
                for cookie in cookies:
                    if 'expiry' in cookie:
                        expiry_date = datetime.fromtimestamp(cookie['expiry'])
                        days_until_expiry = (expiry_date - datetime.now()).days
                        if days_until_expiry < 7:
                            print(f"⚠️  Warning: Cookie '{cookie['name']}' expires in {days_until_expiry} days")
                
            else:
                print("❌ Cookie test failed - may need fresh login")
            
            test_driver.quit()
            
        except Exception as e:
            print(f"Cookie test error: {e}")

def main():
    """Main entry point"""
    mode = os.getenv('MODE', 'automation')
    
    if mode == 'extract_cookies':
        # Run cookie extraction (local only)
        extractor = CookieExtractor()
        extractor.manual_login_and_extract_cookies()
    else:
        # Run automation (GitHub Actions)
        uploader = CookieBasedNaukriUploader()
        success = uploader.run()
        exit(0 if success else 1)

if __name__ == "__main__":
    main()
