"""
taskflow/board.py
Renderiza o board kanban no terminal com cores ANSI.
"""

import re
from datetime import date, datetime
from tasks import get_tasks_by_status, get_agent_tasks_by_status, has_origin, get_project

RESET   = "\033[0m"
BOLD    = "\033[1m"
GRAY    = "\033[90m"
DIM     = "\033[2m"

BG_BLUE    = "\033[44m"
BG_YELLOW  = "\033[103m"
BG_GREEN   = "\033[102m"

WHITE   = "\033[97m"
BLACK   = "\033[30m"
CYAN    = "\033[96m"
YELLOW  = "\033[93m"
GREEN   = "\033[92m"
RED     = "\033[91m"
MAGENTA = "\033[95m"

COL_WIDTH = 30
INNER     = COL_WIDTH + 2

MINI_COL_WIDTH = 22
MINI_INNER     = MINI_COL_WIDTH + 2

ANSI_RE = re.compile(r'\033\[[0-9;]*m')

PRIORITY_COLOR  = {"alta": RED, "media": YELLOW, "baixa": GRAY}
PRIORITY_SYMBOL = {"alta": "▲", "media": "●", "baixa": "▽"}


def strip_ansi(s: str) -> str:
    return ANSI_RE.sub('', s)


def pad(text: str, width: int) -> str:
    vlen = len(strip_ansi(text))
    if vlen > width:
        return strip_ansi(text)[:width - 1] + "…"
    return text + " " * (width - vlen)


def _due_display_short(due_date_str: str) -> tuple[str, str]:
    if not due_date_str or not due_date_str.strip():
        return "", ""
    try:
        due  = datetime.strptime(due_date_str.strip(), "%Y-%m-%d").date()
        diff = (due - date.today()).days
        if diff < 0:
            return f"{due_date_str} !!", RED
        elif diff <= 2:
            return f"{due_date_str}", YELLOW
        else:
            return f"{due_date_str}", GRAY
    except ValueError:
        return due_date_str, GRAY


def _project_name(task) -> str:
    pid = task["project_id"] if "project_id" in task.keys() else None
    if not pid:
        return ""
    proj = get_project(pid)
    return proj["name"] if proj else ""


# ── Board normal ──────────────────────────────────────────────────────────────

