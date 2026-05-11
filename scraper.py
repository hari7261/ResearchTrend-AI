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

NEWS_SOURCES = {
    'times_of_india': {
        'url': 'https://timesofindia.indiatimes.com/topic/{}',
        'selector': '.list5.clearfix li, .article',
        'title': 'span.title, .article-title, h3 a',
        'abstract': '.summary, .article-content, p.synopsis'
    },
    'hindustan_times': {
        'url': 'https://www.hindustantimes.com/topic/{}',
        'selector': '.hdg3, .storyCard',
        'title': 'h3.hdg3 a, .storyHeadline',
        'abstract': '.sortDec, .storyDetail'
    },
    'ndtv': {
        'url': 'https://www.ndtv.com/topic/{}',
        'selector': '.news_Itm, .new_storylising_contentwrap',
        'title': '.newsHdng, .header_text',
        'abstract': '.newsCont, .post_content'
    },
    'india_today': {
        'url': 'https://www.indiatoday.in/topic/{}',
        'selector': '.C6ZIU, .story__grid',
        'title': '.B1OME, .story__title',
        'abstract': '.description, .story__shortDesc'
    },
    'economic_times': {
        'url': 'https://economictimes.indiatimes.com/topic/{}',
        'selector': '.eachStory, .article-block',
        'title': '.title, h3 a',
        'abstract': '.desc, .synopsis'
    }
}

# API Keys - Replace with your valid keys
NEWS_API_KEY = ""  # Your NewsAPI key

def setup_webdriver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-software-rasterizer')
    options.page_load_strategy = 'eager'
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(20)
    return driver

def scrape_news_source(driver, source_config, topic):
    results = []
    try:
        formatted_topic = topic.replace('_', '-').replace(' ', '-')
        url = source_config['url'].format(formatted_topic)
        logger.info(f"Scraping {url}")
        
        driver.get(url)
        # Increase wait time and add scroll
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)
        
        elements = driver.find_elements(By.CSS_SELECTOR, source_config['selector'])
        logger.info(f"Found {len(elements)} elements for {source_config['name']}")
        
        for element in elements[:5]:
            try:
                # Try multiple selectors for title and abstract
                title = ""
                for title_selector in source_config['title'].split(', '):
                    try:
                        title = element.find_element(By.CSS_SELECTOR, title_selector).text.strip()
                        if title:
                            break
                    except:
                        continue
                
                abstract = ""
                for abstract_selector in source_config['abstract'].split(', '):
                    try:
                        abstract = element.find_element(By.CSS_SELECTOR, abstract_selector).text.strip()
                        if abstract:
                            break
                    except:
                        continue
                
                if title and abstract:
                    results.append({
                        'title': title,
                        'abstract': abstract,
                        'source': source_config['name'],
                        'url': url,
                        'published_at': datetime.now().strftime('%Y-%m-%d'),
                        'category': 'news'
                    })
                    logger.info(f"Added article from {source_config['name']}: {title[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to extract article from {source_config['name']}: {e}")
                continue
                
        return results
    except Exception as e:
        logger.error(f"Error scraping {source_config['name']}: {e}")
        return []

def scrape_news_sources(topic):
    try:
        newsapi = NewsApiClient(api_key=NEWS_API_KEY)
        response = newsapi.get_everything(
            q=topic,
            language='en',
            sort_by='relevancy',
            page_size=10
        )
        
        articles = []
        if response and 'articles' in response:
            for article in response['articles']:
                if article['title'] and article['description']:
                    articles.append({
                        'title': article['title'],
                        'abstract': article['description'],
                        'source': article['source']['name'],
                        'url': article['url'],
                        'published_at': article['publishedAt'],
                        'category': 'news'
                    })
        return articles
    except Exception as e:
        logger.error(f"NewsAPI error: {str(e)}")
        return []

def scrape_data(topic):
    data = []
    driver = None
    
    try:
        # Get news from NewsAPI first
        news_articles = scrape_news_sources(topic)
        if news_articles:
            data.extend(news_articles)
            logger.info(f"Found {len(news_articles)} articles from NewsAPI")
        
        # Then try web scraping
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
