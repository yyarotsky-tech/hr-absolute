from .llm_client import ask_llm
from .prompt_builder import build_candidate_prompt

def analyze_candidate(data: dict) -> dict:
    prompt = build_candidate_prompt(data)
    answer = ask_llm(prompt)
    return {"full_report": answer}

import json

def analyze_workforce(data: dict) -> dict:
    from .prompt_builder import build_workforce_prompt
    prompt = build_workforce_prompt(data)
    answer = ask_llm(prompt)
    
    # Пытаемся распарсить ответ как JSON
    try:
        # Убираем возможные markdown-обёртки
        clean = answer.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        report = json.loads(clean)
    except Exception:
        # Если не удалось – возвращаем fallback-структуру
        report = {
            "summary": "Ошибка парсинга ответа. Пожалуйста, попробуйте ещё раз.",
            "recommendations": ["Повторите запрос позже", "Если ошибка повторяется, обратитесь в поддержку"],
            "new_positions": [],
            "total_headcount_change": 0,
            "estimated_budget_impact": "—",
            "vacancies": []

            print("=== RAW LLM RESPONSE ===")
            print(answer)
            ч]print("========================")
        }
    
    return {"status": "success", "report": report}
