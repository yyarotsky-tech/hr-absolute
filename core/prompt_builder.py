def build_candidate_prompt(data: dict) -> str:
    """
    Формирует промпт для анализа кандидата.
    """
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

Твоя задача:
- Оценить соответствие кандидата вакансии.
- Выделить сильные стороны и зоны роста.
- Дать рекомендации по дальнейшему взаимодействию.
- Предложить, какие вопросы задать на собеседовании.

Ответ должен быть структурированным, содержательным и полезным для HR-специалиста.
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