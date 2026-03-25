"""
taskflow/tasks.py
Funções para criar, listar, mover e remover tarefas.
"""

from db import get_connection, init_db

VALID_PRIORITIES = ("alta", "media", "baixa", "")

COLS = "id, title, description, tags, status, priority, due_date, hidden, link, plan, project_id, scheduled_at, action, action_status, action_result, recurrence, is_agent, approved_plan_id, created_at, updated_at"


def add_task(title: str, description: str = "", status: str = "backlog",
             tags: str = "", priority: str = "", due_date: str = "",
             link: str = "", plan: str = "", project_id: int = None,
             approved_plan_id: int = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (title, description, tags, status, priority, due_date, link, plan, project_id, approved_plan_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, description, tags, status, priority, due_date, link, plan, project_id, approved_plan_id))
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


def get_tasks_for_list(done_limit: int = 5) -> dict:
    """Retorna tasks agrupadas para a visualização em lista.
    TO DO e BACKLOG: todas visíveis, ordenadas por priority DESC, due_date ASC, id ASC.
    DONE: últimas N por updated_at DESC.
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

    priority_order = """
        CASE priority
            WHEN 'alta' THEN 1
            WHEN 'media' THEN 2
            WHEN 'baixa' THEN 3
            ELSE 4
        END ASC
    """

    result = {}
    for status in ("todo", "backlog"):
        cursor.execute(f"""
            SELECT {COLS} FROM tasks
            WHERE status = ? AND hidden = 0
              {blocked_filter}
            ORDER BY {priority_order}, due_date ASC NULLS LAST, id ASC
        """, (status,))
        result[status] = cursor.fetchall()

    # DONE: últimas N + contagem total
    cursor.execute(f"""
        SELECT COUNT(*) FROM tasks
        WHERE status = 'done' AND hidden = 0 AND is_agent = 0
    """)
    result["done_total"] = cursor.fetchone()[0]

    cursor.execute(f"""
        SELECT {COLS} FROM tasks
        WHERE status = 'done' AND hidden = 0 AND is_agent = 0
        ORDER BY updated_at DESC
        LIMIT ?
    """, (done_limit,))
    result["done"] = cursor.fetchall()

    conn.close()
    return result


def has_origin(task_id: int) -> bool:
    """Retorna True se a task tem pelo menos uma origem (vem de outra task)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM task_relations WHERE to_task_id = ? LIMIT 1", (task_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result


# ── Funções agent-friendly ───────────────────────────────────────────────────

def task_to_dict(row) -> dict:
    """Converte sqlite3.Row em dict serializável para JSON."""
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def update_task(task_id: int, fields: dict) -> bool:
    """
    Atualiza múltiplos campos de uma task em uma única transação.
    Campos suportados: title, description, priority, due_date, plan, link, tags, project_id, status
    """
    allowed = {"title", "description", "priority", "due_date", "plan", "link", "tags", "project_id", "status"}
    to_update = {k: v for k, v in fields.items() if k in allowed}
    if not to_update:
        return False
    set_clauses = ", ".join(f"{col} = ?" for col in to_update)
    values = list(to_update.values()) + [task_id]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE tasks SET {set_clauses}, updated_at = datetime('now', 'localtime') WHERE id = ?",
        values
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_tasks_filtered(status: str = None, project_id: int = None,
                       tag: str = None, include_hidden: bool = False) -> list:
    """Filtro combinado: status + projeto + tag, sem truncamento."""
    conditions = ["is_agent = 0"]
    params = []
    if not include_hidden:
        conditions.append("hidden = 0")
    if status:
        conditions.append("status = ?")
        params.append(status)
    if project_id:
        conditions.append("project_id = ?")
        params.append(project_id)
    if tag:
        conditions.append("(',' || tags || ',') LIKE ?")
        params.append(f"%,{tag.strip()},%")
    where = " AND ".join(conditions)
    conn = get_connection()
    rows = conn.execute(f"SELECT {COLS} FROM tasks WHERE {where} ORDER BY id ASC", params).fetchall()
    conn.close()
    return rows


_COLS_LIGHT = "id, title, status, tags, priority, due_date, project_id, hidden, is_agent, created_at, updated_at"
_COLS_FULL  = _COLS_LIGHT + ", description, plan, link"
_ORDER_PRIORITY = ("CASE priority WHEN 'alta' THEN 1 WHEN 'media' THEN 2 "
                   "WHEN 'baixa' THEN 3 ELSE 4 END ASC, "
                   "CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END ASC, "
                   "due_date ASC, id ASC")


def get_tasks_filtered_for_ai(
    status=None,
    project_id=None,
    tag=None,
    priority=None,
    search=None,
    due_soon_days=None,
    limit=50,
    full=False,
):
    """Consulta filtrada e paginada para consumo por IAs. Retorna (rows, total_count)."""
    conditions = ["is_agent = 0", "hidden = 0"]
    params = []

    if status and status != "all":
        statuses = status if isinstance(status, list) else [status]
        placeholders = ",".join("?" * len(statuses))
        conditions.append(f"status IN ({placeholders})")
        params.extend(statuses)

    if project_id:
        conditions.append("project_id = ?")
        params.append(project_id)

    if tag:
        conditions.append("(',' || tags || ',') LIKE ?")
        params.append(f"%,{tag.strip()},%")

    if priority:
        conditions.append("priority = ?")
        params.append(priority)

    if search:
        conditions.append("title LIKE ?")
        params.append(f"%{search}%")

    if due_soon_days is not None:
        conditions.append("due_date IS NOT NULL AND due_date != ''")
        conditions.append("julianday(due_date) - julianday('now','localtime') BETWEEN 0 AND ?")
        params.append(due_soon_days)

    where = " AND ".join(conditions)
    cols = _COLS_FULL if full else _COLS_LIGHT
    conn = get_connection()
    total = conn.execute(f"SELECT COUNT(*) FROM tasks WHERE {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT {cols} FROM tasks WHERE {where} ORDER BY {_ORDER_PRIORITY} LIMIT ?",
        params + [limit]
    ).fetchall()
    conn.close()
    return rows, total


