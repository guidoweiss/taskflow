#!/usr/bin/env python3
"""
taskflow — Gerenciador de tarefas no terminal
Uso:
    taskflow                              → mostra o board
    taskflow add "título" ["desc"]        → adiciona tarefa no backlog
    taskflow todo <id>                    → move para To Do
    taskflow done <id>                    → move para Done
    taskflow back <id>                    → move de volta para Backlog
    taskflow tag <id> "tag1,tag2"        → define tags
    taskflow edit <id> <campo> "valor"   → edita title|desc|priority|due
    taskflow filter <tag>                 → filtra board por tag
    taskflow search "termo"              → busca por título ou descrição
    taskflow rm <id>                      → remove tarefa
    taskflow show <id>                    → detalhes de uma tarefa
    taskflow show all                     → lista todas as tarefas
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from db import init_db
from tasks import (add_task, move_task, delete_task, get_task, tag_task,
                   get_all_tasks, search_tasks, edit_task, VALID_PRIORITIES)
from board import render_board

from datetime import date, datetime

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"

PRIORITY_COLOR = {
    "alta":  RED,
    "media": YELLOW,
    "baixa": GRAY,
    "":      GRAY,
}


def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")


def err(msg):
    print(f"  {RED}✗{RESET} {msg}")


def help_text():
    print(f"""
  {BOLD}taskflow{RESET} — Gerenciador de tarefas

  {CYAN}Comandos:{RESET}
    {BOLD}taskflow{RESET}                              Mostra o board
    {BOLD}taskflow add{RESET} "título" ["desc"]        Adiciona tarefa no backlog
    {BOLD}taskflow todo{RESET} <id>                    Move para To Do
    {BOLD}taskflow done{RESET} <id>                    Move para Done
    {BOLD}taskflow back{RESET} <id>                    Move de volta para Backlog
    {BOLD}taskflow tag{RESET} <id> "tag1,tag2"        Define tags de uma tarefa
    {BOLD}taskflow edit{RESET} <id> title "valor"      Edita o título
    {BOLD}taskflow edit{RESET} <id> desc "valor"       Edita a descrição
    {BOLD}taskflow edit{RESET} <id> priority alta|media|baixa  Define prioridade
    {BOLD}taskflow edit{RESET} <id> due YYYY-MM-DD     Define prazo
    {BOLD}taskflow filter{RESET} <tag>                 Filtra board por tag
    {BOLD}taskflow search{RESET} "termo"               Busca por título ou descrição
    {BOLD}taskflow rm{RESET} <id>                      Remove tarefa
    {BOLD}taskflow show{RESET} <id>                    Detalhes de uma tarefa
    {BOLD}taskflow show all{RESET}                     Lista todas as tarefas com detalhes
""")


def _due_display(due_date_str: str) -> tuple[str, str]:
    """Retorna (texto, cor) para exibir o prazo."""
    if not due_date_str or not due_date_str.strip():
        return "—", GRAY
    try:
        due  = datetime.strptime(due_date_str.strip(), "%Y-%m-%d").date()
        diff = (due - date.today()).days
        if diff < 0:
            return f"{due_date_str} (atrasado {abs(diff)}d)", RED
        elif diff == 0:
            return f"{due_date_str} (hoje)", YELLOW
        elif diff <= 2:
            return f"{due_date_str} ({diff}d restantes)", YELLOW
        else:
            return f"{due_date_str} ({diff}d restantes)", GRAY
    except ValueError:
        return due_date_str, GRAY


def cmd_show_all(tasks=None):
    if tasks is None:
        tasks = get_all_tasks()
    if not tasks:
        print(f"\n  {GRAY}Nenhuma tarefa encontrada.{RESET}\n")
        return

    status_color = {"backlog": CYAN, "todo": YELLOW, "done": GREEN}
    status_bg    = {"backlog": "\033[44m\033[97m", "todo": "\033[103m\033[30m", "done": "\033[42m\033[30m"}
    status_label = {"backlog": "BACKLOG", "todo": "TO DO", "done": "DONE"}

    SEP = f"  {GRAY}{'─' * 60}{RESET}"

    print(f"\n  {BOLD}taskflow{RESET}{GRAY} — {len(tasks)} tarefa(s){RESET}\n")

    for task in tasks:
        color = status_color.get(task["status"], RESET)
        badge = status_bg.get(task["status"], RESET)
        label = status_label.get(task["status"], task["status"].upper())

        priority    = task["priority"] or ""
        prio_color  = PRIORITY_COLOR.get(priority, GRAY)
        prio_label  = f"{prio_color}{priority.upper()}{RESET}" if priority else f"{GRAY}—{RESET}"

        tags_raw = task["tags"] or ""
        tag_fmt  = "  ".join(f"{GRAY}[{t.strip()}]{RESET}" for t in tags_raw.split(",") if t.strip()) if tags_raw else f"{GRAY}—{RESET}"

        due_text, due_color = _due_display(task["due_date"] or "")
        due_fmt = f"{due_color}{due_text}{RESET}"

        desc = task["description"] or "—"

        print(f"  {badge} {label} {RESET}  {BOLD}{color}#{task['id']} {task['title']}{RESET}")
        print(f"  {GRAY}Prioridade:{RESET} {prio_label}    {GRAY}Prazo:{RESET} {due_fmt}")
        print(f"  {GRAY}Descrição:{RESET}  {desc}")
        print(f"  {GRAY}Tags:{RESET}       {tag_fmt}")
        print(f"  {GRAY}Criado em:{RESET}  {task['created_at']}  {GRAY}·  Atualizado:{RESET}  {task['updated_at']}")
        print(SEP)

    print()


def cmd_show(task_id):
    task = get_task(task_id)
    if not task:
        err(f"Tarefa #{task_id} não encontrada.")
        return

    status_color = {"backlog": CYAN, "todo": YELLOW, "done": GREEN}
    color = status_color.get(task["status"], RESET)

    priority   = task["priority"] or ""
    prio_color = PRIORITY_COLOR.get(priority, GRAY)
    prio_label = f"{prio_color}{priority.upper()}{RESET}" if priority else "—"

    due_text, due_color = _due_display(task["due_date"] or "")

    print(f"""
  {BOLD}#{task['id']} — {task['title']}{RESET}
  {GRAY}Status:{RESET}     {color}{task['status']}{RESET}
  {GRAY}Prioridade:{RESET} {prio_label}
  {GRAY}Prazo:{RESET}      {due_color}{due_text}{RESET}
  {GRAY}Descrição:{RESET}  {task['description'] or '—'}
  {GRAY}Tags:{RESET}       {task['tags'] or '—'}
  {GRAY}Criado em:{RESET}  {task['created_at']}
  {GRAY}Atualizado:{RESET} {task['updated_at']}