def render_board(tag_filter: str = ""):
    backlog = get_tasks_by_status("backlog", tag_filter)
    todo    = get_tasks_by_status("todo",    tag_filter)
    done    = get_tasks_by_status("done",    tag_filter)

    total    = len(backlog) + len(todo) + len(done)
    max_rows = max(len(backlog), len(todo), len(done), 1)

    seg      = "─" * INNER
    line_top = f"┌{seg}┬{seg}┬{seg}┐"
    line_sep = f"├{seg}┼{seg}┼{seg}┤"
    line_bot = f"└{seg}┴{seg}┴{seg}┘"

    def col_header(label, bg, fg, count):
        return f"│{bg}{fg}{BOLD}{pad(f' {label} ({count})', INNER)}{RESET}"

    # linha 1 — título
    def title_line(tasks, index, color):
        if index < len(tasks):
            t     = tasks[index]
            arrow = "↗ " if has_origin(t["id"]) else ""
            text  = f" {arrow}#{t['id']} {t['title']}"
            return f"│{color}{pad(text, INNER)}{RESET}"
        return f"│{' ' * INNER}"

    # linha 2 — projeto · prioridade
    def meta_line(tasks, index):
        if index < len(tasks):
            t        = tasks[index]
            proj     = _project_name(t)
            priority = (t["priority"] or "").strip()

            parts_plain   = []
            parts_colored = []

            if proj:
                parts_plain.append(proj)
                parts_colored.append(f"{MAGENTA}{proj}{RESET}")

            if priority:
                pc  = PRIORITY_COLOR.get(priority, GRAY)
                sym = PRIORITY_SYMBOL.get(priority, "")
                parts_plain.append(f"{sym} {priority}")
                parts_colored.append(f"{pc}{sym} {priority}{RESET}")

            if not parts_plain:
                return f"│{' ' * INNER}"

            sep_plain   = "  ·  "
            sep_colored = f"  {GRAY}·{RESET}  "
            plain       = "  " + sep_plain.join(parts_plain)
            colored     = "  " + sep_colored.join(parts_colored)
            vlen        = len(plain)

            if vlen > INNER:
                return f"│{GRAY}{plain[:INNER - 1]}…{RESET}"
            return f"│{colored}{' ' * (INNER - vlen)}"
        return f"│{' ' * INNER}"

    # linha 3 — criado · vence
    def dates_line(tasks, index):
        if index < len(tasks):
            t       = tasks[index]
            created = (t["created_at"] or "")[:10]
            due_str = (t["due_date"] or "").strip()

            plain   = f"  C {created}"
            colored = f"  {GRAY}C {created}{RESET}"

            if due_str:
                due_text, due_color = _due_display_short(due_str)
                plain   += f"  ·  V {due_text}"
                colored += f"  {GRAY}·{RESET}  {due_color}V {due_text}{RESET}"

            vlen = len(plain)
            if vlen > INNER:
                return f"│{GRAY}{plain[:INNER - 1]}…{RESET}"
            return f"│{colored}{' ' * (INNER - vlen)}"
        return f"│{' ' * INNER}"

    filter_label = f"  {GRAY}filtro: [{tag_filter}]{RESET}" if tag_filter else ""
    print()
    print(f"  {BOLD}taskflow{RESET}{GRAY} — {total} tarefa(s){RESET}{filter_label}")
    print()
    print(f"  {line_top}")
    print(
        f"  {col_header('BACKLOG', BG_BLUE,   WHITE, len(backlog))}"
        f"{col_header('TO DO',   BG_YELLOW, BLACK, len(todo))}"
        f"{col_header('DONE',    BG_GREEN,  BLACK, len(done))}│"
    )
    print(f"  {line_sep}")

    dash = "╌" * INNER

    def sep_line(tasks, index):
        """Linha separadora leve entre tasks. Só desenha se ainda há tasks na coluna."""
        if index + 1 < len(tasks):
            return f"│{GRAY}{dash}{RESET}"
        return f"│{' ' * INNER}"

    for i in range(max_rows):
        print(f"  {title_line(backlog, i, CYAN)}{title_line(todo, i, YELLOW)}{title_line(done, i, GREEN)}│")
        print(f"  {meta_line(backlog, i)}{meta_line(todo, i)}{meta_line(done, i)}│")
        print(f"  {dates_line(backlog, i)}{dates_line(todo, i)}{dates_line(done, i)}│")
        if i < max_rows - 1:
            print(f"  {sep_line(backlog, i)}{sep_line(todo, i)}{sep_line(done, i)}│")

    print(f"  {line_bot}")
    print()


# ── Board minimal ─────────────────────────────────────────────────────────────

def render_mini(tag_filter: str = ""):
    backlog = get_tasks_by_status("backlog", tag_filter)
    todo    = get_tasks_by_status("todo",    tag_filter)
    done    = get_tasks_by_status("done",    tag_filter)

    total    = len(backlog) + len(todo) + len(done)
    max_rows = max(len(backlog), len(todo), len(done), 1)

    inner    = MINI_INNER
    seg      = "─" * inner
    line_top = f"┌{seg}┬{seg}┬{seg}┐"
    line_sep = f"├{seg}┼{seg}┼{seg}┤"
    line_bot = f"└{seg}┴{seg}┴{seg}┘"

    def col_header(label, bg, fg, count):
        return f"│{bg}{fg}{BOLD}{pad(f' {label} ({count})', inner)}{RESET}"

    def task_line(tasks, index, color):
        if index < len(tasks):
            t     = tasks[index]
            arrow = "↗" if has_origin(t["id"]) else " "
            text  = f" {arrow} #{t['id']} {t['title']}"
            return f"│{color}{pad(text, inner)}{RESET}"
        return f"│{' ' * inner}"

    filter_label = f"  {GRAY}[{tag_filter}]{RESET}" if tag_filter else ""
    print()
    print(f"  {BOLD}taskflow{RESET}{GRAY} — {total} tarefa(s){RESET}{filter_label}")
    print()
    print(f"  {line_top}")
    print(
        f"  {col_header('BACKLOG', BG_BLUE,   WHITE, len(backlog))}"
        f"{col_header('TO DO',   BG_YELLOW, BLACK, len(todo))}"
        f"{col_header('DONE',    BG_GREEN,  BLACK, len(done))}│"
    )
    print(f"  {line_sep}")

    for i in range(max_rows):
        print(f"  {task_line(backlog, i, CYAN)}{task_line(todo, i, YELLOW)}{task_line(done, i, GREEN)}│")

    print(f"  {line_bot}")
    print()


