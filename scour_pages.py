import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import os
from typing import List, Dict, Optional
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

class StealthManager:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        ]
        
    def get_stealth_options(self):
        """Enhanced stealth options with fingerprint randomization"""
        options = uc.ChromeOptions()
        
        # Basic security options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Random window size
        width = random.randint(1050, 1200)
        height = random.randint(800, 1000)
        options.add_argument(f'--window-size={width},{height}')
        
        # Enhanced privacy options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-webgl')
        
        # Random user agent
        options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
        
        return options

    def get_dynamic_delay(self):
        """Generate human-like delays"""
        base_delay = random.uniform(2, 4)
        noise = random.gauss(0, 0.5)
        return max(1, base_delay + noise)

class Scraper:
    def __init__(self, output_file: str = 'guitar_listings.csv'):
        self.output_file = output_file
        self.stealth_manager = StealthManager()

    def extract_dynamic_content(self, driver):
        """Extract content that uses CSS pseudo-elements"""
        phone_number = ""
        seller_name = ""
        
        try:
            # Phone extraction
            phone_script = """
                return Array.from(document.querySelectorAll('.pretty-phone-part span'))
                    .map(el => window.getComputedStyle(el, ':before').content)
                    .join('')
                    .replace(/['"]/g, '');
            """
            phone_number = driver.execute_script(phone_script)
            
            # Name extraction
            name_script = """
                const nameEl = document.querySelector('.username-info-area span');
                return nameEl ? window.getComputedStyle(nameEl, ':before').content.replace(/['"]/g, '') : '';
            """
            seller_name = driver.execute_script(name_script)
            
        except Exception as e:
            logging.warning(f"Error extracting dynamic content: {str(e)}")
            
        return phone_number.strip(), seller_name.strip()

    def parse_listing(self, driver, url: str) -> dict:
        """Parse listing details"""
        try:
            # Wait for content
            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'classifiedDetailTitle')))
            
            # Get dynamic content
            phone_number, seller_name = self.extract_dynamic_content(driver)
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract listing details
            details = {}
            for item in soup.select('.classifiedInfoList li'):
                strong = item.find('strong')
                if strong:
                    label = ' '.join(strong.text.strip(':').split())
                    value = ' '.join(item.get_text(strip=True).replace(strong.text, '').split())
                    details[label] = value

            # Extract comments
            comments = []
            for item in soup.select('.type-question .comment-item, .type-answer .comment-item'):
                try:
                    author_elem = item.select_one('.name-surname')
                    text = ' '.join(item.select_one('.comment-text').text.split()) if item.select_one('.comment-text') else ''
                    timestamp = ' '.join(item.select_one('.comment-date').text.split()) if item.select_one('.comment-date') else ''
                    
                    if author_elem:
                        author_class = author_elem.get('class', [])[-1]
                        author = driver.execute_script(
                            f'return window.getComputedStyle(document.querySelector(".{author_class}"), ":before").content;'
                        ).strip('"\'') if author_class else ''
                        
                        if author and text:
                            comments.append({
                                'author': author,
                                'text': text,
                                'timestamp': timestamp
                            })
                except Exception as e:
                    logging.warning(f"Error parsing comment: {str(e)}")
                    continue

            # Build listing data
            listing_data = {
                'title': ' '.join(soup.select_one('.classifiedDetailTitle h1').text.split()),
                'price': ' '.join(soup.select_one('.classifiedInfo h3 span.classified-price-wrapper').text.split()),
                'listing_id': details.get('İlan No', ''),
                'listing_date': details.get('İlan Tarihi', ''),
                'brand': details.get('Marka', ''),
                'playing_style': details.get('Çalma Biçimi', ''),
                'pickup_config': details.get('Manyetik Dizilimi', ''),
                'pickguard': details.get('Zırhı (Pickguard)', ''),
                'bridge_type': details.get('Köprü Türü', ''),
                'seller_type': details.get('Kimden', ''),
                'condition': details.get('Durumu', ''),
                'location': ' / '.join([' '.join(a.text.split()) for a in soup.select('.classifiedInfo h2 a')]),
                'seller_name': seller_name,
                'seller_since': ' '.join(soup.select_one('.userRegistrationDate').text.split()) if soup.select_one('.userRegistrationDate') else '',
                'phone': phone_number,
                'description': ' '.join(soup.select_one('#classifiedDescription').text.split()),
                'comments': comments,
                'url': url,
                'scraped_at': datetime.now().isoformat()
            }
            
            return listing_data
            
        except Exception as e:
            logging.error(f"Error parsing listing {url}: {str(e)}")
            return None

    def scrape_listings(self, urls: List[str]):
        """Main scraping function - sequential version"""
        # Check for existing results
        processed_urls = set()
        if os.path.exists(self.output_file):
            try:
                existing_df = pd.read_csv(self.output_file, encoding='utf-8-sig')
                processed_urls.update(existing_df['url'].tolist())
            except Exception as e:
                logging.warning(f"Error reading existing file: {str(e)}")

        # Filter unprocessed URLs
        urls_to_process = [url for url in urls if url not in processed_urls]
        logging.info(f"Remaining URLs to process: {len(urls_to_process)}")

        try:
            options = self.stealth_manager.get_stealth_options()
            driver = uc.Chrome(version_main=118, options=options)
            
            # Initial warmup
            driver.get('https://www.sahibinden.com')
            time.sleep(self.stealth_manager.get_dynamic_delay())
            
            for i, url in enumerate(urls_to_process):
                try:
                    logging.info(f"Processing {i + 1}/{len(urls_to_process)}: {url}")
                    
                    # Load page with dynamic delay
                    driver.get(url)
                    time.sleep(self.stealth_manager.get_dynamic_delay())
                    
                    # Parse listing
                    listing = self.parse_listing(driver, url)
                    
                    if listing:
                        # Save to CSV
                        df = pd.DataFrame([listing])
                        df.to_csv(
                            self.output_file,
                            mode='a',
                            header=not os.path.exists(self.output_file),
                            index=False,
                            encoding='utf-8-sig'
                        )
                        logging.info(f"Saved: {listing['title']}")
                    
                    # Random delay between listings
                    time.sleep(self.stealth_manager.get_dynamic_delay())
                    
                except Exception as e:
                    logging.error(f"Error processing URL {url}: {str(e)}")
                    continue
                    
        except Exception as e:
            logging.error(f"Scraping error: {str(e)}")
            
        finally:
            if 'driver' in locals():
                try:
                    driver.quit()
                except:
                    pass

if __name__ == "__main__":
    try:
        urls_df = pd.read_csv('guitars_all_pages.csv')
        urls = urls_df['url'].tolist()
        
        scraper = Scraper('guitar_listings.csv')
        scraper.scrape_listings(urls)
        
    except Exception as e:
        logging.error(f"Main execution error: {str(e)}")