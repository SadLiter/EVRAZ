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
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.md') as temp_file:
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
            {"role": "system", "content": "Пиши на русском языке"},
            {"role": "user", "content": f'''Ты — бот, который проверяет код на наличие ошибок, нарушений лучших практик и других потенциальных проблем. Твоя задача — анализировать присланный код и давать обратную связь в виде списка пунктов. Каждый пункт должен содержать:

Описание ошибки или проблемы.
Причину, почему это является ошибкой или плохой практикой.
Рекомендации по исправлению или улучшению.
Если возможно, предложи альтернативное решение или улучшение для данного участка кода.
Ты не должен переписывать код, а только указывать на ошибки и предложить пути их исправления.

Ты не должен объяснять общие концепции программирования, а сосредоточиться только на конкретных ошибках и улучшениях в присланном коде. Ответ должен быть структурирован по пунктам, чтобы было легко понять, что и где нужно исправить.

Обрати внимание на следующие типы проблем:

Ошибки синтаксиса.
Проблемы с производительностью.
Нарушения стиля кодирования.
Недостаток комментариев и документации.
Использование устаревших или небезопасных методов.
Отвечай только на те ошибки, которые реально можно исправить или улучшить.: {file}'''}
        ]
        model_response = call_model_api(messages)
        report = create_report(f"Результат обработки файла: {model_response}")
        return report
    except Exception as e:
        return f"Ошибка при обработке файла: {str(e)}"

def process_archive(zip_file) -> str:
    """Функция для обработки архивов (.zip) с разбиением на части"""
    try:
        # Временный файл для отчета
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as report_file:
            with ZipFile(io.BytesIO(zip_file), 'r') as archive:
                files = archive.namelist()
                
                # Собираем содержимое файлов архива в группы
                chunks = []
                current_chunk = ""
                max_chunk_size = 1500  # Максимальный размер запроса (примерно, в символах)

                for file in files:
                    with archive.open(file) as nested_file:
                        file_contents = nested_file.read().decode('utf-8')
                        
                        # Проверяем, не превышает ли размер текущего куска максимальный размер
                        if len(current_chunk) + len(file_contents) > max_chunk_size:
                            # Если превышает, добавляем текущий кусок в список и начинаем новый
                            chunks.append(current_chunk)
                            current_chunk = file_contents
                        else:
                            current_chunk += f"Содержимое файла {file}:\n{file_contents}\n\n"
                
                # Добавляем последний кусок, если он есть
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Обрабатываем каждый кусок отдельно
                for chunk in chunks:
                    messages = [
                        {"role": "system", "content": "Пиши на русском языке"},
                        {"role": "user", "content": f'''Ты — бот, который проверяет код на наличие ошибок, нарушений лучших практик и других потенциальных проблем. Твоя задача — анализировать присланный код и давать обратную связь в виде списка пунктов. Каждый пункт должен содержать:

Описание ошибки или проблемы.
Причину, почему это является ошибкой или плохой практикой.
Рекомендации по исправлению или улучшению.
Если возможно, предложи альтернативное решение или улучшение для данного участка кода.
Ты не должен переписывать код, а только указывать на ошибки и предложить пути их исправления.

Ты не должен объяснять общие концепции программирования, а сосредоточиться только на конкретных ошибках и улучшениях в присланном коде. Ответ должен быть структурирован по пунктам, чтобы было легко понять, что и где нужно исправить.

Обрати внимание на следующие типы проблем:

Ошибки синтаксиса.
Проблемы с производительностью.
Нарушения стиля кодирования.
Недостаток комментариев и документации.
Использование устаревших или небезопасных методов.
Отвечай только на те ошибки, которые реально можно исправить или улучшить.: {chunk}'''}
                    ]
                    
                    # Получаем результат от модели
                    model_response = call_model_api(messages)
                    
                    # Добавляем результат в отчет
                    report_file.write(f"Результат обработки архива:\n{model_response}\n\n")
        
        # Возвращаем путь к временному отчету
        return report_file.name

    except Exception as e:
        # Обработка ошибок как для архива, так и для файлов внутри архива
        return f"Ошибка при обработке архива или файлов: {str(e)}"




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
