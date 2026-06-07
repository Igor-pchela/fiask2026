import os
from werkzeug.utils import secure_filename
from flask import current_app
from datetime import datetime

def save_file(file, subfolder):
    """Сохраняет файл в подпапку (tasks/comments) и возвращает относительный путь."""
    if not file or file.filename == '':
        return None
    filename = secure_filename(file.filename)
    # Добавляем временную метку для уникальности
    name, ext = os.path.splitext(filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename = f"{name}_{timestamp}{ext}"
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    file.save(filepath)
    return os.path.join(subfolder, filename).replace('\\', '/')