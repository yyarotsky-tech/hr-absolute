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
# 1. ЭНДПОИНТ: /api/transcribe (Яндекс SpeechKit)
# ============================================================
@app.post("/api/transcribe")
async def transcribe_audio_endpoint(
    audio: UploadFile = File(...)
):
    """Транскрибирует аудио через Яндекс SpeechKit (асинхронное распознавание)"""
    
    # Проверяем наличие ключей
    if not all([YANDEX_API_KEY, YANDEX_FOLDER_ID, YANDEX_ACCESS_KEY, YANDEX_SECRET_KEY]):
        raise HTTPException(
            status_code=500,
            detail="Yandex Cloud credentials are not configured. Please set YANDEX_API_KEY, YANDEX_FOLDER_ID, YANDEX_ACCESS_KEY, YANDEX_SECRET_KEY environment variables."
        )
    
    # Определяем формат по расширению
    filename = audio.filename or "audio.mp3"
    ext = os.path.splitext(filename)[1].lower().replace(".", "")
    
    allowed_extensions = ['mp3', 'ogg', 'opus', 'wav', 'flac']
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Сохраняем во временный файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    object_key = None
    s3 = None
    
    try:
        # 1. Загружаем файл в Object Storage
        object_key = f"audio_{uuid4()}.{ext}"
        
        session = boto3.session.Session()
        s3 = session.client(
            service_name='s3',
            endpoint_url='https://storage.yandexcloud.net',
            aws_access_key_id=YANDEX_ACCESS_KEY,
            aws_secret_access_key=YANDEX_SECRET_KEY,
            config=Config(signature_version='s3v4')
        )
        
        with open(tmp_path, 'rb') as f:
            s3.upload_fileobj(f, YANDEX_BUCKET_NAME, object_key)
        
        file_uri = f"https://storage.yandexcloud.net/{YANDEX_BUCKET_NAME}/{object_key}"
        
        # 2. Запускаем распознавание
        headers = {
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "x-folder-id": YANDEX_FOLDER_ID,
            "Content-Type": "application/json"
        }
        
        # Определяем кодировку
        audio_encoding = "MP3"
        if ext in ['ogg', 'opus']:
            audio_encoding = "OGG_OPUS"
        elif ext == 'wav':
            audio_encoding = "LINEAR16_PCM"
        elif ext == 'flac':
            audio_encoding = "FLAC"
        
        body = {
            "config": {
                "specification": {
                    "languageCode": "ru-RU",
                    "model": "general",
                    "audioEncoding": audio_encoding
                }
            },
            "audio": {
                "uri": file_uri
            }
        }
        
        response = requests.post(
            "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize",
            headers=headers,
            json=body
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Recognition start failed: {response.text}"
            )
        
        operation_id = response.json()["id"]
        
        # 3. Ждём результат
        result_url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"
        
        while True:
            result_response = requests.get(result_url, headers=headers)
            if result_response.status_code != 200:
                raise HTTPException(
                    status_code=result_response.status_code,
                    detail=f"Status check failed: {result_response.text}"
                )
            
            data = result_response.json()
            if data.get("done"):
                break
            
            time.sleep(3)
        
        # 4. Извлекаем текст
        if "response" in data and "chunks" in data["response"]:
            text = "".join(chunk["alternatives"][0]["text"] for chunk in data["response"]["chunks"])
            if not text.strip():
                raise HTTPException(status_code=400, detail="No speech detected in audio")
            return {"text": text.strip()}
        else:
            raise HTTPException(status_code=500, detail="Failed to extract transcription")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    finally:
        # Удаляем временный файл
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        # Удаляем файл из бакета (если загрузили)
        if s3 and object_key:
            try:
                s3.delete_object(Bucket=YANDEX_BUCKET_NAME, Key=object_key)
            except:
                pass  # Не критично


# ============================================================
# 2. ОСТАЛЬНЫЕ ЭНДПОИНТЫ (ваши существующие)
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
# 3. CRUD ЭНДПОИНТЫ (если есть)
# ============================================================

@app.get("/api/candidates")
def get_candidates():
    return {"candidates": get_all_candidates()}

@app.get("/api/vacancies")
def get_vacancies():
    return {"vacancies": get_all_vacancies()}

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