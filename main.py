import os
import tempfile
import whisper
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from core.database import get_db, engine, Base
from core.models import Candidate, Vacancy, AnalysisHistory
from core.analyzers import analyze_candidate
from core.auth import verify_api_key

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="HR Absolute API")

# CORS (разрешаем все для демо)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 1. НОВЫЙ ЭНДПОИНТ: /api/transcribe (отдельная транскрипция)
# ============================================================
@app.post("/api/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Принимает аудиофайл (WAV, MP3, M4A, WebM, OGG),
    транскрибирует через Whisper,
    возвращает текст.
    """
    # 1. Проверка расширения
    allowed_extensions = ('.wav', '.mp3', '.m4a', '.webm', '.ogg', '.flac')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Allowed: {', '.join(allowed_extensions)}"
        )

    # 2. Сохраняем временный файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 3. Загружаем модель Whisper (кешируется после первого вызова)
        model = whisper.load_model("base")  # или "small" / "medium" для лучшего качества
        result = model.transcribe(tmp_path)
        transcribed_text = result["text"].strip()

        if not transcribed_text:
            raise HTTPException(status_code=400, detail="No speech detected in audio")

        return {"text": transcribed_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # 4. Удаляем временный файл
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ============================================================
# 2. СУЩЕСТВУЮЩИЙ ЭНДПОИНТ: /api/analyze/candidate
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

def save_candidate(name: str, data: Dict[str, Any], db: Session) -> int:
    """Сохраняет кандидата в БД (если нет candidate_id)"""
    candidate = Candidate(
        name=name,
        resume_text=data.get("resume_text"),
        transcribed_text=data.get("transcribed_text"),
        source="api"
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate.id

@app.post("/api/analyze/candidate", response_model=AnalyzeCandidateResponse)
async def analyze_candidate_endpoint(
    request: AnalyzeCandidateRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    data = request.model_dump()
    
    if not any([data.get("transcribed_text"), data.get("vacancy_text"), data.get("resume_text")]):
        raise HTTPException(status_code=400, detail="No input data provided")
    
    candidate_id = request.candidate_id
    if not candidate_id:
        candidate_name = "Анонимный кандидат"
        if request.resume_text and len(request.resume_text) > 0:
            candidate_name = request.resume_text[:50].strip() or "Кандидат"
        elif request.transcribed_text:
            candidate_name = request.transcribed_text[:50].strip() or "Кандидат"
        candidate_id = save_candidate(candidate_name, data, db)
    
    # Сохраняем вакансию (если есть)
    vacancy_id = None
    if request.vacancy_text:
        vacancy = Vacancy(
            title=request.vacancy_text[:100],
            description=request.vacancy_text,
            source="api"
        )
        db.add(vacancy)
        db.commit()
        db.refresh(vacancy)
        vacancy_id = vacancy.id
    
    # Запускаем AI-анализ
    analysis_result = await analyze_candidate(
        request.resume_text,
        request.vacancy_text,
        request.transcribed_text,
        mode=request.mode
    )
    
    # Сохраняем историю анализа
    history = AnalysisHistory(
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
        fit_score=analysis_result["fit_score"],
        strengths=analysis_result["strengths"],
        weaknesses=analysis_result["weaknesses"],
        questions=analysis_result["questions_for_interview"],
        recommendation=analysis_result["recommendation"],
        red_flags=analysis_result.get("red_flags"),
        reasoning=analysis_result.get("reasoning")
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    
    return AnalyzeCandidateResponse(
        fit_score=analysis_result["fit_score"],
        strengths=analysis_result["strengths"],
        weaknesses=analysis_result["weaknesses"],
        questions_for_interview=analysis_result["questions_for_interview"],
        recommendation=analysis_result["recommendation"],
        red_flags=analysis_result.get("red_flags"),
        reasoning=analysis_result.get("reasoning", "Анализ завершен"),
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
        analysis_id=history.id
    )


# ============================================================
# 3. ДРУГИЕ ЭНДПОИНТЫ (CRUD для кандидатов, вакансий, история)
# ============================================================
@app.get("/api/candidates")
def get_candidates(db: Session = Depends(get_db)):
    return db.query(Candidate).all()

@app.get("/api/vacancies")
def get_vacancies(db: Session = Depends(get_db)):
    return db.query(Vacancy).all()

@app.get("/api/history")
def get_history(db: Session = Depends(get_db)):
    return db.query(AnalysisHistory).order_by(AnalysisHistory.created_at.desc()).all()

# ============================================================
# 4. HEALTH CHECK (для Render)
# ============================================================
@app.get("/health")
def health_check():
    return {"status": "ok"}


# ============================================================
# 5. ЗАПУСК (для локальной разработки)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)