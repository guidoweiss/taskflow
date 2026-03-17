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
                   get_all_tasks, search_tasks, edit_task, set_hidden,
                   auto_hide_stale, auto_promote_due, get_hidden_tasks, VALID_PRIORITIES,
                   add_relation, remove_relation, get_relations,
                   add_project, get_project, get_all_projects, archive_project,
                   edit_project, assign_task, unassign_task, get_tasks_by_project,
                   delete_project, star_project,
                   add_agent_task, get_agent_tasks, update_action_status)
from board import render_board, render_mini, render_agent_board

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
    {BOLD}taskflow edit{RESET} <id> link "https://..."  Define link de apoio
    {BOLD}taskflow edit{RESET} <id> plan "passo 1\npasso 2"  Define plano de execução
    {BOLD}taskflow filter{RESET} <tag>                 Filtra board por tag
    {BOLD}taskflow search{RESET} "termo"               Busca por título ou descrição
    {BOLD}taskflow rm{RESET} <id>                      Remove tarefa
    {BOLD}taskflow show{RESET} <id>                    Detalhes de uma tarefa
    {BOLD}taskflow show all{RESET}                     Lista todas as tarefas com detalhes
    {BOLD}taskflow hidden{RESET}                       Lista tarefas ocultas
    {BOLD}taskflow hide{RESET} <id>                    Oculta uma tarefa manualmente
    {BOLD}taskflow unhide{RESET} <id>                  Traz uma tarefa oculta de volta ao backlog

  {CYAN}Relações:{RESET}
    {BOLD}taskflow continue{RESET} <id> "título"       Cria nova task que continua de <id>
    {BOLD}taskflow link{RESET} <id> <from_id>          Linka task existente como continuação de <from_id>
    {BOLD}taskflow unlink{RESET} <id> <from_id>        Remove a relação entre as tasks

  {CYAN}Projetos:{RESET}
    {BOLD}taskflow project add{RESET} "nome" ["desc"]  Cria um projeto
    {BOLD}taskflow project list{RESET}                 Lista projetos ativos
    {BOLD}taskflow project list all{RESET}             Lista todos os projetos (incluindo arquivados)
    {BOLD}taskflow project show{RESET} <id>            Detalhes do projeto e suas tasks
    {BOLD}taskflow project edit{RESET} <id> name|desc "valor"  Edita o projeto
    {BOLD}taskflow project archive{RESET} <id>         Arquiva um projeto
    {BOLD}taskflow assign{RESET} <task_id> <project_id>  Vincula task a um projeto
    {BOLD}taskflow unassign{RESET} <task_id>           Remove vínculo da task com o projeto

  {CYAN}Agent:{RESET}
    {BOLD}taskflow agent add{RESET} "título" "action" "YYYY-MM-DD HH:MM"  Agenda task para o agente
    {BOLD}taskflow agent list{RESET}                   Lista todas as agent tasks
    {BOLD}taskflow agent cancel{RESET} <id>            Cancela uma agent task pendente
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

        proj_id = task["project_id"]
        if proj_id:
            proj = get_project(proj_id)
            proj_fmt = f"{CYAN}#{proj_id} {proj['name']}{RESET}" if proj else f"{GRAY}#{proj_id}{RESET}"
        else:
            proj_fmt = f"{GRAY}—{RESET}"

        desc = task["description"] or "—"
        link = task["link"] or "—"

        plan = task["plan"] or ""
        if plan:
            steps = plan.split("\n")
            plan_fmt = "\n".join(f"    {s.strip()}" for s in steps if s.strip())
        else:
            plan_fmt = f"    {GRAY}—{RESET}"

        print(f"  {badge} {label} {RESET}  {BOLD}{color}#{task['id']} {task['title']}{RESET}")
        print(f"  {GRAY}Prioridade:{RESET} {prio_label}    {GRAY}Prazo:{RESET} {due_fmt}")
        print(f"  {GRAY}Descrição:{RESET}  {desc}")
        print(f"  {GRAY}Tags:{RESET}       {tag_fmt}")
        rels    = get_relations(task["id"])
        origins = rels["origins"]
        conts   = rels["continuations"]
        orig_fmt = "  ".join(f"{GRAY}←{RESET} #{t['id']}" for t in origins) or f"{GRAY}—{RESET}"
        cont_fmt = "  ".join(f"{GRAY}→{RESET} #{t['id']}" for t in conts) or f"{GRAY}—{RESET}"

        print(f"  {GRAY}Projeto:{RESET}    {proj_fmt}")
        print(f"  {GRAY}Link:{RESET}       {CYAN}{link}{RESET}")
        print(f"  {GRAY}Continua de:{RESET}  {orig_fmt}")
        print(f"  {GRAY}Continua em:{RESET}  {cont_fmt}")
        print(f"  {GRAY}Plano:{RESET}")
        print(plan_fmt)
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

    link = task["link"] or "—"
    plan = task["plan"] or ""
    if plan:
        steps = plan.split("\n")
        plan_fmt = "\n".join(f"    {s.strip()}" for s in steps if s.strip())
    else:
        plan_fmt = "    —"

    rels     = get_relations(task["id"])
    origins  = rels["origins"]
    conts    = rels["continuations"]

    proj_id  = task["project_id"]
    if proj_id:
        proj = get_project(proj_id)
        proj_fmt = f"{CYAN}#{proj_id} {proj['name']}{RESET}" if proj else f"{GRAY}#{proj_id}{RESET}"
    else:
        proj_fmt = f"{GRAY}—{RESET}"

    def rel_fmt(tasks_list, arrow):
        if not tasks_list:
            return f"{GRAY}—{RESET}"
        parts = [f"{GRAY}{arrow}{RESET} #{t['id']} {t['title']} {GRAY}({t['status']}){RESET}" for t in tasks_list]
        return f"\n              ".join(parts)

    print(f"""
  {BOLD}#{task['id']} — {task['title']}{RESET}
  {GRAY}Status:{RESET}     {color}{task['status']}{RESET}
  {GRAY}Projeto:{RESET}    {proj_fmt}
  {GRAY}Prioridade:{RESET} {prio_label}
  {GRAY}Prazo:{RESET}      {due_color}{due_text}{RESET}
  {GRAY}Descrição:{RESET}  {task['description'] or '—'}
  {GRAY}Tags:{RESET}       {task['tags'] or '—'}
  {GRAY}Link:{RESET}       {CYAN}{link}{RESET}
  {GRAY}Continua de:{RESET}  {rel_fmt(origins, '←')}
  {GRAY}Continua em:{RESET}  {rel_fmt(conts, '→')}
  {GRAY}Plano:{RESET}
{plan_fmt}
  {GRAY}Criado em:{RESET}  {task['created_at']}
  {GRAY}Atualizado:{RESET} {task['updated_at']}
""")


