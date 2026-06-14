import inspect
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from core.transcriber import transcribe_audio
from core.analyzers import analyze_candidate, analyze_workforce
from core.file_parser import extract_text_from_file
from core.db import save_candidate, get_all_candidates, get_candidate, search_candidates, delete_candidate, save_rating, get_industry_avg, add_vacancy, get_all_vacancies, delete_vacancy, add_volunteer_vacancy, get_all_volunteer_vacancies, delete_volunteer_vacancy, save_employee_assessment

load_dotenv()

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
    created_at: str
    transcribed_snippet: Optional[str] = None
    vacancy_snippet: Optional[str] = None
    resume_snippet: Optional[str] = None

class CandidateDetailResponse(BaseModel):
    id: int
    name: str
    created_at: str
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
    created_at: str

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
    created_at: str

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
    audio: UploadFile = File(...),
    language: str = "ru",
    api_key: str = Depends(verify_api_key)
):
    suffix = os.path.splitext(audio.filename)[1] or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
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
    try:
        report = analyze_candidate(data)
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
    return CandidateResponse(id=cand_id, name=request.name, created_at="", transcribed_snippet="", vacancy_snippet="", resume_snippet="")

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

@app.get("/api/vacancies", response_model=List[VacancyResponse])
async def list_vacancies(api_key: str = Depends(verify_api_key)):
    return get_all_vacancies()

@app.delete("/api/vacancies/{vacancy_id}")
async def delete_vacancy(vacancy_id: int, api_key: str = Depends(verify_api_key)):
    if not delete_vacancy(vacancy_id):
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return {"status": "deleted"}

@app.patch("/api/vacancies/{vacancy_id}")
async def update_vacancy(vacancy_id: int, request: VacancyUpdateRequest, api_key: str = Depends(verify_api_key)):
    from core.db import get_vacancy, update_vacancy
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
    from core.db import get_all_candidates, get_all_vacancies
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
    from core.db import get_employee_assessments
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

# ---------- Запуск ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
