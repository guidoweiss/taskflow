"""
taskflow/board.py
Renderiza o board kanban no terminal com cores ANSI.
"""

import re
from datetime import date, datetime
from tasks import get_tasks_by_status

RESET   = "\033[0m"
BOLD    = "\033[1m"
GRAY    = "\033[90m"

BG_BLUE    = "\033[44m"
BG_YELLOW  = "\033[103m"
BG_GREEN   = "\033[102m"

WHITE   = "\033[97m"
BLACK   = "\033[30m"
CYAN    = "\033[96m"
YELLOW  = "\033[93m"
GREEN   = "\033[92m"
RED     = "\033[91m"

COL_WIDTH = 30
INNER     = COL_WIDTH + 2

ANSI_RE = re.compile(r'\033\[[0-9;]*m')

PRIORITY_COLOR = {"alta": RED, "media": YELLOW, "baixa": GRAY}


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
            t    = tasks[index]
            text = f" #{t['id']} {t['title']}"
            return f"│{color}{pad(text, INNER)}{RESET}"
        return f"│{' ' * INNER}"

    # linha 2 — tag · prioridade
    def tag_priority_line(tasks, index):
        if index < len(tasks):
            t        = tasks[index]
            raw      = (t["tags"] or "").strip()
            tag      = raw.split(",")[0].strip() if raw else ""
            priority = (t["priority"] or "").strip()

            parts_plain   = []
            parts_colored = []

            if tag:
                parts_plain.append(f"[{tag}]")
                parts_colored.append(f"{GRAY}[{tag}]{RESET}")

            if priority:
                pc = PRIORITY_COLOR.get(priority, GRAY)
                parts_plain.append(priority)
                parts_colored.append(f"{pc}{priority}{RESET}")

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

    # linha 3 — criado · vence (só mostra vence se existir)
    def dates_line(tasks, index):
        if index < len(tasks):
            t       = tasks[index]
            created = (t["created_at"] or "")[:10]  # só a data, sem hora
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

    for i in range(max_rows):
        print(f"  {title_line(backlog, i, CYAN)}{title_line(todo, i, YELLOW)}{title_line(done, i, GREEN)}│")
        print(f"  {tag_priority_line(backlog, i)}{tag_priority_line(todo, i)}{tag_priority_line(done, i)}│")
        print(f"  {dates_line(backlog, i)}{dates_line(todo, i)}{dates_line(done, i)}│")

    print(f"  {line_bot}")
    print()


if __name__ == "__main__":
    from db import init_db
    init_db()
    render_board()
