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

    # Migração: adiciona a coluna tags se o banco já existia sem ela
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN tags TEXT DEFAULT ''")
    except Exception:
        pass  # coluna já existe, tudo certo

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Banco de dados iniciado em: {DB_PATH}")
