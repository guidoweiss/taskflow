"""
taskflow/tasks.py
Funções para criar, listar, mover e remover tarefas.
"""

from db import get_connection, init_db

VALID_PRIORITIES = ("alta", "media", "baixa", "")

COLS = "id, title, description, tags, status, priority, due_date, hidden, created_at, updated_at"


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
        SET status = ?, hidden = 0, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (new_status, task_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def tag_task(task_id: int, tags: str) -> tuple[bool, str]:
    """
    Define a tag de uma tarefa — apenas 1 tag por task.
    Se forem passadas múltiplas, usa apenas a primeira.
    Retorna (sucesso, tag_usada).
    """
    first_tag = tags.split(",")[0].strip() if tags else ""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks
        SET tags = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (first_tag, task_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated, first_tag


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
        return None

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


def set_hidden(task_id: int, hidden: bool) -> bool:
    """Define o campo hidden de uma tarefa (True = oculta, False = visível)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks
        SET hidden = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (1 if hidden else 0, task_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def auto_hide_stale(days: int = 14) -> int:
    """
    Marca como hidden=1 todas as tasks em backlog sem atividade há `days` dias.
    Retorna a quantidade de tasks ocultadas.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE tasks
        SET hidden = 1, updated_at = datetime('now', 'localtime')
        WHERE status = 'backlog'
          AND hidden = 0
          AND julianday('now', 'localtime') - julianday(updated_at) > ?
    """, (days,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


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
        cursor.execute(f"""
            SELECT {COLS} FROM tasks
            WHERE status = ? AND hidden = 0 AND (',' || tags || ',') LIKE ?
            ORDER BY id ASC
        """, (status, f"%,{tag_filter.strip()},%"))
    else:
        cursor.execute(f"""
            SELECT {COLS} FROM tasks
            WHERE status = ? AND hidden = 0
            ORDER BY id ASC
        """, (status,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_hidden_tasks() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {COLS} FROM tasks
        WHERE hidden = 1
        ORDER BY updated_at ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_tasks() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {COLS} FROM tasks ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def search_tasks(query: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    pattern = f"%{query}%"
    cursor.execute(f"""
        SELECT {COLS} FROM tasks
        WHERE (title LIKE ? OR description LIKE ?) AND hidden = 0
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
