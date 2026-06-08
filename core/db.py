import sqlite3
import json
from typing import List, Dict, Any, Optional

DB_PATH = "hr_absolute.db"

def init_db():
    """Создает таблицы, если их нет"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                transcribed_text TEXT,
                vacancy_text TEXT,
                resume_text TEXT,
                market_analysis TEXT,
                profession TEXT,
                report TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def save_candidate(name: str, data: Dict[str, Any]) -> int:
    """Сохраняет кандидата, возвращает его id"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            INSERT INTO candidates (
                name, transcribed_text, vacancy_text, resume_text,
                market_analysis, profession, report
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            data.get("transcribed_text"),
            data.get("vacancy_text"),
            data.get("resume_text"),
            data.get("market_analysis"),
            data.get("profession"),
            json.dumps(data.get("report", {})) if data.get("report") else None
        ))
        return cursor.lastrowid

def get_all_candidates() -> List[Dict[str, Any]]:
    """Возвращает список всех кандидатов (кратко)"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, name, created_at,
                   substr(transcribed_text, 1, 100) as transcribed_snippet,
                   substr(vacancy_text, 1, 100) as vacancy_snippet,
                   substr(resume_text, 1, 100) as resume_snippet
            FROM candidates ORDER BY created_at DESC
        """).fetchall()
    return [dict(row) for row in rows]

def get_candidate(candidate_id: int) -> Optional[Dict[str, Any]]:
    """Возвращает полный профиль кандидата"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("report"):
            data["report"] = json.loads(data["report"])
        return data

def search_candidates(keyword: str) -> List[Dict[str, Any]]:
    """Поиск по всем текстовым полям"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, name, created_at,
                   substr(transcribed_text, 1, 100) as transcribed_snippet
            FROM candidates
            WHERE name LIKE ? OR transcribed_text LIKE ? OR vacancy_text LIKE ? OR resume_text LIKE ?
            ORDER BY created_at DESC
        """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')).fetchall()
    return [dict(row) for row in rows]

def delete_candidate(candidate_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
        return cursor.rowcount > 0

# Инициализация базы при импорте модуля
init_db()
