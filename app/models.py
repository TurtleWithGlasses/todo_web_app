from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    position = Column(Integer, nullable=False, default=0)
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    data_status = Column(String, default="☐")
    work_status = Column(String, default="☐")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    color = Column(String, nullable=False, default="#06b6d4")
    position = Column(Integer, nullable=False, default=0)


class DailyTask(Base):
    __tablename__ = "daily_tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, default="")
    time = Column(String, default="")          # e.g. "14:00"
    category = Column(String, default="")      # Yazılım | Veri Analizi | Kişisel | Toplantılar
    priority = Column(String, default="orta")  # acil | orta | düşük
    status = Column(String, default="yapılacak")  # yapılacak | yapılıyor | tamamlandı
    date = Column(String, nullable=False)      # ISO date string e.g. "2026-03-10"
    position = Column(Integer, nullable=False, default=0)
    repeat_group_id = Column(Integer, nullable=True)  # NULL = standalone, N = repeat group