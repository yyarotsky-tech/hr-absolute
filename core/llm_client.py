import os
import requests
import json

def ask_llm(prompt: str) -> str:
    """
    Базовый вызов LLM. Замените на вашу реальную реализацию.
    Например, через DeepSeek, OpenAI или локальную модель.
    """
    # Вставьте сюда ваш код вызова LLM
    # Пока возвращаем тестовый ответ
    return f"Это тестовый ответ на ваш запрос: {prompt[:50]}..."

def ask_llm_with_history(messages: list) -> str:
    """
    Отправляет историю сообщений в LLM и возвращает ответ.
    Использует существующую функцию ask_llm, преобразуя историю в единый промпт.
    """
    prompt = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            prompt += f"System: {content}\n"
        elif role == "user":
            prompt += f"User: {content}\n"
        elif role == "assistant":
            prompt += f"Assistant: {content}\n"
    return ask_llm(prompt.strip())