# ── Planos Aprovados ─────────────────────────────────────────────────────────

APPROVED_PLAN_COLS = "id, task_id, project_id, project_path, title, plan, priority, importance_level, approved_at, task_status, link, created_at, updated_at"

VALID_IMPORTANCE = ("backend", "frontend", "structural", "other")


def decide_importance_level(plan: str, title: str = "") -> str:
    """
    Decide o importance_level baseado no conteúdo do plano.
    """
    combined = f"{title} {plan}".lower()

    backend_keywords = [
        "api", "backend", "server", "database", "db", "sql", "postgres",
        "migração", "migration", "auth", "jwt", "webhook", "crud", "model",
        "schema", "refatorar backend", "infrastructure", "deploy", "docker",
        "n8n", "workflow", "integração", "migration", "script", "migration"
    ]

    frontend_keywords = [
        "frontend", "ui", "interface", "componente", "react", "vue", "html",
        "css", "estilo", "layout", "página", "landing", "tela", "modal",
        "form", "input", "botão", "boton", "button"
    ]

    structural_keywords = [
        "arquitetura", "architecture", "refatorar", "refactor", "restrutura",
        "padronizar", "standardize", "migration", "migração", "setup",
        "configuração", "config", "pipeline", "lint", "teste", "ci/cd",
        "github", "workflow"
    ]

    backend_score = sum(1 for kw in backend_keywords if kw in combined)
    frontend_score = sum(1 for kw in frontend_keywords if kw in combined)
    structural_score = sum(1 for kw in structural_keywords if kw in combined)

    max_score = max(backend_score, frontend_score, structural_score)

    if max_score == 0:
        return "other"

    if backend_score == max_score:
        return "backend"
    elif structural_score == max_score:
        return "structural"
    elif frontend_score == max_score:
        return "frontend"
    return "other"


def add_approved_plan(
    title: str,
    plan: str,
    task_id: int = None,
    project_id: int = None,
    project_path: str = "",
    priority: str = "",
    importance_level: str = None,
    task_status: str = "",
    link: str = "",
) -> int:
    """
    Adiciona um plano aprovado ao histórico.
    Se importance_level não for fornecido, decide automaticamente.
    """
    if importance_level is None:
        importance_level = decide_importance_level(plan, title)

    if importance_level not in VALID_IMPORTANCE:
        importance_level = "other"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO approved_plans
        (task_id, project_id, project_path, title, plan, priority, importance_level, task_status, link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (task_id, project_id, project_path, title, plan, priority, importance_level, task_status, link))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_approved_plan(plan_id: int):
    """Retorna um plano aprovado pelo ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM approved_plans WHERE id = ?", (plan_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_all_approved_plans(
    project_id: int = None,
    importance: str = None,
    priority: str = None,
    since: str = None,
) -> list:
    """Retorna lista de planos aprovados com filtros opcionais."""
    conditions = ["1=1"]
    params = []

    if project_id:
        conditions.append("project_id = ?")
        params.append(project_id)

    if importance and importance in VALID_IMPORTANCE:
        conditions.append("importance_level = ?")
        params.append(importance)

    if priority:
        conditions.append("priority = ?")
        params.append(priority)

    if since:
        conditions.append("approved_at >= ?")
        params.append(since)

    where = " AND ".join(conditions)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT * FROM approved_plans
        WHERE {where}
        ORDER BY approved_at DESC
    """, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_approved_plan(plan_id: int) -> bool:
    """Remove um plano aprovado."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM approved_plans WHERE id = ?", (plan_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def parse_plan_steps(plan: str) -> list:
    """
    Parse o plano em passos individuais.
    Aceita formatos como:
    - "1. Fazer algo"
    - "1) Fazer algo"
    - "- Fazer algo"
    - "  1. Fazer algo"
    """
    if not plan:
        return []
    
    lines = plan.replace('\\n', '\n').split('\n')
    steps = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        import re
        match = re.match(r'^[\d]+[.\)]\s*(.+)$', line)
        if match:
            steps.append(match.group(1).strip())
            continue
        
        if line.startswith('- ') or line.startswith('* '):
            steps.append(line[2:].strip())
            continue
        
        if line and not line.startswith('#'):
            steps.append(line)
    
    return [s for s in steps if s]


def create_subtasks_from_plan(
    plan_id: int,
    plan_title: str,
    project_id: int = None,
    priority: str = "",
    parent_task_id: int = None,
) -> list:
    """
    Cria subtasks baseadas nos passos de um plano aprovado.
    Retorna lista de IDs das tasks criadas.
    """
    approved_plan = get_approved_plan(plan_id)
    if not approved_plan:
        return []
    
    plan_text = approved_plan['plan']
    steps = parse_plan_steps(plan_text)
    
    if not steps:
        return []
    
    created_task_ids = []
    
    for i, step in enumerate(steps):
        step_title = step[:200] if len(step) > 200 else step
        
        subtask_id = add_task(
            title=step_title,
            project_id=project_id,
            priority=priority,
            status='todo',
            plan='',
            approved_plan_id=plan_id,
        )
        
        if subtask_id and parent_task_id:
            add_relation(parent_task_id, subtask_id, 'continues')
        
        created_task_ids.append(subtask_id)
    
    return created_task_ids
