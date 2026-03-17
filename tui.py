#!/usr/bin/env python3
"""
taskflow/tui.py
Menu interativo do taskflow usando curses (stdlib).
"""

import curses
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from tasks import (get_tasks_by_status, move_task, delete_task, add_task,
                   get_project, auto_promote_due, auto_hide_stale)
from db import init_db


COLUMNS = [
    ("backlog", "BACKLOG"),
    ("todo",    "TO DO"),
    ("done",    "DONE"),
]

PRIORITY_SYM = {"alta": "▲", "media": "●", "baixa": "▽"}

HINTS = (
    "  ←→ coluna   ↑↓ tarefa   "
    "[t]odo  [d]one  [b]ack  "
    "[a]dd  [Del/x] remover  "
    "[q] sair"
)


def trunc(s: str, n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[: n - 1] + "…"


def prompt_input(stdscr, prompt: str, y: int, x: int, max_len: int = 60) -> str:
    """Lê uma string do usuário com um prompt inline na linha y."""
    height, width = stdscr.getmaxyx()
    max_len = min(max_len, width - x - len(prompt) - 2)

    curses.echo()
    curses.curs_set(1)

    # Limpa a linha e mostra o prompt
    stdscr.move(y, 0)
    stdscr.clrtoeol()
    stdscr.addstr(y, x, prompt, curses.color_pair(2) | curses.A_BOLD)
    stdscr.addstr(y, x + len(prompt), "_" * max_len, curses.color_pair(5))
    stdscr.move(y, x + len(prompt))
    stdscr.refresh()

    try:
        raw = stdscr.getstr(y, x + len(prompt), max_len)
        value = raw.decode("utf-8", errors="replace").strip()
    except Exception:
        value = ""
    finally:
        curses.noecho()
        curses.curs_set(0)

    return value


def draw(stdscr, columns_tasks, col_idx, row_idx, message="", msg_error=False):
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    # Largura de cada coluna
    col_w = max(22, (width - 3) // 3)

    for ci, (status, label) in enumerate(COLUMNS):
        x     = ci * (col_w + 1)
        tasks = columns_tasks[ci]

        # ── Cabeçalho ──────────────────────────────────────────
        header_pair = ci + 1          # pairs 1,2,3 → cyan/yellow/green
        header_text = f" {label} ({len(tasks)}) "
        header_text = header_text.center(col_w)[:col_w]
        try:
            stdscr.addstr(0, x, header_text, curses.color_pair(header_pair) | curses.A_BOLD)
        except curses.error:
            pass

        # Linha separadora
        sep = "─" * col_w
        try:
            stdscr.addstr(1, x, sep[:col_w], curses.color_pair(6))
        except curses.error:
            pass

        # ── Tasks ──────────────────────────────────────────────
        for ti, task in enumerate(tasks):
            y = 2 + ti
            if y >= height - 3:
                break

            is_sel = (ci == col_idx and ti == row_idx[ci])

            prio_sym = PRIORITY_SYM.get(task["priority"] or "", " ")
            title    = trunc(task["title"], col_w - 7)
            line     = f" {prio_sym} #{task['id']} {title}"
            line     = line.ljust(col_w)[:col_w]

            if is_sel:
                attr = curses.color_pair(4) | curses.A_BOLD
            else:
                attr = curses.A_NORMAL

            try:
                stdscr.addstr(y, x, line, attr)
            except curses.error:
                pass

    # ── Barra de mensagem ──────────────────────────────────────
    msg_y = height - 2
    if message:
        pair = 7 if msg_error else 3
        msg_line = trunc(f"  {message}", width - 1).ljust(width - 1)
        try:
            stdscr.addstr(msg_y, 0, msg_line, curses.color_pair(pair) | curses.A_BOLD)
        except curses.error:
            pass

    # ── Barra de atalhos ───────────────────────────────────────
    hint_line = trunc(HINTS, width - 1).ljust(width - 1)
    try:
        stdscr.addstr(height - 1, 0, hint_line, curses.A_REVERSE)
    except curses.error:
        pass

    stdscr.refresh()


def run_tui(stdscr):
    curses.curs_set(0)
    try:
        curses.use_default_colors()
        bg = -1
    except Exception:
        bg = curses.COLOR_BLACK

    # Pares de cor: 1=cyan  2=yellow  3=green  4=seleção  5=input  6=sep  7=erro
    curses.init_pair(1, curses.COLOR_CYAN,    bg)
    curses.init_pair(2, curses.COLOR_YELLOW,  bg)
    curses.init_pair(3, curses.COLOR_GREEN,   bg)
    curses.init_pair(4, curses.COLOR_BLACK,   curses.COLOR_CYAN)
    curses.init_pair(5, curses.COLOR_WHITE,   bg)
    curses.init_pair(6, curses.COLOR_WHITE,   bg)
    curses.init_pair(7, curses.COLOR_RED,     bg)

    init_db()
    auto_promote_due()
    auto_hide_stale(days=14)

    col_idx = 0
    row_idx = [0, 0, 0]
    message = ""
    msg_error = False

    while True:
        columns_tasks = [get_tasks_by_status(s) for s, _ in COLUMNS]

        # Garante índices válidos
        for i, tasks in enumerate(columns_tasks):
            row_idx[i] = min(row_idx[i], max(0, len(tasks) - 1))

        draw(stdscr, columns_tasks, col_idx, row_idx, message, msg_error)
        message   = ""
        msg_error = False

        key = stdscr.getch()

        # ── Navegação ──────────────────────────────────────────
        if key in (ord("q"), 27):      # q ou ESC
            break

        elif key in (curses.KEY_LEFT, ord("h")):
            col_idx = max(0, col_idx - 1)

        elif key in (curses.KEY_RIGHT, ord("l"), 9):  # 9 = Tab
            col_idx = min(2, col_idx + 1)

        elif key in (curses.KEY_UP, ord("k")):
            row_idx[col_idx] = max(0, row_idx[col_idx] - 1)

        elif key in (curses.KEY_DOWN, ord("j")):
            tasks = columns_tasks[col_idx]
            if tasks:
                row_idx[col_idx] = min(len(tasks) - 1, row_idx[col_idx] + 1)

        # ── Ações sobre a task selecionada ─────────────────────
        else:
            tasks = columns_tasks[col_idx]
            task  = tasks[row_idx[col_idx]] if tasks else None

            if key == ord("t") and task:
                move_task(task["id"], "todo")
                col_idx = 1
                message = f"#{task['id']} movida para TO DO."

            elif key == ord("d") and task:
                move_task(task["id"], "done")
                col_idx = 2
                message = f"#{task['id']} movida para DONE."

            elif key == ord("b") and task:
                move_task(task["id"], "backlog")
                col_idx = 0
                message = f"#{task['id']} movida para BACKLOG."

            elif key in (curses.KEY_DC, ord("x")) and task:
                height, _  = stdscr.getmaxyx()
                answer = prompt_input(stdscr, f"Remover #{task['id']} \"{trunc(task['title'], 30)}\"? (s/n): ",
                                      height - 2, 2, 3)
                if answer.lower() == "s":
                    delete_task(task["id"])
                    row_idx[col_idx] = max(0, row_idx[col_idx] - 1)
                    message = f"#{task['id']} removida."
                else:
                    message = "Cancelado."

            elif key == ord("a"):
                height, width = stdscr.getmaxyx()
                status_label  = COLUMNS[col_idx][1]
                title = prompt_input(stdscr, f"Novo título [{status_label}]: ",
                                     height - 2, 2, width - 30)
                if title:
                    new_id = add_task(title, status=COLUMNS[col_idx][0])
                    # Posiciona cursor na nova task
                    tasks_after = get_tasks_by_status(COLUMNS[col_idx][0])
                    ids = [t["id"] for t in tasks_after]
                    if new_id in ids:
                        row_idx[col_idx] = ids.index(new_id)
                    message = f"#{new_id} \"{trunc(title, 40)}\" adicionada."
                else:
                    message = "Cancelado."
                    msg_error = True
