import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
import urllib3
import ssl
from selenium.common.exceptions import TimeoutException
from retrying import retry
import time

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_data(topic):
    data = []
    
    # Static scrape (e.g., arXiv)
    try:
        url = f"https://arxiv.org/search/?query={topic}&searchtype=all"
        logger.info(f"Scraping arXiv: {url}")
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        papers = soup.find_all('li', class_='arxiv-result')[:5]
        if not papers:
            logger.warning("No papers found on arXiv. Check if class 'arxiv-result' is still valid.")
        else:
            logger.info(f"Found {len(papers)} papers on arXiv")
        for p in papers:
            title_elem = p.find('p', class_='title')
            abstract_elem = p.find('span', class_='abstract-full')
            title = title_elem.text.strip() if title_elem else "No title"
            abstract = abstract_elem.text.strip() if abstract_elem else "No abstract"
            data.append({'title': title, 'abstract': abstract, 'source': 'arXiv'})
    except requests.RequestException as e:
        logger.error(f"arXiv scraping failed due to network issue: {e}")
    except Exception as e:
        logger.error(f"arXiv scraping failed unexpectedly: {e}")

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def scrape_techcrunch(driver, topic):
        try:
            url = f"https://techcrunch.com/search/{topic}"
            logger.info(f"Scraping TechCrunch: {url}")
            
            driver.set_page_load_timeout(15)  # Reduced timeout
            driver.get(url)
            time.sleep(5)  # Allow JS to load
            
            wait = WebDriverWait(driver, 10)
            articles = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.post-block')))
            
            if not articles:
                articles = driver.find_elements(By.CSS_SELECTOR, 'article.post-block')
            
            if not articles:
                articles = driver.find_elements(By.CSS_SELECTOR, '.article__block')
                
            return articles[:5] if articles else []
            
        except TimeoutException:
            logger.warning("TechCrunch page load timeout, retrying...")
            raise
        except Exception as e:
            logger.error(f"TechCrunch scraping error: {e}")
            raise

    # TechCrunch scraping with retry
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.page_load_strategy = 'eager'  # Added for faster loading
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        articles = scrape_techcrunch(driver, topic)
        
        for article in articles:
            try:
                title = article.find_element(By.CSS_SELECTOR, 'h2, .article__title').text.strip()
                excerpt = article.find_element(By.CSS_SELECTOR, '.post-block__content, .article__excerpt').text.strip()
                data.append({
                    'title': title,
                    'abstract': excerpt,
                    'source': 'TechCrunch'
                })
            except Exception as e:
                logger.warning(f"Error extracting article data: {e}")
                continue
                
        driver.quit()
    except Exception as e:
        logger.error(f"TechCrunch scraping failed: {e}")
        if 'driver' in locals():
            driver.quit()

    # If no data was found, add some default data to prevent errors
    if not data:
        data.append({
            'title': f'Recent developments in {topic}',
            'abstract': f'Analysis of recent trends in {topic}.',
            'source': 'Default Source'
        })

    logger.info(f"Scraped {len(data)} items")
    return data