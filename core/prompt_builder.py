def build_candidate_prompt(data: dict) -> str:
    transcribed = data.get('transcribed_text', '')
    vacancy = data.get('vacancy_text', '')
    resume = data.get('resume_text', '')
    market = data.get('market_analysis', '')
    profession = data.get('profession', '')
    options = data.get('options', {})

    prompt = f"""
Ты — экспертный HR-аналитик. Проведи комплексный анализ кандидата на основе следующих данных.

Транскрипция собеседования:
{transcribed}

Описание вакансии:
{vacancy}

Резюме кандидата:
{resume}

Анализ рынка:
{market}

Профессия:
{profession}

Дополнительные опции:
{options}

Твоя задача — предоставить анализ в формате Markdown. Используй:
- Заголовки (##, ###) для разделов.
- Списки (-, 1.) для перечисления.
- Жирный текст (**текст**) для выделения ключевых выводов.
- Таблицы (| колонка | колонка |) для сравнений.
- Разделители (---) между смысловыми блоками.

Структура отчёта:
1. **Общее впечатление** (краткое резюме, 1-2 абзаца).
2. **Сильные стороны** (список).
3. **Зоны роста** (список).
4. **Соответствие вакансии** (таблица: критерий, оценка, комментарий).
5. **Рекомендации** (конкретные шаги).
6. **Вопросы для собеседования** (список).

Ответ должен быть информативным, структурированным и полезным для HR-специалиста.
"""
    return prompt.strip()

def build_workforce_prompt(data: dict) -> str:
    """
    Формирует промпт для workforce planning.
    """
    tasks = data.get('tasks', '')
    current_staff = data.get('current_staff', '')
    options = data.get('options', {})

    prompt = f"""
Ты — эксперт по планированию штата (workforce planning). Ответь строго в формате JSON, без пояснений, без markdown.

Задачи организации:
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
