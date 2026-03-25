"""
taskflow/board.py
Renderiza o board kanban no terminal com cores ANSI.
"""

import re
import sys
import shutil
import time
import select
import termios
import tty
from datetime import date, datetime
from tasks import get_tasks_by_status, has_origin, get_project, get_tasks_for_list

RESET   = "\033[0m"
BOLD    = "\033[1m"
GRAY    = "\033[90m"
DIM     = "\033[2m"
BLINK   = "\033[5m"

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


# ── List view (tabela estilizada) ─────────────────────────────────────────────

def render_list():
    data = get_tasks_for_list(done_limit=5)
    todo    = data["todo"]
    backlog = data["backlog"]
    done    = data["done"]
    done_total = data["done_total"]

    total_active = len(todo) + len(backlog)
    term_width = shutil.get_terminal_size((120, 24)).columns
    TABLE_W = max(80, term_width - 4)

    # 7 colunas: ID | Título | Projeto | Tags | Prio | Criado | Prazo
    N_COLS   = 7
    COL_ID   = 5
    COL_PRIO = 11
    COL_CREATED = 8
    COL_DUE  = 12
    SEPS     = N_COLS + 1  # │ entre cada coluna + bordas
    remaining = TABLE_W - COL_ID - COL_PRIO - COL_CREATED - COL_DUE - SEPS
    COL_TAGS  = max(10, remaining * 13 // 100)
    remaining2 = remaining - COL_TAGS
    COL_PROJ  = max(14, remaining2 * 30 // 100)
    COL_TITLE = remaining2 - COL_PROJ

    # Cores para projetos (cicla entre elas)
    PROJ_COLORS = [MAGENTA, CYAN, YELLOW, GREEN, "\033[94m"]

    _proj_color_map = {}
    def _proj_color(name: str) -> str:
        if not name:
            return GRAY
        if name not in _proj_color_map:
            _proj_color_map[name] = PROJ_COLORS[len(_proj_color_map) % len(PROJ_COLORS)]
        return _proj_color_map[name]

    STATUS_CONFIG = {
        "todo":    ("● TO DO",   YELLOW, BG_YELLOW, BLACK),
        "backlog": ("○ BACKLOG", CYAN,   BG_BLUE,   WHITE),
        "done":    ("✓ DONE",    GREEN,  BG_GREEN,  BLACK),
    }

    def _trunc(text: str, width: int) -> str:
        if len(text) > width:
            return text[:width - 1] + "…"
        return text

    def _due_fmt(due_str: str, is_done: bool = False, blink_on: bool = True) -> str:
        if not due_str or not due_str.strip():
            return ""
        try:
            due  = datetime.strptime(due_str.strip(), "%Y-%m-%d").date()
            diff = (due - date.today()).days
            short = f"{due_str[5:]}"
            if is_done:
                return f"{GRAY}{short}{RESET}"
            if diff < 0:
                if blink_on:
                    return f"{RED}{BOLD}⚠ atrasado{RESET}"
                else:
                    return f"{DIM}{RED}⚠ atrasado{RESET}"
            elif diff <= 2:
                return f"{YELLOW}{short}{RESET}"
            else:
                return f"{GRAY}{short}{RESET}"
        except ValueError:
            return f"{GRAY}{due_str}{RESET}"

    def _prio_fmt(priority: str) -> str:
        p = (priority or "").strip()
        if not p:
            return ""
        color = PRIORITY_COLOR.get(p, GRAY)
        sym   = PRIORITY_SYMBOL.get(p, "")
        return f"{color}{sym} {p}{RESET}"

    def _proj_short(task) -> str:
        pid = task["project_id"] if "project_id" in task.keys() else None
        name = _project_name(task)
        if not name:
            return ""
        label = f"#{pid} {name}" if pid else name
        return _trunc(label, COL_PROJ - 1)

    # ── Desenho ──

    cols = [COL_ID, COL_TITLE, COL_PROJ, COL_TAGS, COL_PRIO, COL_CREATED, COL_DUE]

    def _cpad(text_colored: str, width: int) -> str:
        vlen = len(strip_ansi(text_colored))
        if vlen >= width:
            return text_colored
        return text_colored + " " * (width - vlen)

    def _is_overdue(task, is_done=False):
        if is_done:
            return False
        due_str = (task['due_date'] or "").strip()
        if not due_str:
            return False
        try:
            return (datetime.strptime(due_str, "%Y-%m-%d").date() - date.today()).days < 0
        except ValueError:
            return False

    # ── Renderiza um frame completo ──

    def _render_frame(blink_on: bool) -> str:
        """Gera o board completo como string. blink_on alterna visibilidade dos overdue."""
        lines = []
        pr = lines.append

        pr("")
        footer = f"  {GRAY}q = sair{RESET}" if (_has_overdue and sys.stdin.isatty()) else ""
        pr(f"  {BOLD}taskflow{RESET}{GRAY} — {total_active} tarefa(s) ativa(s){RESET}{footer}")
        pr("")

        # helpers locais que escrevem em lines
        def hline():
            pr(f"  {GRAY}{'─' * TABLE_W}{RESET}")

        def row(*cells):
            parts = "  ".join(_cpad(cells[i] if i < len(cells) else '', cols[i]) for i in range(N_COLS))
            pr(f"  {parts}")

        def sec_header(status, extra=""):
            label, _color, bg, fg = STATUS_CONFIG[status]
            text = f"  {label}{extra}"
            pr(f"  {bg}{fg}{BOLD}{pad(text, TABLE_W)}{RESET}")

        def task_row(task, color, is_done=False):
            overdue = _is_overdue(task, is_done)
            # Quando blink_off, tarefas overdue ficam dim
            if overdue and not blink_on:
                dim = DIM
            else:
                dim = ""

            tid   = f"{dim}{color} #{task['id']}{RESET}"
            title_col = f" {dim}{color}{BOLD}{_trunc(task['title'], COL_TITLE - 2)}{RESET}"

            EMPTY = f" {GRAY}---{RESET}"

            proj_name = _proj_short(task)
            pc = _proj_color(proj_name)
            proj = f" {pc}{proj_name}{RESET}" if proj_name else EMPTY

            tags_raw = (task['tags'] or "").strip()
            tags_col = f" {GRAY}{_trunc(tags_raw, COL_TAGS - 2)}{RESET}" if tags_raw else EMPTY

            prio     = _prio_fmt(task['priority'])
            prio_col = f" {prio}" if prio else EMPTY

            created_raw = (task['created_at'] or "")[:10] if 'created_at' in task.keys() else ""
            created_col = f" {GRAY}{created_raw[5:]}{RESET}" if created_raw else EMPTY

            due      = _due_fmt(task['due_date'] or "", is_done=is_done, blink_on=blink_on)
            due_col  = f" {due}" if due else EMPTY

            row(tid, title_col, proj, tags_col, prio_col, created_col, due_col)

        sections = [
            ("backlog", backlog, False),
            ("todo",    todo,    False),
            ("done",    done,    True),
        ]

        row(f"{GRAY}  # ",
            f" {GRAY}Título",
            f" {GRAY}Projeto",
            f" {GRAY}Tags",
            f" {GRAY}Prio",
            f" {GRAY}Criado",
            f" {GRAY}Prazo{RESET}")
        hline()

        for status, tasks, is_done in sections:
            extra = ""
            if status == "done" and done_total > 5:
                extra = f" — últimos 5 de {done_total}"
            sec_header(status, extra)
            hline()
            if tasks:
                for task in tasks:
                    task_row(task, STATUS_CONFIG[status][1], is_done=is_done)
            else:
                row("", f" {GRAY}(vazio){RESET}", "", "", "", "", "")
            pr("")

        return "\n".join(lines)

    # Verificar se há tarefas overdue
    _has_overdue = any(
        _is_overdue(t) for t in (todo + backlog)
    )

    # Se não há overdue ou stdin não é TTY, print estático e sai
    if not _has_overdue or not sys.stdin.isatty():
        print(_render_frame(True))
        return

    # ── Loop interativo com blink simulado ──
    # Usa alternate screen buffer (como htop/vim) para não poluir o terminal
    ALT_ON       = "\033[?1049h"  # entra no buffer alternativo
    ALT_OFF      = "\033[?1049l"  # volta ao buffer original
    CURSOR_HOME  = "\033[H"
    HIDE_CURSOR  = "\033[?25l"
    SHOW_CURSOR  = "\033[?25h"

    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        sys.stdout.write(ALT_ON + HIDE_CURSOR)
        sys.stdout.flush()
        blink_state = True
        while True:
            sys.stdout.write(CURSOR_HOME)
            sys.stdout.write(_render_frame(blink_state))
            sys.stdout.flush()
            blink_state = not blink_state
            # Espera 0.6s ou tecla
            if select.select([sys.stdin], [], [], 0.6)[0]:
                ch = sys.stdin.read(1)
                if ch in ('q', 'Q', '\x03'):  # q ou Ctrl+C
                    break
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        sys.stdout.write(SHOW_CURSOR + ALT_OFF)
        sys.stdout.flush()
        # Print final estático no terminal normal
        print(_render_frame(True))


# ── Board normal ──────────────────────────────────────────────────────────────

def render_board(tag_filter: str = ""):
    backlog = get_tasks_by_status("backlog", tag_filter)
    todo    = get_tasks_by_status("todo",    tag_filter)
    done    = get_tasks_by_status("done",    tag_filter)

    total    = len(backlog) + len(todo) + len(done)
    max_rows = max(len(backlog), len(todo), len(done), 1)

    term_width = shutil.get_terminal_size((120, 24)).columns
    MARGIN = 2
    GAP    = 3
    col_w  = max(20, (term_width - MARGIN - GAP * 2) // 3)
    GAP_S  = " " * GAP
    MAR_S  = " " * MARGIN

    def col_header(label, bg, fg, count):
        return f"{bg}{fg}{BOLD}{pad(f' {label} ({count})', col_w)}{RESET}"

    # linha 1 — título
    def title_line(tasks, index, color):
        if index < len(tasks):
            t     = tasks[index]
            arrow = "↗ " if has_origin(t["id"]) else ""
            text  = f" {arrow}#{t['id']} {t['title']}"
            return f"{color}{pad(text, col_w)}{RESET}"
        return " " * col_w

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
                return " " * col_w

            sep_plain   = "  ·  "
            sep_colored = f"  {GRAY}·{RESET}  "
            plain       = "  " + sep_plain.join(parts_plain)
            colored     = "  " + sep_colored.join(parts_colored)
            vlen        = len(plain)

            if vlen > col_w:
                return f"{GRAY}{plain[:col_w - 1]}…{RESET}"
            return f"{colored}{' ' * (col_w - vlen)}"
        return " " * col_w

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
            if vlen > col_w:
                return f"{GRAY}{plain[:col_w - 1]}…{RESET}"
            return f"{colored}{' ' * (col_w - vlen)}"
        return " " * col_w

    def sep_seg(tasks, index):
        if index + 1 < len(tasks):
            return f"{GRAY}{'╌' * col_w}{RESET}"
        return " " * col_w

    filter_label = f"  {GRAY}filtro: [{tag_filter}]{RESET}" if tag_filter else ""
    print()
    print(f"{MAR_S}{BOLD}taskflow{RESET}{GRAY} — {total} tarefa(s){RESET}{filter_label}")
    print()
    print(
        f"{MAR_S}{col_header('BACKLOG', BG_BLUE,   WHITE, len(backlog))}"
        f"{GAP_S}{col_header('TO DO',   BG_YELLOW, BLACK, len(todo))}"
        f"{GAP_S}{col_header('DONE',    BG_GREEN,  BLACK, len(done))}"
    )

    for i in range(max_rows):
        print(f"{MAR_S}{title_line(backlog, i, CYAN)}{GAP_S}{title_line(todo, i, YELLOW)}{GAP_S}{title_line(done, i, GREEN)}")
        print(f"{MAR_S}{meta_line(backlog, i)}{GAP_S}{meta_line(todo, i)}{GAP_S}{meta_line(done, i)}")
        print(f"{MAR_S}{dates_line(backlog, i)}{GAP_S}{dates_line(todo, i)}{GAP_S}{dates_line(done, i)}")
        if i < max_rows - 1:
            print(f"{MAR_S}{sep_seg(backlog, i)}{GAP_S}{sep_seg(todo, i)}{GAP_S}{sep_seg(done, i)}")

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


# ── Lista focada (view padrão) ────────────────────────────────────────────────

def render_list_focused():
    """Lista vertical priorizada: BACKLOG → TO DO → DONE. View padrão do taskflow."""
    data       = get_tasks_for_list(done_limit=5)
    todo       = data["todo"]
    backlog    = data["backlog"]
    done       = data["done"]
    done_total = data["done_total"]

    today        = date.today()
    today_str    = today.isoformat()
    total_active = len(todo) + len(backlog)

    term_w  = shutil.get_terminal_size((120, 24)).columns
    ID_W    = 5    # "#43  "
    PROJ_W  = 18   # "← Driagenda     "
    RIGHT_W = 15   # "⚠ hoje         "
    TITLE_W = max(20, term_w - 4 - ID_W - 2 - PROJ_W - RIGHT_W - 2)

    def _trunc(text, w):
        return text[:w - 1] + "…" if len(text) > w else text

    def _due_label(due_str):
        if not due_str or not due_str.strip():
            return "", ""
        try:
            due  = datetime.strptime(due_str.strip(), "%Y-%m-%d").date()
            diff = (due - today).days
            if diff < 0:
                return f"⚠ {abs(diff)}d atraso", RED
            elif diff == 0:
                return "⚠ hoje", RED
            elif diff <= 3:
                return f"vence {due.strftime('%d/%m')}", YELLOW
            else:
                return f"vence {due.strftime('%d/%m')}", GRAY
        except ValueError:
            return due_str, GRAY

    def _proj_name(task):
        pid = task["project_id"] if "project_id" in task.keys() else None
        if not pid:
            return ""
        proj = get_project(pid)
        return proj["name"] if proj else ""

    def _print_task(task, is_done=False):
        id_raw    = f"#{task['id']}"
        title_raw = _trunc(task["title"], TITLE_W)
        proj_raw  = _proj_name(task)
        proj_trunc = _trunc(proj_raw, PROJ_W - 3) if proj_raw else ""

        id_col    = pad(f"{GRAY}{id_raw}{RESET}", ID_W)
        title_col = pad(f"{GRAY}{title_raw}{RESET}" if is_done else f"{BOLD}{title_raw}{RESET}", TITLE_W)

        if proj_trunc:
            proj_col = pad(f"{GRAY}← {proj_trunc}{RESET}", PROJ_W)
        else:
            proj_col = " " * PROJ_W

        if is_done:
            right_col = f"{GREEN}✓{RESET}"
        else:
            due_label, due_color = _due_label(task["due_date"] or "")
            prio = (task["priority"] or "").strip()
            if due_label:
                right_col = f"{due_color}{due_label}{RESET}"
            elif prio:
                pc = PRIORITY_COLOR.get(prio, GRAY)
                right_col = f"{pc}{prio}{RESET}"
            else:
                right_col = ""

        print(f"    {id_col}  {title_col}  {proj_col} {right_col}")

    BG_RED = "\033[41m"

    def _sec_header(label, bg, fg):
        print(f"\n  {bg}{fg}{BOLD} {label} {RESET}")

    # ── Cabeçalho ──
    print()
    print(f"  {BOLD}taskflow{RESET}{GRAY} — {total_active} tarefa(s)  ·  {today_str}{RESET}")
    print(f"  {GRAY}{'─' * min(70, term_w - 4)}{RESET}")

    # ── BACKLOG ──
    _sec_header("BACKLOG", BG_BLUE, WHITE)
    if backlog:
        for t in backlog:
            _print_task(t)
    else:
        print(f"    {GRAY}(vazio){RESET}")

    # ── TO DO ──
    _sec_header("TO DO", BG_YELLOW, BLACK)
    if todo:
        for t in todo:
            _print_task(t)
    else:
        print(f"    {GRAY}(vazio){RESET}")

    # ── DONE ──
    if done_total > 5:
        done_label = f"DONE  {GRAY}(últimos {len(done)} de {done_total}){RESET}"
    elif done:
        done_label = f"DONE  {GRAY}(últimos {len(done)}){RESET}"
    else:
        done_label = "DONE"
    print(f"\n  {BG_GREEN}{BLACK}{BOLD} DONE {RESET}  {GRAY}(últimos {len(done)}" + (f" de {done_total}" if done_total > 5 else "") + f"){RESET}")
    if done:
        for t in done:
            _print_task(t, is_done=True)
    else:
        print(f"    {GRAY}(vazio){RESET}")

    print()


if __name__ == "__main__":
    from db import init_db
    init_db()
    render_board()
