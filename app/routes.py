from flask import Blueprint, render_template, request, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Task
from app.utils import (
    load_tasks, add_task, update_task_text, delete_task,
    toggle_task_status, reset_all_tasks
)

main = Blueprint("main", __name__)

engine = create_engine("sqlite:///todo.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

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