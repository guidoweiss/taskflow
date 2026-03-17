"""
taskflow/tasks.py
Funções para criar, listar, mover e remover tarefas.
"""

from db import get_connection, init_db

VALID_PRIORITIES = ("alta", "media", "baixa", "")


def add_task(title: str, description: str = "", status: str = "backlog",
             tags: str = "", priority: str = "", due_date: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, description, tags, status, priority, due_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, description, tags, status, priority, due_date))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def move_task(task_id: int, new_status: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks
        SET status = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (new_status, task_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def tag_task(task_id: int, tags: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks
        SET tags = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (tags, task_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def edit_task(task_id: int, field: str, value: str) -> bool:
    """
    Edita um campo específico de uma tarefa.
    Campos válidos: title, desc, priority, due
    """
    field_map = {
        "title":    "title",
        "desc":     "description",
        "priority": "priority",
        "due":      "due_date",
    }
    col = field_map.get(field)
    if not col:
        return None  # campo inválido

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE tasks
        SET {col} = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (value, task_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_task(task_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_tasks_by_status(status: str, tag_filter: str = "") -> list:
    conn = get_connection()
    cursor = conn.cursor()
    if tag_filter:
        cursor.execute("""
            SELECT id, title, description, tags, status, priority, due_date, created_at, updated_at
            FROM tasks
            WHERE status = ? AND (',' || tags || ',') LIKE ?
            ORDER BY id ASC
        """, (status, f"%,{tag_filter.strip()},%"))
    else:
        cursor.execute("""
            SELECT id, title, description, tags, status, priority, due_date, created_at, updated_at
            FROM tasks
            WHERE status = ?
            ORDER BY id ASC
        """, (status,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_tasks() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, description, tags, status, priority, due_date, created_at, updated_at
        FROM tasks
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def search_tasks(query: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    pattern = f"%{query}%"
    cursor.execute("""
        SELECT id, title, description, tags, status, priority, due_date, created_at, updated_at
        FROM tasks
        WHERE title LIKE ? OR description LIKE ?
        ORDER BY id ASC
    """, (pattern, pattern))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return row
