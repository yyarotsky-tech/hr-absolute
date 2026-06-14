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
    conn.commit()
    conn.close()

init_db()

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
        candidate['data'] = json.loads(candidate['data'])
    return candidate

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
