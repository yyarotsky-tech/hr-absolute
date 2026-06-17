import os
from openai import OpenAI

# Читаем переменные окружения
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")

# Инициализируем клиент (если ключ есть)
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_API_BASE
) if DEEPSEEK_API_KEY else None

def ask_llm(prompt: str) -> str:
    """
    Отправляет одиночный промпт в DeepSeek и возвращает ответ.
    """
    if not client:
        return "Ошибка: DEEPSEEK_API_KEY не задан. Добавьте переменную окружения."
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"DeepSeek error: {e}")
        return f"Извините, произошла ошибка: {str(e)}"

def ask_llm_with_history(messages: list) -> str:
    """
    Отправляет историю сообщений в DeepSeek (формат чата) и возвращает ответ.
    """
    if not client:
        return "Ошибка: DEEPSEEK_API_KEY не задан. Добавьте переменную окружения."
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"DeepSeek chat error: {e}")
        return f"Извините, произошла ошибка: {str(e)}"
