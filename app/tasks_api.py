from flask import Blueprint, jsonify, request

from . import db

bp = Blueprint("tasks_api", __name__)

TITLE_REQUIRED = "Название дела обязательно"


def error(message, status=400):
    return jsonify({"error": message}), status


def clean_fields(title, date, time, description):
    """Возвращает (поля, ошибка)."""
    if not isinstance(title, str) or not title.strip():
        return None, TITLE_REQUIRED
    title = title.strip()
    if len(title) > 200:
        return None, "Название дела не должно быть длиннее 200 символов"
    if not db.valid_date(date):
        return None, "Укажите корректную дату"
    if time is None or time == "":
        time = None
    elif not isinstance(time, str) or not db.TIME_RE.match(time):
        return None, "Укажите время в формате ЧЧ:ММ"
    if description is None:
        description = ""
    if not isinstance(description, str):
        return None, "Описание должно быть текстом"
    description = description.strip()
    if len(description) > 2000:
        return None, "Описание не должно быть длиннее 2000 символов"
    return (title, date, time, description), None


@bp.get("/api/tasks")
def get_tasks():
    date = request.args.get("date", "")
    if not db.valid_date(date):
        return error("Параметр date должен быть в формате ГГГГ-ММ-ДД")
    return jsonify(db.list_tasks(date))


@bp.get("/api/tasks/days")
def get_days():
    month = request.args.get("month", "")
    if not db.MONTH_RE.match(month):
        return error("Параметр month должен быть в формате ГГГГ-ММ")
    return jsonify(db.days_with_tasks(month))


@bp.post("/api/tasks")
def create():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("Неверное тело запроса")
    fields, err = clean_fields(
        data.get("title"), data.get("date"), data.get("time"), data.get("description")
    )
    if err:
        return error(err)
    return jsonify(db.create_task(*fields)), 201


@bp.put("/api/tasks/<int:task_id>")
def update(task_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("Неверное тело запроса")
    existing = db.get_task(task_id)
    if existing is None:
        return error("Дело не найдено", 404)
    fields, err = clean_fields(
        data.get("title", existing["title"]),
        data.get("date", existing["date"]),
        data.get("time", existing["time"]) if "time" in data else existing["time"],
        data.get("description", existing["description"]),
    )
    if err:
        return error(err)
    return jsonify(db.update_task(task_id, *fields))


@bp.patch("/api/tasks/<int:task_id>/done")
def done(task_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("done"), bool):
        return error("Передайте {\"done\": true|false}")
    task = db.set_done(task_id, data["done"])
    if task is None:
        return error("Дело не найдено", 404)
    return jsonify(task)


@bp.delete("/api/tasks/<int:task_id>")
def delete(task_id):
    if not db.delete_task(task_id):
        return error("Дело не найдено", 404)
    return "", 204
