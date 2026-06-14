from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Vacancy, Candidate

def get_all_vacancies(skip: int = 0, limit: int = 100):
    db = SessionLocal()
    try:
        query = db.query(Vacancy)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}
    finally:
        db.close()

def get_all_candidates(skip: int = 0, limit: int = 100):
    db = SessionLocal()
    try:
        query = db.query(Candidate)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}
    finally:
        db.close()
