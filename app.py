import sys
import io
import contextlib
from itertools import cycle
import datetime
from flask import Flask, jsonify, request
app = Flask(__name__)

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

# ---------- Helper functions ----------
def validate_status(status: str) -> tuple[bool, str | None]:
    """Validate task status. Returns (is_valid, error_message)."""
    if status not in status_lst:
        return False, "Поле `status` невалидно"
    return True, None

def validate_priority(priority: str) -> tuple[bool, str | None]:
    """Validate task priority. Returns (is_valid, error_message)."""
    if priority not in priority_lst:
        return False, "Поле `priority` невалидно"
    return True, None

def get_task_by_id(task_id: int) -> dict | None:
    """Return task dict if found, else None."""
    for task in tasks_lst:
        if task["id"] == task_id:
            return task
    return None

def safe_sort_key(task: dict, field: str):
    """
    Return a sortable key for the given field.
    Handles None values for string and datetime fields.
    """
    value = task.get(field)
    if value is None:
        # For datetime fields, treat None as the minimum possible datetime
        if field in ("created_at", "updated_at", "deleted_at"):
            return datetime.datetime.min
        # For string fields (including title, description, status, priority)
        return ""
    return value

def parse_offset(offset_str: str) -> int:
    """Convert offset to non-negative integer."""
    try:
        offset = int(offset_str)
        return max(offset, 0)
    except (ValueError, TypeError):
        return 0

# ---------- Routes ----------
@app.route("/api/v1/tasks", methods=["GET"])
def get_tasks_lst():
    # Query parameters
    query = request.args.get("query", "").strip()
    order = request.args.get("order", "id")
    offset = parse_offset(request.args.get("offset", 0))

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

    # Fallback to "id" if sort_field does not exist in tasks
    if tasks and sort_field not in tasks[0]:
        sort_field = "id"

    # Use safe_sort_key to handle None values
    tasks.sort(key=lambda t: safe_sort_key(t, sort_field), reverse=reverse)

    # Pagination: offset + limit 10
    tasks = tasks[offset:offset + 10]

    return jsonify({"tasks": tasks})

@app.route("/api/v1/tasks/<task_id>", methods=["GET"])
def get_tasks(task_id):
    try:
        task_id = int(task_id)
    except ValueError:
        return jsonify({"error": "Задача не найдена"}), 404

    task = get_task_by_id(task_id)
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404
    return jsonify(task)

@app.route("/api/v1/tasks", methods=["POST"])
def post_tasks():
    data = request.get_json()
    if data is None or data == {}:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    # Required fields
    if "title" not in data:
        return jsonify({"error": "Пропущен обязательный параметр `title`"}), 400
    if "description" not in data:
        return jsonify({"error": "Пропущен обязательный параметр `description`"}), 400

    title = data["title"]
    description = data["description"]
    status = data.get("status", "pending")
    priority = data.get("priority", "medium")

    # Validate optional fields
    valid, err_msg = validate_status(status)
    if not valid:
        return jsonify({"error": err_msg}), 400
    valid, err_msg = validate_priority(priority)
    if not valid:
        return jsonify({"error": err_msg}), 400

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

    task = get_task_by_id(task_id)
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404

    # Soft delete
    task["status"] = "cancelled"
    task["deleted_at"] = datetime.datetime.now().isoformat()
    task["updated_at"] = datetime.datetime.now().isoformat()
    return jsonify(task), 200

@app.route("/api/v1/tasks/<task_id>", methods=["PATCH"])
def patch_tasks(task_id):
    data = request.get_json()
    if data is None or data == {}:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    try:
        task_id = int(task_id)
    except ValueError:
        return jsonify({"error": "Задача не найдена"}), 404

    task = get_task_by_id(task_id)
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404

    # Validate status if present
    if "status" in data:
        valid, err_msg = validate_status(data["status"])
        if not valid:
            return jsonify({"error": err_msg}), 400

    # Validate priority if present
    if "priority" in data:
        valid, err_msg = validate_priority(data["priority"])
        if not valid:
            return jsonify({"error": err_msg}), 400

    # Apply updates
    allowed_fields = {"title", "description", "status", "priority"}
    for field in allowed_fields:
        if field in data:
            task[field] = data[field]

    task["updated_at"] = datetime.datetime.now().isoformat()
    return jsonify(task), 200

if __name__ == "__main__":
    app.run(debug=True)