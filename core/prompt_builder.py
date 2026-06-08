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

Ответ оформи в виде разделов с заголовками:
=== СООТВЕТСТВИЕ ПОЗИЦИИ {(profession or 'профессия не указана').upper()} ===
=== АНАЛИЗ РЫНКА ===
=== ПРЕДПОЛАГАЕМЫЙ ОТВЕТ КАНДИДАТУ ===
"""
    return prompt

def build_workforce_prompt(data: dict) -> str:
    tasks = data.get("tasks", "")
    staff = data.get("current_staff", "")
    options = data.get("options", {})
    generate_vacancies = options.get("generate_vacancies", True)

    prompt = f"""
Ты – эксперт по HR-аналитике и организационному дизайну. Проанализируй текущий штат и список задач.

Данные:
- Задачи/проекты: {tasks if tasks else '❌ не указаны'}
- Текущий штат (роли, навыки, загрузка): {staff if staff else '❌ не указан'}

Твоя задача:
1. Оценить текущую загрузку и распределение задач. Выявить перегруженных сотрудников, узкие места, избыточные зоны.
2. Найти возможности для перераспределения задач без найма (совмещение, переобучение, аутсорсинг).
3. Указать, какие роли или компетенции отсутствуют, и предложить добавить их в штат.
4. {"Создать структурированное описание вакансий для недостающих ролей." if generate_vacancies else ""}
5. Дать итоговые рекомендации по оптимизации штата и повышению эффективности.

Ответ оформи в виде разделов:
=== АНАЛИЗ ТЕКУЩЕЙ ЗАГРУЗКИ ===
=== ПЕРЕРАСПРЕДЕЛЕНИЕ ЗАДАЧ (внутренние резервы) ===
=== НЕДОСТАЮЩИЕ РОЛИ И КОМПЕТЕНЦИИ ===
=== {"СГЕНЕРИРОВАННЫЕ ВАКАНСИИ" if generate_vacancies else "РЕКОМЕНДАЦИИ ПО НАЙМУ"} ===
=== ИТОГОВЫЕ РЕКОМЕНДАЦИИ ===
"""
    return prompt
