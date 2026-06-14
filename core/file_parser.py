import os
import tempfile
import docx
import PyPDF2

def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Извлекает текст из файла (PDF, DOCX, TXT) по байтам и имени файла.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == '.txt':
        return file_bytes.decode('utf-8', errors='ignore')
    elif ext == '.docx':
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            doc = docx.Document(tmp.name)
            return '\n'.join(para.text for para in doc.paragraphs)
    elif ext == '.pdf':
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            reader = PyPDF2.PdfReader(tmp.name)
            text = ''
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
            return text
    else:
        raise ValueError(f"Неподдерживаемый тип файла: {ext}")

def extract_text_from_file(file_path: str) -> str:
    """Извлекает текст из файла по его пути (PDF, DOCX, TXT)"""
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    return extract_text_from_bytes(file_bytes, os.path.basename(file_path))
