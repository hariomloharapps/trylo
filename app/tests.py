from flask import Flask, render_template_string, request, send_file, flash, redirect, url_for
import lzma
import os
import hashlib
import tempfile
import shutil
import zipfile
import json
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Create temp directory for file processing
TEMP_DIR = tempfile.mkdtemp()

# --- UTILITY FUNCTIONS ---
def get_file_hash(filepath):
    """Calculates the SHA-256 hash of a file for accurate comparison."""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        return None

def get_folder_structure(folder_path):
    """Get the complete folder structure with file info."""
    structure = {}
    
    for root, dirs, files in os.walk(folder_path):
        # Get relative path from the base folder
        rel_path = os.path.relpath(root, folder_path)
        if rel_path == '.':
            rel_path = ''
        
        # Store directory info
        structure[rel_path] = {
            'type': 'directory',
            'files': [],
            'subdirs': dirs.copy()
        }
        
        # Store file info
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            file_hash = get_file_hash(file_path)
            
            structure[rel_path]['files'].append({
                'name': file,
                'size': file_size,
                'hash': file_hash
            })
    
    return structure

def create_folder_archive(folder_path, output_path):
    """Create a ZIP archive of the folder with metadata."""
    try:
        # Get folder structure
        folder_structure = get_folder_structure(folder_path)
        
        # Create ZIP file
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add metadata file
            metadata = {
                'original_folder': os.path.basename(folder_path),
                'structure': folder_structure,
                'total_files': sum(len(info['files']) for info in folder_structure.values()),
                'created_by': 'Flask Folder Compressor'
            }
            zipf.writestr('_metadata.json', json.dumps(metadata, indent=2))
            
            # Add all files to ZIP
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Get relative path for ZIP
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)
        
        return True, folder_structure
    except Exception as e:
        print(f"Error creating archive: {e}")
        return False, None

def compress_archive_to_hl(zip_path, hl_path):
    """Compress the ZIP archive using LZMA."""
    try:
        with open(zip_path, 'rb') as f_in, lzma.open(hl_path, "wb") as f_out:
            f_out.write(f_in.read())
        return True
    except Exception as e:
        print(f"LZMA compression error: {e}")
        return False

def decompress_hl_to_archive(hl_path, zip_path):
    """Decompress LZMA file to ZIP archive."""
    try:
        with lzma.open(hl_path, "rb") as f_in, open(zip_path, "wb") as f_out:
            f_out.write(f_in.read())
        return True
    except Exception as e:
        print(f"LZMA decompression error: {e}")
        return False

def extract_archive_to_folder(zip_path, extract_to):
    """Extract ZIP archive to folder."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # Read metadata
            metadata = None
            if '_metadata.json' in zipf.namelist():
                metadata_content = zipf.read('_metadata.json').decode('utf-8')
                metadata = json.loads(metadata_content)
            
            # Extract all files
            zipf.extractall(extract_to)
            
            # Remove metadata file from extracted folder
            metadata_path = os.path.join(extract_to, '_metadata.json')
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            return True, metadata
    except Exception as e:
        print(f"Extraction error: {e}")
        return False, None

def get_file_info(filepath):
    """Get file size and other info."""
    try:
        size = os.path.getsize(filepath)
        return {
            'size': size,
            'size_kb': size / 1024,
            'size_mb': size / (1024 * 1024)
        }
    except:
        return None

# HTML Templates as simple strings without CSS
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Folder Compressor</title>
</head>
<body>
    <h1>Folder Compressor & Decompressor</h1>
    <hr>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <p><strong>{{ category.upper() }}:</strong> {{ message }}</p>
            {% endfor %}
            <hr>
        {% endif %}
    {% endwith %}
    
    <h2>Compress Folder</h2>
    <form action="{{ url_for('compress') }}" method="post" enctype="multipart/form-data">
        <p>Select folder to compress:</p>
        <input type="file" name="files" webkitdirectory multiple required>
        <br><br>
        <input type="submit" value="Compress Folder">
    </form>
    
    <hr>
    
    <h2>Decompress .hl File</h2>
    <form action="{{ url_for('decompress') }}" method="post" enctype="multipart/form-data">
        <p>Select .hl file to decompress:</p>
        <input type="file" name="file" accept=".hl" required>
        <br><br>
        <input type="submit" value="Decompress File">
    </form>
</body>
</html>
"""

RESULT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
</head>
<body>
    <h1>{{ title }}</h1>
    <hr>
    
    <h2>Operation Successful!</h2>
    
    <h3>File Information:</h3>
    <ul>
        <li><strong>Original Size:</strong> {{ original_size_kb }} KB</li>
        <li><strong>Final Size:</strong> {{ final_size_kb }} KB</li>
        {% if compression_ratio %}
        <li><strong>Compression Ratio:</strong> {{ "%.2f"|format(compression_ratio) }}%</li>
        {% endif %}
        <li><strong>File Hash:</strong> {{ file_hash }}</li>
    </ul>
    
    {% if folder_structure %}
    <h3>Folder Structure:</h3>
    <pre>{{ folder_structure }}</pre>
    {% endif %}
    
    <hr>
    
    <h3>Download Result:</h3>
    <p><a href="{{ url_for('download', filename=output_filename) }}">Download {{ 'Compressed' if compression_ratio else 'Decompressed' }} File</a></p>
    
    <p><a href="{{ url_for('index') }}">Process Another File/Folder</a></p>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/compress', methods=['POST'])
