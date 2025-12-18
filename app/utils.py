from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Task

engine = create_engine("sqlite:///todo.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def load_tasks():
    with SessionLocal() as db:
        return db.query(Task).order_by(Task.position).all()
    
def add_task(text):
    with SessionLocal() as db:
        last_position = db.query(Task).order_by(Task.position.desc()).first()
        position = last_position.position + 1 if last_position else 0
        task = Task(text=text, position=position)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task


def update_task_text(task_id, new_text):
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        if task:
            task.text = new_text
            db.commit()

def delete_task(task_id):
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        if task:
            db.delete(task)
            db.commit()

def toggle_task_status(task_id, column):
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        if task:
            if column == "data":
                task.data_status = "☐" if task.data_status == "☑" else "☑"
            elif column == "work":
                task.work_status = "☐" if task.work_status == "☑" else "☑"
            db.commit()

def reset_all_tasks():
    with SessionLocal() as db:
        tasks = db.query(Task).all()
        for task in tasks:
            task.data_status = "☐"
            task.work_status = "☐"
        db.commit()