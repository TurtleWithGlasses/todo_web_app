from sqlalchemy import create_engine, func
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

def move_daily_task(task_id: int, new_date: str, new_time: str = None):
    with SessionLocal() as db:
        task = db.get(DailyTask, task_id)
        if task:
            task.date = new_date
            if new_time is not None:
                task.time = new_time
            db.commit()

def duplicate_daily_task(task_id: int, new_date: str, new_time: str = None):
    with SessionLocal() as db:
        task = db.get(DailyTask, task_id)
        if not task:
            return None
        last = db.query(DailyTask).filter(DailyTask.date == new_date).order_by(DailyTask.position.desc()).first()
        position = last.position + 1 if last else 0
        new_task = DailyTask(
            title=task.title,
            description=task.description,
            time=new_time if new_time is not None else task.time,
            category=task.category,
            priority=task.priority,
            date=new_date,
            position=position,
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        return new_task

def create_repeat_tasks(task_id: int, dates: list, time: str):
    with SessionLocal() as db:
        source = db.get(DailyTask, task_id)
        if not source:
            return None
        max_gid = db.query(func.max(DailyTask.repeat_group_id)).scalar()
        group_id = (max_gid or 0) + 1
        source.repeat_group_id = group_id
        if time:
            source.time = time
        for date in dates:
            if date == source.date:
                continue
            last = db.query(DailyTask).filter(DailyTask.date == date).order_by(DailyTask.position.desc()).first()
            position = last.position + 1 if last else 0
            db.add(DailyTask(
                title=source.title,
                description=source.description,
                time=time if time else source.time,
                category=source.category,
                priority=source.priority,
                date=date,
                position=position,
                repeat_group_id=group_id,
            ))
        db.commit()
        return group_id

def delete_repeat_group(group_id: int):
    with SessionLocal() as db:
        db.query(DailyTask).filter(DailyTask.repeat_group_id == group_id).delete()
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

def get_analysis(from_date: str, to_date: str):
    """Return per-day stats and category breakdown for a date range."""
    from datetime import date as DateType, timedelta
    from collections import defaultdict

    start = DateType.fromisoformat(from_date)
    end   = DateType.fromisoformat(to_date)
    if end < start:
        start, end = end, start

    days = []
    cur = start
    while cur <= end:
        days.append(cur.isoformat())
        cur += timedelta(days=1)

    with SessionLocal() as db:
        tasks = (
            db.query(DailyTask)
            .filter(DailyTask.date.in_(days))
            .all()
        )

    totals    = defaultdict(int)
    completed = defaultdict(int)
    cat_total = defaultdict(int)
    cat_done  = defaultdict(int)

    for t in tasks:
        totals[t.date]    += 1
        cat_total[t.category or 'Diğer'] += 1
        if t.status == 'tamamlandı':
            completed[t.date] += 1
            cat_done[t.category or 'Diğer'] += 1

    daily = [
        {'date': d, 'total': totals[d], 'completed': completed[d]}
        for d in days
    ]

    categories = [
        {'name': name, 'total': cat_total[name], 'completed': cat_done[name]}
        for name in sorted(cat_total)
    ]

    return {'daily': daily, 'categories': categories}


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