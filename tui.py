#!/usr/bin/env python3
"""
taskflow/tui.py
Menu interativo completo do taskflow (curses — stdlib).

Lançar com: taskflow tui
"""

import curses
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from tasks import (
    get_tasks_by_status, get_agent_tasks, get_all_projects, get_project,
    get_tasks_by_project, get_hidden_tasks, search_tasks,
    move_task, delete_task, add_task, update_action_status,
    auto_promote_due, auto_hide_stale,
)
from db import init_db


# ── Constantes ────────────────────────────────────────────────────────────────

PRIO_SYM = {"alta": "▲", "media": "●", "baixa": "▽"}

STATUS_ICON = {
    "pending":   "○",
    "running":   "◉",
    "done":      "✓",
    "failed":    "✗",
    "cancelled": "✗",
}

MENU_ITEMS = [
    ("k", "Tasks pessoais",  "Kanban: BACKLOG / TO DO / DONE"),
    ("a", "Agent tasks",     "Tasks agendadas e executadas pelo Claude"),
    ("p", "Projetos",        "Listar e explorar projetos ativos"),
    ("f", "Filtrar por tag", "Kanban filtrado por tag"),
    ("s", "Buscar tasks",    "Pesquisar por título ou descrição"),
    ("h", "Tasks ocultas",   "Tasks com hidden = 1"),
]

KANBAN_COLS = [("backlog", "BACKLOG"), ("todo", "TO DO"), ("done", "DONE")]


# ── Helpers ───────────────────────────────────────────────────────────────────