# ── Agent board ───────────────────────────────────────────────────────────────

def render_agent_board():
    pending   = get_agent_tasks_by_status("pending")
    running   = get_agent_tasks_by_status("running")
    done      = get_agent_tasks_by_status("done")
    failed    = get_agent_tasks_by_status("failed")
    cancelled = get_agent_tasks_by_status("cancelled")

    total    = len(pending) + len(running) + len(done) + len(failed) + len(cancelled)
    max_rows = max(len(pending), len(running), len(done), len(failed), len(cancelled), 1)

    ACOL = 20
    AIN  = ACOL + 2

    BG_RED    = "\033[41m"
    BG_GRAY   = "\033[100m"

    seg      = "─" * AIN
    line_top = f"┌{seg}┬{seg}┬{seg}┬{seg}┬{seg}┐"
    line_sep = f"├{seg}┼{seg}┼{seg}┼{seg}┼{seg}┤"
    line_bot = f"└{seg}┴{seg}┴{seg}┴{seg}┴{seg}┘"

    STATUS_ICON = {
        "pending":   "○",
        "running":   "◉",
        "done":      "✓",
        "failed":    "✗",
        "cancelled": "⊘",
    }

    def col_header(label, bg, fg, count):
        return f"│{bg}{fg}{BOLD}{pad(f' {label} ({count})', AIN)}{RESET}"

    def task_line(tasks, index, color):
        if index < len(tasks):
            t    = tasks[index]
            icon = STATUS_ICON.get(t["action_status"] or "pending", "○")
            text = f" {icon} #{t['id']} {t['title']}"
            return f"│{color}{pad(text, AIN)}{RESET}"
        return f"│{' ' * AIN}"

    def sched_line(tasks, index):
        if index < len(tasks):
            t     = tasks[index]
            sched = (t["scheduled_at"] or "")[:16]
            if sched:
                plain   = f"  ⏱ {sched}"
                colored = f"  {GRAY}⏱ {sched}{RESET}"
                vlen    = len(plain)
                return f"│{colored}{' ' * (AIN - vlen)}"
        return f"│{' ' * AIN}"

    print()
    print(f"  {BOLD}taskflow agent{RESET}{GRAY} — {total} tarefa(s){RESET}")
    print()
    print(f"  {line_top}")
    print(
        f"  {col_header('PENDING',   BG_BLUE,   WHITE, len(pending))}"
        f"{col_header('RUNNING',   BG_YELLOW, BLACK, len(running))}"
        f"{col_header('DONE',      BG_GREEN,  BLACK, len(done))}"
        f"{col_header('FAILED',    BG_RED,    WHITE, len(failed))}"
        f"{col_header('CANCELLED', BG_GRAY,   WHITE, len(cancelled))}│"
    )
    print(f"  {line_sep}")

    for i in range(max_rows):
        print(
            f"  {task_line(pending, i, CYAN)}"
            f"{task_line(running, i, YELLOW)}"
            f"{task_line(done, i, GREEN)}"
            f"{task_line(failed, i, RED)}"
            f"{task_line(cancelled, i, GRAY)}│"
        )
        print(
            f"  {sched_line(pending, i)}"
            f"{sched_line(running, i)}"
            f"{sched_line(done, i)}"
            f"{sched_line(failed, i)}"
            f"{sched_line(cancelled, i)}│"
        )

    print(f"  {line_bot}")
    print()


if __name__ == "__main__":
    from db import init_db
    init_db()
    render_board()
