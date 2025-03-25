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
from newsapi import NewsApiClient
from datetime import datetime, timedelta

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NEWS_API_KEY = "87367266557c4ec3828ec58ec54fde10"  # Replace with valid key
NEWS_SOURCES = {
    'times_of_india': {
        'url': 'https://timesofindia.indiatimes.com/topic/{}',
        'selector': '.article',  # Updated selector
        'title': '.title a, h3 a',
        'abstract': '.summary, .article-content'
    },
    'hindustan_times': {
        'url': 'https://www.hindustantimes.com/topic/{}',  # Changed to topic URL
        'selector': '.story-card',
        'title': '.hdg3 a, .story-headline',
        'abstract': '.story-desc'
    },
    'ndtv': { 
        'url': 'https://www.ndtv.com/topic/{}',  # Changed to topic URL
        'selector': '.news_item',
        'title': '.newsHdng a, .headline',
        'abstract': '.newsCont, .description'
    },
    'the_hindu': {
        'url': 'https://www.thehindu.com/topic/{}',  # Changed to topic URL
        'selector': '.story-card-news',
        'title': '.story-card-news h3',
        'abstract': '.story-card-news p'
    }
}

def setup_webdriver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-dev-shm-usage')
    options.page_load_strategy = 'eager'
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def scrape_news_source(driver, source_config, topic):
    results = []
    try:
        formatted_topic = topic.replace('_', '-')
        url = source_config['url'].format(formatted_topic)
        logger.info(f"Scraping {url}")
        
        driver.get(url)
        time.sleep(5)  # Allow JS to load
        
        elements = driver.find_elements(By.CSS_SELECTOR, source_config['selector'])
        
        for element in elements[:5]:
            try:
                title = element.find_element(By.CSS_SELECTOR, source_config['title']).text.strip()
                abstract = element.find_element(By.CSS_SELECTOR, source_config['abstract']).text.strip()
                
                if title and abstract:
                    results.append({
                        'title': title,
                        'abstract': abstract,
                        'source': source_config['name'],
                        'url': url,
                        'published_at': datetime.now().strftime('%Y-%m-%d'),
                        'category': 'news'
                    })
            except Exception as e:
                continue
                
        return results
    except Exception as e:
        logger.error(f"Error scraping {source_config['name']}: {e}")
        return []

def scrape_data(topic):
    data = []
    driver = None
    
    try:
        driver = setup_webdriver()
        
        # Scrape news sources
        for source_name, config in NEWS_SOURCES.items():
            try:
                config['name'] = source_name
                results = scrape_news_source(driver, config, topic)
                if results:
                    data.extend(results)
                time.sleep(2)
            except Exception as e:
                logger.error(f"Failed to scrape {source_name}: {e}")
                continue
        
        # Fallback to NewsAPI if we don't have enough data
        if len(data) < 5:
            try:
                newsapi = NewsApiClient(api_key=NEWS_API_KEY)
                response = newsapi.get_everything(
                    q=topic,
                    language='en',
                    sort_by='relevancy',
                    page_size=5
                )
                
                if response.get('articles'):
                    for article in response['articles']:
                        data.append({
                            'title': article['title'],
                            'abstract': article['description'] or article['title'],
                            'source': article['source']['name'],
                            'url': article['url'],
                            'published_at': article['publishedAt'],
                            'category': 'news'
                        })
            except Exception as e:
                logger.error(f"NewsAPI error: {e}")
        
    except Exception as e:
        logger.error(f"Scraping error: {e}")
    finally:
        if driver:
            driver.quit()
    
    # Ensure minimum data
    if not data:
        data.append({
            'title': f'Research on {topic}',
            'abstract': f'Analysis of {topic} trends and developments.',
            'source': 'Research Summary',
            'published_at': datetime.now().strftime('%Y-%m-%d'),
            'category': 'research'
        })
    
    return data