import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

def get_max_page(driver):
    try:
        # Find all page numbers
        page_links = driver.find_elements(By.CSS_SELECTOR, "ul.pageNaviButtons li a")
        # Get the last numbered page (excluding "Next" button)
        max_page = max([int(link.get_attribute('title')) for link in page_links 
                       if link.get_attribute('title').isdigit()])
        return max_page
    except Exception as e:
        print(f"Error getting max page: {e}")
        return 1

def scrape_sahibinden():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    
    driver = uc.Chrome(version_main=118, options=options)
    all_results = []
    
    try:
        # First load the initial page
        print("Starting browser...")
        driver.get('https://www.sahibinden.com/elektro-gitar?query_text_mf=elektro+gitar')
        time.sleep(10)
        
        # Get total number of pages
        max_page = get_max_page(driver)
        print(f"Total pages to scrape: {max_page}")

        # Loop through all pages
        for page in range(max_page):
            offset = page * 20
            url = f'https://www.sahibinden.com/elektro-gitar?pagingOffset={offset}&query_text_mf=elektro+gitar'
            
            print(f"Scraping page {page + 1}/{max_page}")
            driver.get(url)
            time.sleep(5)  # Wait between pages to avoid detection
            
            wait = WebDriverWait(driver, 20)
            listings = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'searchResultsItem')))
            
            print(f"Found {len(listings)} listings on page {page + 1}")
            
            for listing in listings:
                try:
                    title = listing.find_element(By.CLASS_NAME, 'classifiedTitle').text
                    price = listing.find_element(By.CLASS_NAME, 'searchResultsPriceValue').text
                    location = listing.find_element(By.CLASS_NAME, 'searchResultsLocationValue').text
                    
                    all_results.append({
                        'title': title,
                        'price': price,
                        'location': location,
                        'page': page + 1
                    })
                    print(f"Scraped: {title}")
                    
                except Exception as e:
                    print(f"Error scraping listing: {e}")
                    continue
            
            # Save progress after each page
            df = pd.DataFrame(all_results)
            df.to_csv('guitars_all_pages.csv', index=False)
            print(f"Progress saved - {len(all_results)} total listings scraped")
            
            # Add a random delay between pages
            time.sleep(3)
        
        print("Scraping completed!")
        return df
        
    except Exception as e:
        print(f"Major error: {e}")
        # Save whatever we've got so far
        if all_results:
            pd.DataFrame(all_results).to_csv('guitars_partial.csv', index=False)
            print("Partial results saved to guitars_partial.csv")
    finally:
        driver.quit()

if __name__ == "__main__":
    print("Starting scraper...")
    scrape_sahibinden()