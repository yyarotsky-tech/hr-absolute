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
async def transcribe_audio_endpoint(audio: UploadFile = File(...)):
    """Транскрибирует аудио через Яндекс SpeechKit (асинхронное распознавание)"""

    print("🔵 1. Эндпоинт вызван")

    # Проверяем наличие ключей
    if not all([YANDEX_API_KEY, YANDEX_FOLDER_ID, YANDEX_ACCESS_KEY, YANDEX_SECRET_KEY]):
        print("🔴 2. Ошибка: не все ключи заданы")
        raise HTTPException(
            status_code=500,
            detail="Yandex Cloud credentials are not configured. Please set YANDEX_API_KEY, YANDEX_FOLDER_ID, YANDEX_ACCESS_KEY, YANDEX_SECRET_KEY environment variables."
        )
    print("✅ 2. Ключи найдены")

    # Определяем формат по расширению
    filename = audio.filename or "audio.mp3"
    ext = os.path.splitext(filename)[1].lower().replace(".", "")
    print(f"✅ 3. Формат: {ext}")

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
    print(f"✅ 4. Файл сохранен: {tmp_path}, размер: {len(content)} байт")

    object_key = None
    s3 = None

    try:
        # 1. Загружаем файл в Object Storage
        object_key = f"audio_{uuid4()}.{ext}"
        print(f"✅ 5. Object key: {object_key}")

        session = boto3.session.Session()
        s3 = session.client(
            service_name='s3',
            endpoint_url='https://storage.yandexcloud.net',
            aws_access_key_id=YANDEX_ACCESS_KEY,
            aws_secret_access_key=YANDEX_SECRET_KEY,
            config=Config(
                signature_version='s3v4',
                region_name='ru-central1'
            )
        )
        print("✅ 6. S3 клиент создан")

        with open(tmp_path, 'rb') as f:
            s3.upload_fileobj(f, YANDEX_BUCKET_NAME, object_key)
        print("✅ 7. Файл загружен в бакет")

        file_uri = f"https://storage.yandexcloud.net/{YANDEX_BUCKET_NAME}/{object_key}"
        print(f"✅ 8. URI: {file_uri}")

        # 2. Запускаем распознавание
        print("🔵 9. Запуск распознавания...")
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
        print(f"✅ 10. Распознавание запущено, статус: {response.status_code}")

        if response.status_code != 200:
            print(f"🔴 11. Ошибка запуска: {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Recognition start failed: {response.text}"
            )

        operation_id = response.json()["id"]
        print(f"✅ 11. Операция: {operation_id}")

        # 3. Ждём результат
        print("🔵 12. Ожидание результата...")
        result_url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"
        max_attempts = 120
        attempts = 0

        while attempts < max_attempts:
            result_response = requests.get(result_url, headers=headers)
            if result_response.status_code != 200:
                print(f"🔴 13. Ошибка проверки статуса: {result_response.text}")
                raise HTTPException(
                    status_code=result_response.status_code,
                    detail=f"Status check failed: {result_response.text}"
                )

            data = result_response.json()
            if data.get("done"):
                print("✅ 13. Операция завершена")
                break

            attempts += 1
            time.sleep(3)

        if attempts >= max_attempts:
            print("🔴 14. Таймаут")
            raise HTTPException(status_code=408, detail="Recognition timeout")

        # 4. Извлекаем текст
        if "response" in data and "chunks" in data["response"]:
            text = "".join(chunk["alternatives"][0]["text"] for chunk in data["response"]["chunks"])
            if not text.strip():
                print("🔴 15. Речь не обнаружена")
                raise HTTPException(status_code=400, detail="No speech detected in audio")
            print(f"✅ 16. Транскрипция получена, длина: {len(text)}")
            return {
                "text": text.strip(),
                "data": {"text": text.strip()},
                "transcription": text.strip(),
                "result": text.strip()
            }
        else:
            print("🔴 15. Не удалось извлечь текст")
            raise HTTPException(status_code=500, detail="Failed to extract transcription")

    except Exception as e:
        print(f"🔴 ОшибКА: {type(e).__name__}: {str(e)}")
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
                pass


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