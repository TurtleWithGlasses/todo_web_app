from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Task
from app.utils import (
    load_tasks, add_task, update_task_text, delete_task,
    toggle_task_status, reset_all_tasks,
    load_daily_tasks, add_daily_task, update_daily_task,
    delete_daily_task, set_daily_task_status, get_daily_stats,
    get_weekly_stats, get_analysis,
    load_categories, add_category, update_category, delete_category,
    seed_categories,
)

main = Blueprint("main", __name__)

engine = create_engine("sqlite:///todo.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
seed_categories()

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/tasks", methods=["GET"])
def get_tasks():
    tasks = load_tasks()
    return jsonify([
        {
            "id": task.id,
            "text": task.text,
            "data_status": task.data_status,
            "work_status": task.work_status,
            "position": task.position
        }
        for task in tasks
    ])

@main.route("/add", methods=["POST"])
def add():
    data = request.get_json()
    task_text = data.get("task")
    if task_text:
        task = add_task(task_text)
        return jsonify({
            "success": True,
            "id": task.id,
            "text": task.text,
            "data_status": task.data_status,
            "work_status": task.work_status
        })
    return jsonify({"success": False}), 400

@main.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    delete_task(id)
    return jsonify({"success": True})

@main.route("/edit", methods=["POST"])
def edit():
    data = request.get_json()
    update_task_text(data["id"], data["new_text"])
    return jsonify({"success": True})

@main.route("/toggle/<int:id>/<column>", methods=["POST"])
def toggle(id, column):
    toggle_task_status(id, column)
    return jsonify({"success": True})

@main.route("/reset", methods=["POST"])
def reset():
    reset_all_tasks()
    return jsonify({"success": True})

@main.route("/move", methods=["POST"])
def move():
    data = request.get_json()
    print("Move request received:", data)
    task_id = data["id"]
    direction = data["direction"]

    with SessionLocal() as db:
        tasks = db.query(Task).order_by(Task.position).all()
        task_ids = [t.id for t in tasks]
        index = task_ids.index(task_id)

        swap_index = index -1 if direction == "up" else index + 1

        if 0 <= swap_index < len(tasks):
            tasks[index].position, tasks[swap_index].position = tasks[swap_index].position, tasks[index].position
            db.commit()
    
    return jsonify({"success": True})

@main.route("/reorder", methods=["POST"])
def reorder():
    """Update task positions based on drag-and-drop order"""
    data = request.get_json()
    task_ids = data.get("order", [])

    with SessionLocal() as db:
        for position, task_id in enumerate(task_ids):
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.position = position
        db.commit()

    return jsonify({"success": True})


# --- Daily task routes ---

@main.route("/daily")
def daily():
    return render_template("daily.html")

@main.route("/daily/tasks", methods=["GET"])
def daily_get_tasks():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "date required"}), 400
    tasks = load_daily_tasks(date)
    return jsonify([
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "time": t.time,
            "category": t.category,
            "priority": t.priority,
            "status": t.status,
            "date": t.date,
            "position": t.position,
        }
        for t in tasks
    ])

@main.route("/daily/add", methods=["POST"])
def daily_add():
    data = request.get_json()
    required = ("title", "date")
    if not all(data.get(k) for k in required):
        return jsonify({"success": False, "error": "title and date are required"}), 400
    task = add_daily_task(
        title=data["title"],
        description=data.get("description", ""),
        time=data.get("time", ""),
        category=data.get("category", ""),
        priority=data.get("priority", "orta"),
        date=data["date"],
    )
    return jsonify({
        "success": True,
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "time": task.time,
        "category": task.category,
        "priority": task.priority,
        "status": task.status,
        "date": task.date,
        "position": task.position,
    })

@main.route("/daily/edit/<int:id>", methods=["POST"])
def daily_edit(id):
    data = request.get_json()
    allowed = {"title", "description", "time", "category", "priority"}
    fields = {k: v for k, v in data.items() if k in allowed}
    update_daily_task(id, **fields)
    return jsonify({"success": True})

@main.route("/daily/status/<int:id>", methods=["POST"])
def daily_status(id):
    data = request.get_json()
    status = data.get("status")
    valid = {"yapılacak", "yapılıyor", "tamamlandı"}
    if status not in valid:
        return jsonify({"success": False, "error": "invalid status"}), 400
    set_daily_task_status(id, status)
    return jsonify({"success": True})

@main.route("/daily/delete/<int:id>", methods=["POST"])
def daily_delete(id):
    delete_daily_task(id)
    return jsonify({"success": True})

@main.route("/daily/stats", methods=["GET"])
def daily_stats():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "date required"}), 400
    return jsonify(get_daily_stats(date))

@main.route("/daily/categories", methods=["GET"])
def categories_list():
    cats = load_categories()
    return jsonify([{"id": c.id, "name": c.name, "color": c.color, "position": c.position} for c in cats])

@main.route("/daily/categories", methods=["POST"])
def categories_add():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    color = data.get("color", "#06b6d4")
    if not name:
        return jsonify({"success": False, "error": "name required"}), 400
    cat = add_category(name, color)
    return jsonify({"success": True, "id": cat.id, "name": cat.name, "color": cat.color, "position": cat.position})

@main.route("/daily/categories/<int:id>/edit", methods=["POST"])
def categories_edit(id):
    data = request.get_json()
    update_category(id, name=data.get("name"), color=data.get("color"))
    return jsonify({"success": True})

@main.route("/daily/categories/<int:id>/delete", methods=["POST"])
def categories_delete(id):
    delete_category(id)
    return jsonify({"success": True})


@main.route("/daily/weekly-stats", methods=["GET"])
def daily_weekly_stats():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "date required"}), 400
    return jsonify(get_weekly_stats(date))

@main.route("/daily/analysis", methods=["GET"])
def daily_analysis():
    from_date = request.args.get("from")
    to_date   = request.args.get("to")
    if not from_date or not to_date:
        return jsonify({"error": "from and to required"}), 400
    return jsonify(get_analysis(from_date, to_date))