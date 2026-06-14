from .llm_client import ask_llm

def build_candidate_prompt(data: dict) -> str:
    audio_text = data.get("transcribed_text", "")
    vacancy = data.get("vacancy_text", "")
    resume = data.get("resume_text", "")
    market = data.get("market_analysis", "")
    profession = data.get("profession", "")
    transferable = data.get("options", {}).get("transferable", True)
    antifilter = data.get("options", {}).get("antifilter", True)

    blocks = [
        f"Расшифровка аудио собеседования: {audio_text if audio_text else '❌ Не предоставлена'}",
        f"Текст вакансии: {vacancy if vacancy else '❌ Не предоставлен'}",
        f"Текст резюме кандидата: {resume if resume else '❌ Не предоставлен'}",
        f"Анализ рынка: {market if market else '❌ Не предоставлен (используй свои знания)'}"
    ]

    tasks = []
    if vacancy and resume:
        tasks.append(f"1. Оцени соответствие резюме вакансии для позиции {(profession or 'профессия не указана').upper()}. Укажи процент, сильные стороны, слабые места.")
    elif vacancy and not resume:
        tasks.append(f"1. Оцени, насколько кандидат (по аудио) подходит под вакансию {(profession or 'профессия не указана').upper()}.")
    elif resume and not vacancy:
        tasks.append(f"1. Проанализируй резюме кандидата для позиции {(profession or 'профессия не указана').upper()}. Напиши, на какие задачи он может претендовать.")
    else:
        tasks.append(f"1. Проведи общий анализ аудио собеседования для позиции {(profession or 'профессия не указана').upper()}. Выдели ключевые компетенции.")

    tasks.append(f"2. Проанализируй рынок для профессии {(profession or 'профессия не указана').upper()}. Укажи востребованность, среднюю зарплату, конкуренцию.")
    tasks.append(f"3. Напиши предполагаемый ответ кандидату на позицию {(profession or 'профессия не указана').upper()} (приглашение, отказ, уточнения).")

    if transferable:
        tasks.insert(1, "Учитывай переносимые навыки и смежные компетенции, даже если нет прямого опыта.")
    if antifilter:
        tasks.insert(0, "РАБОТАЙ В РЕЖИМЕ АНТИФИЛЬТРА: ищи сценарии успеха, а не причины отказа.")

    prompt = f"""
Ты – профессиональный рекрутер, специализирующийся на найме {(profession or 'профессия не указана').upper()}.

Данные:
{chr(10).join(blocks)}

Выполни задачи:
{chr(10).join(tasks)}

=== ЗАРПЛАТНАЯ АНАЛИТИКА ===
1. Укажи рыночную вилку для этой позиции (минимальную, среднюю, максимальную) по региону (Москва/СПБ/удалёнка) с учётом опыта кандидата и стека технологий.
2. Дай конкретную рекомендацию по офферу (диапазон или точную сумму) для этого кандидата.
3. Прогноз удержания: как долго кандидат (с учётом его опыта и ожиданий) вероятнее всего останется в компании с такой зарплатой? (коротко: менее 6 мес, 6-12 мес, 1-2 года, более 2 лет).

Ответ оформи в виде разделов с заголовками:
=== СООТВЕТСТВИЕ ПОЗИЦИИ {(profession or 'профессия не указана').upper()} ===
=== АНАЛИЗ РЫНКА ===
=== ЗАРПЛАТНАЯ АНАЛИТИКА ===
=== ПРЕДПОЛАГАЕМЫЙ ОТВЕТ КАНДИДАТУ ===
"""
    return prompt

def build_workforce_prompt(data: dict) -> str:
    tasks = data.get('tasks', '')
    current_staff = data.get('current_staff', '')
    options = data.get('options', {})

    prompt = f"""
Ты — эксперт по планированию штата (workforce planning). Ответь строго в формате JSON, без лишних пояснений, без markdown.

Задачи организации (что нужно сделать):
{tasks}

Текущий штат:
{current_staff}

Структура ответа (все поля обязательны):
{{
  "summary": "Краткое резюме (2-3 предложения)",
  "recommendations": ["Рекомендация 1", "Рекомендация 2", ...],
  "new_positions": [
    {{"title": "Название должности", "quantity": число, "reason": "почему нужна"}}
  ],
  "total_headcount_change": целое_число,
  "estimated_budget_impact": "Строка с оценкой бюджета",
  "vacancies": [
    {{"title": "Вакансия", "requirements": "требования", "salary_range": "диапазон", "schedule": "график"}}
  ]
}}

Если какие-то данные неизвестны, укажи "Не указано" или пустой массив.
"""
    return prompt.strip()
