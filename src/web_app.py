"""Flask web server for Progressive Summarization Viewer."""

import os
import webbrowser
import threading
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from werkzeug.utils import secure_filename

from config import load_config
from processor import process_file

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Store processed documents in memory
processed_docs = {}


@app.route('/')
def index():
    """Serve the main viewer page."""
    return render_template('index.html')


@app.route('/api/process', methods=['POST'])
def process_document():
    """Process a markdown file and return abstraction levels."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.md'):
            return jsonify({'error': 'Only markdown files (.md) are supported'}), 400

        # Save uploaded file temporarily
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Load config and process
        config = load_config()
        document_cache = process_file(filepath, config)

        # Store in memory
        doc_id = filename
        processed_docs[doc_id] = document_cache

        # Clean up temp file
        os.remove(filepath)

        # Return document data
        return jsonify({
            'success': True,
            'doc_id': doc_id,
            'filename': filename,
            'levels': document_cache['levels'],
            'metadata': document_cache['metadata']
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<doc_id>')
def get_document(doc_id):
    """Get a processed document."""
    if doc_id not in processed_docs:
        return jsonify({'error': 'Document not found'}), 404

    return jsonify(processed_docs[doc_id])


def open_browser():
    """Open browser after a short delay."""
    import time
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')


def run_server(port=5000, open_browser_tab=True):
    """Run the Flask server."""
    if open_browser_tab:
        threading.Thread(target=open_browser, daemon=True).start()

    print(f"\n🚀 Progressive Summarization Viewer")
    print(f"📍 Running at: http://127.0.0.1:{port}")
    print(f"👉 Opening browser...\n")

    app.run(port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    run_server()
