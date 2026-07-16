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
