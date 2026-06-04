import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from core.transcriber import transcribe_audio
from core.analyzers import analyze_candidate
from core.file_parser import extract_text_from_file

load_dotenv()

API_KEY = os.getenv("API_KEY", "test_key_123")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key is None or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API Key")
    return api_key

app = FastAPI(title="HR Absolute API", version="0.1.0")

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

@app.get("/")
async def root():
    return {"message": "HR Absolute API is running"}

@app.get("/api/check_key")
async def check_key(api_key: str = Depends(verify_api_key)):
    return {"status": "valid", "message": "API key is valid"}

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
