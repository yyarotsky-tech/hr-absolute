from datetime import datetime
import inspect
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
from fastapi import FastAPI, UploadFile, File as FastAPIFile, HTTPException, Security, Depends, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from core.transcriber import transcribe_audio
from core.analyzers import analyze_candidate, analyze_workforce
from core.file_parser import extract_text_from_file, extract_text_from_bytes
from core.db import save_candidate, get_all_candidates, get_candidate, search_candidates, delete_candidate, save_rating, get_industry_avg, add_vacancy, get_all_vacancies, delete_vacancy, add_volunteer_vacancy, get_all_volunteer_vacancies, delete_volunteer_vacancy, save_employee_assessment, get_employee_assessments, get_all_vacancies_paginated, get_candidate_reports, get_conversation_messages, add_message_to_conversation

load_dotenv()

class AnalyzeCandidateRequest(BaseModel):
    candidate_id: Optional[int] = None
    transcribed_text: Optional[str] = None
    vacancy_text: Optional[str] = None
    resume_text: Optional[str] = None
    market_analysis: Optional[str] = None
    profession: Optional[str] = None
    options: Optional[Dict[str, bool]] = {}

class AnalyzeCandidateResponse(BaseModel):
    status: str
    report: Dict[str, Any]

API_KEY = os.getenv("API_KEY", "test_key_123")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key is None or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return api_key

app = FastAPI(title="HR Absolute API", version="0.1.0")

# CORS настроен с явным разрешением методов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# ---------- Модели ----------
class AnalyzeCandidateRequest(BaseModel):
    transcribed_text: Optional[str] = None
    vacancy_text: Optional[str] = None
    resume_text: Optional[str] = None
    market_analysis: Optional[str] = None
    profession: Optional[str] = None
    options: Optional[Dict[str, bool]] = {"transferable": True, "antifilter": True}
    candidate_id: Optional[int] = None

class AnalyzeCandidateResponse(BaseModel):
    status: str
    report: Dict[str, Any]

class TranscribeResponse(BaseModel):
    status: str
    transcribed_text: str

class WorkforceRequest(BaseModel):
    tasks: str
    current_staff: str
    options: Optional[Dict[str, bool]] = {"generate_vacancies": True}

class WorkforceResponse(BaseModel):
    status: str
    report: Dict[str, Any]

class CandidateSaveRequest(BaseModel):
    name: str
    data: Dict[str, Any]

class CandidateResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    transcribed_snippet: Optional[str] = None
    vacancy_snippet: Optional[str] = None
    resume_snippet: Optional[str] = None

class CandidateDetailResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    transcribed_text: Optional[str] = None
    vacancy_text: Optional[str] = None
    resume_text: Optional[str] = None
    market_analysis: Optional[str] = None
    profession: Optional[str] = None
    report: Optional[Dict[str, Any]] = None

class SearchRequest(BaseModel):
    keyword: str

class RatingRequest(BaseModel):
    candidate_id: int
    rating: int
    comment: Optional[str] = None

class QueryRequest(BaseModel):
    text: Optional[str] = None
    min_rating: Optional[int] = None
    max_rating: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

class BenchmarkCompareRequest(BaseModel):
    industry: str
    employee_count: int
    turnover_rate: float
    time_to_hire: int
    avg_salary: int
    additional_question: Optional[str] = None

class VacancyRequest(BaseModel):
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

class VacancyResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    status: str
    created_at: datetime

class VacancyUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    status: Optional[str] = None

class VolunteerRequest(BaseModel):
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    organization: Optional[str] = None
    contact: Optional[str] = None

class VolunteerResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    organization: Optional[str] = None
    contact: Optional[str] = None
    created_at: datetime

class EmployeeAssessmentRequest(BaseModel):
    employee_name: str
    position: Optional[str] = None
    raw_text: str

class EmployeeAssessmentResponse(BaseModel):
    status: str
    assessment: Dict[str, Any]

class MatchRequest(BaseModel):
    candidate_id: Optional[int] = None
    vacancy_id: Optional[int] = None

class MatchResponse(BaseModel):
    candidate_id: int
    candidate_name: str
    vacancy_id: int
    vacancy_title: str
    score: int
    strengths: str
    growth_points: str
    success_scenario: str
    alternative_roles: str

