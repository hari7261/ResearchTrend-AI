from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from collections import Counter
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import logging
from wordcloud import WordCloud
import os

logger = logging.getLogger(__name__)

def analyze_topic_insights(data):
    """Generate AI-driven insights from the data"""
    insights = []
    
    # Analyze sentiment distribution
    sentiments = [d['sentiment'] for d in data]
    avg_sentiment = np.mean(sentiments)
    if avg_sentiment > 0.2:
        sentiment_insight = "Overall positive sentiment detected in the research"
    elif avg_sentiment < -0.2:
        sentiment_insight = "Generally negative sentiment observed in the research"
    else:
        sentiment_insight = "Neutral sentiment detected across sources"
    insights.append(sentiment_insight)
    
    # Analyze source distribution
    sources = Counter(d['source'] for d in data)
    source_insight = f"Data collected from {len(sources)} different sources"
    insights.append(source_insight)
    
    # Analyze content themes
    all_text = " ".join([d['summary'] for d in data])
    words = all_text.lower().split()
    common_words = Counter(words).most_common(5)
    theme_insight = f"Key themes identified: {', '.join([word for word, _ in common_words])}"
    insights.append(theme_insight)
    
    return insights

def create_trend_chart(trends, filename):
    try:
        # Create figure without using pyplot
        fig = Figure(figsize=(10, 6))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        
        terms, counts = zip(*trends)
        bars = ax.bar(terms, counts)
        ax.set_title("Top Trending Topics", fontsize=14, pad=20)
        ax.tick_params(axis='x', rotation=45, ha='right')
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom')
        
        fig.tight_layout()
        fig.savefig(filename, dpi=300, bbox_inches='tight')
        return True
    except Exception as e:
        logger.error(f"Error creating trend chart: {e}")
        return False

def create_sentiment_chart(data, filename):
    try:
        fig = Figure(figsize=(10, 6))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        
        sentiments = [d['sentiment'] for d in data]
        sources = [d['source'] for d in data]
        
        # Create scatter plot
        for source in set(sources):
            source_sentiments = [s for s, src in zip(sentiments, sources) if src == source]
            source_indices = [i for i, src in enumerate(sources) if src == source]
            ax.scatter(source_indices, source_sentiments, label=source, s=100)
            
        ax.axhline(y=0, color='r', linestyle='--', alpha=0.3)
        ax.set_title("Sentiment Analysis by Source", fontsize=14, pad=20)
        ax.set_xlabel("Articles")
        ax.set_ylabel("Sentiment Score")
        ax.legend()
        
        fig.tight_layout()
        fig.savefig(filename, dpi=300, bbox_inches='tight')
        return True
    except Exception as e:
        logger.error(f"Error creating sentiment chart: {e}")
        return False

def create_word_cloud(data, filename):
    try:
        # Combine all text relevant to the topic
        text = ' '.join([d['title'] + ' ' + d['summary'] for d in data])
        
        # Generate word cloud
        wordcloud = WordCloud(
            width=800, height=400,
            background_color='white',
            colormap='viridis',
            max_words=50
        ).generate(text)
        
        # Save to file using Figure
        fig = Figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        
        fig.savefig(filename, dpi=300, bbox_inches='tight', pad_inches=0)
        return True
    except Exception as e:
        logger.error(f"Error creating word cloud: {e}")
        return False

def clean_and_filter_trends(trends, min_length=3):
    """Filter out irrelevant terms from trends"""
    stopwords = {'the', 'and', 'or', 'in', 'at', 'to', 'for', 'of', 'with', 'by'}
    return [(term, count) for term, count in trends 
            if len(term) >= min_length 
            and term.isalnum()
            and term not in stopwords]

def generate_pdf(data, trends, filename):
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    story = []

    # Add custom styles
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#1a1a2e')
    ))
    
    styles.add(ParagraphStyle(
        name='CustomHeading',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=16,
        textColor=colors.HexColor('#ff6b35')
    ))
    
    styles.add(ParagraphStyle(
        name='Insight',
        parent=styles['BodyText'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.HexColor('#4a4a4a'),
        bulletIndent=20,
        leftIndent=20
    ))

    # Cover page
    topic = data[0].get('topic', 'Research')
    story.append(Paragraph(f"{topic.replace('_', ' ').title()} Research Report", styles['CustomTitle']))
    story.append(Paragraph(f"Generated on {data[0]['date']}", styles['Heading2']))
    story.append(Spacer(1, 30))

    # AI Insights
    story.append(Paragraph("Key Insights", styles['CustomHeading']))
    insights = analyze_topic_insights(data)
    for insight in insights:
        story.append(Paragraph(f"• {insight}", styles['Insight']))
    story.append(Spacer(1, 20))

    # Add Word Cloud
    story.append(Paragraph("Topic Overview", styles['CustomHeading']))
    wordcloud_path = f"{filename.replace('.pdf', '_wordcloud.png')}"
    if create_word_cloud(data, wordcloud_path):
        story.append(Image(wordcloud_path, width=400, height=200))
    story.append(Spacer(1, 20))

    # Filter trends before visualization
    filtered_trends = clean_and_filter_trends(trends)
    
    # Create charts with filtered data
    trend_chart_path = f"{filename.replace('.pdf', '_trends.png')}"
    if create_trend_chart(filtered_trends[:10], trend_chart_path):
        story.append(Image(trend_chart_path, width=400, height=200))
        
    try:
        doc.build(story)
        return True
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        return False