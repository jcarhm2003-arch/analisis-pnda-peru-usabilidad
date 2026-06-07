from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from pnda.config import WAIT_SECONDS


def create_driver():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    wait = WebDriverWait(driver, WAIT_SECONDS)
    return driver, wait


def navigate_and_wait(driver, wait, url, selector, *, required=True):
    driver.get(url)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
    try:
        wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
        )
    except TimeoutException:
        if required:
            raise
    return driver.find_elements(By.CSS_SELECTOR, selector)


def safe_find_text(parent, selector):
    try:
        return parent.find_element(By.CSS_SELECTOR, selector).text.strip()
    except Exception:
        return ""


def safe_find_attr(parent, selector, attr):
    try:
        value = parent.find_element(By.CSS_SELECTOR, selector).get_attribute(attr)
        return value.strip() if value else ""
    except Exception:
        return ""


def has_child_element(parent, selector):
    try:
        parent.find_element(By.CSS_SELECTOR, selector)
        return True
    except Exception:
        return False
