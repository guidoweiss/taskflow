"""
taskflow/tui.py
Funções TUI (Terminal User Interface) para o taskflow.
"""
import curses
import time
from tasks import get_all_tasks, get_task, move_task, delete_task, tag_task, \
                   edit_task, get_personal_tasks, get_tasks_by_status
from board import render_board, render_mini, render_list
from db import get_connection


def run_tui():
    """Executa a interface TUI interativa."""
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)

    try:
        screen_menu(stdscr)
    finally:
        curses.nocbreak()
        curses.echo()
        curses.endwin()


def run_crud():
    """Executa operações CRUD em batch a partir de STDIN."""
    import sys
    import re

    def _ask(prompt: str) -> str:
        print(f"{prompt}", end="", flush=True)
        return sys.stdin.readline().strip()

    title = _ask("Título da tarefa: ")
    if not title:
        print("  Abortado.")
        return

    # Tags
    tags_raw = _ask("Tags (separadas por vírgula, Enter para ignorar): ") or ""
    tags = tags_raw if tags_raw else ""

    # Status
    print("\nStatus da tarefa:")
    print("  1. Backlog")
    print("  2. To Do")
    print("  3. Done")
    status_choice = _ask("Escolha (1/2/3): ")
    status_map = {"1": "backlog", "2": "todo", "3": "done"}
    status = status_map.get(status_choice, "backlog")

    # Prioridade
    prio_raw = _ask("Prioridade (alta/media/baixa, Enter para ignorar): ") or ""
    prio = prio_raw if prio_raw else ""

    # Due date
    due_raw = _ask("Prazo (YYYY-MM-DD, Enter para ignorar): ") or ""
    due = due_raw if due_raw else ""

    # Descrição
    desc = _ask("Descrição (Enter para ignorar): ") or ""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (title, description, tags, status, priority, due_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, desc, tags, status, prio, due))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(f"\n  Tarefa #{new_id} criada: {title}")