def compress():
    if 'files' not in request.files:
        flash('No files selected', 'error')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        flash('No files selected', 'error')
        return redirect(url_for('index'))
    
    # Create a temporary folder to store uploaded files
    upload_folder = os.path.join(TEMP_DIR, 'uploaded_folder')
    os.makedirs(upload_folder, exist_ok=True)
    
    # Save all uploaded files maintaining folder structure
    for file in files:
        if file.filename:
            # Create directory structure
            file_path = os.path.join(upload_folder, file.filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)
    
    # Get original folder size
    original_size = sum(os.path.getsize(os.path.join(root, file)) 
                       for root, dirs, files in os.walk(upload_folder) 
                       for file in files)
    
    # Create ZIP archive
    zip_path = os.path.join(TEMP_DIR, 'folder_archive.zip')
    success, folder_structure = create_folder_archive(upload_folder, zip_path)
    
    if not success:
        flash('Failed to create archive', 'error')
        return redirect(url_for('index'))
    
    # Compress ZIP to .hl file
    folder_name = os.path.basename(list(files)[0].filename.split('/')[0])
    hl_filename = f"{folder_name}_compressed.hl"
    hl_path = os.path.join(TEMP_DIR, hl_filename)
    
    if compress_archive_to_hl(zip_path, hl_path):
        # Get compressed file info
        compressed_info = get_file_info(hl_path)
        compression_ratio = (compressed_info['size'] / original_size) * 100
        file_hash = get_file_hash(hl_path)
        
        # Clean up temporary files
        shutil.rmtree(upload_folder)
        os.remove(zip_path)
        
        # Format folder structure for display
        structure_display = json.dumps(folder_structure, indent=2)
        
        return render_template_string(RESULT_HTML,
                                    title="Folder Compression Complete",
                                    compression_ratio=compression_ratio,
                                    original_size_kb=f"{original_size / 1024:.2f}",
                                    final_size_kb=f"{compressed_info['size_kb']:.2f}",
                                    file_hash=file_hash,
                                    output_filename=hl_filename,
                                    folder_structure=structure_display)
    else:
        flash('Compression failed. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/decompress', methods=['POST'])
def decompress():
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if not file.filename.endswith('.hl'):
        flash('Please select a .hl file for decompression.', 'error')
        return redirect(url_for('index'))
    
    # Save uploaded .hl file
    filename = secure_filename(file.filename)
    hl_path = os.path.join(TEMP_DIR, filename)
    file.save(hl_path)
    
    # Get compressed file info
    compressed_info = get_file_info(hl_path)
    
    # Decompress .hl to ZIP
    zip_path = os.path.join(TEMP_DIR, 'decompressed_archive.zip')
    if not decompress_hl_to_archive(hl_path, zip_path):
        flash('Decompression failed. Please ensure the file is a valid .hl file.', 'error')
        return redirect(url_for('index'))
    
    # Extract ZIP to folder
    extract_folder = os.path.join(TEMP_DIR, 'extracted_folder')
    os.makedirs(extract_folder, exist_ok=True)
    
    success, metadata = extract_archive_to_folder(zip_path, extract_folder)
    
    if not success:
        flash('Extraction failed.', 'error')
        return redirect(url_for('index'))
    
    # Create new ZIP for download (without metadata)
    base_name = os.path.splitext(filename)[0]
    download_filename = f"{base_name}_restored.zip"
    download_path = os.path.join(TEMP_DIR, download_filename)
    
    with zipfile.ZipFile(download_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(extract_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_folder)
                zipf.write(file_path, arcname)
    
    # Get final file info
    final_info = get_file_info(download_path)
    final_hash = get_file_hash(download_path)
    
    # Clean up temporary files
    os.remove(hl_path)
    os.remove(zip_path)
    shutil.rmtree(extract_folder)
    
    # Format metadata for display
    structure_display = json.dumps(metadata, indent=2) if metadata else "No metadata available"
    
    return render_template_string(RESULT_HTML,
                                title="Folder Decompression Complete",
                                compression_ratio=None,
                                original_size_kb=f"{compressed_info['size_kb']:.2f}",
                                final_size_kb=f"{final_info['size_kb']:.2f}",
                                file_hash=final_hash,
                                output_filename=download_filename,
                                folder_structure=structure_display)

@app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(TEMP_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        flash('File not found or may have expired.', 'error')
        return redirect(url_for('index'))

@app.errorhandler(413)
def too_large(e):
    flash('File too large! Maximum size is 500MB.', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("🚀 Starting Folder Compressor Web App...")
    print("📍 Open your browser and go to http://localhost:5000")
    print("🔧 Press Ctrl+C to stop the server")
    print("\nFeatures:")
    print("- Upload entire folders for compression")
    print("- Maintains folder structure and file metadata")
    print("- Creates .hl compressed files")
    print("- Decompresses .hl files back to ZIP folders")
    print("- Shows complete folder structure before/after")
    
    # Clean up temp directory on exit
    import atexit
    atexit.register(lambda: shutil.rmtree(TEMP_DIR, ignore_errors=True))
    
    app.run(debug=True, host='0.0.0.0', port=5000)