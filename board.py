"""
taskflow/board.py
Renderiza o board kanban no terminal com cores ANSI.
"""

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

COL_WIDTH  = 30
CELL_WIDTH = COL_WIDTH + 4

PRIORITY_BADGE = {
    "alta":  f"\033[91m!\033[0m",   # vermelho
    "media": f"\033[93m~\033[0m",   # amarelo
    "baixa": "",
    "":      "",
}


def pad(text: str, width: int) -> str:
    if len(text) > width:
        return text[:width - 1] + "…"
    return text.ljust(width)


def _due_label(due_date_str: str) -> tuple[str, str]:
    """Retorna (texto, cor_ansi) para exibir o prazo."""
    if not due_date_str or not due_date_str.strip():
        return "", ""
    try:
        due = datetime.strptime(due_date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return due_date_str, GRAY
    today = date.today()
    diff = (due - today).days
    if diff < 0:
        return f"prazo: {due_date_str} !!", RED
    elif diff <= 2:
        return f"prazo: {due_date_str}", YELLOW
    else:
        return f"prazo: {due_date_str}", GRAY


def render_board(tag_filter: str = ""):
    backlog = get_tasks_by_status("backlog", tag_filter)
    todo    = get_tasks_by_status("todo",    tag_filter)
    done    = get_tasks_by_status("done",    tag_filter)

    total    = len(backlog) + len(todo) + len(done)
    max_rows = max(len(backlog), len(todo), len(done), 1)

    seg      = "─" * (COL_WIDTH + 2)
    line_top = f"┌{seg}┬{seg}┬{seg}┐"
    line_sep = f"├{seg}┼{seg}┼{seg}┤"
    line_bot = f"└{seg}┴{seg}┴{seg}┘"

    def col_header(label, bg, fg, count):
        text   = f" {label} ({count})"
        padded = pad(text, COL_WIDTH + 2)
        return f"│{bg}{fg}{BOLD}{padded}{RESET}"

    inner_width = COL_WIDTH + 2

    def task_title_line(tasks, index, color):
        if index < len(tasks):
            t     = tasks[index]
            badge = PRIORITY_BADGE.get(t["priority"] or "", "")
            badge_plain = f"[{t['priority']}] " if t["priority"] in ("alta", "media") else ""
            prefix = f" {badge}{badge_plain}" if badge else " "
            text  = f"{prefix}#{t['id']} {t['title']}"
            return f"│{color}{pad(text, inner_width)}{RESET}"
        return f"│{' ' * inner_width}"

    def task_tags_line(tasks, index):
        if index < len(tasks):
            t   = tasks[index]
            raw = (t["tags"] or "").strip()
            parts = []
            if raw:
                parts += [f"[{tag.strip()}]" for tag in raw.split(",") if tag.strip()]
            due_text, due_color = _due_label(t["due_date"] or "")
            if due_text:
                parts.append(f"[{due_text}]")
                # colorir o prazo separadamente — simplificado: só color no texto todo
                text = f"  {' '.join(parts)}"
                # apply due color to last bracket
                tags_part = " ".join(parts[:-1])
                due_part  = parts[-1]
                combined  = f"  {GRAY}{tags_part}{RESET} {due_color}{due_part}{RESET}" if tags_part else f"  {due_color}{due_part}{RESET}"
                return f"│{pad(combined, inner_width + len(GRAY) + len(RESET) + len(due_color) + len(RESET))}{RESET}"
            text = f"  {' '.join(parts)}"
            return f"│{GRAY}{pad(text, inner_width)}{RESET}"
        return f"│{' ' * inner_width}"

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
        b = task_title_line(backlog, i, CYAN)
        t = task_title_line(todo,    i, YELLOW)
        d = task_title_line(done,    i, GREEN)
        print(f"  {b}{t}{d}│")
        b = task_tags_line(backlog, i)
        t = task_tags_line(todo,    i)
        d = task_tags_line(done,    i)
        print(f"  {b}{t}{d}│")

    print(f"  {line_bot}")
    print()


if __name__ == "__main__":
    from db import init_db
    init_db()
    render_board()