def cmd_agent_list():
    tasks = get_agent_tasks()
    if not tasks:
        print(f"\n  {GRAY}Nenhuma agent task encontrada.{RESET}\n")
        return

    STATUS_COLOR = {
        "pending":   CYAN,
        "running":   YELLOW,
        "done":      GREEN,
        "cancelled": GRAY,
    }
    STATUS_ICON = {
        "pending":   "○",
        "running":   "◉",
        "done":      "✓",
        "cancelled": "✗",
    }

    print(f"\n  {BOLD}Agent tasks{RESET}{GRAY} — {len(tasks)} tarefa(s){RESET}\n")
    SEP = f"  {GRAY}{'─' * 60}{RESET}"

    for t in tasks:
        st    = t["action_status"] or "pending"
        color = STATUS_COLOR.get(st, GRAY)
        icon  = STATUS_ICON.get(st, "○")
        sched = (t["scheduled_at"] or "")[:16]

        print(f"  {color}{icon}{RESET}  {BOLD}#{t['id']} {t['title']}{RESET}  {GRAY}{sched}{RESET}")
        print(f"     {GRAY}Action:{RESET} {t['action']}")
        if t["action_result"]:
            result_preview = t["action_result"][:120].replace("\n", " ")
            print(f"     {GRAY}Result:{RESET} {result_preview}{'…' if len(t['action_result']) > 120 else ''}")
        print(SEP)
    print()


def cmd_project_list(include_archived=False):
    projects = get_all_projects(include_archived)
    if not projects:
        print(f"\n  {GRAY}Nenhum projeto encontrado.{RESET}\n")
        return
    label = "todos os projetos" if include_archived else "projetos ativos"
    print(f"\n  {BOLD}taskflow{RESET}{GRAY} — {len(projects)} {label}{RESET}\n")
    for p in projects:
        star     = f"{YELLOW}★{RESET} " if p["starred"] else "  "
        archived = f"  {GRAY}[arquivado]{RESET}" if p["status"] == "archived" else ""
        desc     = f"  {GRAY}{p['description']}{RESET}" if p["description"] else ""
        print(f"  {star}{CYAN}{BOLD}#{p['id']} {p['name']}{RESET}{archived}{desc}")
    print()


