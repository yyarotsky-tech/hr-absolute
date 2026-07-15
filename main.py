import os
import tempfile
import whisper
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="HR Absolute API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Транскрибирует аудио через Whisper"""
    if not file.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.webm', '.ogg', '.flac')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        model = whisper.load_model("base")
        result = model.transcribe(tmp_path)
        return {"text": result["text"].strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)