""")


def cmd_search(query):
    results = search_tasks(query)
    if not results:
        print(f"\n  {GRAY}Nenhuma tarefa encontrada para \"{query}\".{RESET}\n")
        return
    print(f"\n  {BOLD}Resultados para \"{query}\"{RESET}{GRAY} — {len(results)} tarefa(s){RESET}\n")
    cmd_show_all(results)


def main():
    init_db()
    args = sys.argv[1:]

    if not args:
        render_board()
        return

    cmd = args[0].lower()

    if cmd in ("help", "--help", "-h"):
        help_text()

    elif cmd == "add":
        if len(args) < 2:
            err('Uso: taskflow add "título da tarefa" ["descrição"]')
            return
        title = args[1]
        desc  = args[2] if len(args) > 2 else ""
        new_id = add_task(title, desc)
        ok(f'Tarefa #{new_id} "{title}" adicionada ao backlog.')
        render_board()

    elif cmd in ("todo", "done", "back"):
        if len(args) < 2:
            err(f"Uso: taskflow {cmd} <id>")
            return
        task_id    = int(args[1])
        status_map = {"todo": "todo", "done": "done", "back": "backlog"}
        new_status = status_map[cmd]
        if move_task(task_id, new_status):
            ok(f"Tarefa #{task_id} movida para {new_status}.")
            render_board()
        else:
            err(f"Tarefa #{task_id} não encontrada.")

    elif cmd == "tag":
        if len(args) < 3:
            err('Uso: taskflow tag <id> "tag1,tag2,tag3"')
            return
        task_id = int(args[1])
        tags    = args[2]
        if tag_task(task_id, tags):
            ok(f"Tags da tarefa #{task_id} atualizadas: {tags}")
            render_board()
        else:
            err(f"Tarefa #{task_id} não encontrada.")

    elif cmd == "edit":
        if len(args) < 4:
            err('Uso: taskflow edit <id> title|desc|priority|due "valor"')
            return
        task_id = int(args[1])
        field   = args[2].lower()
        value   = args[3]

        valid_fields = ("title", "desc", "priority", "due")
        if field not in valid_fields:
            err(f'Campo inválido: "{field}". Use: {", ".join(valid_fields)}')
            return

        if field == "priority" and value not in VALID_PRIORITIES:
            err(f'Prioridade inválida: "{value}". Use: alta, media, baixa')
            return

        if field == "due" and value.lower() != "clear":
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                err('Formato de data inválido. Use: YYYY-MM-DD (ex: 2026-03-25)')
                return

        actual_value = "" if (field == "due" and value.lower() == "clear") else value
        result = edit_task(task_id, field, actual_value)
        if result is None:
            err(f'Campo inválido: "{field}".')
        elif result:
            ok(f'Tarefa #{task_id} — {field} atualizado para "{actual_value or "(vazio)"}".')
            render_board()
        else:
            err(f"Tarefa #{task_id} não encontrada.")

    elif cmd == "filter":
        if len(args) < 2:
            err('Uso: taskflow filter <tag>')
            return
        render_board(tag_filter=args[1])

    elif cmd == "search":
        if len(args) < 2:
            err('Uso: taskflow search "termo"')
            return
        cmd_search(args[1])

    elif cmd == "rm":
        if len(args) < 2:
            err("Uso: taskflow rm <id>")
            return
        task_id = int(args[1])
        if delete_task(task_id):
            ok(f"Tarefa #{task_id} removida.")
            render_board()
        else:
            err(f"Tarefa #{task_id} não encontrada.")

    elif cmd == "show":
        if len(args) < 2:
            err('Uso: taskflow show <id> ou taskflow show all')
            return
        if args[1].lower() == "all":
            cmd_show_all()
        else:
            cmd_show(int(args[1]))

    else:
        err(f'Comando desconhecido: "{cmd}"')
        help_text()


if __name__ == "__main__":
    main()
