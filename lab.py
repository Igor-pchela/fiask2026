# Этот код уже есть в шаблоне. Используйте его в своей работе, для отладки. В ответ добавлять этот код не нужно

import sys
import io
import contextlib
from itertools import cycle
import datetime
from flask import Flask, jsonify, request

status_lst = ["cancelled", "completed", "in_progress", "pending"]
priority_lst = ["high", "low", "medium"]

def get_task_list():
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        import this
    text = f.getvalue()
    status_cycle = cycle(status_lst)
    priority_cycle = cycle(priority_lst)
    tasks_lst = []
    num = 0
    for line in text.splitlines():
        if not line:
            continue
        num += 1
        tasks_lst.append({
            "id": num,
            "title": "Zen of Python",
            "description": line,
            "status": next(status_cycle),
            "priority": next(priority_cycle),
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "deleted_at": None,
        })
    return tasks_lst

tasks_lst = get_task_list()
from flask import Flask, jsonify, request
import datetime

app = Flask(__name__)
# Этот код уже есть в шаблоне. Используйте его в своей работе, для отладки. В ответ добавлять этот код не нужно
# ... (код инициализации tasks_lst) ...

from flask import Flask, jsonify, request
import datetime

app = Flask(__name__)

# tasks_lst уже заполнен данными из get_task_list() (id от 1 до 20)


@app.route("/api/v1/tasks", methods=["GET"])
def get_tasks_lst():
    # Get query parameters
    query = request.args.get("query", "").strip()
    order = request.args.get("order", "id")
    offset = request.args.get("offset", 0)

    # Convert offset to int
    try:
        offset = int(offset)
    except ValueError:
        offset = 0

    # Start with all tasks
    tasks = tasks_lst[:]

    # Filter by search query (case-insensitive)
    if query:
        query_lower = query.lower()
        tasks = [
            task for task in tasks
            if query_lower in task["title"].lower() or query_lower in task["description"].lower()
        ]

    # Sorting
    reverse = False
    sort_field = order
    if order.startswith("-"):
        sort_field = order[1:]
        reverse = True

    # Ensure sort_field exists in task dict (default to "id")
    if sort_field not in tasks[0] if tasks else {}:
        sort_field = "id"

    tasks.sort(key=lambda x: x.get(sort_field), reverse=reverse)

    # Pagination: offset and limit 10
    tasks = tasks[offset:]
    tasks = tasks[:10]  # ограничение вывода 10 задачами

    return jsonify({"tasks": tasks})


@app.route("/api/v1/tasks/<task_id>", methods=["GET"])
def get_tasks(task_id):
    try:
        task_id = int(task_id)
    except ValueError:
        return jsonify({"error": "Задача не найдена"}), 404

    for task in tasks_lst:
        if task["id"] == task_id:
            return jsonify(task)

    return jsonify({"error": "Задача не найдена"}), 404


@app.route("/api/v1/tasks", methods=["POST"])
def post_tasks():
    data = request.get_json()
    # Пустой JSON или отсутствие данных -> ошибка
    if data is None or data == {}:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    # Validate required fields
    if "title" not in data:
        return jsonify({"error": "Пропущен обязательный параметр `title`"}), 400
    if "description" not in data:
        return jsonify({"error": "Пропущен обязательный параметр `description`"}), 400

    title = data["title"]
    description = data["description"]
    status = data.get("status", "pending")
    priority = data.get("priority", "medium")

    # Validate status if provided
    if status not in ["cancelled", "completed", "in_progress", "pending"]:
        return jsonify({"error": "Поле `status` невалидно"}), 400

    # Validate priority if provided
    if priority not in ["high", "low", "medium"]:
        return jsonify({"error": "Поле `priority` невалидно"}), 400

    # Generate new id
    new_id = max((task["id"] for task in tasks_lst), default=0) + 1
    now = datetime.datetime.now().isoformat()

    new_task = {
        "id": new_id,
        "title": title,
        "description": description,
        "status": status,
        "priority": priority,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }

    tasks_lst.append(new_task)
    return jsonify(new_task), 200


@app.route("/api/v1/tasks/<task_id>", methods=["DELETE"])
def delete_tasks(task_id):
    try:
        task_id = int(task_id)
    except ValueError:
        return jsonify({"error": "Задача не найдена"}), 404

    for task in tasks_lst:
        if task["id"] == task_id:
            # Soft delete: set status to "cancelled" and deleted_at to now
            task["status"] = "cancelled"
            task["deleted_at"] = datetime.datetime.now().isoformat()
            task["updated_at"] = datetime.datetime.now().isoformat()
            return jsonify(task), 200

    return jsonify({"error": "Задача не найдена"}), 404


@app.route("/api/v1/tasks/<task_id>", methods=["PATCH"])
def patch_tasks(task_id):
    data = request.get_json()
    if data is None or data == {}:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    try:
        task_id = int(task_id)
    except ValueError:
        return jsonify({"error": "Задача не найдена"}), 404

    # Find the task
    target_task = None
    for task in tasks_lst:
        if task["id"] == task_id:
            target_task = task
            break

    if target_task is None:
        return jsonify({"error": "Задача не найдена"}), 404

    # Validate status if present
    if "status" in data and data["status"] not in ["cancelled", "completed", "in_progress", "pending"]:
        return jsonify({"error": "Поле `status` невалидно"}), 400

    # Validate priority if present
    if "priority" in data and data["priority"] not in ["high", "low", "medium"]:
        return jsonify({"error": "Поле `priority` невалидно"}), 400

    # Apply updates
    allowed_fields = ["title", "description", "status", "priority"]
    for field in allowed_fields:
        if field in data:
            target_task[field] = data[field]

    # Update updated_at timestamp
    target_task["updated_at"] = datetime.datetime.now().isoformat()

    return jsonify(target_task), 200


if __name__ == "__main__":
    app.run(debug=True)