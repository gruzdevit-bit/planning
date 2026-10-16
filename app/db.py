import json
import os
import re
import sqlite3
from datetime import datetime

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def db_path():
    data_dir = os.environ.get("DATA_DIR", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "daily.db")


def connect():
    conn = sqlite3.connect(db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NULL,
                description TEXT NOT NULL DEFAULT '',
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_date ON tasks(date)")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )"""
        )
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "date": row["date"],
        "time": row["time"],
        "description": row["description"],
        "done": bool(row["done"]),
        "created_at": row["created_at"],
    }


def valid_date(value):
    if not isinstance(value, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def list_tasks(date):
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE date = ? ORDER BY time IS NULL, time, id",
            (date,),
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def days_with_tasks(month):
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT DISTINCT date FROM tasks WHERE date LIKE ? ORDER BY date",
            (month + "-%",),
        ).fetchall()
        return [r["date"] for r in rows]
    finally:
        conn.close()


def get_task(task_id):
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def create_task(title, date, time, description):
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT INTO tasks (title, date, time, description, done, created_at) "
            "VALUES (?, ?, ?, ?, 0, ?)",
            (title, date, time, description, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        task_id = cur.lastrowid
    finally:
        conn.close()
    return get_task(task_id)


def update_task(task_id, title, date, time, description):
    conn = connect()
    try:
        cur = conn.execute(
            "UPDATE tasks SET title = ?, date = ?, time = ?, description = ? WHERE id = ?",
            (title, date, time, description, task_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get_task(task_id)


def set_done(task_id, done):
    conn = connect()
    try:
        cur = conn.execute(
            "UPDATE tasks SET done = ? WHERE id = ?", (1 if done else 0, task_id)
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get_task(task_id)


def delete_task(task_id):
    conn = connect()
    try:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_setting(key):
    conn = connect()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_setting(key, value):
    conn = connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        conn.commit()
    finally:
        conn.close()


def get_city():
    raw = get_setting("city")
    if not raw:
        return None
    try:
        city = json.loads(raw)
    except ValueError:
        return None
    return city if isinstance(city, dict) else None


def set_city(city):
    set_setting("city", json.dumps(city, ensure_ascii=False))
