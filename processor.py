import requests
from textblob import TextBlob
import nltk
import time
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import logging
import json
from textblob.tokenizers import WordTokenizer
from collections import Counter
from datetime import datetime

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
except Exception as e:
    logging.error(f"Failed to download NLTK data: {e}")

GEMINI_API_KEY = "AIzaSyDn0QOJrVrtCgfFN1v304AMhmh8brEwVqs"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

logger = logging.getLogger(__name__)

def text_rank_summarize(text, num_sentences=3):
    try:
        if not text or len(text.strip()) == 0:
            return "No text provided for summarization."
            
        sentences = sent_tokenize(text)
        if len(sentences) <= num_sentences:
            return text
            
        # Create TF-IDF matrix
        try:
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(sentences)
        except ValueError:
            return text  # Return original text if vectorization fails
        
        # Create similarity matrix
        similarity_matrix = (tfidf_matrix * tfidf_matrix.T).toarray()
        
        # PageRank-like algorithm
        scores = np.ones(len(sentences)) / len(sentences)
        for _ in range(10):
            scores = similarity_matrix.dot(scores)
            scores = scores / scores.sum()
        
        # Get top sentences
        ranked_sentences = [(score, sent) for score, sent in zip(scores, sentences)]
        ranked_sentences.sort(reverse=True)
        
        summary = ' '.join(sent for _, sent in ranked_sentences[:num_sentences])
        return summary if summary else text
        
    except Exception as e:
        logger.error(f"TextRank summarization failed: {e}")
        return text  # Return original text if summarization fails

def summarize_with_gemini(text, retries=3):
    for attempt in range(retries):
        try:
            if not text:
                return None
            
            # Limit text length
            text = text[:1000] if len(text) > 1000 else text
            
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': GEMINI_API_KEY
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": f"Provide a concise 2-3 sentence summary of: {text}"
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 200
                }
            }
            
            response = requests.post(
                GEMINI_URL,
                headers=headers,
                json=data,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0]['text']
            
            logger.warning(f"Gemini API attempt {attempt + 1} failed with status {response.status_code}")
            logger.debug(f"Response: {response.text}")
            time.sleep(2)
            
        except Exception as e:
            logger.warning(f"Gemini API attempt {attempt + 1} failed: {str(e)}")
            time.sleep(2)
    
    return None

def get_topic_analysis(text, topic):
    """Get detailed analysis using Gemini API"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': GEMINI_API_KEY
        }
        
        prompt = f"""Analyze this text about '{topic}' and provide:
1. Key findings
2. Main themes
3. Important statistics or data points
4. Related implications
Text: {text}"""

        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 500
            }
        }
        
        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=data,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and result['candidates']:
                return result['candidates'][0]['content']['parts'][0]['text']
        return None
    except Exception as e:
        logger.warning(f"Gemini analysis failed: {e}")
        return None

def clean_source_text(text, source):
    """Clean text based on source-specific patterns"""
    text = text.replace('\n', ' ').strip()
    if 'times_of_india' in source.lower():
        text = text.split('READ MORE')[0]
    elif 'hindustan_times' in source.lower():
        text = text.split('Also Read')[0]
    elif 'ndtv' in source.lower():
        text = text.split('Read more')[0]
    return text.strip()

def process_data(raw_data, topic):
    processed_data = []
    gemini_failures = 0
    
    # Group similar content to reduce API calls
    grouped_data = {}
    for item in raw_data:
        source = item['source']
        if source not in grouped_data:
            grouped_data[source] = []
        grouped_data[source].append(item)
    
    for source, items in grouped_data.items():
        # Process each source group
        combined_text = " ".join([
            f"{item['title']}. {item.get('abstract', '')}" 
            for item in items
        ])
        
        # Get one summary for similar content
        summary = summarize_with_gemini(combined_text)
        if summary:
            logger.info(f"Successfully generated summary for {source}")
        else:
            logger.warning(f"Using TextRank fallback for {source}")
            summary = text_rank_summarize(combined_text)
        
        # Process individual items
        for item in items:
            processed_data.append({
                'title': item['title'],
                'summary': summary,
                'sentiment': TextBlob(item.get('abstract', '')).sentiment.polarity,
                'source': source,
                'date': item.get('published_at', datetime.now().strftime('%Y-%m-%d')),
                'url': item.get('url', ''),
                'topic': topic
            })
    
    return processed_data

def analyze_time_trends(data):
    """Analyze trends over time"""
    time_data = {}
    for item in data:
        if 'published_at' in item:
            date = datetime.strptime(item['published_at'][:10], '%Y-%m-%d')
            if date not in time_data:
                time_data[date] = []
            time_data[date].append(item)
    return time_data

def detect_trends(data):
    try:
        # Initialize trend data structure
        trend_data = {
            'word_freq': [],
            'time_trends': {},
            'sources': Counter(),
            'categories': Counter()
        }
        
        if not data:
            return trend_data
            
        # Process text and extract trends
        all_text = " ".join([
            d.get('title', '') + " " + 
            d.get('abstract', '') + " " + 
            d.get('summary', '') 
            for d in data
        ])
        
        # Update source and category counters
        trend_data['sources'].update(d['source'] for d in data)
        trend_data['categories'].update(d.get('category', 'unknown') for d in data)
        
        # Process time trends
        trend_data['time_trends'] = analyze_time_trends(data)
        
        # Process word frequency if we have text
        if all_text.strip():
            tokens = word_tokenize(all_text.lower())
            stop_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'])
            valid_tokens = [t for t in tokens if t.isalnum() and len(t) > 2 and t not in stop_words]
            trend_data['word_freq'] = Counter(valid_tokens).most_common(10)
        
        return trend_data
        
    except Exception as e:
        logger.error(f"Error in trend detection: {e}")
        return {
            'word_freq': [],
            'time_trends': {},
            'sources': Counter(),
            'categories': Counter()
        }