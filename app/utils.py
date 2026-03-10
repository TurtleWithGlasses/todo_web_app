from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Task, DailyTask, Category

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


# --- Category utilities ---

DEFAULT_CATEGORIES = [
    {"name": "Yazılım",      "color": "#6366f1"},
    {"name": "Veri Analizi", "color": "#06b6d4"},
    {"name": "Kişisel",      "color": "#10b981"},
    {"name": "Toplantılar",  "color": "#f59e0b"},
]

def seed_categories():
    with SessionLocal() as db:
        if db.query(Category).count() == 0:
            for i, cat in enumerate(DEFAULT_CATEGORIES):
                db.add(Category(name=cat["name"], color=cat["color"], position=i))
            db.commit()

def load_categories():
    with SessionLocal() as db:
        return db.query(Category).order_by(Category.position).all()

def add_category(name: str, color: str):
    with SessionLocal() as db:
        last = db.query(Category).order_by(Category.position.desc()).first()
        position = last.position + 1 if last else 0
        cat = Category(name=name, color=color, position=position)
        db.add(cat)
        db.commit()
        db.refresh(cat)
        return cat

def update_category(cat_id: int, name: str = None, color: str = None):
    with SessionLocal() as db:
        cat = db.get(Category, cat_id)
        if cat:
            if name is not None:
                cat.name = name
            if color is not None:
                cat.color = color
            db.commit()

def delete_category(cat_id: int):
    with SessionLocal() as db:
        cat = db.get(Category, cat_id)
        if cat:
            db.delete(cat)
            db.commit()


# --- DailyTask utilities ---

def load_daily_tasks(date: str):
    with SessionLocal() as db:
        return db.query(DailyTask).filter(DailyTask.date == date).order_by(DailyTask.position).all()

def add_daily_task(title: str, description: str, time: str, category: str, priority: str, date: str):
    with SessionLocal() as db:
        last = db.query(DailyTask).filter(DailyTask.date == date).order_by(DailyTask.position.desc()).first()
        position = last.position + 1 if last else 0
        task = DailyTask(
            title=title,
            description=description,
            time=time,
            category=category,
            priority=priority,
            date=date,
            position=position,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

def update_daily_task(task_id: int, **fields):
    with SessionLocal() as db:
        task = db.get(DailyTask, task_id)
        if task:
            for key, value in fields.items():
                setattr(task, key, value)
            db.commit()

def delete_daily_task(task_id: int):
    with SessionLocal() as db:
        task = db.get(DailyTask, task_id)
        if task:
            db.delete(task)
            db.commit()

def set_daily_task_status(task_id: int, status: str):
    with SessionLocal() as db:
        task = db.get(DailyTask, task_id)
        if task:
            task.status = status
            db.commit()

def get_daily_stats(date: str):
    with SessionLocal() as db:
        tasks = db.query(DailyTask).filter(DailyTask.date == date).all()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "tamamlandı")
        return {"total": total, "completed": completed}

def get_weekly_stats(reference_date: str):
    """Return completion data for the 7 days ending on reference_date (inclusive)."""
    from datetime import date as DateType, timedelta
    ref = DateType.fromisoformat(reference_date)
    days = [ref - timedelta(days=i) for i in range(6, -1, -1)]
    date_strs = [d.isoformat() for d in days]

    with SessionLocal() as db:
        tasks = (
            db.query(DailyTask)
            .filter(DailyTask.date.in_(date_strs))
            .all()
        )

    # Group by date
    from collections import defaultdict
    totals    = defaultdict(int)
    completed = defaultdict(int)
    for t in tasks:
        totals[t.date] += 1
        if t.status == "tamamlandı":
            completed[t.date] += 1

    return [
        {
            "date":      d,
            "total":     totals[d],
            "completed": completed[d],
        }
        for d in date_strs
    ]