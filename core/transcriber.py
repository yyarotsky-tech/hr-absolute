import whisper

_model = None

def load_whisper_model(model_name: str = "base"):
    global _model
    if _model is None:
        print(f"Loading Whisper model '{model_name}'...")
        _model = whisper.load_model(model_name)
    return _model

def transcribe_audio(file_path: str, language: str = "ru") -> str:
    model = load_whisper_model()
    result = model.transcribe(file_path, language=language)
    return result["text"]
