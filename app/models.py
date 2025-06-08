from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    data_status = Column(String, default="☐")
    work_status = Column(String, default="☐")