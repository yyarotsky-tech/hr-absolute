import sqlite3
import json
from typing import List, Dict, Any, Optional

DB_PATH = "hr_absolute.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # Таблица кандидатов
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
        # Таблица оценок
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            )
        """)
        # Таблица бенчмарков (для будущего использования)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                industry TEXT,
                employee_count INTEGER,
                turnover_rate REAL,
                time_to_hire INTEGER,
                avg_salary INTEGER,
                data_year INTEGER
            )
        """)

def save_candidate(name: str, data: Dict[str, Any]) -> int:
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

def save_rating(candidate_id: int, rating: int, comment: str = None) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "INSERT INTO ratings (candidate_id, rating, comment) VALUES (?, ?, ?)",
            (candidate_id, rating, comment)
        )
        return cursor.lastrowid

def get_ratings(candidate_id: int = None) -> List[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if candidate_id:
            rows = conn.execute("SELECT * FROM ratings WHERE candidate_id = ? ORDER BY created_at DESC", (candidate_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM ratings ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]

# Инициализация базы
init_db()

def add_benchmark(company_name: str, industry: str, employee_count: int, turnover_rate: float, time_to_hire: int, avg_salary: int, data_year: int = None) -> int:
    import sqlite3
    from datetime import datetime
    if data_year is None:
        data_year = datetime.now().year
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            INSERT INTO benchmarks (company_name, industry, employee_count, turnover_rate, time_to_hire, avg_salary, data_year)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (company_name, industry, employee_count, turnover_rate, time_to_hire, avg_salary, data_year))
        return cursor.lastrowid

def get_benchmarks(industry: str = None, min_employees: int = None, max_employees: int = None) -> List[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM benchmarks WHERE 1=1"
        params = []
        if industry:
            query += " AND industry = ?"
            params.append(industry)
        if min_employees:
            query += " AND employee_count >= ?"
            params.append(min_employees)
        if max_employees:
            query += " AND employee_count <= ?"
            params.append(max_employees)
        query += " ORDER BY data_year DESC"
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]

def get_industry_avg(industry: str) -> Dict:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT 
                AVG(turnover_rate) as avg_turnover,
                AVG(time_to_hire) as avg_time_to_hire,
                AVG(avg_salary) as avg_salary
            FROM benchmarks 
            WHERE industry = ?
        """, (industry,)).fetchone()
    return dict(row) if row else {}

# ---------- Vacancies ----------
def init_vacancies_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
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

def add_vacancy(title: str, description: str = None, requirements: str = None, 
                salary_min: int = None, salary_max: int = None) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            INSERT INTO vacancies (title, description, requirements, salary_min, salary_max)
            VALUES (?, ?, ?, ?, ?)
        """, (title, description, requirements, salary_min, salary_max))
        return cursor.lastrowid

def get_all_vacancies(status: str = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if status:
            rows = conn.execute("SELECT * FROM vacancies WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM vacancies ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]

def get_vacancy(vacancy_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM vacancies WHERE id = ?", (vacancy_id,)).fetchone()
        return dict(row) if row else None

def update_vacancy(vacancy_id: int, **kwargs):
    with sqlite3.connect(DB_PATH) as conn:
        fields = [f"{k} = ?" for k in kwargs.keys()]
        values = list(kwargs.values()) + [vacancy_id]
        conn.execute(f"UPDATE vacancies SET {', '.join(fields)} WHERE id = ?", values)

def delete_vacancy(vacancy_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM vacancies WHERE id = ?", (vacancy_id,))
        return cursor.rowcount > 0

# Инициализация таблицы vacancies
init_vacancies_table()

# ---------- Matches ----------
def init_matches_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                vacancy_id INTEGER NOT NULL,
                score INTEGER,
                strengths TEXT,
                growth_points TEXT,
                success_scenario TEXT,
                alternative_roles TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id),
                FOREIGN KEY (vacancy_id) REFERENCES vacancies(id)
            )
        """)

def save_match(candidate_id: int, vacancy_id: int, result: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO matches (candidate_id, vacancy_id, score, strengths, growth_points, success_scenario, alternative_roles)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate_id, vacancy_id,
            result.get("score"),
            result.get("strengths"),
            result.get("growth_points"),
            result.get("success_scenario"),
            result.get("alternative_roles")
        ))

def get_matches(candidate_id: int = None, vacancy_id: int = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM matches WHERE 1=1"
        params = []
        if candidate_id:
            query += " AND candidate_id = ?"
            params.append(candidate_id)
        if vacancy_id:
            query += " AND vacancy_id = ?"
            params.append(vacancy_id)
        query += " ORDER BY score DESC"
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]

def clear_matches():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM matches")

init_matches_table()

# ---------- Volunteer Vacancies ----------
def init_volunteer_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS volunteer_vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                requirements TEXT,
                organization TEXT,
                contact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def add_volunteer_vacancy(title: str, description: str = None, requirements: str = None, 
                          organization: str = None, contact: str = None) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            INSERT INTO volunteer_vacancies (title, description, requirements, organization, contact)
            VALUES (?, ?, ?, ?, ?)
        """, (title, description, requirements, organization, contact))
        return cursor.lastrowid

def get_all_volunteer_vacancies() -> List[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM volunteer_vacancies ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]

def delete_volunteer_vacancy(vacancy_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM volunteer_vacancies WHERE id = ?", (vacancy_id,))
        return cursor.rowcount > 0

init_volunteer_table()

# ---------- Employee Assessments ----------
def init_employee_assessments_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS employee_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT NOT NULL,
                position TEXT,
                assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        """)

def save_employee_assessment(data: dict) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            INSERT INTO employee_assessments (
                employee_name, position, leadership_score, stress_resilience_score,
                communication_score, learnability_score, responsibility_score,
                strengths, growth_points, recommendations, burnout_risk, raw_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("employee_name"),
            data.get("position"),
            data.get("leadership_score"),
            data.get("stress_resilience_score"),
            data.get("communication_score"),
            data.get("learnability_score"),
            data.get("responsibility_score"),
            data.get("strengths"),
            data.get("growth_points"),
            data.get("recommendations"),
            data.get("burnout_risk"),
            data.get("raw_text")
        ))
        return cursor.lastrowid

def get_employee_assessments(employee_name: str = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if employee_name:
            rows = conn.execute("SELECT * FROM employee_assessments WHERE employee_name = ? ORDER BY created_at DESC", (employee_name,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM employee_assessments ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]

init_employee_assessments_table()
