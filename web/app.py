# web/app.py
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, constr

# ---------- DB (SQLAlchemy + SQLite/Postgres) ----------
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'milk.db'}")

# --- normalize DATABASE_URL (Render + Neon) ---
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


# Dependency cho FastAPI
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Feeding(Base):
    __tablename__ = "feedings"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)  # YYYY-MM-DD
    time = Column(String)  # HH:MM
    milk_type = Column(String)  # me | pre | sct
    amount = Column(Integer)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------- Schemas (Pydantic v2) -----------
from pydantic import BaseModel, Field, ConfigDict


class FeedingIn(BaseModel):
    # YYYY-MM-DD
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    # HH:MM
    time: str = Field(pattern=r"^\d{2}:\d{2}$")
    # me | pre | sct
    milk_type: str = Field(pattern=r"^(me|pre|sct)$")
    # cho thêm ràng buộc cho tử tế
    amount: int = Field(ge=0, le=2000)


class FeedingOut(FeedingIn):
    id: int
    # pydantic v2: thay Config class bằng model_config
    model_config = ConfigDict(from_attributes=True)


# ---------- App + static ----------
app = FastAPI()
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=FileResponse)
def index():
    return STATIC_DIR / "index.html"


# ---------- API ----------
@app.get("/feedings", response_model=List[FeedingOut])
def list_feedings(date: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Feeding)
    if date:
        q = q.filter(Feeding.date == date)
    return q.order_by(Feeding.date, Feeding.time).all()


@app.post("/feedings", response_model=FeedingOut)
def create_feeding(data: FeedingIn, db: Session = Depends(get_db)):
    row = Feeding(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.delete("/feedings/{feeding_id}", status_code=204)
def delete_feeding(feeding_id: int, db: Session = Depends(get_db)):
    obj = db.get(Feeding, feeding_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return


# Admin: xoá sạch bảng khi cần “clean”
@app.post("/admin/wipe", status_code=204)
def wipe(db: Session = Depends(get_db)):
    db.query(Feeding).delete()
    db.commit()
    return
