"""
taskflow/db.py
Responsável por criar e gerenciar a conexão com o banco de dados SQLite.
"""

import sqlite3
from pathlib import Path

# Caminho do arquivo do banco de dados
DB_PATH = Path(__file__).parent / "taskflow.db"


def get_connection():
    """Retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    # Faz com que as linhas retornadas sejam acessíveis por nome de coluna
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Cria as tabelas se ainda não existirem.
    O comando CREATE TABLE IF NOT EXISTS é seguro: não apaga dados existentes.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            tags        TEXT    DEFAULT '',
            status      TEXT    NOT NULL DEFAULT 'backlog'
                            CHECK(status IN ('backlog', 'todo', 'done')),
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # Migrações: adiciona colunas se o banco já existia sem elas
    for migration in [
        "ALTER TABLE tasks ADD COLUMN tags     TEXT    DEFAULT ''",
        "ALTER TABLE tasks ADD COLUMN priority TEXT    DEFAULT ''",
        "ALTER TABLE tasks ADD COLUMN due_date TEXT    DEFAULT ''",
        "ALTER TABLE tasks ADD COLUMN hidden   INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE tasks ADD COLUMN link     TEXT    DEFAULT ''",
        "ALTER TABLE tasks ADD COLUMN plan     TEXT    DEFAULT ''",
    ]:
        try:
            cursor.execute(migration)
        except Exception:
            pass  # coluna já existe, tudo certo

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            status      TEXT    NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active', 'archived')),
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN project_id INTEGER DEFAULT NULL")
    except Exception:
        pass  # coluna já existe

    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN starred INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass  # coluna já existe

    for migration in [
        "ALTER TABLE tasks ADD COLUMN scheduled_at   TEXT DEFAULT NULL",
        "ALTER TABLE tasks ADD COLUMN action         TEXT DEFAULT NULL",
        "ALTER TABLE tasks ADD COLUMN action_status  TEXT DEFAULT NULL",
        "ALTER TABLE tasks ADD COLUMN action_result  TEXT DEFAULT NULL",
        "ALTER TABLE tasks ADD COLUMN recurrence     TEXT DEFAULT NULL",
        "ALTER TABLE tasks ADD COLUMN is_agent       INTEGER NOT NULL DEFAULT 0",
    ]:
        try:
            cursor.execute(migration)
        except Exception:
            pass  # coluna já existe

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_relations (
            from_task_id INTEGER NOT NULL,
            to_task_id   INTEGER NOT NULL,
            type         TEXT    NOT NULL DEFAULT 'continues',
            PRIMARY KEY (from_task_id, to_task_id)
        )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Banco de dados iniciado em: {DB_PATH}")
