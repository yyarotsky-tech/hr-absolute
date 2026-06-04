import io
import pypdf
from docx import Document

def extract_text_from_file(file_bytes: bytes, filename: str) -> str | None:
    filename_lower = filename.lower()
    if filename_lower.endswith('.pdf'):
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
        return text
    elif filename_lower.endswith('.docx'):
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join(para.text for para in doc.paragraphs)
        return text
    elif filename_lower.endswith('.txt'):
        return file_bytes.decode('utf-8')
    return None
