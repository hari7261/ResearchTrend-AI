import requests
from textblob import TextBlob
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import logging
import json

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

def summarize_with_gemini(text):
    try:
        if not text:
            return None
            
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [{"text": f"Summarize this text concisely: {text}"}]
            }]
        }
        
        # Add timeout to request
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 503:
            logger.warning("Gemini API temporarily unavailable")
            return None
            
        response.raise_for_status()
        
        result = response.json()
        if 'candidates' in result and result['candidates']:
            return result['candidates'][0]['content']['parts'][0]['text']
        return None
            
    except requests.exceptions.Timeout:
        logger.warning("Gemini API request timed out")
        return None
    except Exception as e:
        logger.warning(f"Gemini API summarization failed: {e}")
        return None

def process_data(raw_data):
    processed_data = []
    
    for item in raw_data:
        text = item['title'] + " " + item.get('abstract', '')
        
        # Try Gemini first, fallback to TextRank
        summary = summarize_with_gemini(text) or text_rank_summarize(text)
        
        # Sentiment with TextBlob
        sentiment = TextBlob(text).sentiment.polarity
        
        processed_data.append({
            'title': item['title'],
            'summary': summary,
            'sentiment': sentiment,
            'source': item['source'],
            'date': '2025-03-25'  # Static for demo
        })
    return processed_data

def detect_trends(data):
    all_text = " ".join([d['summary'] for d in data])
    tokens = word_tokenize(all_text.lower())
    freq = nltk.FreqDist(tokens)
    return freq.most_common(5)  # Top 5 terms