def cmd_project_show(project_id):
    proj = get_project(project_id)
    if not proj:
        err(f"Projeto #{project_id} não encontrado.")
        return
    tasks = get_tasks_by_project(project_id)
    status_color = {"backlog": CYAN, "todo": YELLOW, "done": GREEN}
    archived = f"  {GRAY}[arquivado]{RESET}" if proj["status"] == "archived" else ""
    star     = f"{YELLOW}★  {RESET}" if proj["starred"] else ""

    print(f"\n  {star}{BOLD}#{proj['id']} — {proj['name']}{RESET}{archived}")
    if proj["description"]:
        print(f"  {GRAY}Descrição:{RESET} {proj['description']}")
    print(f"  {GRAY}Criado em:{RESET} {proj['created_at'][:10]}")
    print(f"\n  {GRAY}Tasks ({len(tasks)}):{RESET}")
    if tasks:
        for t in tasks:
            color = status_color.get(t["status"], RESET)
            print(f"    {color}#{t['id']} {t['title']}{RESET}  {GRAY}({t['status']}){RESET}")
    else:
        print(f"    {GRAY}Nenhuma task vinculada.{RESET}")
    print()


def cmd_search(query):
    results = search_tasks(query)
    if not results:
        print(f"\n  {GRAY}Nenhuma tarefa encontrada para \"{query}\".{RESET}\n")
        return
    print(f"\n  {BOLD}Resultados para \"{query}\"{RESET}{GRAY} — {len(results)} tarefa(s){RESET}\n")
    cmd_show_all(results)


def cmd_hidden():
    tasks = get_hidden_tasks()
    if not tasks:
        print(f"\n  {GRAY}Nenhuma tarefa oculta.{RESET}\n")
        return
    print(f"\n  {BOLD}Tarefas ocultas{RESET}{GRAY} — {len(tasks)} tarefa(s){RESET}\n")
    SEP = f"  {GRAY}{'─' * 60}{RESET}"
    for task in tasks:
        tags_raw = task["tags"] or ""
        tag_fmt  = f"{GRAY}[{tags_raw.split(',')[0].strip()}]{RESET}" if tags_raw else f"{GRAY}—{RESET}"
        print(f"  {GRAY}#{task['id']} {task['title']}{RESET}")
        print(f"  {GRAY}Tag:{RESET} {tag_fmt}    {GRAY}Oculta desde:{RESET} {GRAY}{(task['updated_at'] or '')[:10]}{RESET}")
        print(SEP)
    print()


