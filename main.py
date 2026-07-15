import os
import tempfile
import json
import time
import requests
import boto3
from botocore.config import Config
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4

from core.db import (
    get_db_connection,
    save_candidate,
    get_all_candidates,
    get_candidate,
    search_candidates,
    delete_candidate,
    add_vacancy,
    get_all_vacancies,
    get_vacancy,
    update_vacancy,
    delete_vacancy,
    get_all_vacancies_paginated,
    add_volunteer_vacancy,
    get_all_volunteer_vacancies,
    delete_volunteer_vacancy,
    save_employee_assessment,
    get_employee_assessments,
    save_candidate_report,
    get_candidate_reports,
    get_or_create_conversation,
    add_message_to_conversation,
    get_conversation_messages,
    init_db
)
from core.analyzers import analyze_candidate
# from core.auth import verify_api_key  # Раскомментируйте, если есть

# Инициализация БД
init_db()

app = FastAPI(title="HR Absolute API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Настройки Яндекс.Облака (из переменных окружения) ---
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID")
YANDEX_BUCKET_NAME = os.environ.get("YANDEX_BUCKET_NAME", "hr-absolute-stt")
YANDEX_ACCESS_KEY = os.environ.get("YANDEX_ACCESS_KEY")
YANDEX_SECRET_KEY = os.environ.get("YANDEX_SECRET_KEY")


# ============================================================
# 1. ЭНДПОИНТ: /api/transcribe (ЗАГЛУШКА)
# ============================================================
@app.post("/api/transcribe")
async def transcribe_audio_endpoint(audio: UploadFile = File(...)):
    """ВРЕМЕННАЯ ЗАГЛУШКА для диагностики"""
    # Читаем файл, чтобы проверить, что он доходит
    content = await audio.read()
    print(f"✅ Файл получен: {audio.filename}, размер: {len(content)} байт")
    
    # Возвращаем тестовый текст
    return {"text": f"Тестовая транскрипция для файла {audio.filename}"}


# ============================================================
# 2. ОСТАЛЬНЫЕ ЭНДПОИНТЫ
# ============================================================

class AnalyzeCandidateRequest(BaseModel):
    candidate_id: Optional[int] = None
    transcribed_text: Optional[str] = None
    vacancy_text: Optional[str] = None
    resume_text: Optional[str] = None
    mode: str = "executive"

class AnalyzeCandidateResponse(BaseModel):
    fit_score: int
    strengths: List[str]
    weaknesses: List[str]
    questions_for_interview: List[str]
    recommendation: str
    red_flags: Optional[List[str]] = None
    reasoning: str
    candidate_id: int
    vacancy_id: Optional[int] = None
    analysis_id: int

@app.post("/api/analyze/candidate", response_model=AnalyzeCandidateResponse)
async def analyze_candidate_endpoint(request: AnalyzeCandidateRequest):
    """
    Анализирует кандидата на основе текста резюме, вакансии и транскрипции.
    Возвращает оценку, сильные/слабые стороны, вопросы и рекомендацию.
    """
    try:
        # Вызов вашей существующей функции анализа
        result = await analyze_candidate(
            resume_text=request.resume_text,
            vacancy_text=request.vacancy_text,
            transcribed_text=request.transcribed_text,
            mode=request.mode
        )
        
        # Сохранение кандидата и анализа в БД
        # Здесь ваш код сохранения...
        
        return AnalyzeCandidateResponse(
            fit_score=result.get("fit_score", 85),
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
            questions_for_interview=result.get("questions_for_interview", []),
            recommendation=result.get("recommendation", "Рекомендован"),
            red_flags=result.get("red_flags"),
            reasoning=result.get("reasoning", "Анализ завершен"),
            candidate_id=1,  # Замените на реальный ID из БД
            vacancy_id=1,    # Замените на реальный ID из БД
            analysis_id=1    # Замените на реальный ID из БД
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ============================================================
# 3. CRUD ЭНДПОИНТЫ
# ============================================================

@app.get("/api/candidates")
def get_candidates():
    return get_all_candidates()  # просто массив

@app.get("/api/vacancies")
def get_vacancies():
    return get_all_vacancies()  # просто массив

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# ============================================================
# 4. ЗАПУСК
# ============================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)