"""
taskflow/tasks.py
Funções para criar, listar, mover e remover tarefas.
Cada função executa um comando SQL diferente — ótimo para aprender!
"""

from db import get_connection, init_db


def add_task(title: str, description: str = "", status: str = "backlog", tags: str = "") -> int:
    """
    Insere uma nova tarefa no banco.
    SQL: INSERT INTO tasks (...) VALUES (...)
    Retorna o ID da tarefa criada.
    Tags são uma string separada por vírgulas: "dev,api,urgente"
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (title, description, tags, status)
        VALUES (?, ?, ?, ?)
    """, (title, description, tags, status))

    new_id = cursor.lastrowid  # ID gerado automaticamente pelo banco
    conn.commit()
    conn.close()
    return new_id


def move_task(task_id: int, new_status: str) -> bool:
    """
    Muda o status de uma tarefa.
    SQL: UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?
    Retorna True se a tarefa foi encontrada e atualizada.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tasks
        SET status = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (new_status, task_id))

    updated = cursor.rowcount > 0  # rowcount = quantas linhas foram afetadas
    conn.commit()
    conn.close()
    return updated


def tag_task(task_id: int, tags: str) -> bool:
    """
    Define as tags de uma tarefa (sobrescreve as anteriores).
    SQL: UPDATE tasks SET tags = ?, updated_at = ? WHERE id = ?
    Passe tags="" para limpar todas as tags.
    """
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


def delete_task(task_id: int) -> bool:
    """
    Remove uma tarefa permanentemente.
    SQL: DELETE FROM tasks WHERE id = ?
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_tasks_by_status(status: str) -> list:
    """
    Busca todas as tarefas de uma coluna específica.
    SQL: SELECT * FROM tasks WHERE status = ? ORDER BY id ASC
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, description, tags, status, created_at, updated_at
        FROM tasks
        WHERE status = ?
        ORDER BY id ASC
    """, (status,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_tasks() -> list:
    """
    Busca todas as tarefas do banco.
    SQL: SELECT * FROM tasks ORDER BY id ASC
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, description, tags, status, created_at, updated_at
        FROM tasks
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_task(task_id: int):
    """
    Busca uma tarefa específica pelo ID.
    SQL: SELECT * FROM tasks WHERE id = ?
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return row
