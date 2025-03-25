import requests
from textblob import TextBlob
import nltk
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
                
            headers = {'Content-Type': 'application/json'}
            data = {
                "contents": [{
                    "parts": [{"text": f"Summarize this text concisely in 2-3 sentences: {text}"}]
                }]
            }
            
            response = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0]['text']
            
            time.sleep(1)  # Wait before retry
            
        except Exception as e:
            logger.warning(f"Gemini API attempt {attempt + 1} failed: {e}")
            time.sleep(1)
    
    return None

def get_topic_analysis(text, topic):
    """Get detailed analysis using Gemini API"""
    try:
        headers = {'Content-Type': 'application/json'}
        prompt = f"""Analyze this text about '{topic}' and provide:
1. Key findings
2. Main themes
3. Important statistics or data points
4. Related implications
Text: {text}"""
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
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

def process_data(raw_data, topic):
    processed_data = []
    gemini_failures = 0
    max_retries = 3
    
    # Group data by source
    source_groups = {}
    for item in raw_data:
        source = item['source']
        if source not in source_groups:
            source_groups[source] = []
        source_groups[source].append(item)
    
    # Process each source group
    for source, items in source_groups.items():
        combined_text = " ".join([f"{i['title']}. {i.get('abstract', '')}" for i in items])
        
        # Try Gemini analysis
        analysis = get_topic_analysis(combined_text, topic)
        
        for item in items:
            text = item['title'] + " " + item.get('abstract', '')
            summary = None
            
            # Try Gemini with retries
            for _ in range(max_retries):
                if gemini_failures < len(raw_data) // 2:  # Only try Gemini if failure rate is low
                    summary = summarize_with_gemini(text)
                    if summary:
                        break
                    gemini_failures += 1
                else:
                    logger.warning("Too many Gemini API failures, switching to TextRank")
                    break
            
            # Fallback to TextRank if Gemini failed
            if not summary:
                summary = text_rank_summarize(text)
            
            # Sentiment with TextBlob
            sentiment = TextBlob(text).sentiment.polarity
            
            processed_data.append({
                'title': item['title'],
                'summary': summary,
                'analysis': analysis,  # Add detailed analysis
                'sentiment': sentiment,
                'source': source,
                'date': item.get('published_at', '2025-03-25'),
                'url': item.get('url', ''),
                'topic': topic  # Add topic to processed data
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