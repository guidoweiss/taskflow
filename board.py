"""
taskflow/board.py
Renderiza o board kanban no terminal com cores ANSI.
Não precisa de bibliotecas externas.
"""

from tasks import get_tasks_by_status

# Códigos de cor ANSI
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

BG_BLUE    = "\033[44m"
BG_YELLOW  = "\033[103m"
BG_GREEN   = "\033[102m"

WHITE   = "\033[97m"
BLACK   = "\033[30m"
CYAN    = "\033[96m"
YELLOW  = "\033[93m"
GREEN   = "\033[92m"
GRAY    = "\033[90m"

COL_WIDTH = 30  # largura do conteúdo interno de cada coluna
CELL_WIDTH = COL_WIDTH + 4  # largura total da célula (conteúdo + 2 espaços + 2 bordas internas)


def pad(text: str, width: int) -> str:
    """Trunca ou preenche texto para caber na largura indicada (sem ANSI)."""
    if len(text) > width:
        return text[:width - 1] + "…"
    return text.ljust(width)


def render_board():
    """Renderiza o board completo no terminal."""
    backlog = get_tasks_by_status("backlog")
    todo    = get_tasks_by_status("todo")
    done    = get_tasks_by_status("done")

    total    = len(backlog) + len(todo) + len(done)
    max_rows = max(len(backlog), len(todo), len(done), 1)

    # Bordas — cada segmento tem COL_WIDTH + 2 traços (1 espaço de cada lado)
    seg      = "─" * (COL_WIDTH + 2)
    line_top = f"┌{seg}┬{seg}┬{seg}┐"
    line_sep = f"├{seg}┼{seg}┼{seg}┤"
    line_bot = f"└{seg}┴{seg}┴{seg}┘"

    def col_header(label: str, bg: str, fg: str, count: int) -> str:
        """Cabeçalho de coluna com background e foreground definidos separadamente."""
        text = f" {label} ({count})"
        padded = pad(text, COL_WIDTH + 2)  # +2 para os espaços internos
        return f"│{bg}{fg}{BOLD}{padded}{RESET}"

    inner_width = COL_WIDTH + 2  # espaço disponível entre os │

    def task_title_line(tasks: list, index: int, color: str) -> str:
        """Linha do título da tarefa."""
        if index < len(tasks):
            t    = tasks[index]
            text = f" #{t['id']} {t['title']}"
            return f"│{color}{pad(text, inner_width)}{RESET}"
        return f"│{' ' * inner_width}"

    def task_tags_line(tasks: list, index: int) -> str:
        """Linha das tags (segunda linha de cada slot)."""
        if index < len(tasks):
            t   = tasks[index]
            raw = (t['tags'] or "").strip()
            if raw:
                tags_text = " ".join(f"[{tag.strip()}]" for tag in raw.split(",") if tag.strip())
                text = f"  {tags_text}"
                return f"│{GRAY}{pad(text, inner_width)}{RESET}"
        return f"│{' ' * inner_width}"

    print()
    print(f"  {BOLD}taskflow{RESET}{GRAY} — {total} tarefa(s){RESET}")
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