def trunc(s: str, n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[: n - 1] + "…"


def init_colors():
    try:
        curses.use_default_colors()
        bg = -1
    except Exception:
        bg = curses.COLOR_BLACK
    # 1=cyan  2=yellow  3=green  4=seleção  5=branco  6=vermelho  7=cinza  8=magenta
    curses.init_pair(1, curses.COLOR_CYAN,    bg)
    curses.init_pair(2, curses.COLOR_YELLOW,  bg)
    curses.init_pair(3, curses.COLOR_GREEN,   bg)
    curses.init_pair(4, curses.COLOR_BLACK,   curses.COLOR_CYAN)
    curses.init_pair(5, curses.COLOR_WHITE,   bg)
    curses.init_pair(6, curses.COLOR_RED,     bg)
    curses.init_pair(7, curses.COLOR_WHITE,   bg)
    curses.init_pair(8, curses.COLOR_MAGENTA, bg)


def hint_bar(stdscr, text: str):
    h, w = stdscr.getmaxyx()
    line = trunc(f"  {text}", w - 1).ljust(w - 1)
    try:
        stdscr.addstr(h - 1, 0, line, curses.A_REVERSE)
    except curses.error:
        pass


def status_bar(stdscr, text: str, error: bool = False):
    h, w = stdscr.getmaxyx()
    pair = curses.color_pair(6) if error else curses.color_pair(3)
    line = trunc(f"  {text}", w - 1).ljust(w - 1)
    try:
        stdscr.addstr(h - 2, 0, line, pair | curses.A_BOLD)
    except curses.error:
        pass


def prompt_input(stdscr, prompt: str, y: int, x: int, max_len: int = 60) -> str:
    """Lê uma string do usuário na linha y, posição x."""
    h, w = stdscr.getmaxyx()
    max_len = min(max_len, w - x - len(prompt) - 2)

    curses.echo()
    curses.curs_set(1)
    stdscr.move(y, 0)
    stdscr.clrtoeol()
    try:
        stdscr.addstr(y, x, prompt, curses.color_pair(2) | curses.A_BOLD)
        stdscr.addstr(y, x + len(prompt), "─" * max_len, curses.color_pair(7))
    except curses.error:
        pass
    stdscr.move(y, x + len(prompt))
    stdscr.refresh()

    try:
        raw = stdscr.getstr(y, x + len(prompt), max_len)
        val = raw.decode("utf-8", errors="replace").strip()
    except Exception:
        val = ""
    finally:
        curses.noecho()
        curses.curs_set(0)

    return val


# ── Tela: Menu principal ──────────────────────────────────────────────────────

def screen_menu(stdscr) -> str | None:
    """
    Mostra o menu principal.
    Retorna a letra da opção escolhida, ou None para sair.
    """
    cursor = 0

    while True:
        personal = sum(len(get_tasks_by_status(s)) for s, _ in KANBAN_COLS)
        agents   = get_agent_tasks()
        pending  = sum(1 for t in agents if (t["action_status"] or "pending") == "pending")
        hidden   = len(get_hidden_tasks())

        stdscr.erase()
        h, w = stdscr.getmaxyx()

        # Título
        try:
            stdscr.addstr(1, 3, "taskflow", curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass

        # Stats rápidos
        stats = (
            f"  {personal} task(s) pessoal(is)   "
            f"{pending} agent(s) pendente(s)   "
            f"{hidden} oculta(s)"
        )
        try:
            stdscr.addstr(2, 3, trunc(stats, w - 6), curses.color_pair(7))
        except curses.error:
            pass
        try:
            stdscr.addstr(3, 3, "─" * min(54, w - 6), curses.color_pair(7))
        except curses.error:
            pass

        # Itens do menu
        for i, (key, label, desc) in enumerate(MENU_ITEMS):
            y = 5 + i * 2
            if y >= h - 3:
                break
            is_sel = (i == cursor)
            line   = trunc(f"  [{key}]  {label:<22}  {desc}", w - 6)
            line   = line.ljust(min(62, w - 6))
            attr   = curses.color_pair(4) | curses.A_BOLD if is_sel else curses.A_NORMAL
            try:
                stdscr.addstr(y, 3, line, attr)
            except curses.error:
                pass

        hint_bar(stdscr, "↑↓ navegar   Enter / letra selecionar   [q] sair")
        stdscr.refresh()

        key = stdscr.getch()

        if key in (ord("q"), 27):
            return None
        elif key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(len(MENU_ITEMS) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            return MENU_ITEMS[cursor][0]
        else:
            ch = chr(key) if 32 <= key <= 126 else ""
            for item in MENU_ITEMS:
                if item[0] == ch:
                    return ch


# ── Tela: Kanban pessoal ──────────────────────────────────────────────────────

def screen_kanban(stdscr, tag_filter: str = "", init_msg: str = ""):
    col_idx = 0
    row_idx = [0, 0, 0]
    msg     = init_msg
    msg_err = False

    while True:
        cols = [get_tasks_by_status(s, tag_filter) for s, _ in KANBAN_COLS]
        for i, tasks in enumerate(cols):
            row_idx[i] = min(row_idx[i], max(0, len(tasks) - 1))

        stdscr.erase()
        h, w = stdscr.getmaxyx()
        col_w = max(22, (w - 3) // 3)

        # Título se houver filtro
        if tag_filter:
            try:
                stdscr.addstr(0, 1, trunc(f" filtro: [{tag_filter}] ", w - 2),
                              curses.color_pair(2) | curses.A_BOLD)
            except curses.error:
                pass
            row_start = 1
        else:
            row_start = 0

        for ci, (status, label) in enumerate(KANBAN_COLS):
            x     = ci * (col_w + 1)
            tasks = cols[ci]

            header = f" {label} ({len(tasks)}) ".center(col_w)[:col_w]
            try:
                stdscr.addstr(row_start, x, header,
                              curses.color_pair(ci + 1) | curses.A_BOLD)
            except curses.error:
                pass
            try:
                stdscr.addstr(row_start + 1, x, "─" * col_w, curses.color_pair(7))
            except curses.error:
                pass

            for ti, task in enumerate(tasks):
                y = row_start + 2 + ti
                if y >= h - 3:
                    break
                is_sel   = (ci == col_idx and ti == row_idx[ci])
                prio_sym = PRIO_SYM.get(task["priority"] or "", " ")
                line     = trunc(f" {prio_sym} #{task['id']} {task['title']}", col_w).ljust(col_w)
                attr     = curses.color_pair(4) | curses.A_BOLD if is_sel else curses.A_NORMAL
                try:
                    stdscr.addstr(y, x, line, attr)
                except curses.error:
                    pass

        if msg:
            status_bar(stdscr, msg, msg_err)
            msg = ""; msg_err = False

        hint_bar(stdscr,
                 "←→ col   ↑↓ task   [t]odo [d]one [b]ack   "
                 "[a]dd   [x] remover   [ESC] menu")
        stdscr.refresh()

        key = stdscr.getch()
        if key == 27:
            return
        elif key == curses.KEY_LEFT:
            col_idx = max(0, col_idx - 1)
        elif key in (curses.KEY_RIGHT, 9):  # 9=Tab
            col_idx = min(2, col_idx + 1)
        elif key == curses.KEY_UP:
            row_idx[col_idx] = max(0, row_idx[col_idx] - 1)
        elif key == curses.KEY_DOWN:
            tasks = cols[col_idx]
            if tasks:
                row_idx[col_idx] = min(len(tasks) - 1, row_idx[col_idx] + 1)
        else:
            tasks = cols[col_idx]
            task  = tasks[row_idx[col_idx]] if tasks else None

            if key == ord("t") and task:
                move_task(task["id"], "todo")
                col_idx = 1
                msg = f"#{task['id']} → TO DO"

            elif key == ord("d") and task:
                move_task(task["id"], "done")
                col_idx = 2
                msg = f"#{task['id']} → DONE"

            elif key == ord("b") and task:
                move_task(task["id"], "backlog")
                col_idx = 0
                msg = f"#{task['id']} → BACKLOG"

            elif key in (curses.KEY_DC, ord("x")) and task:
                ans = prompt_input(
                    stdscr,
                    f"Remover #{task['id']} \"{trunc(task['title'], 28)}\"? (s/n): ",
                    h - 2, 2, 3,
                )
                if ans.lower() == "s":
                    delete_task(task["id"])
                    row_idx[col_idx] = max(0, row_idx[col_idx] - 1)
                    msg = f"#{task['id']} removida."
                else:
                    msg = "Cancelado."

            elif key == ord("a"):
                label = KANBAN_COLS[col_idx][1]
                title = prompt_input(
                    stdscr, f"Novo título [{label}]: ", h - 2, 2, w - 30
                )
                if title:
                    new_id = add_task(title, status=KANBAN_COLS[col_idx][0])
                    msg = f"#{new_id} \"{trunc(title, 40)}\" adicionada."
                else:
                    msg = "Cancelado."; msg_err = True


# ── Tela: Agent tasks ─────────────────────────────────────────────────────────

STATUS_PAIR = {
    "pending":   1,
    "running":   2,
    "done":      3,
    "failed":    6,
    "cancelled": 7,
}


def screen_agent(stdscr):
    cursor = 0
    msg    = ""
    msg_err = False

    while True:
        tasks  = get_agent_tasks()
        cursor = min(cursor, max(0, len(tasks) - 1))

        stdscr.erase()
        h, w = stdscr.getmaxyx()

        try:
            stdscr.addstr(0, 3, " AGENT TASKS ", curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        try:
            stdscr.addstr(1, 3, "─" * min(60, w - 6), curses.color_pair(7))
        except curses.error:
            pass

        if not tasks:
            try:
                stdscr.addstr(3, 5, "Nenhuma agent task.", curses.color_pair(7))
            except curses.error:
                pass

        for ti, t in enumerate(tasks):
            y = 2 + ti * 3
            if y >= h - 4:
                break

            st     = t["action_status"] or "pending"
            icon   = STATUS_ICON.get(st, "○")
            pair   = STATUS_PAIR.get(st, 7)
            sched  = (t["scheduled_at"] or "")[:16]
            is_sel = (ti == cursor)

            title_line = trunc(
                f"  {icon}  #{t['id']} {t['title']}   {sched}", w - 4
            ).ljust(min(w - 4, 72))

            attr = curses.color_pair(4) | curses.A_BOLD if is_sel else (
                curses.color_pair(pair) | curses.A_BOLD
            )
            try:
                stdscr.addstr(y, 3, title_line, attr)
            except curses.error:
                pass

            # Resultado
            if t["action_result"]:
                result = trunc(t["action_result"].replace("\n", " "), w - 10)
                try:
                    stdscr.addstr(y + 1, 7, result, curses.color_pair(7))
                except curses.error:
                    pass
            # Action (preview)
            elif t["action"]:
                action_prev = trunc(t["action"].replace("\n", " "), w - 10)
                try:
                    stdscr.addstr(y + 1, 7, action_prev, curses.color_pair(7))
                except curses.error:
                    pass

        if msg:
            status_bar(stdscr, msg, msg_err)
            msg = ""; msg_err = False

        hint_bar(stdscr, "↑↓ navegar   [c] cancelar pendente   [ESC] menu")
        stdscr.refresh()

        key = stdscr.getch()
        if key == 27:
            return
        elif key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            if tasks:
                cursor = min(len(tasks) - 1, cursor + 1)
        elif key == ord("c") and tasks:
            t  = tasks[cursor]
            st = t["action_status"] or "pending"
            if st == "pending":
                update_action_status(t["id"], "cancelled", "Cancelado manualmente.")
                msg = f"#{t['id']} cancelada."
            else:
                msg = f"#{t['id']} não está pendente (status: {st})."
                msg_err = True


# ── Tela: Projetos ────────────────────────────────────────────────────────────

def screen_projects(stdscr):
    cursor = 0

    while True:
        projects = get_all_projects(include_archived=False)
        cursor   = min(cursor, max(0, len(projects) - 1))

        stdscr.erase()
        h, w = stdscr.getmaxyx()

        try:
            stdscr.addstr(0, 3, " PROJETOS ", curses.color_pair(8) | curses.A_BOLD)
        except curses.error:
            pass
        try:
            stdscr.addstr(1, 3, "─" * min(50, w - 6), curses.color_pair(7))
        except curses.error:
            pass

        if not projects:
            try:
                stdscr.addstr(3, 5, "Nenhum projeto ativo.", curses.color_pair(7))
            except curses.error:
                pass

        for pi, p in enumerate(projects):
            y      = 2 + pi * 2
            if y >= h - 3:
                break
            is_sel = (pi == cursor)
            star   = "★ " if p["starred"] else "  "
            tasks  = get_tasks_by_project(p["id"])
            n      = len(tasks)
            desc   = f"  —  {p['description']}" if p["description"] else ""
            line   = trunc(f"  {star}#{p['id']} {p['name']}  ({n} task(s)){desc}", w - 6)
            line   = line.ljust(min(w - 6, 70))
            attr   = curses.color_pair(4) | curses.A_BOLD if is_sel else (
                curses.color_pair(8) | curses.A_BOLD
            )
            try:
                stdscr.addstr(y, 3, line, attr)
            except curses.error:
                pass

        hint_bar(stdscr, "↑↓ navegar   [Enter] detalhes   [ESC] menu")
        stdscr.refresh()

        key = stdscr.getch()
        if key == 27:
            return
        elif key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            if projects:
                cursor = min(len(projects) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13) and projects:
            screen_project_detail(stdscr, projects[cursor]["id"])


def screen_project_detail(stdscr, project_id: int):
    while True:
        proj  = get_project(project_id)
        tasks = get_tasks_by_project(project_id)
        if not proj:
            return

        stdscr.erase()
        h, w = stdscr.getmaxyx()

        star = "★ " if proj["starred"] else ""
        try:
            stdscr.addstr(0, 3,
                          trunc(f" {star}#{proj['id']} {proj['name']} ", w - 4),
                          curses.color_pair(8) | curses.A_BOLD)
        except curses.error:
            pass

        y_off = 1
        if proj["description"]:
            try:
                stdscr.addstr(1, 5, trunc(proj["description"], w - 8), curses.color_pair(7))
            except curses.error:
                pass
            y_off = 2

        try:
            stdscr.addstr(y_off, 3, "─" * min(50, w - 6), curses.color_pair(7))
        except curses.error:
            pass

        STATUS_PAIR_MAP = {"backlog": 1, "todo": 2, "done": 3}

        if not tasks:
            try:
                stdscr.addstr(y_off + 1, 5, "Nenhuma task vinculada.", curses.color_pair(7))
            except curses.error:
                pass
        else:
            for ti, t in enumerate(tasks):
                y = y_off + 1 + ti
                if y >= h - 3:
                    break
                pair = STATUS_PAIR_MAP.get(t["status"], 7)
                line = trunc(f"  [{t['status']:<7}]  #{t['id']} {t['title']}", w - 6)
                try:
                    stdscr.addstr(y, 3, line, curses.color_pair(pair))
                except curses.error:
                    pass

        hint_bar(stdscr, "[ESC] voltar")
        stdscr.refresh()

        key = stdscr.getch()
        if key in (27, ord("q")):
            return


# ── Tela: Filtrar por tag ─────────────────────────────────────────────────────

def screen_filter(stdscr):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    try:
        stdscr.addstr(2, 3, " FILTRAR POR TAG ", curses.color_pair(1) | curses.A_BOLD)
    except curses.error:
        pass
    try:
        stdscr.addstr(3, 3, "─" * min(40, w - 6), curses.color_pair(7))
    except curses.error:
        pass
    hint_bar(stdscr, "Digite a tag e pressione Enter   [ESC] cancela")
    stdscr.refresh()

    tag = prompt_input(stdscr, "  Tag: ", h - 2, 2, 30)
    if tag:
        screen_kanban(stdscr, tag_filter=tag)


# ── Tela: Busca ───────────────────────────────────────────────────────────────

def screen_search(stdscr):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    try:
        stdscr.addstr(2, 3, " BUSCAR TASKS ", curses.color_pair(1) | curses.A_BOLD)
    except curses.error:
        pass
    try:
        stdscr.addstr(3, 3, "─" * min(40, w - 6), curses.color_pair(7))
    except curses.error:
        pass
    hint_bar(stdscr, "Digite o termo e pressione Enter   [ESC] cancela")
    stdscr.refresh()

    query = prompt_input(stdscr, "  Buscar: ", h - 2, 2, 50)
    if not query:
        return

    cursor = 0
    while True:
        results = search_tasks(query)
        cursor  = min(cursor, max(0, len(results) - 1))

        stdscr.erase()
        h, w = stdscr.getmaxyx()

        header = trunc(f" RESULTADOS: \"{query}\" ({len(results)}) ", w - 4)
        try:
            stdscr.addstr(0, 3, header, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        try:
            stdscr.addstr(1, 3, "─" * min(60, w - 6), curses.color_pair(7))
        except curses.error:
            pass

        if not results:
            try:
                stdscr.addstr(3, 5, "Nenhuma task encontrada.", curses.color_pair(7))
            except curses.error:
                pass

        STATUS_PAIR_MAP = {"backlog": 1, "todo": 2, "done": 3}

        for ri, t in enumerate(results):
            y = 2 + ri
            if y >= h - 3:
                break
            is_sel = (ri == cursor)
            pair   = STATUS_PAIR_MAP.get(t["status"], 7)
            line   = trunc(f"  [{t['status']:<7}]  #{t['id']} {t['title']}", w - 6)
            line   = line.ljust(min(w - 6, 70))
            attr   = curses.color_pair(4) | curses.A_BOLD if is_sel else curses.color_pair(pair)
            try:
                stdscr.addstr(y, 3, line, attr)
            except curses.error:
                pass

        hint_bar(stdscr, "↑↓ navegar   [ESC] menu")
        stdscr.refresh()

        key = stdscr.getch()
        if key == 27:
            return
        elif key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            if results:
                cursor = min(len(results) - 1, cursor + 1)


# ── Tela: Tasks ocultas ───────────────────────────────────────────────────────

def screen_hidden(stdscr):
    cursor = 0

    while True:
        tasks  = get_hidden_tasks()
        cursor = min(cursor, max(0, len(tasks) - 1))

        stdscr.erase()
        h, w = stdscr.getmaxyx()

        try:
            stdscr.addstr(0, 3, " TASKS OCULTAS ", curses.color_pair(6) | curses.A_BOLD)
        except curses.error:
            pass
        try:
            stdscr.addstr(1, 3, "─" * min(50, w - 6), curses.color_pair(7))
        except curses.error:
            pass

        if not tasks:
            try:
                stdscr.addstr(3, 5, "Nenhuma task oculta.", curses.color_pair(7))
            except curses.error:
                pass

        for ti, t in enumerate(tasks):
            y = 2 + ti
            if y >= h - 3:
                break
            is_sel = (ti == cursor)
            date   = (t["updated_at"] or "")[:10]
            line   = trunc(f"  #{t['id']} {t['title']}   oculta desde {date}", w - 6)
            line   = line.ljust(min(w - 6, 70))
            attr   = curses.color_pair(4) | curses.A_BOLD if is_sel else curses.color_pair(7)
            try:
                stdscr.addstr(y, 3, line, attr)
            except curses.error:
                pass

        hint_bar(stdscr, "↑↓ navegar   [ESC] menu")
        stdscr.refresh()

        key = stdscr.getch()
        if key == 27:
            return
        elif key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            if tasks:
                cursor = min(len(tasks) - 1, cursor + 1)


# ── Entry point ───────────────────────────────────────────────────────────────

SCREEN_MAP = {
    "k": screen_kanban,
    "a": screen_agent,
    "p": screen_projects,
    "f": screen_filter,
    "s": screen_search,
    "h": screen_hidden,
}


def run_tui(stdscr):
    curses.curs_set(0)
    init_colors()
    init_db()
    auto_promote_due()
    auto_hide_stale(days=14)

    while True:
        choice = screen_menu(stdscr)
        if choice is None:
            return
        fn = SCREEN_MAP.get(choice)
        if fn:
            fn(stdscr)
