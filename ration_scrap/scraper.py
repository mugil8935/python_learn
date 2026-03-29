from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import csv
from bs4 import BeautifulSoup

# Initialize the Chrome driver
driver = webdriver.Chrome()

try:
    # Open the TNPDS website
    print("Opening https://www.tnpds.gov.in/home.xhtml...")
    driver.get("https://www.tnpds.gov.in/home.xhtml")
    time.sleep(3)  # Wait for page to load
    
    # Step 1: Click on "NFSA அறிக்கைகள்" link
    print("Looking for 'NFSA அறிக்கைகள்' link...")
    wait = WebDriverWait(driver, 10)
    nfsa_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "NFSA அறிக்கைகள்")))
    nfsa_link.click()
    time.sleep(3)
    
    # Step 2: Click on "சேலம்" link
    print("Looking for 'சேலம்' link...")
    salem_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "சேலம்")))
    salem_link.click()
    time.sleep(3)
    
    # Step 3: Click on "attur ஆத்தூர் (வ)" link
    print("Looking for 'attur ஆத்தூர் (வ)' link...")
    attur_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "ஆத்தூர் (வ)")))
    attur_link.click()
    time.sleep(3)
    
    # Step 4: Click on "07BB006PN" link
    print("Looking for '07BB006PN' link...")
    pn_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "07BB006PN")))
    pn_link.click()
    time.sleep(3)
    
    # Step 5: Find all 12-digit number links
    print("Finding all 12-digit number links...")
    time.sleep(2)
    
    # Get all links on the page
    all_links = driver.find_elements(By.TAG_NAME, "a")
    twelve_digit_links = []
    
    for link in all_links:
        link_text = link.text.strip()
        # Match 12-digit numbers
        if re.match(r'^\d{12}$', link_text):
            twelve_digit_links.append(link_text)
    
    print(f"Found {len(twelve_digit_links)} links with 12-digit numbers: {twelve_digit_links}")
    
    # Loop through each 12-digit link and scrape the table
    all_csv_data = []
    
    for i, link_number in enumerate(twelve_digit_links):
        print(f"\n[{i+1}/{len(twelve_digit_links)}] Processing link: {link_number}")
        try:
            # Find and click the link
            link_element = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, link_number)))
            link_element.click()
            time.sleep(3)
            
            # Get the HTML content
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find the searchedMemberdetailsdlg div and extract table data
            member_details_dlg = soup.find('div', {'id': re.compile('.*searchedMemberdetailsdlg.*')})
            
            if not member_details_dlg:
                # Try finding by class name
                member_details_dlg = soup.find('div', class_='searchedMemberdetailsdlg')
            
            if member_details_dlg:
                print(f"  Found searchedMemberdetailsdlg for {link_number}")
                # Extract table data from within the div
                table = member_details_dlg.find('table')
                if table:
                    rows = table.find_all('tr')
                    link_data = []
                    for row in rows:
                        cols = row.find_all(['td', 'th'])
                        row_data = [col.get_text(strip=True) for col in cols]
                        if row_data:
                            all_csv_data.append((link_number, row_data))
                            link_data.append(row_data)
                    
                    # Print extracted data for this link
                    print(f"  Data extracted for {link_number}:")
                    for row_data in link_data:
                        print(f"    {row_data}")
                else:
                    print(f"  No table found in searchedMemberdetailsdlg for {link_number}")
            else:
                print(f"  searchedMemberdetailsdlg not found for {link_number}")
            
            # Click the close link (ui-dialog-titlebar-close) within dialog
            print(f"  Clicking close button...")
            try:
                # Try to find and click the close button using XPath - look for the <a> tag with class ui-dialog-titlebar-close
                element = driver.find_element(By.XPATH, "//a[@aria-label='Close']")
                element.click();
                time.sleep(2)
                print(f"  Close button clicked successfully")
            except:
                try:
                    # Try clicking via JavaScript if normal click fails
                    print(f"  Trying JavaScript click...")
                    close_btn = driver.find_element(By.XPATH, "//a[@aria-label='Close']")
                    close_btn.click();
                    time.sleep(2)
                    print(f"  Close button clicked via JavaScript")
                except:
                    try:
                        # Use BeautifulSoup to verify and find alternative close method
                        page_source = driver.page_source
                        soup = BeautifulSoup(page_source, 'html.parser')
                        close_link = soup.find('a', class_='ui-dialog-titlebar-close')
                        if close_link:
                            print(f"  Close button found via BeautifulSoup but could not click")
                            # Try clicking by finding it again with more specific XPath
                            try:
                                close_btn = driver.find_element(By.XPATH, "//a[@aria-label='Close']")
                                close_btn.click();                                time.sleep(2)
                                print(f"  Close button clicked via alternative method")
                            except:
                                print(f"  Could not click close button, using back button as fallback")
                                driver.back()
                                time.sleep(2)
                        else:
                            print(f"  Close button not found in HTML, using back button")
                            driver.back()
                            time.sleep(2)
                    except Exception as inner_e:
                        print(f"  Error during close button fallback: {inner_e}")
                        driver.back()
                        time.sleep(2)
            
        except Exception as e:
            print(f"  Error processing {link_number}: {e}")
            import traceback
            traceback.print_exc()
            try:
                # Try to find and click close button on error
                close_btn = driver.find_element(By.XPATH, "//a[@class='ui-dialog-titlebar-close']")
                driver.execute_script("arguments[0].click();", close_btn)
                time.sleep(2)
            except:
                driver.back()
                time.sleep(2)
            continue
    
    # Print CSV data
    print("\n" + "="*80)
    print("SCRAPED TABLE DATA (CSV FORMAT)")
    print("="*80)
    
    # Write to CSV file
    with open('data.csv', 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        for link_id, row_data in all_csv_data:
            # Prepend link_id to each row
            full_row = [link_id] + row_data
            csv_writer.writerow(full_row)
            # Print to console
            print(','.join(map(str, full_row)))
    
    print("\n" + "="*80)
    print(f"Total rows scraped: {len(all_csv_data)}")
    print(f"Data saved to: data.csv")
    print("="*80)
    
except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
