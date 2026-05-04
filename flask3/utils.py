import os
import json
from pathlib import Path


def get_project_root():
    """Получение корневой директории проекта"""
    return Path(__file__).parent


def load_json(folder_name, file_name):
    """
    Загрузка данных из JSON файла.
    Если файл или папка не существуют, создаются.
    """
    # Получаем абсолютный путь
    base_path = get_project_root()
    folder_path = base_path / folder_name
    filename = folder_path / file_name
    
    # Создаём папку, если её нет (создаёт все промежуточные папки)
    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Создана папка: {folder_path}")
    
    # Создаём файл, если его нет
    if not filename.exists():
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        print(f"📄 Создан файл: {filename}")
    
    # Загружаем данные
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Если файл повреждён, создаём новый
        print(f"⚠️ Файл {filename} повреждён. Создаём новый.")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        return {}


def save_json(folder_name, file_name, save_dct):
    """
    Сохранение данных в JSON файл.
    """
    # Получаем абсолютный путь
    base_path = get_project_root()
    folder_path = base_path / folder_name
    filename = folder_path / file_name
    
    # Создаём папку, если её нет
    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"📁 Создана папка: {folder_path}")
    
    # Сохраняем данные
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(save_dct, f, ensure_ascii=False, indent=4)