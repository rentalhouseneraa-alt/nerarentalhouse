import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import current_app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file):
    """
    Save uploaded file to UPLOAD_FOLDER.
    Returns the saved filename or None if invalid.
    """
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        filename = f"{timestamp}_{name}{ext}"
        
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return filename
    return None

def parse_datetime_str(date_str):
    """
    Parse datetime string from form input.
    Supports both formats:
    - 'YYYY-MM-DD HH:MM' (from text input)
    - 'YYYY-MM-DDTHH:MM' (from datetime-local input)
    Returns datetime object or None if invalid.
    """
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    # Try datetime-local format first (YYYY-MM-DDTHH:MM)
    try:
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        pass
    
    # Try standard format (YYYY-MM-DD HH:MM)
    try:
        return datetime.strptime(date_str, '%Y-%m-%d %H:%M')
    except ValueError:
        pass
    
    # Try with seconds (YYYY-MM-DD HH:MM:SS)
    try:
        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass
    
    # Try ISO format
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass
    
    return None