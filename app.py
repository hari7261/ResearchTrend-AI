from flask import Flask, render_template, request, send_file, jsonify
from scraper import scrape_data
from processor import process_data, detect_trends
from report_generator import generate_pdf
from apscheduler.schedulers.background import BackgroundScheduler
import os
import logging

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.add_job(lambda: scrape_data('ai_ethics'), 'interval', days=1)
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_report', methods=['POST'])
def generate_report():
    topic = request.form.get('topic', 'ai_ethics')
    logger.info(f"Generating report for topic: {topic}")
    
    # Step 1: Scrape data
    raw_data = scrape_data(topic)
    if not raw_data:
        logger.error("Scraping returned no data")
        return jsonify({'error': 'No data scraped. Check server logs for details.'}), 400
    
    # Step 2: Process data
    try:
        processed_data = process_data(raw_data)
        trends = detect_trends(processed_data)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500
    
    # Step 3: Generate PDF
    try:
        pdf_path = f"static/{topic}_report_March_2025.pdf"
        generate_pdf(processed_data, trends, pdf_path)
        logger.info(f"PDF generated at {pdf_path}")
        return jsonify({'message': 'Report generated', 'download_url': f'/download/{os.path.basename(pdf_path)}'})
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(f'static/{filename}', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)