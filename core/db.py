import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import json

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL and DATABASE_URL.startswith("postgresql")

def get_db_connection():
    if IS_POSTGRES:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        conn = sqlite3.connect(os.environ.get("DB_PATH", "/data/hr_absolute.db"))
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_POSTGRES:
        # PostgreSQL tables
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
    else:
        # SQLite tables
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
    
    conn.commit()
    conn.close()

# ---------- ОСТАЛЬНЫЕ ФУНКЦИИ (ВСТАВЬТЕ ИХ СЮДА) ----------
# save_candidate, get_all_candidates, get_candidate, search_candidates,
# delete_candidate, save_rating, get_industry_avg, add_vacancy,
# get_all_vacancies, get_all_vacancies_paginated, get_vacancy,
# update_vacancy, delete_vacancy, add_volunteer_vacancy,
# get_all_volunteer_vacancies, delete_volunteer_vacancy,
# save_employee_assessment, get_employee_assessments,
# save_candidate_report, get_candidate_reports