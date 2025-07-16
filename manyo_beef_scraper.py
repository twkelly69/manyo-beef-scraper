#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import csv
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import pandas as pd

class ManyoBeefScraper:
    def __init__(self, headless=True):
        self.setup_driver(headless)
        self.restaurants = []
        
    def setup_driver(self, headless=True):
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-javascript')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # Additional options for cloud environments
        chrome_options.add_argument('--single-process')
        chrome_options.add_argument('--no-zygote')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        
        # Try to use system chrome first, fallback to webdriver-manager
        try:
            # Try system chrome path first
            service = Service('/usr/bin/google-chrome')
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except:
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                print(f"Error setting up Chrome driver: {e}")
                raise
        
        self.wait = WebDriverWait(self.driver, 15)
        
    def search_restaurants(self, search_query="万葉牛 焼肉 鳥取県"):
        """Search for Manyo Beef restaurants in Tottori"""
        try:
            self.driver.get("https://www.google.com/maps")
            time.sleep(2)
            
            # Find search box and enter query
            search_box = self.wait.until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            search_box.clear()
            search_box.send_keys(search_query)
            search_box.send_keys(Keys.RETURN)
            
            # Wait for results to load
            time.sleep(3)
            
            # Get restaurant list
            self.scroll_results()
            return self.extract_restaurant_links()
            
        except TimeoutException:
            print("Search timeout - please check your internet connection")
            return []
        except Exception as e:
            print(f"Error during search: {e}")
            return []
    
    def scroll_results(self):
        """Scroll through search results to load more restaurants"""
        try:
            results_panel = self.driver.find_element(By.CSS_SELECTOR, '[role="main"]')
            last_height = self.driver.execute_script("return arguments[0].scrollHeight", results_panel)
            
            for _ in range(3):  # Scroll 3 times
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
                time.sleep(2)
                
                new_height = self.driver.execute_script("return arguments[0].scrollHeight", results_panel)
                if new_height == last_height:
                    break
                last_height = new_height
                
        except Exception as e:
            print(f"Error scrolling results: {e}")
    
    def extract_restaurant_links(self):
        """Extract restaurant links from search results"""
        restaurant_links = []
        try:
            # Find all restaurant result elements
            elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[data-value="Directions"]')
            
            for element in elements:
                try:
                    # Get the href attribute which contains the place URL
                    href = element.get_attribute('href')
                    if href and '/place/' in href:
                        restaurant_links.append(href)
                except Exception as e:
                    continue
                    
            # Alternative method - find by role
            if not restaurant_links:
                elements = self.driver.find_elements(By.CSS_SELECTOR, '[role="article"] a')
                for element in elements:
                    try:
                        href = element.get_attribute('href')
                        if href and '/place/' in href:
                            restaurant_links.append(href)
                    except Exception:
                        continue
            
            return list(set(restaurant_links))  # Remove duplicates
            
        except Exception as e:
            print(f"Error extracting restaurant links: {e}")
            return []
    
    def extract_restaurant_info(self, restaurant_url):
        """Extract detailed information from a restaurant page"""
        try:
            self.driver.get(restaurant_url)
            time.sleep(3)
            
            restaurant_info = {
                'name': '',
                'rating': '',
                'review_count': '',
                'address': '',
                'phone': '',
                'website': '',
                'hours': '',
                'reviews': []
            }
            
            # Extract name
            try:
                name_element = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[data-attrid="title"]'))
                )
                restaurant_info['name'] = name_element.text.strip()
            except:
                try:
                    name_element = self.driver.find_element(By.CSS_SELECTOR, 'h1')
                    restaurant_info['name'] = name_element.text.strip()
                except:
                    pass
            
            # Extract rating and review count
            try:
                rating_element = self.driver.find_element(By.CSS_SELECTOR, 'span.ceNzKf')
                restaurant_info['rating'] = rating_element.text.strip()
                
                review_count_element = self.driver.find_element(By.CSS_SELECTOR, 'span.RDApEe')
                restaurant_info['review_count'] = review_count_element.text.strip()
            except:
                pass
            
            # Extract address
            try:
                address_element = self.driver.find_element(By.CSS_SELECTOR, 'button[data-item-id="address"]')
                restaurant_info['address'] = address_element.text.strip()
            except:
                pass
            
            # Extract phone
            try:
                phone_element = self.driver.find_element(By.CSS_SELECTOR, 'button[data-item-id*="phone"]')
                restaurant_info['phone'] = phone_element.text.strip()
            except:
                pass
            
            # Extract website
            try:
                website_element = self.driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
                restaurant_info['website'] = website_element.get_attribute('href')
            except:
                pass
            
            # Extract reviews
            restaurant_info['reviews'] = self.extract_reviews()
            
            return restaurant_info
            
        except Exception as e:
            print(f"Error extracting restaurant info: {e}")
            return None
    
    def extract_reviews(self):
        """Extract review content from the restaurant page"""
        reviews = []
        try:
            # Try to find and click on reviews tab
            try:
                reviews_tab = self.driver.find_element(By.CSS_SELECTOR, 'button[data-tab-index="1"]')
                reviews_tab.click()
                time.sleep(2)
            except:
                pass
            
            # Scroll to load more reviews
            self.scroll_reviews()
            
            # Extract review elements
            review_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.jftiEf')
            
            for review_element in review_elements[:10]:  # Limit to first 10 reviews
                try:
                    review_data = {}
                    
                    # Extract reviewer name
                    try:
                        name_element = review_element.find_element(By.CSS_SELECTOR, 'div.d4r55')
                        review_data['reviewer_name'] = name_element.text.strip()
                    except:
                        review_data['reviewer_name'] = ''
                    
                    # Extract rating
                    try:
                        rating_element = review_element.find_element(By.CSS_SELECTOR, 'span.kvMYJc')
                        rating_stars = rating_element.get_attribute('aria-label')
                        review_data['rating'] = rating_stars
                    except:
                        review_data['rating'] = ''
                    
                    # Extract review text
                    try:
                        # Try to expand full review text
                        try:
                            more_button = review_element.find_element(By.CSS_SELECTOR, 'button.w8nwRe')
                            more_button.click()
                            time.sleep(1)
                        except:
                            pass
                        
                        text_element = review_element.find_element(By.CSS_SELECTOR, 'span.wiI7pd')
                        review_data['review_text'] = text_element.text.strip()
                    except:
                        review_data['review_text'] = ''
                    
                    # Extract date
                    try:
                        date_element = review_element.find_element(By.CSS_SELECTOR, 'span.rsqaWe')
                        review_data['date'] = date_element.text.strip()
                    except:
                        review_data['date'] = ''
                    
                    if review_data['review_text']:  # Only add if there's actual review text
                        reviews.append(review_data)
                        
                except Exception as e:
                    continue
            
            return reviews
            
        except Exception as e:
            print(f"Error extracting reviews: {e}")
            return []
    
    def scroll_reviews(self):
        """Scroll through reviews to load more"""
        try:
            # Find reviews container
            reviews_container = self.driver.find_element(By.CSS_SELECTOR, 'div[data-review-id]')
            
            for _ in range(2):  # Scroll 2 times
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", reviews_container)
                time.sleep(2)
                
        except Exception as e:
            pass
    
    def run_scraper(self):
        """Main method to run the scraper"""
        print("Starting Manyo Beef restaurant scraper...")
        
        # Search for restaurants
        restaurant_urls = self.search_restaurants()
        print(f"Found {len(restaurant_urls)} restaurants")
        
        if not restaurant_urls:
            print("No restaurants found. Please check your search query.")
            return
        
        # Extract information for each restaurant
        for i, url in enumerate(restaurant_urls, 1):
            print(f"Processing restaurant {i}/{len(restaurant_urls)}")
            
            restaurant_info = self.extract_restaurant_info(url)
            if restaurant_info:
                self.restaurants.append(restaurant_info)
                print(f"  - {restaurant_info['name']} (Rating: {restaurant_info['rating']})")
            
            time.sleep(2)  # Be respectful to the server
        
        print(f"\nCompleted scraping. Found {len(self.restaurants)} restaurants with data.")
        
        # Save data
        self.save_data()
        
    def save_data(self):
        """Save extracted data to JSON and CSV files"""
        if not self.restaurants:
            print("No data to save.")
            return
        
        # Save to JSON
        with open('manyo_beef_restaurants.json', 'w', encoding='utf-8') as f:
            json.dump(self.restaurants, f, ensure_ascii=False, indent=2)
        
        # Prepare data for CSV
        csv_data = []
        for restaurant in self.restaurants:
            base_data = {
                'name': restaurant['name'],
                'rating': restaurant['rating'],
                'review_count': restaurant['review_count'],
                'address': restaurant['address'],
                'phone': restaurant['phone'],
                'website': restaurant['website'],
                'hours': restaurant['hours']
            }
            
            if restaurant['reviews']:
                for review in restaurant['reviews']:
                    row_data = base_data.copy()
                    row_data.update({
                        'reviewer_name': review['reviewer_name'],
                        'review_rating': review['rating'],
                        'review_text': review['review_text'],
                        'review_date': review['date']
                    })
                    csv_data.append(row_data)
            else:
                csv_data.append(base_data)
        
        # Save to CSV
        if csv_data:
            df = pd.DataFrame(csv_data)
            df.to_csv('manyo_beef_restaurants.csv', index=False, encoding='utf-8')
        
        print("Data saved to manyo_beef_restaurants.json and manyo_beef_restaurants.csv")
    
    def close(self):
        """Close the browser"""
        self.driver.quit()

def main():
    scraper = ManyoBeefScraper(headless=False)  # Set to True for headless mode
    try:
        scraper.run_scraper()
    finally:
        scraper.close()

if __name__ == "__main__":
    main()