from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Launch browser
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

driver.get("https://www.cricbuzz.com")

wait = WebDriverWait(driver, 20)

# ✅ Click Australia vs Oman match
match = wait.until(
    EC.element_to_be_clickable(
        (By.XPATH, "//a[contains(@title,'Oman vs Australia')]")
    )
)

match.click()

# optional wait to see result
import time
time.sleep(5)

driver.quit()