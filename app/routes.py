from flask import Blueprint, render_template, request, redirect, jsonify
from app.utils import load_tasks, save_tasks

main = Blueprint("main", __name__)

@main.route("/")
def index():
    tasks = load_tasks()
    return render_template("index.html", tasks=tasks)

@main.route("/add", methods=["POST"])
def add():
    task_text = request.form.get("task")
    if task_text:
        tasks = load_tasks()
        tasks.append([task_text, "☐", "☐"])
        save_tasks(tasks)
    return redirect("/")

@main.route("/edit", methods=["POST"])
def edit():
    idx = int(request.form.get("index"))
    new_text = request.form.get("new_text")
    tasks = load_tasks()
    if 0 <= idx < len(tasks):
        tasks[idx][0] = new_text
        save_tasks(tasks)
    return redirect("/")

@main.route("/delete/<int:index>", methods=["POST"])
def delete(index):
    tasks = load_tasks()
    if 0 <= index < len(tasks):
        del tasks[index]
        save_tasks(tasks)
    return redirect("/")

@main.route("/toggle/<int:index>/<column>", methods=["POST"])
def toggle(index, column):
    tasks = load_tasks()
    if 0 <= index < len(tasks):
        if column == "data":
            tasks[index][1] = "☐" if tasks[index][1] == "☑" else "☑"
        elif column == "work":
            tasks[index][2] = "☐" if tasks[index][2] == "☑" else "☑"
        save_tasks(tasks)
    return redirect("/")

@main.route("/reset", methods=["POST"])
def reset():
    tasks = load_tasks()
    for task in tasks:
        task[1] = "☐"
        task[2] = "☐"
    save_tasks(tasks)
    return redirect("/")