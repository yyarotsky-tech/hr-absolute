from .config import client, DEEPSEEK_MODEL

def ask_llm(prompt: str, model: str = None, temperature: float = 0.7) -> str:
    if model is None:
        model = DEEPSEEK_MODEL
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature
    )
    return response.choices[0].message.content

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
            prompt += f"System: {content}
"
        elif role == "user":
            prompt += f"User: {content}
"
        elif role == "assistant":
            prompt += f"Assistant: {content}
"
    from .llm_client import ask_llm
    return ask_llm(prompt.strip())

