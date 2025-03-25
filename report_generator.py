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
        if not trends:
            logger.warning("No trends data available")
            return False
            
        fig = Figure(figsize=(10, 6))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        
        # Ensure we have data to plot
        if len(trends) < 2:
            terms = [trends[0][0] if trends else "No Data"]
            counts = [trends[0][1] if trends else 0]
        else:
            terms, counts = zip(*trends)
            
        bars = ax.bar(range(len(terms)), counts)
        
        # Configure x-axis
        ax.set_xticks(range(len(terms)))
        ax.set_xticklabels(terms, rotation=45)
        
        # Adjust layout to prevent label cutoff
        fig.tight_layout()
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2.,
                height,
                f'{int(height)}',
                horizontalalignment='center',
                verticalalignment='bottom'
            )
        
        fig.savefig(filename, bbox_inches='tight', dpi=300)
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

def create_time_trend_chart(time_trends, filename):
    try:
        fig = Figure(figsize=(12, 6))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        
        dates = sorted(time_trends.keys())
        counts = [len(time_trends[date]) for date in dates]
        
        ax.plot(dates, counts, marker='o')
        ax.set_title("Content Publication Timeline", fontsize=14, pad=20)
        ax.set_xlabel("Date")
        ax.set_ylabel("Number of Articles")
        ax.tick_params(axis='x', rotation=45)
        
        fig.tight_layout()
        fig.savefig(filename, dpi=300, bbox_inches='tight')
        return True
    except Exception as e:
        logger.error(f"Error creating time trend chart: {e}")
        return False

def generate_pdf(data, trends_data, filename):
    try:
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

        # Handle trends data properly
        word_freq = trends_data.get('word_freq', [])
        time_trends = trends_data.get('time_trends', {})
        sources = trends_data.get('sources', Counter())
        
        # Add trend analysis if we have word frequency data
        if word_freq:
            filtered_trends = clean_and_filter_trends(word_freq)
            if filtered_trends:
                trend_chart_path = os.path.join(
                    os.path.dirname(filename),
                    f"{os.path.splitext(os.path.basename(filename))[0]}_trends.png"
                )
                if create_trend_chart(filtered_trends[:5], trend_chart_path):
                    story.append(Paragraph("Trend Analysis", styles['CustomHeading']))
                    story.append(Image(trend_chart_path, width=400, height=200))
                    story.append(Spacer(1, 20))

        # Add timeline analysis if we have time data
        if time_trends:
            timeline_chart = os.path.join(
                os.path.dirname(filename),
                f"{os.path.splitext(os.path.basename(filename))[0]}_timeline.png"
            )
            if create_time_trend_chart(time_trends, timeline_chart):
                story.append(Paragraph("Publication Timeline", styles['CustomHeading']))
                story.append(Image(timeline_chart, width=450, height=250))
                story.append(Spacer(1, 20))

        # Add source distribution if we have source data
        if sources:
            story.append(Paragraph("Source Distribution", styles['CustomHeading']))
            source_data = list(sources.items())  # Convert Counter items to list of tuples
            if source_data:
                source_chart = os.path.join(
                    os.path.dirname(filename),
                    f"{os.path.splitext(os.path.basename(filename))[0]}_sources.png"
                )
                if create_trend_chart(source_data, source_chart):
                    story.append(Image(source_chart, width=400, height=200))

        # Add Source-wise Analysis
        story.append(Paragraph("Source-wise Analysis", styles['CustomHeading']))
        source_groups = {}
        for item in data:
            source = item['source']
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(item)
        
        for source, items in source_groups.items():
            story.append(Paragraph(f"Analysis from {source}", styles['CustomHeading']))
            if items[0].get('analysis'):
                story.append(Paragraph(items[0]['analysis'], styles['BodyText']))
            story.append(Spacer(1, 20))

        # Add summary table
        table_data = [["Source", "Summary", "Sentiment"]]
        for d in data:
            summary = d.get('summary', '')[:200] + '...' if len(d.get('summary', '')) > 200 else d.get('summary', '')
            sentiment = "Positive" if d['sentiment'] > 0.1 else "Negative" if d['sentiment'] < -0.1 else "Neutral"
            table_data.append([d['source'], summary, sentiment])

        if len(table_data) > 1:
            try:
                story.append(Paragraph("Detailed Analysis", styles['CustomHeading']))
                table = Table(table_data, colWidths=[1.5*inch, 4*inch, inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            except Exception as e:
                logger.error(f"Error adding summary table to PDF: {e}")

        # Build the PDF
        doc.build(story)
        return True
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        return False