# ---------- Корневые эндпоинты ----------
@app.get("/")
async def root():
    return {"message": "HR Absolute API is running"}

@app.get("/api/check_key")
async def check_key(api_key: str = Depends(verify_api_key)):
    return {"status": "valid", "message": "API key is valid"}

# ---------- Транскрипция ----------
@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_endpoint(
    audio: UploadFile = FastAPIFile(...),
    language: str = "ru",
    api_key: str = Depends(verify_api_key)
):
    suffix = os.path.splitext(audio.filename)[1] or ".mp3"
    with tempfile.NamedTemporaryFastAPIFile(suffix=suffix, delete=False) as tmp:
        content = await audio.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio file")
        tmp.write(content)
        tmp_path = tmp.name
    try:
        transcribed = transcribe_audio(tmp_path, language=language)
        if not transcribed:
            raise HTTPException(status_code=400, detail="Could not transcribe audio")
        return TranscribeResponse(status="success", transcribed_text=transcribed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)

# ---------- Анализ кандидата ----------
@app.post("/api/analyze/candidate", response_model=AnalyzeCandidateResponse)
async def analyze_candidate_endpoint(
    request: AnalyzeCandidateRequest,
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
        from core.db import save_candidate
        candidate_id = save_candidate(candidate_name, data)
    
    try:
        from core.analyzers import analyze_candidate
        report = analyze_candidate(data)
        from core.db import save_candidate_report
        save_candidate_report(
            candidate_id=candidate_id,
            report_type="full_analysis",
            input_data=data,
            report=report if isinstance(report, dict) else {"raw": report}
        )
        return AnalyzeCandidateResponse(status="success", report=report)
    except Exception as e:
        print("\n" + "="*60)
        print("ОШИБКА В analyze_candidate_endpoint:")
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

# ---------- Workforce Planning ----------
@app.post("/api/analyze/workforce", response_model=WorkforceResponse)
async def workforce_endpoint(
    request: WorkforceRequest,
    api_key: str = Depends(verify_api_key)
):
    data = request.model_dump()
    if not data.get("tasks") and not data.get("current_staff"):
        raise HTTPException(status_code=400, detail="Provide at least tasks or current_staff")
    try:
        report = analyze_workforce(data)
        return WorkforceResponse(status="success", report=report)
    except Exception as e:
        print(f"Workforce error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------- База кандидатов ----------
@app.post("/api/candidates/save", response_model=CandidateResponse)
async def save_candidate_endpoint(request: CandidateSaveRequest, api_key: str = Depends(verify_api_key)):
    cand_id = save_candidate(request.name, request.data)
    candidate = get_candidate(cand_id)
    return CandidateResponse(
        id=candidate["id"],
        name=candidate["name"],
        created_at=candidate["created_at"],
        transcribed_snippet=candidate.get("transcribed_text", "")[:100] or "",
        vacancy_snippet=candidate.get("vacancy_text", "")[:100] or "",
        resume_snippet=candidate.get("resume_text", "")[:100] or ""
    )

@app.get("/api/candidates", response_model=List[CandidateResponse])
async def list_candidates(api_key: str = Depends(verify_api_key)):
    return get_all_candidates()

@app.get("/api/candidates/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate_endpoint(candidate_id: int, api_key: str = Depends(verify_api_key)):
    cand = get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return cand

@app.post("/api/candidates/search", response_model=List[CandidateResponse])
async def search_candidates_endpoint(request: SearchRequest, api_key: str = Depends(verify_api_key)):
    return search_candidates(request.keyword)

@app.delete("/api/candidates/{candidate_id}")
async def delete_candidate_endpoint(candidate_id: int, api_key: str = Depends(verify_api_key)):
    deleted = delete_candidate(candidate_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"status": "deleted"}

# ---------- Rate Endpoint ----------
@app.post("/api/rate")
async def rate_candidate(request: RatingRequest, api_key: str = Depends(verify_api_key)):
    if request.rating < 1 or request.rating > 10:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 10")
    save_rating(request.candidate_id, request.rating, request.comment)
    return {"status": "success", "message": f"Rating {request.rating} saved for candidate {request.candidate_id}"}

# ---------- Query Endpoint ----------
@app.post("/api/query")
async def query_candidates(request: QueryRequest, api_key: str = Depends(verify_api_key)):
    candidates = get_all_candidates()
    result = []
    for cand in candidates:
        if request.date_from and cand["created_at"] < request.date_from:
            continue
        if request.date_to and cand["created_at"] > request.date_to:
            continue
        if request.text:
            text_match = False
            full_text = f"{cand.get('transcribed_snippet') or ''} {cand.get('vacancy_snippet') or ''} {cand.get('resume_snippet') or ''}".lower()
            if request.text.lower() in full_text:
                text_match = True
            if not text_match:
                continue
        snippet = cand.get("transcribed_snippet") or ""
        result.append({
            "id": cand["id"],
            "name": cand["name"],
            "created_at": cand["created_at"],
            "snippet": snippet[:100] if snippet else ""
        })
    return {"status": "success", "count": len(result), "candidates": result}

# ---------- Бенчмаркинг ----------
@app.post("/api/benchmark/compare")
async def compare_benchmark(request: BenchmarkCompareRequest, api_key: str = Depends(verify_api_key)):
    industry_avg = get_industry_avg(request.industry)
    from core.llm_client import ask_llm
    prompt = f"""
Ты — HR-аналитик. Сравни показатели компании с рыночными средними.

Показатели компании (отрасль: {request.industry}, число сотрудников: {request.employee_count}):
- Текучесть: {request.turnover_rate}%
- Время закрытия вакансии: {request.time_to_hire} дней
- Средняя зарплата: {request.avg_salary} руб.

Рыночные средние (по отрасли {request.industry}):
- Средняя текучесть: {industry_avg.get('avg_turnover', 'нет данных')}%
- Среднее время закрытия: {industry_avg.get('avg_time_to_hire', 'нет данных')} дней
- Средняя зарплата: {industry_avg.get('avg_salary', 'нет данных')} руб.

Задачи:
1. Сравни каждый показатель с рынком (лучше/хуже/на уровне).
2. Оцени риски.
3. Дай рекомендации по улучшению.
"""
    if request.additional_question:
        prompt += f"\n\nДОПОЛНИТЕЛЬНЫЙ ВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{request.additional_question}\n\nПожалуйста, ответь на этот вопрос в дополнение к основному анализу."

    analysis = ask_llm(prompt)
    return {
        "status": "success",
        "company_metrics": {
            "turnover_rate": request.turnover_rate,
            "time_to_hire": request.time_to_hire,
            "avg_salary": request.avg_salary
        },
        "industry_avg": industry_avg,
        "analysis": analysis
    }

# ---------- Росстат ----------
@app.get("/api/rosstat/construction")
async def get_rosstat_construction(api_key: str = Depends(verify_api_key)):
    from core.rosstat_client import get_construction_salary
    data = get_construction_salary()
    if data and data.get("value"):
        return {
            "status": "success",
            "industry": "Строительство",
            "avg_salary": data["value"],
            "period": data.get("period", "последний доступный период"),
            "source": "Росстат (ЕМИСС)"
        }
    else:
        return {
            "status": "error",
            "message": "Не удалось получить данные. Возможно, API временно недоступно."
        }

# ---------- Вакансии ----------
@app.post("/api/vacancies/add", response_model=VacancyResponse)
async def add_vacancy_endpoint(request: VacancyRequest, api_key: str = Depends(verify_api_key)):
    vid = add_vacancy(request.title, request.description, request.requirements, request.salary_min, request.salary_max)
    return VacancyResponse(id=vid, title=request.title, description=request.description,
                          requirements=request.requirements, salary_min=request.salary_min,
                          salary_max=request.salary_max, status="active", created_at="")

@app.get("/api/vacancies")
async def list_vacancies(api_key: str = Depends(verify_api_key)):
    return get_all_vacancies()

@app.delete("/api/vacancies/{vacancy_id}")
async def delete_vacancy(vacancy_id: int, api_key: str = Depends(verify_api_key)):
    if not delete_vacancy(vacancy_id):
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return {"status": "deleted"}

@app.patch("/api/vacancies/{vacancy_id}")
async def update_vacancy(vacancy_id: int, request: VacancyUpdateRequest, api_key: str = Depends(verify_api_key)):
    from core.db import get_vacancy, update_vacancy, get_candidate_reports, get_candidate_reports
    vacancy = get_vacancy(vacancy_id)
    if not vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    update_data = request.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated = update_vacancy(vacancy_id, update_data)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update vacancy")
    return {"status": "updated", "id": vacancy_id}

@app.get("/api/vacancies/paginated")
async def list_vacancies_paginated(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    return get_all_vacancies_paginated(skip=skip, limit=limit, status=status)

# ---------- Волонтёрство ----------
@app.post("/api/volunteer/add", response_model=VolunteerResponse)
async def add_volunteer(request: VolunteerRequest, api_key: str = Depends(verify_api_key)):
    vid = add_volunteer_vacancy(request.title, request.description, request.requirements, request.organization, request.contact)
    return VolunteerResponse(id=vid, title=request.title, description=request.description,
                           requirements=request.requirements, organization=request.organization,
                           contact=request.contact, created_at="")

@app.get("/api/volunteer", response_model=List[VolunteerResponse])
async def list_volunteer(api_key: str = Depends(verify_api_key)):
    return get_all_volunteer_vacancies()

@app.delete("/api/volunteer/{vacancy_id}")
async def delete_volunteer(vacancy_id: int, api_key: str = Depends(verify_api_key)):
    if not delete_volunteer_vacancy(vacancy_id):
        raise HTTPException(status_code=404, detail="Volunteer vacancy not found")
    return {"status": "deleted"}

# ---------- Матчинг ----------
@app.post("/api/match", response_model=List[MatchResponse])
async def run_matching(request: MatchRequest, api_key: str = Depends(verify_api_key)):
    from core.db import get_all_candidates, get_all_vacancies, get_candidate_reports, get_candidate_reports
    from core.llm_client import ask_llm
    import json
    candidates = get_all_candidates()
    vacancies = get_all_vacancies(status="active")
    if request.candidate_id:
        candidates = [c for c in candidates if c["id"] == request.candidate_id]
    if request.vacancy_id:
        vacancies = [v for v in vacancies if v["id"] == request.vacancy_id]
    results = []
    for candidate in candidates:
        for vacancy in vacancies:
            prompt = f"""
Проанализируй соответствие кандидата вакансии.

Данные кандидата:
- Имя: {candidate.get('name')}
- Текст из аудио/резюме: {candidate.get('transcribed_snippet', '')} {candidate.get('resume_snippet', '')}
- Вакансия: {vacancy.get('title')} - {vacancy.get('description', '')} {vacancy.get('requirements', '')}

Твоя задача:
1. Оцени соответствие в процентах (0-100).
2. Напиши 2-3 сильные стороны кандидата для этой вакансии.
3. Напиши 2-3 точки роста (чего не хватает).
4. Предложи сценарий успеха (как кандидат может быть полезен).
5. Если соответствие <50%, предложи альтернативные роли.

Ответ строго в формате JSON:
{{
    "score": 85,
    "strengths": "Опыт Python 5 лет, знание FastAPI",
    "growth_points": "Нет опыта с Docker",
    "success_scenario": "Пригласить на собеседование",
    "alternative_roles": "Мидл разработчик, технический писатель"
}}
"""
            try:
                response = ask_llm(prompt)
                result = json.loads(response)
            except Exception as e:
                result = {
                    "score": 50,
                    "strengths": "Анализ не удался",
                    "growth_points": "Попробуйте позже",
                    "success_scenario": "Требуется ручная проверка",
                    "alternative_roles": ""
                }
            results.append({
                "candidate_id": candidate["id"],
                "candidate_name": candidate["name"],
                "vacancy_id": vacancy["id"],
                "vacancy_title": vacancy["title"],
                "score": result.get("score", 50),
                "strengths": result.get("strengths", ""),
                "growth_points": result.get("growth_points", ""),
                "success_scenario": result.get("success_scenario", ""),
                "alternative_roles": result.get("alternative_roles", "")
            })
    return results

# ---------- Оценка сотрудников ----------
@app.post("/api/employee/assess", response_model=EmployeeAssessmentResponse)
async def assess_employee(request: EmployeeAssessmentRequest, api_key: str = Depends(verify_api_key)):
    from core.llm_client import ask_llm
    import json
    prompt = f"""
Ты — HR-эксперт. Оцени сотрудника по следующим параметрам на основе текста.

Данные о сотруднике:
Имя: {request.employee_name}
Должность: {request.position or "не указана"}
Текст: {request.raw_text}

Оцени каждый параметр от 1 до 10 (только число):
- leadership_score
- stress_resilience_score
- communication_score
- learnability_score
- responsibility_score

Также укажи:
- strengths (строка, 3 сильные стороны через запятую)
- growth_points (строка, 3 зоны роста через запятую)
- recommendations (строка, рекомендации)
- burnout_risk (одно слово: низкий, средний или высокий)

Верни ТОЛЬКО JSON без пояснений. Пример:
{{"leadership_score": 6, "stress_resilience_score": 4, "communication_score": 8, "learnability_score": 9, "responsibility_score": 7, "strengths": "коммуникабельность, обучаемость, ответственность", "growth_points": "лидерство, стрессоустойчивость", "recommendations": "курс по управлению стрессом", "burnout_risk": "средний"}}
"""
    try:
        response = ask_llm(prompt)
        result = json.loads(response)
    except Exception as e:
        result = {
            "leadership_score": 5,
            "stress_resilience_score": 5,
            "communication_score": 5,
            "learnability_score": 5,
            "responsibility_score": 5,
            "strengths": "Анализ не удался",
            "growth_points": "Попробуйте позже",
            "recommendations": "Требуется ручная проверка",
            "burnout_risk": "неизвестен"
        }
    assessment_data = {
        "employee_name": request.employee_name,
        "position": request.position,
        "leadership_score": result.get("leadership_score"),
        "stress_resilience_score": result.get("stress_resilience_score"),
        "communication_score": result.get("communication_score"),
        "learnability_score": result.get("learnability_score"),
        "responsibility_score": result.get("responsibility_score"),
        "strengths": result.get("strengths"),
        "growth_points": result.get("growth_points"),
        "recommendations": result.get("recommendations"),
        "burnout_risk": result.get("burnout_risk"),
        "raw_text": request.raw_text
    }
    save_employee_assessment(assessment_data)
    return {"status": "success", "assessment": result}

# ---------- Team Assessment ----------
@app.get("/api/employee/team")
async def team_assessment(api_key: str = Depends(verify_api_key)):
    from core.db import get_employee_assessments, get_candidate_reports, get_candidate_reports
    assessments = get_employee_assessments()
    if not assessments:
        return {"status": "success", "assessments": [], "summary": {"total_employees": 0}}
    total = len(assessments)
    avg_leadership = sum(a.get("leadership_score", 0) for a in assessments) / total
    avg_stress = sum(a.get("stress_resilience_score", 0) for a in assessments) / total
    avg_communication = sum(a.get("communication_score", 0) for a in assessments) / total
    avg_learnability = sum(a.get("learnability_score", 0) for a in assessments) / total
    avg_responsibility = sum(a.get("responsibility_score", 0) for a in assessments) / total
    burnout_counts = {"низкий": 0, "средний": 0, "высокий": 0}
    for a in assessments:
        risk = a.get("burnout_risk", "неизвестен").lower()
        if risk in burnout_counts:
            burnout_counts[risk] += 1
    return {
        "status": "success",
        "assessments": assessments,
        "summary": {
            "total_employees": total,
            "avg_leadership": round(avg_leadership, 1),
            "avg_stress_resilience": round(avg_stress, 1),
            "avg_communication": round(avg_communication, 1),
            "avg_learnability": round(avg_learnability, 1),
            "avg_responsibility": round(avg_responsibility, 1),
            "burnout_risk_distribution": burnout_counts
        }
    }

@app.post("/api/upload/resume")
async def upload_resume(
    file: UploadFile = FastAPIFile(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Загрузить файл резюме (PDF, DOCX, TXT). Возвращает извлечённый текст.
    """
    try:
        contents = await file.read()
        text = extract_text_from_bytes(contents, file.filename)
        return {"filename": file.filename, "text": text, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка обработки файла: {str(e)}")

@app.post("/api/upload/vacancy")
async def upload_vacancy(
    file: UploadFile = FastAPIFile(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Загрузить файл с описанием вакансии (PDF, DOCX, TXT). Возвращает извлечённый текст.
    """
    try:
        contents = await file.read()
        text = extract_text_from_bytes(contents, file.filename)
        return {"filename": file.filename, "text": text, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка обработки файла: {str(e)}")

# ---------- Чат с продолжением диалога ----------
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    context: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    import uuid
    session_id = request.session_id or str(uuid.uuid4())
    messages = get_conversation_messages(session_id)
    if not messages:
        system_prompt = "Ты — полезный ассистент по HR. Отвечай на вопросы по найму, анализу кандидатов и workforce planning."
        messages.append({"role": "system", "content": system_prompt})
        if request.context:
            messages.append({"role": "system", "content": f"Контекст для текущего диалога:\n{request.context}"})
    messages.append({"role": "user", "content": request.message})
    from core.llm_client import ask_llm_with_history
    answer = ask_llm_with_history(messages)
    add_message_to_conversation(session_id, "user", request.message)
    add_message_to_conversation(session_id, "assistant", answer)
    return {"session_id": session_id, "response": answer}

# ---------- Чат с продолжением диалога ----------
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    context: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    import uuid
    session_id = request.session_id or str(uuid.uuid4())
    messages = get_conversation_messages(session_id)
    if not messages:
        system_prompt = "Ты — полезный ассистент по HR. Отвечай на вопросы по найму, анализу кандидатов и workforce planning."
        messages.append({"role": "system", "content": system_prompt})
        if request.context:
            messages.append({"role": "system", "content": f"Контекст для текущего диалога:\n{request.context}"})
    messages.append({"role": "user", "content": request.message})
    from core.llm_client import ask_llm_with_history
    answer = ask_llm_with_history(messages)
    add_message_to_conversation(session_id, "user", request.message)
    add_message_to_conversation(session_id, "assistant", answer)
    return {"session_id": session_id, "response": answer}

# ---------- Генерация вопросов для собеседования ----------
class InterviewQuestionsRequest(BaseModel):
    candidate_id: Optional[int] = None
    resume_text: Optional[str] = None
    vacancy_text: Optional[str] = None
    transcribed_text: Optional[str] = None

class InterviewQuestionsResponse(BaseModel):
    status: str
    questions: List[str]

@app.post("/api/interview/questions", response_model=InterviewQuestionsResponse)
async def generate_interview_questions(
    request: InterviewQuestionsRequest,
    api_key: str = Depends(verify_api_key)
):
    # Собираем тексты
    resume = request.resume_text or ""
    vacancy = request.vacancy_text or ""
    transcribed = request.transcribed_text or ""

    if request.candidate_id:
        candidate = get_candidate(request.candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        if not resume:
            resume = candidate.get('resume_text', '') or ""
        if not vacancy:
            vacancy = candidate.get('vacancy_text', '') or ""
        if not transcribed:
            transcribed = candidate.get('transcribed_text', '') or ""

    # Проверяем, что есть хоть какие-то данные
    if not resume and not vacancy and not transcribed:
        raise HTTPException(
            status_code=400,
            detail="Не предоставлены данные: укажите резюме, описание вакансии или транскрипцию (или candidate_id)"
        )

    # Формируем контекст для промпта
    context = "Информация о кандидате:\n"
    if resume:
        context += f"Резюме: {resume}\n"
    if vacancy:
        context += f"Описание вакансии: {vacancy}\n"
    if transcribed:
        context += f"Транскрипция собеседования: {transcribed}\n"

    prompt = f"""
Ты — опытный HR-эксперт и интервьюер. На основе предоставленных данных о кандидате и вакансии сгенерируй персонализированные вопросы для собеседования.

Вот данные:
{context}

Твоя задача — составить список из 5–7 вопросов, которые помогут:
1. Раскрыть реальный опыт и навыки кандидата (не шаблонные).
2. Оценить его мотивацию и культурное соответствие.
3. Выявить зоны роста и потенциал.
4. Проверить знание конкретных технологий / методов, указанных в вакансии.

Вопросы должны быть открытыми, ситуационными и проективными. 
Ответ выведи в виде JSON-массива строк, без пояснений. Например: ["Вопрос 1", "Вопрос 2", ...]
"""

    from core.llm_client import ask_llm
    raw = ask_llm(prompt)

    # Парсим JSON
    import json
    try:
        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        questions = json.loads(clean)
        if not isinstance(questions, list):
            questions = [str(questions)]
    except Exception as e:
        # Fallback – разбить текст на строки
        questions = [line.strip() for line in raw.split('\n') if line.strip()]

    # Если есть candidate_id, сохраняем вопросы в историю (как отчёт)
    if request.candidate_id:
        from core.db import save_candidate_report
        save_candidate_report(
            candidate_id=request.candidate_id,
            report_type="interview_questions",
            input_data={"resume": resume, "vacancy": vacancy, "transcribed": transcribed},
            report={"questions": questions}
        )

    return {"status": "success", "questions": questions}

# ---------- Батч-матчинг (оценка нескольких кандидатов на вакансию) ----------
class MatchBatchRequest(BaseModel):
    vacancy_id: Optional[int] = None
    vacancy_text: Optional[str] = None
    candidate_ids: Optional[List[int]] = None
    candidates: Optional[List[Dict[str, str]]] = None  # список {"name": ..., "text": ...}

class MatchBatchResponse(BaseModel):
    status: str
    matches: List[Dict[str, Any]]  # каждый элемент: candidate_id, name, fit_score, strengths, risks, recommendation

@app.post("/api/match/batch", response_model=MatchBatchResponse)
async def match_batch(
    request: MatchBatchRequest,
    api_key: str = Depends(verify_api_key)
):
    # 1. Получаем текст вакансии
    vacancy_text = request.vacancy_text or ""
    if request.vacancy_id:
        from core.db import get_vacancy
        vacancy = get_vacancy(request.vacancy_id)
        if not vacancy:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        vacancy_text = vacancy.get('description', '') + "\n" + vacancy.get('requirements', '')

    if not vacancy_text.strip():
        raise HTTPException(status_code=400, detail="Не указан текст вакансии (передайте vacancy_text или vacancy_id)")

    # 2. Получаем данные кандидатов
    candidates_data = []
    if request.candidate_ids:
        from core.db import get_candidate
        for cid in request.candidate_ids:
            cand = get_candidate(cid)
            if cand:
                # Собираем текст из всех полей
                text = (cand.get('transcribed_text', '') or "") + "\n" + \
                       (cand.get('resume_text', '') or "") + "\n" + \
                       (cand.get('vacancy_text', '') or "")
                candidates_data.append({
                    "id": cid,
                    "name": cand.get('name', f"Кандидат {cid}"),
                    "text": text.strip()
                })
    elif request.candidates:
        for idx, cand in enumerate(request.candidates):
            name = cand.get('name', f"Кандидат {idx+1}")
            text = cand.get('text', '')
            candidates_data.append({
                "id": None,
                "name": name,
                "text": text
            })
    else:
        raise HTTPException(status_code=400, detail="Передайте candidate_ids или candidates")

    if not candidates_data:
        raise HTTPException(status_code=400, detail="Нет данных о кандидатах")

    # 3. Формируем промпт для LLM
    candidates_info = ""
    for i, c in enumerate(candidates_data):
        candidates_info += f"Кандидат {i+1} ({c['name']}):\n{c['text'][:1000]}\n\n"

    prompt = f"""
Ты — HR-эксперт по оценке персонала. Твоя задача — оценить соответствие каждого кандидата вакансии.

Вакансия:
{vacancy_text}

Список кандидатов:
{candidates_info}

Для каждого кандидата укажи:
- fit_score (число от 0 до 100) – насколько кандидат подходит.
- strengths (краткий список сильных сторон).
- risks (краткий список рисков или зон роста).
- recommendation (что делать: "Пригласить на собеседование", "Отложить", "Отказать" – с кратким пояснением).

Ответ выведи строго в формате JSON-массива объектов с полями: candidate_index, fit_score, strengths, risks, recommendation.
Пример ответа:
[
  {{"candidate_index": 1, "fit_score": 85, "strengths": ["Опыт Python", "Знание микросервисов"], "risks": ["Мало опыта в лидерстве"], "recommendation": "Пригласить на собеседование"}},
  ...
]
Не добавляй пояснений вне JSON.
"""

    from core.llm_client import ask_llm
    raw = ask_llm(prompt)

    # 4. Парсим ответ
    import json
    try:
        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        results = json.loads(clean)
        if not isinstance(results, list):
            results = []
    except Exception:
        results = []

    # 5. Сопоставляем с исходными кандидатами и формируем финальный ответ
    matches = []
    for i, cand in enumerate(candidates_data):
        # Находим результат по индексу (индексы в ответе могут быть с 1)
        res = next((r for r in results if r.get('candidate_index') == i+1), None)
        if res:
            matches.append({
                "candidate_id": cand["id"],
                "name": cand["name"],
                "fit_score": res.get('fit_score', 0),
                "strengths": res.get('strengths', []),
                "risks": res.get('risks', []),
                "recommendation": res.get('recommendation', "Не определён")
            })
        else:
            matches.append({
                "candidate_id": cand["id"],
                "name": cand["name"],
                "fit_score": 0,
                "strengths": [],
                "risks": [],
                "recommendation": "Не удалось оценить"
            })

    # 6. Сортируем по убыванию fit_score
    matches.sort(key=lambda x: x['fit_score'], reverse=True)

    # 7. Сохраняем результаты в историю (для каждого кандидата)
    if request.vacancy_id:
        from core.db import save_candidate_report
        for m in matches:
            if m["candidate_id"]:
                save_candidate_report(
                    candidate_id=m["candidate_id"],
                    report_type="match",
                    input_data={"vacancy_id": request.vacancy_id, "vacancy_text": vacancy_text},
                    report=m
                )

    return {"status": "success", "matches": matches}

# ---------- Саммари кандидата ----------
class SummaryRequest(BaseModel):
    candidate_id: Optional[int] = None
    transcribed_text: Optional[str] = None
    vacancy_text: Optional[str] = None
    resume_text: Optional[str] = None

class SummaryResponse(BaseModel):
    status: str
    summary: Dict[str, Any]

@app.post("/api/candidates/summary", response_model=SummaryResponse)
async def generate_summary(
    request: SummaryRequest,
    api_key: str = Depends(verify_api_key)
):
    if request.candidate_id:
        candidate = get_candidate(request.candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Кандидат не найден")
        text_parts = []
        if candidate.get('transcribed_text'):
            text_parts.append(candidate['transcribed_text'])
        if candidate.get('vacancy_text'):
            text_parts.append(candidate['vacancy_text'])
        if candidate.get('resume_text'):
            text_parts.append(candidate['resume_text'])
        if not text_parts:
            raise HTTPException(status_code=400, detail="У кандидата нет текстовых данных для саммари")
        combined_text = "\n".join(text_parts)
    else:
        combined_text = (request.transcribed_text or "") + "\n" + (request.vacancy_text or "") + "\n" + (request.resume_text or "")
        if not combined_text.strip():
            raise HTTPException(status_code=400, detail="Не переданы текстовые данные")

    prompt = f"""
Ты — эксперт по HR. Составь краткое саммари по кандидату на основе предоставленного текста.
Вот текст (может быть транскрипцией, описанием вакансии, резюме):
{combined_text}

Твоя задача: выделить ключевую информацию и представить её в виде структурированного JSON со следующими полями:
- "key_skills": массив строк (основные навыки, не более 5),
- "experience": строка (кратко о релевантном опыте),
- "motivation": строка (чем кандидат мотивирован, если указано),
- "strengths": массив строк (сильные стороны),
- "weaknesses": массив строк (слабые стороны или зоны роста, если видны),
- "summary": строка (общее впечатление, 1-2 предложения).

Ответ выведи только в формате JSON, без пояснений.
"""

    from core.llm_client import ask_llm
    raw = ask_llm(prompt)

    import json
    try:
        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        summary_data = json.loads(clean)
    except Exception:
        summary_data = {
            "key_skills": [],
            "experience": "",
            "motivation": "",
            "strengths": [],
            "weaknesses": [],
            "summary": raw
        }

    if request.candidate_id:
        from core.db import save_candidate_report
        save_candidate_report(
            candidate_id=request.candidate_id,
            report_type="summary",
            input_data={"text": combined_text},
            report=summary_data
        )

    return {"status": "success", "summary": summary_data}

# ---------- Запуск ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.get("/api/candidates/{candidate_id}/reports")
async def candidate_reports(
    candidate_id: int,
    limit: int = Query(10, ge=1, le=50),
    api_key: str = Depends(verify_api_key)
):
    reports = get_candidate_reports(candidate_id, limit=limit)
    if not reports:
        raise HTTPException(status_code=404, detail="No reports found for this candidate")
    return {"candidate_id": candidate_id, "reports": reports}
