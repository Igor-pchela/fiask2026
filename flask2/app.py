from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
import uuid
import hashlib
import mimetypes
from datetime import datetime
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(256)

ROOT = os.path.dirname(os.path.realpath(__file__))
UPLOAD_FOLDER = os.path.join(ROOT, 'uploads')
DATA_FOLDER = os.path.join(ROOT, 'data')
FILES_INFO_FILE = os.path.join(DATA_FOLDER, 'files_info.json')

for folder in [UPLOAD_FOLDER, DATA_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Запрещенные расширения файлов
FORBIDDEN_EXTENSIONS = {
    '.exe', '.sh', '.php', '.js', '.bat', '.cmd', '.vbs', '.ps1', '.pyc'
}

def load_files_info():
    """Загрузка информации о файлах из JSON"""
    if not os.path.exists(FILES_INFO_FILE):
        return {}
    
    with open(FILES_INFO_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_files_info(files_info):
    """Сохранение информации о файлах в JSON"""
    with open(FILES_INFO_FILE, 'w', encoding='utf-8') as f:
        json.dump(files_info, f, ensure_ascii=False, indent=4)

def calculate_md5(file_path):
    """Вычисление MD5 хэша файла"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def is_allowed_file(filename, file_content):
    """Проверка разрешен ли файл для загрузки"""
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext in FORBIDDEN_EXTENSIONS:
        return False, f"Запрещенное расширение файла: {file_ext}"
    
    return True, "OK"

def save_file_with_uuid(file, original_filename):
    """Сохранение файла с UUID именем во вложенных папках"""
    file_uuid = uuid.uuid4().hex

    subfolder1 = file_uuid[:2]
    subfolder2 = file_uuid[2:4]

    save_dir = os.path.join(app.config['UPLOAD_FOLDER'], subfolder1, subfolder2)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    file_ext = os.path.splitext(original_filename)[1].lower()
    save_filename = f"{file_uuid}{file_ext}"
    save_path = os.path.join(save_dir, save_filename)
    file.save(save_path)
    
    return {
        'uuid': file_uuid,
        'save_path': save_path,
        'save_filename': save_filename,
        'relative_path': os.path.join(subfolder1, subfolder2, save_filename),
        'subfolder1': subfolder1,
        'subfolder2': subfolder2
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    """Главная страница с формой загрузки и таблицей файлов"""
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(url_for('index'))
        
        original_filename = file.filename
        
        file_content = file.read()
        file_md5 = hashlib.md5(file_content).hexdigest()
        file.seek(0)
        
        is_allowed, error_message = is_allowed_file(original_filename, file_content)
        if not is_allowed:
            flash(error_message, 'error')
            return redirect(url_for('index'))
        
        files_info = load_files_info()

        for file_id, file_data in files_info.items():
            if file_data.get('md5') == file_md5:
                flash(f'Файл уже существует! Оригинальное имя: {file_data["user_filename"]}, '
                      f'загружен: {file_data["upload_date"]}', 'warning')
                return redirect(url_for('index'))
        
        try:
            save_info = save_file_with_uuid(file, original_filename)
            
            file_info = {
                'uuid': save_info['uuid'],
                'user_filename': original_filename,
                'upload_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'file_size': os.path.getsize(save_info['save_path']),
                'file_extension': os.path.splitext(original_filename)[1].lower(),
                'mime_type': mimetypes.guess_type(original_filename)[0] or None,
                'md5': file_md5,
                'server_path': f"uploads/{save_info['relative_path']}",
                'full_save_path': save_info['save_path'],
                'subfolder1': save_info['subfolder1'],
                'subfolder2': save_info['subfolder2']
            }
            
            files_info[save_info['uuid']] = file_info
            save_files_info(files_info)
        
            flash(f'Файл "{original_filename}" успешно загружен!', 'success')
            
        except Exception as e:
            flash(f'Ошибка при сохранении файла: {str(e)}', 'error')
        
        return redirect(url_for('index'))
    
    files_info = load_files_info()
    
    # Преобразуем словарь в список и сортируем по дате (новые сверху)
    files_list = list(files_info.values())
    files_list.sort(key=lambda x: x['upload_date'], reverse=True)
    
    return render_template('index.html', files=files_list)


@app.route('/view/<file_uuid>')
def view_file(file_uuid):
    """Просмотр файла прямо в браузере"""
    files_info = load_files_info()
    
    if file_uuid not in files_info:
        flash('Файл не найден', 'error')
        return redirect(url_for('index'))
    
    file_data = files_info[file_uuid]
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                            file_data['subfolder1'], 
                            file_data['subfolder2'],
                            f"{file_data['uuid']}{file_data['file_extension']}")
    
    if not os.path.exists(file_path):
        flash('Файл не найден на диске', 'error')
        return redirect(url_for('index'))
    
    mime_type = file_data['mime_type']
    
    viewable_types = [
        'image/',           # Все изображения
        'application/pdf',  # PDF документы
        'text/',           # Все текстовые файлы
        'video/',          # Видео файлы
        'audio/'           # Аудио файлы
    ]
    
    is_viewable = any(mime_type.startswith(t) for t in viewable_types)
    
    if is_viewable:
        # Отправляем файл для просмотра в браузере
        return send_from_directory(
            os.path.dirname(file_path),
            os.path.basename(file_path),
            as_attachment=False
        )
    else:
        # Для остальных типов - скачивание
        return send_from_directory(
            os.path.dirname(file_path),
            os.path.basename(file_path),
            as_attachment=True,
            download_name=file_data['user_filename']
        )

@app.route('/download/<file_uuid>')
def download_file(file_uuid):
    """Скачивание файла"""
    files_info = load_files_info()
    
    if file_uuid not in files_info:
        flash('Файл не найден', 'error')
        return redirect(url_for('index'))
    
    file_data = files_info[file_uuid]
    
    # Формируем путь к файлу
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                            file_data['subfolder1'], 
                            file_data['subfolder2'],
                            f"{file_data['uuid']}{file_data['file_extension']}")
    
    if not os.path.exists(file_path):
        flash('Файл не найден на диске', 'error')
        return redirect(url_for('index'))
    
    # Отправляем файл с оригинальным именем
    return send_from_directory(
        os.path.dirname(file_path),
        os.path.basename(file_path),
        as_attachment=True,
        download_name=file_data['user_filename']
    )


@app.route('/delete/<file_uuid>')
def delete_file(file_uuid):
    """Удаление файла"""
    files_info = load_files_info()
    
    if file_uuid not in files_info:
        flash('Файл не найден', 'error')
        return redirect(url_for('index'))
    
    file_data = files_info[file_uuid]
    
    # Формируем путь к файлу
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                            file_data['subfolder1'], 
                            file_data['subfolder2'],
                            f"{file_data['uuid']}{file_data['file_extension']}")
    
    # Удаляем файл с диска
    if os.path.exists(file_path):
        os.remove(file_path)
        
        # Пытаемся удалить пустые папки
        try:
            os.rmdir(os.path.dirname(file_path))
            os.rmdir(os.path.join(app.config['UPLOAD_FOLDER'], file_data['subfolder1']))
        except:
            pass
    
    # Удаляем информацию из JSON
    del files_info[file_uuid]
    save_files_info(files_info)
    
    flash(f'Файл "{file_data["user_filename"]}" успешно удален', 'success')
    return redirect(url_for('index'))


@app.route('/file/<file_uuid>')
def file_info(file_uuid):
    """Страница с подробной информацией о файле"""
    files_info = load_files_info()
    
    if file_uuid not in files_info:
        flash('Файл не найден', 'error')
        return redirect(url_for('index'))
    
    file_data = files_info[file_uuid]
    return render_template('file_info.html', file=file_data)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)