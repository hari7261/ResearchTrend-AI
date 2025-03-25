from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib.pyplot as plt

def create_trend_chart(trends, filename):
    terms, counts = zip(*trends)
    plt.bar(terms, counts)
    plt.title("Top 5 Trending Topics")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def generate_pdf(data, trends, filename):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Cover page
    story.append(Paragraph("Research Report - March 2025", styles['Title']))
    story.append(Spacer(1, 12))

    # Executive Summary
    story.append(Paragraph("Executive Summary", styles['Heading1']))
    story.append(Paragraph("This report summarizes key findings and trends.", styles['BodyText']))

    # Key Findings
    story.append(Paragraph("Key Findings", styles['Heading1']))
    table_data = [["Title", "Sentiment", "Source"]] + [[d['title'][:50], f"{d['sentiment']:.2f}", d['source']] for d in data[:3]]
    story.append(Table(table_data))

    # Trend Analysis
    story.append(Paragraph("Trend Analysis", styles['Heading1']))
    chart_path = filename.replace('.pdf', '_chart.png')
    create_trend_chart(trends, chart_path)
    story.append(Image(chart_path, width=300, height=200))

    doc.build(story)