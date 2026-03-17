#!/usr/bin/env python3
"""
taskflow — Gerenciador de tarefas no terminal
Uso:
    taskflow               → mostra o board
    taskflow add "título"  → adiciona tarefa no backlog
    taskflow todo <id>     → move para To Do
    taskflow done <id>     → move para Done
    taskflow back <id>     → move de volta para Backlog
    taskflow rm <id>       → remove tarefa
    taskflow show <id>     → detalhes de uma tarefa
"""

import sys
import os

# Garante que os módulos do projeto sejam encontrados
sys.path.insert(0, os.path.dirname(__file__))

from db import init_db
from tasks import add_task, move_task, delete_task, get_task, tag_task, get_all_tasks
from board import render_board

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
RED    = "\033[91m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"


def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")


def err(msg):
    print(f"  {RED}✗{RESET} {msg}")


def help_text():
    print(f"""
  {BOLD}taskflow{RESET} — Gerenciador de tarefas

  {CYAN}Comandos:{RESET}
    {BOLD}taskflow{RESET}                          Mostra o board
    {BOLD}taskflow add{RESET} "título"            Adiciona tarefa no backlog
    {BOLD}taskflow todo{RESET} <id>               Move para To Do
    {BOLD}taskflow done{RESET} <id>               Move para Done
    {BOLD}taskflow back{RESET} <id>               Move de volta para Backlog
    {BOLD}taskflow tag{RESET} <id> "tag1,tag2"   Define tags de uma tarefa
    {BOLD}taskflow rm{RESET} <id>                 Remove tarefa
    {BOLD}taskflow show{RESET} <id>               Detalhes de uma tarefa
    {BOLD}taskflow show all{RESET}               Lista todas as tarefas com detalhes
""")


def cmd_show_all():
    tasks = get_all_tasks()
    if not tasks:
        print(f"\n  {GRAY}Nenhuma tarefa encontrada.{RESET}\n")
        return

    status_color = {"backlog": "\033[96m", "todo": "\033[93m", "done": "\033[92m"}
    status_label = {"backlog": "BACKLOG", "todo": "TO DO", "done": "DONE"}
    status_bg    = {"backlog": "\033[44m\033[97m", "todo": "\033[103m\033[30m", "done": "\033[42m\033[30m"}

    SEP = f"  {GRAY}{'─' * 60}{RESET}"

    print(f"\n  {BOLD}taskflow{RESET}{GRAY} — {len(tasks)} tarefa(s){RESET}\n")

    for task in tasks:
        color  = status_color.get(task["status"], RESET)
        badge  = status_bg.get(task["status"], RESET)
        label  = status_label.get(task["status"], task["status"].upper())
        tags   = task["tags"] or "—"
        desc   = task["description"] or "—"

        tag_fmt = "  ".join(f"{GRAY}[{t.strip()}]{RESET}" for t in tags.split(",") if t.strip()) if task["tags"] else GRAY + "—" + RESET

        print(f"  {badge} {label} {RESET}  {BOLD}{color}#{task['id']} {task['title']}{RESET}")
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
    status_color = {"backlog": CYAN, "todo": "\033[93m", "done": GREEN}
    color = status_color.get(task["status"], RESET)
    print(f"""
  {BOLD}#{task['id']} — {task['title']}{RESET}
  {GRAY}Status:{RESET}     {color}{task['status']}{RESET}
  {GRAY}Descrição:{RESET}  {task['description'] or '—'}
  {GRAY}Tags:{RESET}       {task['tags'] or '—'}
  {GRAY}Criado em:{RESET}  {task['created_at']}
  {GRAY}Atualizado:{RESET} {task['updated_at']}
""")


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
            err('Uso: taskflow add "título da tarefa"')
            return
        title = args[1]
        desc = args[2] if len(args) > 2 else ""
        new_id = add_task(title, desc)
        ok(f'Tarefa #{new_id} "{title}" adicionada ao backlog.')
        render_board()

    elif cmd in ("todo", "done", "back"):
        if len(args) < 2:
            err(f"Uso: taskflow {cmd} <id>")
            return
        task_id = int(args[1])
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
        tags = args[2]
        if tag_task(task_id, tags):
            ok(f"Tags da tarefa #{task_id} atualizadas: {tags}")
            render_board()
        else:
            err(f"Tarefa #{task_id} não encontrada.")

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
