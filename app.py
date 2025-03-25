from flask import Flask, render_template, request, send_file, jsonify
from scraper import scrape_data
from processor import process_data, detect_trends
from report_generator import generate_pdf
from apscheduler.schedulers.background import BackgroundScheduler
import os
import logging
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create reports directory if it doesn't exist
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)

# Create subdirectories for better organization
REPORTS_ARCHIVE = os.path.join(REPORTS_DIR, 'archive')
REPORTS_TEMP = os.path.join(REPORTS_DIR, 'temp')
Path(REPORTS_ARCHIVE).mkdir(exist_ok=True)
Path(REPORTS_TEMP).mkdir(exist_ok=True)

scheduler = BackgroundScheduler()
scheduler.add_job(lambda: scrape_data('ai_ethics'), 'interval', days=1)
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_report', methods=['POST'])
def generate_report():
    topic = request.form.get('topic', 'ai_ethics')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Generating report for topic: {topic}")
    
    try:
        # Cleanup old temp files
        for old_file in Path(REPORTS_TEMP).glob("*.*"):
            try:
                old_file.unlink()
            except Exception as e:
                logger.warning(f"Could not delete old file {old_file}: {e}")
        
        # Step 1: Scrape data
        raw_data = scrape_data(topic)
        if not raw_data:
            logger.error("Scraping returned no data")
            return jsonify({'error': 'No data found for the given topic.'}), 400
        
        # Step 2: Process data with topic
        processed_data = process_data(raw_data, topic)
        trends = detect_trends(processed_data)
        
        # Generate PDF in temp directory
        temp_pdf_path = os.path.join(REPORTS_TEMP, f"{topic}_{timestamp}.pdf")
        if generate_pdf(processed_data, trends, temp_pdf_path):
            # Move successful report to archive
            archive_path = os.path.join(REPORTS_ARCHIVE, f"{topic}_{timestamp}.pdf")
            os.rename(temp_pdf_path, archive_path)
            
            logger.info(f"PDF generated and archived at {archive_path}")
            return jsonify({
                'message': 'Report generated successfully',
                'download_url': f'/download/{os.path.basename(archive_path)}'
            })
        else:
            return jsonify({'error': 'Failed to generate PDF report'}), 500
            
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(REPORTS_ARCHIVE, filename)
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        else:
            logger.error(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return jsonify({'error': 'Failed to download file'}), 500

if __name__ == '__main__':
    app.run(debug=True)