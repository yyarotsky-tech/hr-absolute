import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        conn = sqlite3.connect('hr_absolute.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vacancies (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                requirements TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candidates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transcribed_snippet TEXT,
                vacancy_snippet TEXT,
                resume_snippet TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employee_assessments (
                id SERIAL PRIMARY KEY,
                employee_name TEXT NOT NULL,
                position TEXT,
                leadership_score INTEGER,
                stress_resilience_score INTEGER,
                communication_score INTEGER,
                learnability_score INTEGER,
                responsibility_score INTEGER,
                strengths TEXT,
                growth_points TEXT,
                recommendations TEXT,
                burnout_risk TEXT,
                raw_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                requirements TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transcribed_snippet TEXT,
                vacancy_snippet TEXT,
                resume_snippet TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employee_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT NOT NULL,
                position TEXT,
                leadership_score INTEGER,
                stress_resilience_score INTEGER,
                communication_score INTEGER,
                learnability_score INTEGER,
                responsibility_score INTEGER,
                strengths TEXT,
                growth_points TEXT,
                recommendations TEXT,
                burnout_risk TEXT,
                raw_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidate_reports (
                id SERIAL PRIMARY KEY,
                candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
                report_type VARCHAR(50) NOT NULL,  -- 'full_analysis', 'summary', 'questions', 'match'
                input_data TEXT,                   -- JSON или текст входных данных (например, текст вакансии)
                report TEXT NOT NULL,               -- JSON или текст отчёта
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidate_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                report_type TEXT NOT NULL,
                input_data TEXT,
                report TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidate_reports (
                id SERIAL PRIMARY KEY,
                candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
                report_type VARCHAR(50) NOT NULL,
                input_data TEXT,
                report TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                user_id INTEGER,  -- если таблицы users пока нет, можно без REFERENCES
                messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()
    conn.close()



def save_candidate(name, data):
    conn = get_db_connection()
    cursor = conn.cursor()
    import json
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("INSERT INTO candidates (name, data, transcribed_snippet, vacancy_snippet, resume_snippet) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                       (name, json.dumps(data), data.get('transcribed_text', '')[:200], data.get('vacancy_text', '')[:200], data.get('resume_text', '')[:200]))
        cand_id = cursor.fetchone()['id']
    else:
        cursor.execute("INSERT INTO candidates (name, data, transcribed_snippet, vacancy_snippet, resume_snippet) VALUES (?, ?, ?, ?, ?)",
                       (name, json.dumps(data), data.get('transcribed_text', '')[:200], data.get('vacancy_text', '')[:200], data.get('resume_text', '')[:200]))
        cand_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return cand_id

def get_all_candidates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at, transcribed_snippet, vacancy_snippet, resume_snippet FROM candidates ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_candidate(cand_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    import json
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("SELECT id, name, created_at, transcribed_snippet, vacancy_snippet, resume_snippet, data FROM candidates WHERE id = %s", (cand_id,))
    else:
        cursor.execute("SELECT id, name, created_at, transcribed_snippet, vacancy_snippet, resume_snippet, data FROM candidates WHERE id = ?", (cand_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    candidate = dict(row)
    if 'data' in candidate:
        if isinstance(candidate['data'], str):
           candidate['data'] = json.loads(candidate['data'])

def search_candidates(keyword):
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("SELECT id, name, created_at, transcribed_snippet, vacancy_snippet, resume_snippet FROM candidates WHERE name LIKE %s OR transcribed_snippet LIKE %s OR vacancy_snippet LIKE %s OR resume_snippet LIKE %s ORDER BY created_at DESC",
                       (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
    else:
        cursor.execute("SELECT id, name, created_at, transcribed_snippet, vacancy_snippet, resume_snippet FROM candidates WHERE name LIKE ? OR transcribed_snippet LIKE ? OR vacancy_snippet LIKE ? OR resume_snippet LIKE ? ORDER BY created_at DESC",
                       (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_candidate(cand_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("DELETE FROM candidates WHERE id = %s", (cand_id,))
    else:
        cursor.execute("DELETE FROM candidates WHERE id = ?", (cand_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def save_rating(candidate_id, rating, comment):
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("UPDATE candidates SET rating = %s, rating_comment = %s WHERE id = %s", (rating, comment, candidate_id))
    else:
        cursor.execute("UPDATE candidates SET rating = ?, rating_comment = ? WHERE id = ?", (rating, comment, candidate_id))
    conn.commit()
    conn.close()

def add_vacancy(title, description, requirements, salary_min, salary_max):
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("INSERT INTO vacancies (title, description, requirements, salary_min, salary_max) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                       (title, description, requirements, salary_min, salary_max))
        vid = cursor.fetchone()['id']
    else:
        cursor.execute("INSERT INTO vacancies (title, description, requirements, salary_min, salary_max) VALUES (?, ?, ?, ?, ?)",
                       (title, description, requirements, salary_min, salary_max))
        vid = cursor.lastrowid
    conn.commit()
    conn.close()
    return vid

def get_all_vacancies(status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if status:
        if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
            cursor.execute("SELECT * FROM vacancies WHERE status = %s ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM vacancies WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        cursor.execute("SELECT * FROM vacancies ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_vacancy(vacancy_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("DELETE FROM vacancies WHERE id = %s", (vacancy_id,))
    else:
        cursor.execute("DELETE FROM vacancies WHERE id = ?", (vacancy_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def get_vacancy(vacancy_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("SELECT * FROM vacancies WHERE id = %s", (vacancy_id,))
    else:
        cursor.execute("SELECT * FROM vacancies WHERE id = ?", (vacancy_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_vacancy(vacancy_id, data):
    conn = get_db_connection()
    cursor = conn.cursor()
    set_clause = ", ".join([f"{key} = %s" if DATABASE_URL and DATABASE_URL.startswith("postgresql") else f"{key} = ?" for key in data.keys()])
    values = list(data.values()) + [vacancy_id]
    cursor.execute(f"UPDATE vacancies SET {set_clause} WHERE id = {'%s' if DATABASE_URL and DATABASE_URL.startswith('postgresql') else '?'}", values)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def save_employee_assessment(assessment_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    columns = ', '.join(assessment_data.keys())
    placeholders = ', '.join(['%s'] * len(assessment_data)) if DATABASE_URL and DATABASE_URL.startswith("postgresql") else ', '.join(['?'] * len(assessment_data))
    query = f"INSERT INTO employee_assessments ({columns}) VALUES ({placeholders})"
    cursor.execute(query, list(assessment_data.values()))
    conn.commit()
    conn.close()

def get_employee_assessments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employee_assessments ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_industry_avg(industry):
    # Placeholder implementation
    return {"avg_turnover": 12.5, "avg_time_to_hire": 38, "avg_salary": 380000}

def add_volunteer_vacancy(title, description, requirements, organization, contact):
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("INSERT INTO volunteer_vacancies (title, description, requirements, organization, contact) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                       (title, description, requirements, organization, contact))
        vid = cursor.fetchone()['id']
    else:
        cursor.execute("INSERT INTO volunteer_vacancies (title, description, requirements, organization, contact) VALUES (?, ?, ?, ?, ?)",
                       (title, description, requirements, organization, contact))
        vid = cursor.lastrowid
    conn.commit()
    conn.close()
    return vid

def get_all_volunteer_vacancies():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM volunteer_vacancies ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_volunteer_vacancy(vacancy_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("DELETE FROM volunteer_vacancies WHERE id = %s", (vacancy_id,))
    else:
        cursor.execute("DELETE FROM volunteer_vacancies WHERE id = ?", (vacancy_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def get_all_vacancies_paginated(skip: int, limit: int, status=None):
    """Возвращает словарь {'items': [...], 'total': int} для пагинации."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # ---- Подсчёт общего количества записей ----
    if status:
        if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
            cursor.execute("SELECT COUNT(*) FROM vacancies WHERE status = %s", (status,))
        else:
            cursor.execute("SELECT COUNT(*) FROM vacancies WHERE status = ?", (status,))
    else:
        cursor.execute("SELECT COUNT(*) FROM vacancies")
    total = cursor.fetchone()["count"] if DATABASE_URL and DATABASE_URL.startswith("postgresql") else cursor.fetchone()[0]

    # ---- Выборка нужной страницы ----
    if status:
        if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
            cursor.execute("""
                SELECT * FROM vacancies
                WHERE status = %s
                ORDER BY created_at DESC
                OFFSET %s LIMIT %s
            """, (status, skip, limit))
        else:
            cursor.execute("""
                SELECT * FROM vacancies
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (status, limit, skip))
    else:
        if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
            cursor.execute("""
                SELECT * FROM vacancies
                ORDER BY created_at DESC
                OFFSET %s LIMIT %s
            """, (skip, limit))
        else:
            cursor.execute("""
                SELECT * FROM vacancies
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, skip))

    rows = cursor.fetchall()
    conn.close()
    items = [dict(row) for row in rows]
    return {"items": items, "total": total}

def save_candidate_report(candidate_id: int, report_type: str, input_data: dict, report: dict) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    import json
    input_json = json.dumps(input_data, ensure_ascii=False) if input_data else None
    report_json = json.dumps(report, ensure_ascii=False)
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("""
            INSERT INTO candidate_reports (candidate_id, report_type, input_data, report)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (candidate_id, report_type, input_json, report_json))
        report_id = cursor.fetchone()['id']
    else:
        cursor.execute("""
            INSERT INTO candidate_reports (candidate_id, report_type, input_data, report)
            VALUES (?, ?, ?, ?)
        """, (candidate_id, report_type, input_json, report_json))
        report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return report_id

def get_candidate_reports(candidate_id: int, limit: int = 10) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    import json
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("""
            SELECT id, report_type, input_data, report, created_at
            FROM candidate_reports
            WHERE candidate_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (candidate_id, limit))
    else:
        cursor.execute("""
            SELECT id, report_type, input_data, report, created_at
            FROM candidate_reports
            WHERE candidate_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (candidate_id, limit))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        if item.get('input_data'):
            try:
                item['input_data'] = json.loads(item['input_data'])
            except:
                pass
        if item.get('report'):
            try:
                item['report'] = json.loads(item['report'])
            except:
                pass
        result.append(item)
    return result

def save_candidate_report(candidate_id: int, report_type: str, input_data: dict, report: dict) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    import json
    input_json = json.dumps(input_data, ensure_ascii=False) if input_data else None
    report_json = json.dumps(report, ensure_ascii=False)
    if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
        cursor.execute("""
            INSERT INTO candidate_reports (candidate_id, report_type, input_data, report)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (candidate_id, report_type, input_json, report_json))
        report_id = cursor.fetchone()['id']
    else:
        cursor.execute("""
            INSERT INTO candidate_reports (candidate_id, report_type, input_data, report)
            VALUES (?, ?, ?, ?)
        """, (candidate_id, report_type, input_json, report_json))
        report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return report_id

