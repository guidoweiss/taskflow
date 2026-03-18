"""
taskflow/tasks.py
Funções para criar, listar, mover e remover tarefas.
"""

from db import get_connection, init_db

VALID_PRIORITIES = ("alta", "media", "baixa", "")

COLS = "id, title, description, tags, status, priority, due_date, hidden, link, plan, project_id, scheduled_at, action, action_status, action_result, recurrence, is_agent, created_at, updated_at"


def add_task(title: str, description: str = "", status: str = "backlog",
             tags: str = "", priority: str = "", due_date: str = "",
             link: str = "", plan: str = "", project_id: int = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, description, tags, status, priority, due_date, link, plan, project_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, description, tags, status, priority, due_date, link, plan, project_id))
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
        "link":     "link",
        "plan":     "plan",
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


def auto_promote_due(days_ahead: int = 0) -> int:
    """
    Move para 'todo' todas as tasks em 'backlog' que têm due_date definida.
    Retorna a quantidade de tasks promovidas.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks
        SET status = 'todo', updated_at = datetime('now', 'localtime')
        WHERE status = 'backlog'
          AND hidden = 0
          AND due_date IS NOT NULL
          AND due_date != ''
    """)
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


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
    """
    Retorna tasks pessoais (sem action) pelo status, excluindo:
    - tasks ocultas (hidden = 1)
    - agent tasks (action IS NOT NULL)
    - tasks bloqueadas na fila (origem ainda não concluída)
    """
    conn = get_connection()
    cursor = conn.cursor()

    blocked_filter = """
        AND is_agent = 0
        AND NOT EXISTS (
            SELECT 1 FROM task_relations r
            JOIN tasks origin ON origin.id = r.from_task_id
            WHERE r.to_task_id = tasks.id
              AND origin.status != 'done'
        )
    """

    if tag_filter:
        cursor.execute(f"""
            SELECT {COLS} FROM tasks
            WHERE status = ? AND hidden = 0
              AND (',' || tags || ',') LIKE ?
              {blocked_filter}
            ORDER BY id ASC
        """, (status, f"%,{tag_filter.strip()},%"))
    else:
        cursor.execute(f"""
            SELECT {COLS} FROM tasks
            WHERE status = ? AND hidden = 0
              {blocked_filter}
            ORDER BY id ASC
        """, (status,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_agent_tasks_by_status(action_status: str) -> list:
    """Retorna agent tasks por action_status para o kanban de agente."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {COLS} FROM tasks
        WHERE is_agent = 1
          AND (action_status = ? OR (action_status IS NULL AND ? = 'pending'))
          AND hidden = 0
        ORDER BY scheduled_at ASC
    """, (action_status, action_status))
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


def get_personal_tasks() -> list:
    """Retorna todas as tasks pessoais (is_agent = 0), incluindo ocultas."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {COLS} FROM tasks WHERE is_agent = 0 ORDER BY id ASC")
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


# ── Relações entre tasks ──────────────────────────────────────────────────────

def add_relation(from_task_id: int, to_task_id: int, rel_type: str = "continues") -> bool:
    """Cria uma relação entre duas tasks. Retorna False se já existir."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO task_relations (from_task_id, to_task_id, type)
            VALUES (?, ?, ?)
        """, (from_task_id, to_task_id, rel_type))
        conn.commit()
        return True
    except Exception:
        return False  # violação de PK = relação já existe
    finally:
        conn.close()


def remove_relation(from_task_id: int, to_task_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM task_relations
        WHERE from_task_id = ? AND to_task_id = ?
    """, (from_task_id, to_task_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_relations(task_id: int) -> dict:
    """
    Retorna dict com duas listas:
      'origins'       → tasks das quais esta veio (from_task_id → task_id)
      'continuations' → tasks que vieram desta    (task_id → to_task_id)
    Cada item é uma Row da tabela tasks enriquecida com o tipo de relação.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT t.*, r.type as rel_type
        FROM task_relations r
        JOIN tasks t ON t.id = r.from_task_id
        WHERE r.to_task_id = ?
        ORDER BY t.id ASC
    """, (task_id,))
    origins = cursor.fetchall()

    cursor.execute(f"""
        SELECT t.*, r.type as rel_type
        FROM task_relations r
        JOIN tasks t ON t.id = r.to_task_id
        WHERE r.from_task_id = ?
        ORDER BY t.id ASC
    """, (task_id,))
    continuations = cursor.fetchall()

    conn.close()
    return {"origins": origins, "continuations": continuations}


# ── Projetos ─────────────────────────────────────────────────────────────────

def add_project(name: str, description: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO projects (name, description) VALUES (?, ?)
    """, (name, description))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_project_by_name(name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE lower(name) = lower(?)", (name,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_project(project_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_all_projects(include_archived: bool = False) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    if include_archived:
        cursor.execute("SELECT * FROM projects ORDER BY starred DESC, id ASC")
    else:
        cursor.execute("SELECT * FROM projects WHERE status = 'active' ORDER BY starred DESC, id ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def archive_project(project_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE projects SET status = 'archived', updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (project_id,))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def edit_project(project_id: int, field: str, value: str) -> bool:
    field_map = {"name": "name", "desc": "description"}
    col = field_map.get(field)
    if not col:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE projects SET {col} = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (value, project_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_project(project_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET project_id = NULL WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def star_project(project_id: int, starred: bool) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE projects SET starred = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (1 if starred else 0, project_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def assign_task(task_id: int, project_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks SET project_id = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (project_id, task_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def unassign_task(task_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks SET project_id = NULL, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (task_id,))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_tasks_by_project(project_id: int) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {COLS} FROM tasks
        WHERE project_id = ? AND hidden = 0
        ORDER BY id ASC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ── Agent tasks ──────────────────────────────────────────────────────────────

def add_agent_task(title: str, action: str, scheduled_at: str,
                   description: str = "", project_id: int = None, tags: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, description, tags, project_id, status, action, scheduled_at, action_status, is_agent)
        VALUES (?, ?, ?, ?, 'backlog', ?, ?, 'pending', 1)
    """, (title, description, tags, project_id, action, scheduled_at))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_due_agent_tasks() -> list:
    """Agent tasks vencidas e ainda pendentes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {COLS} FROM tasks
        WHERE is_agent = 1
          AND action_status = 'pending'
          AND scheduled_at <= datetime('now', 'localtime')
          AND hidden = 0
        ORDER BY scheduled_at ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_agent_tasks() -> list:
    """Todas as agent tasks (para listagem)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT {COLS} FROM tasks
        WHERE is_agent = 1
        ORDER BY scheduled_at ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def count_agent_done_today() -> int:
    """Quantas agent tasks foram executadas hoje."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE action_status IN ('done', 'cancelled')
          AND date(updated_at) = date('now', 'localtime')
    """)
    count = cursor.fetchone()[0]
    conn.close()
    return count


def update_action_status(task_id: int, status: str, result: str = "") -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks
        SET action_status = ?, action_result = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (status, result, task_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def has_origin(task_id: int) -> bool:
    """Retorna True se a task tem pelo menos uma origem (vem de outra task)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM task_relations WHERE to_task_id = ? LIMIT 1", (task_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result
