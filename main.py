import io
import os
import tempfile
import requests
from decouple import config
from zipfile import ZipFile
from telebot import TeleBot

# Загрузка конфигурации из .env файла
TOKEN = config('TELEGRAM_TOKEN')
API_KEY = config('API_KEY')  # Ключ API для доступа к модели

# URL модели
API_URL = "http://84.201.152.196:8020/v1/completions"

def create_report(contents):
    """Создание временного файла для отчёта"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(contents)
            return temp_file.name
    except Exception as e:
        return f"Ошибка при создании отчета: {str(e)}"

def call_model_api(messages) -> str:
    """Отправляем запрос к модели и получаем ответ"""
    headers = {
        "Authorization": f"{API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "mistral-nemo-instruct-2407",
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.3
    }
    
    try:
        response = requests.post(API_URL, json=data, headers=headers)
        response.raise_for_status()  # Проверка на ошибки HTTP
        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', 'Не удалось получить ответ от модели')
    except requests.exceptions.RequestException as e:
        return f"Ошибка при обращении к API: {str(e)}"

def process_file(file) -> str:
    """Функция для обработки файлов (.txt, .py и т.д.)"""
    print("Processing file:", file)
    try:
        messages = [
            {"role": "system", "content": "отвечай на русском языке"},
            {"role": "user", "content": f"Что это за файл: {file}"}
        ]
        model_response = call_model_api(messages)
        report = create_report(f"Результат обработки файла: {model_response}")
        return report
    except Exception as e:
        return f"Ошибка при обработке файла: {str(e)}"

def process_archive(zip_file) -> str:
    """Функция для обработки архивов (.zip)"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as report_file:
            with ZipFile(io.BytesIO(zip_file), 'r') as archive:
                for file in archive.namelist():
                    try:
                        with archive.open(file) as nested_file:
                            file_contents = nested_file.read().decode('utf-8')
                            report_file.write(f"Содержимое файла {file}:\n{file_contents}\n\n")
                    except Exception as e:
                        report_file.write(f"Ошибка при обработке файла {file}: {str(e)}\n\n")
            return report_file.name
    except Exception as e:
        return f"Ошибка при обработке архива: {str(e)}"

def remove_temp_file(file_path):
    """Удаляем временный файл после обработки"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Временный файл {file_path} удален.")
        else:
            print(f"Файл {file_path} не найден для удаления.")
    except Exception as e:
        print(f"Ошибка при удалении файла {file_path}: {str(e)}")

# Создание бота и обработка сообщений
bot = TeleBot(TOKEN)

@bot.message_handler(content_types=['document'])
def handle_document(message):
    try:
        # Получаем файл
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Обработка в зависимости от типа файла
        if message.document.file_name.endswith('.zip'):
            result_report = process_archive(downloaded_file)
            r_type = "архив"
        else:
            result_report = process_file(downloaded_file)
            r_type = "файл"

        # Ответ с прикрепленным отчетом
        bot.reply_to(message, f"Ваш {r_type} был обработан, результаты прикреплены к сообщению.")
        with open(result_report, "rb") as report_file:
            bot.send_document(chat_id=message.chat.id, document=report_file)

        # Удаление временного отчета после отправки
        remove_temp_file(result_report)

    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! Я бот для проверки проектов. Отправьте мне файл или архив для обработки.")

@bot.message_handler(func=lambda message: True)
def unknown_command(message):
    bot.reply_to(message, "Я не знаю, что делать с этим. Пожалуйста, отправьте мне файл или архив для обработки.")

if __name__ == '__main__':
    print("Bot started")
    bot.infinity_polling()
