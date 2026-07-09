import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import uuid

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL and DATABASE_URL.startswith("postgresql")

def get_db_connection():
    if IS_POSTGRES:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        conn = sqlite3.connect(os.environ.get("DB_PATH", "hr_absolute.db"))
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_POSTGRES:
        cursor.execute("""
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
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                transcribed_text TEXT,
                vacancy_text TEXT,
                resume_text TEXT,
                market_analysis TEXT,
                profession TEXT,
                report TEXT,
                data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_assessments (
                id SERIAL PRIMARY KEY,
                employee_name TEXT NOT NULL,
                position TEXT,
                raw_text TEXT,
                leadership_score INTEGER,
                stress_resilience_score INTEGER,
                communication_score INTEGER,
                learnability_score INTEGER,
                responsibility_score INTEGER,
                burnout_risk TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                user_id INTEGER,
                messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor.execute("""
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
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                transcribed_text TEXT,
                vacancy_text TEXT,
                resume_text TEXT,
                market_analysis TEXT,
                profession TEXT,
                report TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT NOT NULL,
                position TEXT,
                raw_text TEXT,
                leadership_score INTEGER,
                stress_resilience_score INTEGER,
                communication_score INTEGER,
                learnability_score INTEGER,
                responsibility_score INTEGER,
                burnout_risk TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidate_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                report_type TEXT NOT NULL,
                input_data TEXT,
                report TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER,
                messages TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

# ---------- Candidate functions ----------
def save_candidate(name: str, data: dict) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    data_json = json.dumps(data, ensure_ascii=False)
    transcribed = data.get('transcribed_text', '') or ''
    vacancy = data.get('vacancy_text', '') or ''
    resume = data.get('resume_text', '') or ''
    market = data.get('market_analysis', '') or ''
    profession = data.get('profession', '') or ''
    report = data.get('report', '') or ''
    
    if IS_POSTGRES:
        cursor.execute("""
            INSERT INTO candidates (name, transcribed_text, vacancy_text, resume_text, market_analysis, profession, report, data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (name, transcribed, vacancy, resume, market, profession, report, data_json))
        cand_id = cursor.fetchone()['id']
    else:
        cursor.execute("""
            INSERT INTO candidates (name, transcribed_text, vacancy_text, resume_text, market_analysis, profession, report, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, transcribed, vacancy, resume, market, profession, report, data_json))
        cand_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return cand_id

def get_all_candidates():
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("SELECT id, name, created_at, transcribed_text, vacancy_text, resume_text FROM candidates ORDER BY created_at DESC")
    else:
        cursor.execute("SELECT id, name, created_at, transcribed_text, vacancy_text, resume_text FROM candidates ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_candidate(cand_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("SELECT * FROM candidates WHERE id = %s", (cand_id,))
    else:
        cursor.execute("SELECT * FROM candidates WHERE id = ?", (cand_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    candidate = dict(row)
    if 'data' in candidate and candidate['data']:
        if isinstance(candidate['data'], str):
            try:
                candidate['data'] = json.loads(candidate['data'])
            except:
                pass
        # если уже dict, оставляем как есть
    return candidate

def search_candidates(keyword: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("SELECT id, name, created_at, transcribed_text, vacancy_text, resume_text FROM candidates WHERE name LIKE %s OR transcribed_text LIKE %s OR vacancy_text LIKE %s OR resume_text LIKE %s ORDER BY created_at DESC",
                       (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
    else:
        cursor.execute("SELECT id, name, created_at, transcribed_text, vacancy_text, resume_text FROM candidates WHERE name LIKE ? OR transcribed_text LIKE ? OR vacancy_text LIKE ? OR resume_text LIKE ? ORDER BY created_at DESC",
                       (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_candidate(cand_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("DELETE FROM candidates WHERE id = %s", (cand_id,))
    else:
        cursor.execute("DELETE FROM candidates WHERE id = ?", (cand_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def save_rating(candidate_id: int, rating: int, comment: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("INSERT INTO ratings (candidate_id, rating, comment) VALUES (%s, %s, %s)", (candidate_id, rating, comment))
    else:
        cursor.execute("INSERT INTO ratings (candidate_id, rating, comment) VALUES (?, ?, ?)", (candidate_id, rating, comment))
    conn.commit()
    conn.close()

def get_industry_avg(industry: str):
    return {"industry": industry, "avg_salary": 80000, "turnover": 12.5}

# ---------- Vacancy functions ----------
def add_vacancy(title: str, description: str = None, requirements: str = None, 
                salary_min: int = None, salary_max: int = None) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("""
            INSERT INTO vacancies (title, description, requirements, salary_min, salary_max)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (title, description, requirements, salary_min, salary_max))
        vid = cursor.fetchone()['id']
    else:
        cursor.execute("""
            INSERT INTO vacancies (title, description, requirements, salary_min, salary_max)
            VALUES (?, ?, ?, ?, ?)
        """, (title, description, requirements, salary_min, salary_max))
        vid = cursor.lastrowid
    conn.commit()
    conn.close()
    return vid

def get_all_vacancies(status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if status:
        if IS_POSTGRES:
            cursor.execute("SELECT * FROM vacancies WHERE status = %s ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM vacancies WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        cursor.execute("SELECT * FROM vacancies ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_vacancies_paginated(skip: int, limit: int, status=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if status:
        if IS_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM vacancies WHERE status = %s", (status,))
            total = cursor.fetchone()['count']
            cursor.execute("""
                SELECT * FROM vacancies
                WHERE status = %s
                ORDER BY created_at DESC
                OFFSET %s LIMIT %s
            """, (status, skip, limit))
        else:
            cursor.execute("SELECT COUNT(*) FROM vacancies WHERE status = ?", (status,))
            total = cursor.fetchone()[0]
            cursor.execute("""
                SELECT * FROM vacancies
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (status, limit, skip))
    else:
        if IS_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM vacancies")
            total = cursor.fetchone()['count']
            cursor.execute("""
                SELECT * FROM vacancies
                ORDER BY created_at DESC
                OFFSET %s LIMIT %s
            """, (skip, limit))
        else:
            cursor.execute("SELECT COUNT(*) FROM vacancies")
            total = cursor.fetchone()[0]
            cursor.execute("""
                SELECT * FROM vacancies
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, skip))
    rows = cursor.fetchall()
    conn.close()
    items = [dict(row) for row in rows]
    return {"items": items, "total": total}

def get_vacancy(vacancy_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("SELECT * FROM vacancies WHERE id = %s", (vacancy_id,))
    else:
        cursor.execute("SELECT * FROM vacancies WHERE id = ?", (vacancy_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_vacancy(vacancy_id: int, data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    set_clause = ", ".join([f"{key} = %s" if IS_POSTGRES else f"{key} = ?" for key in data.keys()])
    values = list(data.values()) + [vacancy_id]
    cursor.execute(f"UPDATE vacancies SET {set_clause} WHERE id = {'%s' if IS_POSTGRES else '?'}", values)
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def delete_vacancy(vacancy_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("DELETE FROM vacancies WHERE id = %s", (vacancy_id,))
    else:
        cursor.execute("DELETE FROM vacancies WHERE id = ?", (vacancy_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# ---------- Volunteer vacancies ----------
def add_volunteer_vacancy(title: str, description: str = None, requirements: str = None,
                         organization: str = None, contact: str = None) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("""
            INSERT INTO volunteer_vacancies (title, description, requirements, organization, contact)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (title, description, requirements, organization, contact))
        vid = cursor.fetchone()['id']
    else:
        cursor.execute("""
            INSERT INTO volunteer_vacancies (title, description, requirements, organization, contact)
            VALUES (?, ?, ?, ?, ?)
        """, (title, description, requirements, organization, contact))
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

def delete_volunteer_vacancy(vacancy_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("DELETE FROM volunteer_vacancies WHERE id = %s", (vacancy_id,))
    else:
        cursor.execute("DELETE FROM volunteer_vacancies WHERE id = ?", (vacancy_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# ---------- Employee assessments ----------
def save_employee_assessment(employee_name: str, position: str, raw_text: str) -> int:
    import random
    conn = get_db_connection()
    cursor = conn.cursor()
    leadership = random.randint(60, 95)
    stress = random.randint(60, 95)
    communication = random.randint(60, 95)
    learnability = random.randint(60, 95)
    responsibility = random.randint(60, 95)
    burnout_risk = random.choice(["низкий", "средний", "высокий"])
    if IS_POSTGRES:
        cursor.execute("""
            INSERT INTO employee_assessments (employee_name, position, raw_text, leadership_score, stress_resilience_score,
                communication_score, learnability_score, responsibility_score, burnout_risk)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (employee_name, position, raw_text, leadership, stress, communication, learnability, responsibility, burnout_risk))
        aid = cursor.fetchone()['id']
    else:
        cursor.execute("""
            INSERT INTO employee_assessments (employee_name, position, raw_text, leadership_score, stress_resilience_score,
                communication_score, learnability_score, responsibility_score, burnout_risk)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (employee_name, position, raw_text, leadership, stress, communication, learnability, responsibility, burnout_risk))
        aid = cursor.lastrowid
    conn.commit()
    conn.close()
    return aid

def get_employee_assessments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employee_assessments ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ---------- Candidate reports ----------
def save_candidate_report(candidate_id: int, report_type: str, input_data: dict, report: dict) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    input_json = json.dumps(input_data, ensure_ascii=False) if input_data else None
    report_json = json.dumps(report, ensure_ascii=False)
    if IS_POSTGRES:
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
    if IS_POSTGRES:
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

# ---------- Conversation functions ----------
def get_or_create_conversation(session_id: str) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    if IS_POSTGRES:
        cursor.execute("SELECT id, session_id, messages, created_at, updated_at FROM conversations WHERE session_id = %s", (session_id,))
    else:
        cursor.execute("SELECT id, session_id, messages, created_at, updated_at FROM conversations WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    if row:
        result = dict(row)
        if isinstance(result['messages'], str):
            result['messages'] = json.loads(result['messages'])
        conn.close()
        return result
    else:
        messages = []
        if IS_POSTGRES:
            cursor.execute("INSERT INTO conversations (session_id, messages) VALUES (%s, %s) RETURNING id, session_id, messages, created_at, updated_at",
                           (session_id, json.dumps(messages)))
            row = cursor.fetchone()
        else:
            cursor.execute("INSERT INTO conversations (session_id, messages) VALUES (?, ?)",
                           (session_id, json.dumps(messages)))
            cursor.execute("SELECT id, session_id, messages, created_at, updated_at FROM conversations WHERE id = last_insert_rowid()")
            row = cursor.fetchone()
        conn.commit()
        result = dict(row)
        if isinstance(result['messages'], str):
            result['messages'] = json.loads(result['messages'])
        conn.close()
        return result

def add_message_to_conversation(session_id: str, role: str, content: str):
    conv = get_or_create_conversation(session_id)
    messages = conv['messages']
    messages.append({"role": role, "content": content})
    conn = get_db_connection()
    cursor = conn.cursor()
    messages_json = json.dumps(messages, ensure_ascii=False)
    if IS_POSTGRES:
        cursor.execute("UPDATE conversations SET messages = %s, updated_at = CURRENT_TIMESTAMP WHERE session_id = %s",
                       (messages_json, session_id))
    else:
        cursor.execute("UPDATE conversations SET messages = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                       (messages_json, session_id))
    conn.commit()
    conn.close()

def get_conversation_messages(session_id: str) -> list:
    conv = get_or_create_conversation(session_id)
    return conv['messages']