def main():
    init_db()
    auto_promote_due()
    hidden_count = auto_hide_stale(days=14)
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
            err('Uso: taskflow tag <id> "tag"')
            return
        task_id = int(args[1])
        success, used_tag = tag_task(task_id, args[2])
        if success:
            ok(f'Tag da tarefa #{task_id} definida como "{used_tag}".')
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

        valid_fields = ("title", "desc", "priority", "due", "link", "plan")
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

    elif cmd == "mini":
        tag = args[1] if len(args) > 1 else ""
        render_mini(tag_filter=tag)

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

    elif cmd == "hidden":
        cmd_hidden()

    elif cmd == "hide":
        if len(args) < 2:
            err("Uso: taskflow hide <id>")
            return
        task_id = int(args[1])
        if set_hidden(task_id, True):
            ok(f"Tarefa #{task_id} ocultada.")
            render_board()
        else:
            err(f"Tarefa #{task_id} não encontrada.")

    elif cmd == "unhide":
        if len(args) < 2:
            err("Uso: taskflow unhide <id>")
            return
        task_id = int(args[1])
        if set_hidden(task_id, False):
            ok(f"Tarefa #{task_id} visível novamente.")
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

    elif cmd == "continue":
        if len(args) < 3:
            err('Uso: taskflow continue <id> "título da nova task"')
            return
        from_id = int(args[1])
        if not get_task(from_id):
            err(f"Tarefa #{from_id} não encontrada.")
            return
        title  = args[2]
        desc   = args[3] if len(args) > 3 else ""
        new_id = add_task(title, desc)
        add_relation(from_id, new_id)
        ok(f'Tarefa #{new_id} "{title}" criada como continuação de #{from_id}.')
        render_board()

    elif cmd == "link":
        if len(args) < 3:
            err("Uso: taskflow link <id> <from_id>")
            return
        task_id = int(args[1])
        from_id = int(args[2])
        if not get_task(task_id):
            err(f"Tarefa #{task_id} não encontrada.")
            return
        if not get_task(from_id):
            err(f"Tarefa #{from_id} não encontrada.")
            return
        if add_relation(from_id, task_id):
            ok(f"Tarefa #{task_id} linkada como continuação de #{from_id}.")
            render_board()
        else:
            err(f"Relação entre #{from_id} e #{task_id} já existe.")

    elif cmd == "unlink":
        if len(args) < 3:
            err("Uso: taskflow unlink <id> <from_id>")
            return
        task_id = int(args[1])
        from_id = int(args[2])
        if remove_relation(from_id, task_id):
            ok(f"Relação entre #{from_id} e #{task_id} removida.")
            render_board()
        else:
            err(f"Relação entre #{from_id} e #{task_id} não encontrada.")

    elif cmd == "agent":
        if len(args) < 2:
            render_agent_board()
            return
        sub = args[1].lower()

        if sub == "add":
            if len(args) < 5:
                err('Uso: taskflow agent add "título" "action" "YYYY-MM-DD HH:MM"')
                return
            title      = args[2]
            action     = args[3]
            sched      = args[4]
            try:
                datetime.strptime(sched, "%Y-%m-%d %H:%M")
            except ValueError:
                err('Formato de data inválido. Use: YYYY-MM-DD HH:MM')
                return
            new_id = add_agent_task(title, action, sched)
            ok(f'Agent task #{new_id} "{title}" agendada para {sched}.')

        elif sub == "list":
            cmd_agent_list()

        elif sub == "cancel":
            if len(args) < 3:
                err("Uso: taskflow agent cancel <id>")
                return
            task_id = int(args[2])
            if update_action_status(task_id, "cancelled", "Cancelado manualmente."):
                ok(f"Agent task #{task_id} cancelada.")
            else:
                err(f"Task #{task_id} não encontrada.")

        else:
            err(f'Subcomando desconhecido: "agent {sub}"')

    elif cmd == "project":
        if len(args) < 2:
            cmd_project_list()
            return
        sub = args[1].lower()

        if sub == "add":
            if len(args) < 3:
                err('Uso: taskflow project add "nome" ["desc"]')
                return
            name = args[2]
            desc = args[3] if len(args) > 3 else ""
            new_id = add_project(name, desc)
            ok(f'Projeto #{new_id} "{name}" criado.')

        elif sub == "list":
            include_all = len(args) > 2 and args[2].lower() == "all"
            cmd_project_list(include_all)

        elif sub == "show":
            if len(args) < 3:
                err("Uso: taskflow project show <id>")
                return
            cmd_project_show(int(args[2]))

        elif sub == "edit":
            if len(args) < 5:
                err('Uso: taskflow project edit <id> name|desc "valor"')
                return
            proj_id = int(args[2])
            field   = args[3].lower()
            value   = args[4]
            if field not in ("name", "desc"):
                err('Campo inválido. Use: name ou desc')
                return
            result = edit_project(proj_id, field, value)
            if result is None:
                err(f'Campo inválido: "{field}".')
            elif result:
                ok(f'Projeto #{proj_id} — {field} atualizado.')
            else:
                err(f"Projeto #{proj_id} não encontrado.")

        elif sub == "archive":
            if len(args) < 3:
                err("Uso: taskflow project archive <id>")
                return
            proj_id = int(args[2])
            if archive_project(proj_id):
                ok(f"Projeto #{proj_id} arquivado.")
            else:
                err(f"Projeto #{proj_id} não encontrado.")

        elif sub == "rm":
            if len(args) < 3:
                err("Uso: taskflow project rm <id>")
                return
            proj_id = int(args[2])
            if delete_project(proj_id):
                ok(f"Projeto #{proj_id} removido.")
            else:
                err(f"Projeto #{proj_id} não encontrado.")

        elif sub == "star":
            if len(args) < 3:
                err("Uso: taskflow project star <id>")
                return
            proj_id = int(args[2])
            if star_project(proj_id, True):
                ok(f"Projeto #{proj_id} marcado como principal.")
                cmd_project_list()
            else:
                err(f"Projeto #{proj_id} não encontrado.")

        elif sub == "unstar":
            if len(args) < 3:
                err("Uso: taskflow project unstar <id>")
                return
            proj_id = int(args[2])
            if star_project(proj_id, False):
                ok(f"Projeto #{proj_id} desmarcado.")
                cmd_project_list()
            else:
                err(f"Projeto #{proj_id} não encontrado.")

        else:
            err(f'Subcomando desconhecido: "project {sub}"')

    elif cmd == "assign":
        if len(args) < 3:
            err("Uso: taskflow assign <task_id> <project_id>")
            return
        task_id    = int(args[1])
        project_id = int(args[2])
        if not get_task(task_id):
            err(f"Tarefa #{task_id} não encontrada.")
            return
        if not get_project(project_id):
            err(f"Projeto #{project_id} não encontrado.")
            return
        if assign_task(task_id, project_id):
            proj = get_project(project_id)
            ok(f'Tarefa #{task_id} vinculada ao projeto #{project_id} "{proj["name"]}".')
            render_board()
        else:
            err(f"Tarefa #{task_id} não encontrada.")

    elif cmd == "unassign":
        if len(args) < 2:
            err("Uso: taskflow unassign <task_id>")
            return
        task_id = int(args[1])
        if unassign_task(task_id):
            ok(f"Tarefa #{task_id} desvinculada do projeto.")
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
