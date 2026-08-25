from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models import Base, Task, DailyTask, Category, Setting, TaskLink

engine = create_engine("sqlite:///todo.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_month():
    from datetime import date
    return date.today().strftime("%Y-%m")

def load_tasks(month: str):
    with SessionLocal() as db:
        return db.query(Task).filter(Task.month == month).order_by(Task.position).all()

def initialize_month(month: str):
    """If no tasks exist for this month, copy from the most recent previous month with reset statuses."""
    with SessionLocal() as db:
        if db.query(Task).filter(Task.month == month).count() > 0:
            return
        prev = (
            db.query(Task.month)
            .filter(Task.month < month, Task.month != "")
            .order_by(Task.month.desc())
            .first()
        )
        if not prev:
            return
        prev_tasks = db.query(Task).filter(Task.month == prev[0]).order_by(Task.position).all()
        for t in prev_tasks:
            db.add(Task(text=t.text, data_status="☐", work_status="☐", position=t.position, month=month))
        db.commit()

def get_available_months():
    with SessionLocal() as db:
        rows = db.query(Task.month).distinct().order_by(Task.month.desc()).all()
        return [r[0] for r in rows if r[0]]

def add_task(text, month: str):
    with SessionLocal() as db:
        last = db.query(Task).filter(Task.month == month).order_by(Task.position.desc()).first()
        position = last.position + 1 if last else 0
        task = Task(text=text, position=position, month=month)
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

def reset_all_tasks(month: str):
    with SessionLocal() as db:
        tasks = db.query(Task).filter(Task.month == month).all()
        for task in tasks:
            task.data_status = "☐"
            task.work_status = "☐"
        db.commit()


# --- Setting utilities (key-value store) ---

def get_setting(key: str):
    with SessionLocal() as db:
        s = db.get(Setting, key)
        return s.value if s else None

def set_setting(key: str, value: str):
    with SessionLocal() as db:
        s = db.get(Setting, key)
        if s:
            s.value = value
        else:
            db.add(Setting(key=key, value=value))
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
            old_name = cat.name
            if name is not None:
                cat.name = name
                if name != old_name:
                    # Tasks reference the category by name — cascade the rename
                    db.query(DailyTask).filter(DailyTask.category == old_name).update(
                        {DailyTask.category: name}
                    )
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

def update_repeat_group(group_id: int, **fields):
    with SessionLocal() as db:
        tasks = db.query(DailyTask).filter(DailyTask.repeat_group_id == group_id).all()
        for task in tasks:
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

def duplicate_daily_task(task_id: int, new_date: str, new_time: str = None, new_title: str = None):
    with SessionLocal() as db:
        task = db.get(DailyTask, task_id)
        if not task:
            return None
        last = db.query(DailyTask).filter(DailyTask.date == new_date).order_by(DailyTask.position.desc()).first()
        position = last.position + 1 if last else 0
        new_task = DailyTask(
            title=new_title if new_title else task.title,
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

def delete_repeat_group_after(group_id: int, after_date: str):
    """Delete a repeat group's tasks dated strictly after after_date.

    Used to cut a long-running series short without touching the task on
    the given day or any earlier ones. Dates are stored as ISO strings
    (YYYY-MM-DD), so a plain string comparison orders them correctly.
    Returns how many rows were removed.
    """
    with SessionLocal() as db:
        deleted = db.query(DailyTask).filter(
            DailyTask.repeat_group_id == group_id,
            DailyTask.date > after_date,
        ).delete(synchronize_session=False)
        db.commit()
        return deleted

def get_month_dots(year: int, month: int):
    """Per-day calendar data for a month.

    Returns {"dots": {date: [colors]}, "tasks": {date: [task, ...]}} —
    the dots drive the calendar markers, the task lists feed the
    hover tooltip on each day cell.
    """
    import calendar as cal_mod
    last_day  = cal_mod.monthrange(year, month)[1]
    from_date = f"{year}-{str(month).zfill(2)}-01"
    to_date   = f"{year}-{str(month).zfill(2)}-{str(last_day).zfill(2)}"
    with SessionLocal() as db:
        tasks = db.query(DailyTask).filter(
            DailyTask.date >= from_date,
            DailyTask.date <= to_date
        ).all()
        cat_colors = {c.name: c.color for c in db.query(Category).all()}
    from collections import defaultdict
    dots  = defaultdict(list)
    seen  = defaultdict(set)
    day_tasks = defaultdict(list)
    for t in tasks:
        color = cat_colors.get(t.category, '#64748b') if t.category else '#64748b'
        if color not in seen[t.date]:
            dots[t.date].append(color)
            seen[t.date].add(color)
        day_tasks[t.date].append({
            "title":    t.title,
            "category": t.category or "Diğer",
            "done":     t.status == "tamamlandı",
            "time":     t.time or "",
        })
    return {
        "dots": dict(dots),
        "tasks": {
            d: sorted(items, key=lambda x: x["time"] or "99:99")
            for d, items in day_tasks.items()
        },
    }

# --- Task entity helpers (Phase 1: derived at query time, no schema change) ---

def normalize_title(s: str) -> str:
    """A task's identity key: trimmed, Turkish-aware case folded.

    Python's str.lower() mishandles Turkish: "KITAP".lower() leaves a
    stray combining dot ("ki̇tap") and "I".lower() gives "i" rather
    than "ı". Mapping the two dotted/dotless pairs first keeps
    "IŞIK"/"ışık" and "KİTAP"/"kitap" grouping together correctly.
    """
    return (s or "").strip().replace("İ", "i").replace("I", "ı").lower()

def _entity_rows():
    with SessionLocal() as db:
        return db.query(DailyTask).all()

def search_task_entities(query: str = "", limit: int = 60):
    """Group every task row by normalized title into one entity per task.

    Grouping is derived on read, so nothing is stored and nothing can
    drift out of sync. Titles are matched on the normalized key, so
    "SOCAR Aylik Raporu" and "SOCAR aylik raporu" collapse into one.
    """
    from collections import defaultdict
    q = normalize_title(query)
    buckets = defaultdict(list)
    for t in _entity_rows():
        key = normalize_title(t.title)
        if not key or (q and q not in key):
            continue
        buckets[key].append(t)

    out = []
    for key, items in buckets.items():
        items.sort(key=lambda t: (t.date, t.time or ""))
        # Newest spelling wins as the display title, and categories are
        # listed most-recent-first since they can differ per occurrence.
        cats, seen = [], set()
        for t in reversed(items):
            c = t.category or ""
            if c and c not in seen:
                seen.add(c)
                cats.append(c)
        out.append({
            "key":        key,
            "title":      items[-1].title,
            "total":      len(items),
            "completed":  sum(1 for t in items if t.status == "tamamlandı"),
            "first_date": items[0].date,
            "last_date":  items[-1].date,
            "categories": cats,
        })
    out.sort(key=lambda e: (-e["total"], e["title"]))
    return out[:limit]

def get_daily_task(task_id: int):
    """Minimal read of one task row (used to learn its title before a rename)."""
    with SessionLocal() as db:
        t = db.get(DailyTask, task_id)
        return {"id": t.id, "title": t.title} if t else None

def count_task_occurrences(title: str) -> int:
    """How many rows share this task's identity (i.e. a rename's blast radius)."""
    key = normalize_title(title)
    if not key:
        return 0
    with SessionLocal() as db:
        return sum(1 for t in db.query(DailyTask).all()
                   if normalize_title(t.title) == key)

def rename_task_entity(old_title: str, new_title: str) -> int:
    """Retitle every occurrence sharing this task's identity.

    Under title-as-identity a rename is a re-identification, so it always
    applies to the whole task rather than a single day - independent of
    the repeat-group checkbox, and reaching standalone rows and other
    repeat groups that happen to share the title. Returns rows changed.
    """
    key = normalize_title(old_title)
    new_title = (new_title or "").strip()
    if not key or not new_title:
        return 0
    with SessionLocal() as db:
        rows = [t for t in db.query(DailyTask).all()
                if normalize_title(t.title) == key]
        for t in rows:
            t.title = new_title
        # Carry any lineage over to the new identity, otherwise a rename
        # would silently orphan the "is a revision of" link.
        _remap_task_links(db, key, normalize_title(new_title))
        db.commit()
        return len(rows)

def split_task_entity(task_id: int, new_title: str, include_later: bool = False) -> int:
    """Peel occurrences off a task so they become a separate task.

    Renaming re-identifies the whole task, so splitting needs its own
    operation: it retitles only this occurrence, or this one plus every
    later occurrence sharing the same identity, leaving earlier ones under
    the original name.

    Peeled rows are also detached from the old repeat group - otherwise
    that group would span two different titles and "delete all repeats"
    would reach across both tasks. Several rows moving together get a
    fresh group of their own; a lone row becomes standalone.
    """
    new_title = (new_title or "").strip()
    if not new_title:
        return 0
    with SessionLocal() as db:
        src = db.get(DailyTask, task_id)
        if not src:
            return 0
        key = normalize_title(src.title)
        if include_later:
            rows = [t for t in db.query(DailyTask).all()
                    if normalize_title(t.title) == key and t.date >= src.date]
        else:
            rows = [src]

        new_gid = None
        if len(rows) > 1:
            new_gid = (db.query(func.max(DailyTask.repeat_group_id)).scalar() or 0) + 1
        for t in rows:
            t.title = new_title
            t.repeat_group_id = new_gid
        db.commit()

    # A split can retire the original title entirely (e.g. splitting from
    # the very first date), leaving its lineage row dangling.
    prune_task_links()
    return len(rows)

# --- Revision lineage (phase 4) ---

def _existing_task_keys(db):
    return {normalize_title(t.title) for t in db.query(DailyTask).all()}

def prune_task_links():
    """Drop lineage rows pointing at titles that no longer exist.

    Splitting or merging can retire a title entirely; without this the
    orphaned link would keep surfacing a task that is gone.
    """
    with SessionLocal() as db:
        live = _existing_task_keys(db)
        removed = 0
        for row in db.query(TaskLink).all():
            if row.norm_title not in live:
                db.delete(row); removed += 1
            elif row.parent_norm_title and row.parent_norm_title not in live:
                row.parent_norm_title = None
        db.commit()
        return removed

def set_task_parent(child_title: str, parent_title: str = None) -> bool:
    """Mark one task as a revision of another (or clear it when parent is None).

    Refuses anything that would make a task its own ancestor, so the
    chain can always be walked to a root.
    """
    ck = normalize_title(child_title)
    if not ck:
        return False
    pk = normalize_title(parent_title) if parent_title else None
    if pk == ck:
        return False

    with SessionLocal() as db:
        links = {r.norm_title: r.parent_norm_title for r in db.query(TaskLink).all()}
        # Walk up from the proposed parent; reaching the child means a cycle.
        seen, cur = set(), pk
        while cur:
            if cur == ck or cur in seen:
                return False
            seen.add(cur)
            cur = links.get(cur)

        row = db.query(TaskLink).filter(TaskLink.norm_title == ck).first()
        if pk is None:
            if row:
                db.delete(row)
        elif row:
            row.parent_norm_title = pk
        else:
            db.add(TaskLink(norm_title=ck, parent_norm_title=pk))
        db.commit()
        return True

def get_task_lineage(key: str):
    """Ancestor chain (nearest first) and direct revisions of a task."""
    with SessionLocal() as db:
        links = {r.norm_title: r.parent_norm_title for r in db.query(TaskLink).all()}
        titles, totals = {}, {}
        for t in db.query(DailyTask).all():
            k = normalize_title(t.title)
            titles[k] = t.title
            totals[k] = totals.get(k, 0) + 1

    def node(k):
        return {"key": k, "title": titles.get(k, k), "total": totals.get(k, 0)}

    chain, seen, cur = [], set(), links.get(key)
    while cur and cur not in seen:
        seen.add(cur)
        chain.append(node(cur))
        cur = links.get(cur)

    children = sorted(
        (node(k) for k, p in links.items() if p == key),
        key=lambda n: n["title"],
    )
    return {"parents": chain, "children": children}

def _remap_task_links(db, old_key: str, new_key: str):
    """Follow a rename so lineage survives it."""
    if old_key == new_key:
        return
    target = db.query(TaskLink).filter(TaskLink.norm_title == new_key).first()
    moving = db.query(TaskLink).filter(TaskLink.norm_title == old_key).first()
    if moving:
        if target:
            # Merging into a task that already has lineage: keep the target's.
            db.delete(moving)
        else:
            moving.norm_title = new_key
    for row in db.query(TaskLink).filter(TaskLink.parent_norm_title == old_key).all():
        row.parent_norm_title = new_key

def get_task_history(key: str):
    """Every occurrence of one task entity, newest first."""
    items = [t for t in _entity_rows() if normalize_title(t.title) == key]
    items.sort(key=lambda t: (t.date, t.time or ""), reverse=True)
    return [{
        "id":          t.id,
        "date":        t.date,
        "time":        t.time or "",
        "title":       t.title,
        "category":    t.category or "",
        "priority":    t.priority,
        "status":      t.status,
        "description": t.description or "",
    } for t in items]

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

def get_analysis(from_date: str, to_date: str, category: str = None):
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
        query = db.query(DailyTask).filter(DailyTask.date.in_(days))
        if category:
            query = query.filter(DailyTask.category == category)
        tasks = query.all()

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

    task_list = [
        {
            'id': t.id,
            'date': t.date,
            'title': t.title,
            'description': t.description or '',
            'time': t.time or '',
            'category': t.category or '',
            'priority': t.priority,
            'status': t.status,
        }
        for t in sorted(tasks, key=lambda t: (t.date, t.time or '99:99'))
    ]

    return {'daily': daily, 'categories': categories, 'tasks': task_list}


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
    cat_done  = defaultdict(lambda: defaultdict(int))
    day_tasks = defaultdict(list)
    for t in tasks:
        totals[t.date] += 1
        if t.status == "tamamlandı":
            completed[t.date] += 1
            cat_done[t.date][t.category or "Diğer"] += 1
        day_tasks[t.date].append({
            "title":    t.title,
            "category": t.category or "Diğer",
            "done":     t.status == "tamamlandı",
            "time":     t.time or "",
        })

    return [
        {
            "date":      d,
            "total":     totals[d],
            "completed": completed[d],
            "cats":      dict(cat_done[d]),  # completed count per category
            "tasks":     sorted(day_tasks[d], key=lambda x: x["time"] or "99:99"),
        }
        for d in date_strs
    ]