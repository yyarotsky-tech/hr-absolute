def build_candidate_prompt(data: dict) -> str:
    audio_text = data.get("transcribed_text", "")
    vacancy = data.get("vacancy_text", "")
    resume = data.get("resume_text", "")
    market = data.get("market_analysis", "")
    profession = data.get("profession", "профессия не указана")
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
        tasks.append(f"1. Оцени соответствие резюме вакансии для позиции {profession}. Укажи процент, сильные стороны, слабые места.")
    elif vacancy and not resume:
        tasks.append(f"1. Оцени, насколько кандидат (по аудио) подходит под вакансию {profession}.")
    elif resume and not vacancy:
        tasks.append(f"1. Проанализируй резюме кандидата для позиции {profession}. Напиши, на какие задачи он может претендовать.")
    else:
        tasks.append(f"1. Проведи общий анализ аудио собеседования для позиции {profession}. Выдели ключевые компетенции.")

    tasks.append(f"2. Проанализируй рынок для профессии {profession}. Укажи востребованность, среднюю зарплату, конкуренцию.")
    tasks.append(f"3. Напиши предполагаемый ответ кандидату на позицию {profession} (приглашение, отказ, уточнения).")

    if transferable:
        tasks.insert(1, "Учитывай переносимые навыки и смежные компетенции, даже если нет прямого опыта.")
    if antifilter:
        tasks.insert(0, "РАБОТАЙ В РЕЖИМЕ АНТИФИЛЬТРА: ищи сценарии успеха, а не причины отказа.")

    prompt = f"""
Ты – профессиональный рекрутер, специализирующийся на найме {profession}.

Данные:
{chr(10).join(blocks)}

Выполни задачи:
{chr(10).join(tasks)}

Ответ оформи в виде разделов с заголовками:
=== СООТВЕТСТВИЕ ПОЗИЦИИ {profession.upper()} ===
=== АНАЛИЗ РЫНКА ===
=== ПРЕДПОЛАГАЕМЫЙ ОТВЕТ КАНДИДАТУ ===
"""
    return prompt
