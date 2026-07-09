# Бэкап контекста чата

## 📌 Дата
YYYY-MM-DD

## 📋 Бэклог (актуальный)
### 🔥 Высокий приоритет
1. Пагинация для кандидатов – ...
2. Интеграция загрузки файлов на фронтенд – ...
3. Улучшенный поиск/фильтрация – ...

### 🟡 Средний приоритет
- ...

### 🟢 Низкий приоритет
- ...

## 🧩 Инфраструктурный трек
- Переход на PostgreSQL
- Docker-контейнеризация
- GitHub Actions
- Интеграция RouterAI

## 🏗️ Архитектура (кратко)
- Бэкенд: FastAPI, Python 3.14, SQLite/PostgreSQL, DeepSeek API (через RouterAI)
- Фронтенд: React (Vite), ReactMarkdown + remark-gfm, Axios
- Деплой: Render (бэкенд и фронтенд), PostgreSQL
- Аутентификация: API-ключ (в планах JWT)

## 🚧 Текущий статус
- ✅ Бэкенд работает, все эндпоинты доступны.
- ✅ Фронтенд работает, чат форматирует ответы.
- ⚠️ Нет пагинации для кандидатов, нет JWT.
- ❌ Нет миграций Alembic, нет Redis.

## 🧠 История решений и проблем
- `max_tokens` увеличен до 8000, чтобы ответы не обрывались.
- Добавлен `react-markdown` и `remark-gfm` для форматирования таблиц.
- Отказались от Amvera и Timeweb из-за проблем с Docker-образами и манифестами.
- Сейчас используем Render (PostgreSQL, бэкенд, фронтенд).

## 🔑 Переменные окружения (без секретов)
- `API_KEY=test_key_123`
- `DB_PATH=/data/hr_absolute.db` (для локального SQLite)
- `DATABASE_URL` (для PostgreSQL на Render)
- `DEEPSEEK_API_KEY` (или RouterAI)

## 🔗 Ссылки
- Бэкенд: https://hr-absolute.onrender.com
- Фронтенд: https://hr-dashboard-react.onrender.com
- GitHub (бэкенд): https://github.com/yyarotsky-tech/hr-absolute
- GitHub (фронтенд): https://github.com/yyarotsky-tech/hr-dashboard-react

## 📌 Следующие шаги (после восстановления)
1. Интеграция RouterAI.
2. Пагинация для кандидатов.
3. Docker-контейнеризация.
