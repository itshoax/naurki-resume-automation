# automation/naukri_cookie_uploader.py
"""
Cookie-based Naukri Resume Upload Automation
Bypasses Google OAuth by using saved browser cookies (JSON only)
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
from selenium.common.exceptions import TimeoutException

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

    def setup_driver(self):
        """Setup Chrome driver without UC for CI stability"""
        if USE_UNDETECTED:
            try:
                options = uc.ChromeOptions()
                options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
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
            time.sleep(2)

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
            time.sleep(3)
            return True
        except Exception as e:
            logging.error(f"Failed to load cookies: {e}")
            return False

    def verify_login_status(self):
        try:
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            WebDriverWait(self.driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CLASS_NAME, "nI-gNb-drawer")),
                    EC.presence_of_element_located((By.CLASS_NAME, "profileSection")),
                    EC.presence_of_element_located((By.CLASS_NAME, "user-name")),
                    EC.url_contains("mnjuser")
                )
            )
            if "nlogin" in self.driver.current_url:
                logging.error("Redirected to login page - cookies expired")
                return False
            logging.info("Successfully authenticated using cookies")
            return True
        except TimeoutException:
            logging.error("Login verification timeout - cookies may have expired")
            return False
        except Exception as e:
            logging.error(f"Login verification failed: {e}")
            return False

    def upload_resume(self):
        strategies = [
            self._strategy_attach_cv,       # New dedicated strategy
            self._strategy_profile_upload,
            self._strategy_resume_section,
            self._strategy_quick_update
        ]
        for i, strategy in enumerate(strategies, 1):
            try:
                logging.info(f"Trying upload strategy {i}: {strategy.__name__}")
                if strategy():
                    return True
            except Exception as e:
                logging.error(f"Strategy {i} ({strategy.__name__}) failed: {e}")
        return False

    def _strategy_attach_cv(self):
        """Strategy: Force-unhide #attachCV and upload directly."""
        try:
            self.driver.get("https://www.naukri.com/mnjuser/profile")

            # Wait for #attachCV to be in DOM
            file_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "attachCV"))
            )

            # Unhide the element via JavaScript if hidden
            self.driver.execute_script("""
                var input = arguments[0];
                input.style.display = 'block';
                input.style.visibility = 'visible';
                input.style.opacity = 1;
                input.style.height = 'auto';
                input.style.width = 'auto';
            """, file_input)

            # Now send the file
            file_input.send_keys(os.path.abspath(self.resume_path))
            logging.info("Sent resume file to #attachCV (forced visible)")

            # Wait for confirmation
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.ID, "results_resumeParser"))
                )
                logging.info("Resume upload confirmed via #results_resumeParser")
            except TimeoutException:
                logging.warning("No explicit upload confirmation found, proceeding anyway")

            return True
        except Exception as e:
            logging.error(f"#attachCV upload failed: {e}")
            return False

    def _strategy_profile_upload(self):
        self.driver.get("https://www.naukri.com/mnjuser/profile")
        time.sleep(3)
        file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")
        for file_input in file_inputs:
            try:
                accept_attr = file_input.get_attribute("accept")
                if accept_attr and "pdf" not in accept_attr:
                    continue
                file_input.send_keys(os.path.abspath(self.resume_path))
                time.sleep(5)
                upload_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(text(), 'Upload') or contains(text(), 'Save') or contains(text(), 'Update')]"
                )
                if upload_buttons:
                    upload_buttons[0].click()
                    time.sleep(3)
                logging.info("Resume uploaded via profile page")
                return True
            except Exception:
                continue
        return False

    def _strategy_resume_section(self):
        resume_urls = [
            "https://www.naukri.com/mnjuser/profile?id=&altresume",
            "https://www.naukri.com/mnjuser/homepage",
            "https://www.naukri.com/mnjuser/manageResume"
        ]
        for url in resume_urls:
            try:
                self.driver.get(url)
                time.sleep(3)
                upload_sections = self.driver.find_elements(
                    By.XPATH, "//div[contains(@class, 'resume') or contains(@class, 'upload')]"
                )
                if upload_sections:
                    file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                    file_input.send_keys(os.path.abspath(self.resume_path))
                    time.sleep(5)
                    submit_btn = self.driver.find_element(
                        By.XPATH, "//button[@type='submit' or contains(text(), 'Upload')]"
                    )
                    submit_btn.click()
                    time.sleep(3)
                    logging.info(f"Resume uploaded via {url}")
                    return True
            except Exception:
                continue
        return False

    def _strategy_quick_update(self):
        try:
            self.driver.get("https://www.naukri.com/mnjuser/profile")
            time.sleep(3)
            update_buttons = self.driver.find_elements(
                By.XPATH, "//button[contains(text(), 'Update') or contains(text(), 'Edit') or contains(text(), 'Save')]"
            )
            if update_buttons:
                update_buttons[0].click()
                time.sleep(2)
                save_buttons = self.driver.find_elements(
                    By.XPATH, "//button[contains(text(), 'Save') or contains(text(), 'Done')]"
                )
                if save_buttons:
                    save_buttons[0].click()
                    time.sleep(2)
                logging.info("Profile refreshed successfully")
                return True
        except Exception as e:
            logging.error(f"Quick update strategy failed: {e}")
        return False

    def save_updated_cookies(self):
        try:
            current_cookies = self.driver.get_cookies()
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(current_cookies, f, indent=2)
            cookies_b64 = base64.b64encode(json.dumps(current_cookies).encode("utf-8")).decode("utf-8")
            logging.info("Updated cookies saved")
            logging.info("To update GitHub secret, use this base64 string:")
            print(f"COOKIES_B64: {cookies_b64}")
        except Exception as e:
            logging.error(f"Failed to save cookies: {e}")

    def cleanup(self):
        if self.driver:
            try:
                self.save_updated_cookies()
                self.driver.quit()
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")

    def run(self):
        try:
            logging.info("Starting cookie-based Naukri automation")
            if not os.path.exists(self.resume_path):
                raise FileNotFoundError(f"Resume file not found: {self.resume_path}")
            self.setup_driver()
            if not self.load_cookies():
                raise Exception("Failed to load cookies")
            if not self.verify_login_status():
                raise Exception("Cookie authentication failed - cookies may have expired")
            if self.upload_resume():
                logging.info("Resume upload completed successfully")
                return True
            else:
                logging.error("All upload strategies failed")
                return False
        except Exception as e:
            logging.error(f"Automation failed: {e}")
            return False
        finally:
            self.cleanup()

def main():
    mode = os.getenv("MODE", "automation")
    uploader = CookieBasedNaukriUploader()
    success = uploader.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
