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
import json

sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, get_connection
from tasks import (add_task, move_task, delete_task, get_task, tag_task,
                   get_all_tasks, get_personal_tasks, search_tasks, edit_task, set_hidden,
                   auto_hide_stale, auto_promote_due, get_hidden_tasks, VALID_PRIORITIES,
                   add_relation, remove_relation, get_relations,
                   add_project, get_project, get_project_by_name, get_all_projects, archive_project,
                   edit_project, assign_task, unassign_task, get_tasks_by_project,
                   delete_project, star_project,
                   task_to_dict, update_task, get_tasks_filtered,
                   get_tasks_filtered_for_ai,
                   add_approved_plan, get_approved_plan, get_all_approved_plans, delete_approved_plan,
                   VALID_IMPORTANCE, create_subtasks_from_plan)
from board import render_board, render_mini, render_list, render_list_focused
from tui import run_tui, run_crud

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
  {BOLD}taskflow{RESET} — Gerenciador de tarefas pessoal

  {CYAN}Visualização:{RESET}
    {BOLD}taskflow{RESET}                               Lista focada (BACKLOG → TO DO → DONE)
    {BOLD}taskflow board{RESET}                         Board kanban (3 colunas)
    {BOLD}taskflow board{RESET} <tag>                   Board kanban filtrado por tag
    {BOLD}taskflow tui{RESET}                           Menu interativo (navegar com ←→↑↓)
    {BOLD}taskflow mini{RESET}                          Board compacto
    {BOLD}taskflow filter{RESET} <tag>                  Filtra board por tag
    {BOLD}taskflow search{RESET} "termo"                Busca em títulos e descrições
    {BOLD}taskflow context{RESET}                       Resumo estruturado para Claude

  {CYAN}Tasks pessoais:{RESET}
    {BOLD}taskflow add{RESET} "título" [flags]          Adiciona tarefa ao backlog
      {GRAY}--desc "..."        Descrição
      --tag "tag"         Tag da tarefa
      --project id|nome   Vincula a um projeto (aceita ID ou nome)
      --link "..."        Link de apoio
      --plan "..."        Plano de execução
      --priority alta|media|baixa
      --due YYYY-MM-DD    Prazo{RESET}
    {BOLD}taskflow todo{RESET} <id>                     Move para To Do
    {BOLD}taskflow done{RESET} <id>                     Move para Done
    {BOLD}taskflow back{RESET} <id>                     Move de volta para Backlog
    {BOLD}taskflow show{RESET} <id>                     Detalhes de uma tarefa
    {BOLD}taskflow show all{RESET}                      Lista todas as tarefas pessoais
    {BOLD}taskflow rm{RESET} <id>                       Remove uma tarefa
    {BOLD}taskflow hide{RESET} <id>                     Oculta uma tarefa
    {BOLD}taskflow unhide{RESET} <id>                   Traz tarefa oculta de volta ao backlog
    {BOLD}taskflow hidden{RESET}                        Lista tarefas ocultas
    {BOLD}taskflow tag{RESET} <id> "tag"                Redefine tag da tarefa
    {BOLD}taskflow edit{RESET} <id> title "valor"       Edita o título
    {BOLD}taskflow edit{RESET} <id> desc "valor"        Edita a descrição
    {BOLD}taskflow edit{RESET} <id> priority alta|media|baixa  Define prioridade
    {BOLD}taskflow edit{RESET} <id> due YYYY-MM-DD      Define prazo  ({GRAY}due clear{RESET} para remover)
    {BOLD}taskflow edit{RESET} <id> link "https://..."  Define link de apoio
    {BOLD}taskflow edit{RESET} <id> plan "..."          Define plano de execução
    {BOLD}taskflow assign{RESET} <task_id> <project_id> Vincula task a um projeto
    {BOLD}taskflow unassign{RESET} <task_id>            Remove vínculo da task

  {CYAN}Relações (fila encadeada):{RESET}
    {BOLD}taskflow continue{RESET} <id> "título"        Cria task que continua de <id>
    {BOLD}taskflow link{RESET} <id> <from_id>           Liga task existente como continuação
    {BOLD}taskflow unlink{RESET} <id> <from_id>         Remove relação entre tasks

  {CYAN}Projetos:{RESET}
    {BOLD}taskflow project add{RESET} "nome" ["desc"]   Cria um projeto
    {BOLD}taskflow project list{RESET}                  Lista projetos ativos
    {BOLD}taskflow project list all{RESET}              Inclui projetos arquivados
    {BOLD}taskflow project show{RESET} <id>             Detalhes do projeto e suas tasks
    {BOLD}taskflow project edit{RESET} <id> name|desc "valor"  Edita o projeto
    {BOLD}taskflow project star{RESET} <id>             Marca como favorito
    {BOLD}taskflow project unstar{RESET} <id>           Remove favorito
    {BOLD}taskflow project archive{RESET} <id>          Arquiva um projeto
    {BOLD}taskflow project rm{RESET} <id>               Remove um projeto

  {CYAN}Consulta para IAs:{RESET}
    {BOLD}taskflow query{RESET} [filtros]               Consulta filtrada e paginada (padrão: todo+backlog, limite 50)
      {GRAY}--status todo|backlog|done|all    Status (padrão: todo+backlog)
      --project id|nome             Filtra por projeto
      --tag "tag"                   Filtra por tag
      --priority alta|media|baixa   Filtra por prioridade
      --search "termo"              Busca no título
      --due-soon N                  Tasks com prazo nos próximos N dias
      --limit N                     Máximo retornado (padrão 50, máx 500)
      --full                        Inclui description, plan, link, relações{RESET}
    {BOLD}taskflow sql{RESET} "SELECT ..."             Executa SQL bruto (somente SELECT)

  {CYAN}Planos Aprovados:{RESET}
    {BOLD}taskflow approve{RESET} <task_id> [--importance backend|frontend|structural|other]
                                               Aprova e registra o plano da task
    {BOLD}taskflow approve{RESET} --title "..." --plan "..." [--project id|nom] [--importance ...]
                                               Cria plano aprovado sem task vinculada
    {BOLD}taskflow plans{RESET} [--project id] [--importance ...] [--priority ...] [--since YYYY-MM-DD]
                                               Lista planos aprovados
    {BOLD}taskflow plans show{RESET} <id>              Detalhes de um plano
    {BOLD}taskflow plans rm{RESET} <id>                Remove plano da lista
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
        tasks = get_personal_tasks()
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


def _parse_flags(args):
    """Extrai --flag valor de uma lista de args. Retorna dict com os pares encontrados."""
    flags = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                flags[key] = args[i + 1]
                i += 2
            else:
                flags[key] = True
                i += 1
        else:
            i += 1
    return flags


def cmd_context(json_mode: bool = False):
    """Exibe resumo estruturado do taskflow para Claude ler."""
    data = _build_context_data()

    if json_mode:
        print(json.dumps(data, default=str, ensure_ascii=False, indent=2))
        return

    # Saída texto (sem ANSI)
    today = date.today()
    projects   = data["projects"]
    todo_tasks    = data["tasks"]["todo"]
    backlog_tasks = data["tasks"]["backlog"]
    done_recent   = data["tasks"]["done_recent"]
    summary    = data["summary"]

    lines = [
        f"=== TASKFLOW — {today.isoformat()} ===",
        "",
        f"PROJETOS ATIVOS ({len(projects)})",
    ]
    for p in projects:
        desc = p["description"] or "(sem descrição)"
        lines.append(f"  #{p['id']:2d}  {p['name']:<20s} — {desc}")

    lines.extend(["", f"TO DO ({len(todo_tasks)})"])
    for t in todo_tasks:
        proj = f" ({t['project_name']})" if t.get("project_name") else ""
        due  = f" vence {t['due_date']}" if t["due_date"] else ""
        lines.append(f"  #{t['id']:2d}  {t['title']}{proj}{due}")

    lines.extend(["", f"BACKLOG ({len(backlog_tasks)})"])
    for t in backlog_tasks:
        proj = f" ({t['project_name']})" if t.get("project_name") else ""
        prio = f" [{t['priority']}]" if t["priority"] else ""
        lines.append(f"  #{t['id']:2d}  {t['title']}{proj}{prio}")

    lines.extend(["", f"DONE — últimos 7 dias ({len(done_recent)})"])
    for t in done_recent:
        lines.append(f"  #{t['id']:2d}  {t['title']}")

    print("\n".join(lines))


def cmd_query(args: list, json_mode: bool = False):
    """Consulta filtrada e paginada para consumo por IAs."""
    flags = _parse_flags(args)

    status_raw = flags.get("status", "todo+backlog")
    try:
        limit = min(int(flags.get("limit", 50)), 500)
    except (ValueError, TypeError):
        limit = 50
    full       = "full" in flags
    tag        = flags.get("tag")
    search     = flags.get("search")

    priority = flags.get("priority")
    if priority and priority not in VALID_PRIORITIES:
        err(f'Prioridade inválida: "{priority}". Use: alta, media, baixa')
        return

    due_soon = None
    if "due-soon" in flags:
        try:
            due_soon = int(flags["due-soon"])
        except (ValueError, TypeError):
            err('--due-soon requer um número inteiro (ex: --due-soon 7)')
            return

    STATUS_MAP = {
        "all":          "all",
        "todo+backlog": ["todo", "backlog"],
        "todo":         "todo",
        "backlog":      "backlog",
        "done":         "done",
    }
    if status_raw not in STATUS_MAP:
        err(f'Status inválido: "{status_raw}". Use: todo, backlog, done, all, todo+backlog')
        return
    status = STATUS_MAP[status_raw]

    project_id = None
    if "project" in flags:
        project_id = _resolve_project(flags["project"])
        if project_id is None:
            return

    rows, total = get_tasks_filtered_for_ai(
        status=status, project_id=project_id, tag=tag,
        priority=priority, search=search, due_soon_days=due_soon,
        limit=limit, full=full,
    )

    returned  = len(rows)
    truncated = returned < total

    # Índice de projetos para enriquecimento
    projects = get_all_projects(include_archived=True)
    proj_map = {p["id"]: p["name"] for p in projects}

    def _row_to_dict(row):
        d = {
            "id":          row["id"],
            "title":       row["title"],
            "status":      row["status"],
            "tags":        row["tags"] or "",
            "priority":    row["priority"] or "",
            "due_date":    row["due_date"] or "",
            "project_name": proj_map.get(row["project_id"]) or "",
        }
        if full:
            d["description"] = row["description"] if "description" in row.keys() else ""
            d["plan"]        = row["plan"]        if "plan"        in row.keys() else ""
            d["link"]        = row["link"]        if "link"        in row.keys() else ""
            rels = get_relations(row["id"])
            d["relations"] = {
                "blocked_by": [r["id"] for r in rels["origins"]],
                "unblocks":   [r["id"] for r in rels["continuations"]],
            }
        return d

    tasks_list = [_row_to_dict(r) for r in rows]

    if json_mode:
        output = {
            "query": {
                "status":        status_raw,
                "project_id":    project_id,
                "tag":           tag,
                "priority":      priority,
                "search":        search,
                "due_soon_days": due_soon,
                "limit":         limit,
                "full":          full,
            },
            "total":     total,
            "returned":  returned,
            "truncated": truncated,
            "tasks":     tasks_list,
        }
        print(json.dumps(output, default=str, ensure_ascii=False, indent=2))
        return

    # Saída texto compacta
    trunc_note = f"  {GRAY}(truncado — use --limit ou filtros para refinar){RESET}" if truncated else ""
    print(f"\n  {BOLD}taskflow query{RESET}{GRAY} — {returned} de {total} task(s){RESET}{trunc_note}")
    print(f"  {GRAY}{'─' * 60}{RESET}")

    if not tasks_list:
        print(f"  {GRAY}(nenhuma task encontrada){RESET}")
    else:
        for t in tasks_list:
            id_col   = f"{GRAY}#{t['id']}{RESET}"
            title    = t["title"][:45] + "…" if len(t["title"]) > 45 else t["title"]
            proj_col = f"  {GRAY}({t['project_name']}){RESET}" if t["project_name"] else ""
            tag_col  = f"  {CYAN}[{t['tags']}]{RESET}"        if t["tags"]         else ""
            prio_col = ""
            if t["priority"]:
                pc = {PRIORITY_COLOR.get(t["priority"], GRAY)}
                prio_col = f"  {PRIORITY_COLOR.get(t['priority'], GRAY)}[{t['priority']}]{RESET}"
            due_col  = ""
            if t["due_date"]:
                from datetime import date as _date, datetime as _datetime
                try:
                    due   = _datetime.strptime(t["due_date"], "%Y-%m-%d").date()
                    diff  = (due - _date.today()).days
                    color = RED if diff <= 0 else (YELLOW if diff <= 3 else GRAY)
                    due_col = f"  {color}vence {due.strftime('%d/%m')}{RESET}"
                except ValueError:
                    due_col = f"  {GRAY}{t['due_date']}{RESET}"
            print(f"  {BOLD}{id_col}{RESET}  {title}{proj_col}{tag_col}{prio_col}{due_col}")
    print()


def _is_safe_query(sql: str) -> bool:
    """Permite apenas queries SELECT (segurança básica para o agente)."""
    normalized = sql.strip().upper()
    if '--' in normalized or '/*' in normalized:
        return False
    first_word = normalized.split()[0] if normalized else ""
    return first_word == "SELECT"


def cmd_sql(sql: str, json_mode: bool = False) -> None:
    """Executa SQL bruto (apenas SELECT) e retorna resultado em JSON."""
    sql = sql.strip()
    if not sql:
        err("SQL não pode ser vazio.")
        return

    if not _is_safe_query(sql):
        err("Apenas queries SELECT são permitidas.")
        return

    conn = get_connection()
    try:
        rows = conn.execute(sql).fetchall()
        columns = list(rows[0].keys()) if rows else []
        data = [dict(row) for row in rows]
    except Exception as e:
        err(f"Erro na query: {e}")
        conn.close()
        return
    conn.close()

    if json_mode:
        print(json.dumps({"columns": columns, "rows": data, "count": len(data)}, default=str, ensure_ascii=False, indent=2))
    else:
        if not rows:
            print(f"  {GRAY}(nenhum resultado){RESET}\n")
            return
        col_widths = {col: max(len(col), max(len(str(row.get(col, ""))) for row in data)) for col in columns}
        header = "  " + " | ".join(f"{col:<{col_widths[col]}}" for col in columns)
        sep = "  " + "-+-".join("-" * col_widths[col] for col in columns)
        print(f"\n  {BOLD}{header}{RESET}")
        print(f"  {GRAY}{sep}{RESET}")
        for row in data:
            line = "  " + " | ".join(f"{str(row.get(col, '')):<{col_widths[col]}}" for col in columns)
            print(line)
        print(f"\n  {GRAY}{len(data)} linha(s){RESET}\n")


def _build_context_data() -> dict:
    """Coleta todos os dados do taskflow em um dict estruturado."""
    from datetime import timedelta
    today = date.today()
    seven_days_ago = (today - timedelta(days=7)).isoformat()

    projects = get_all_projects(include_archived=False)
    personal_tasks = get_personal_tasks()

    todo_tasks    = [t for t in personal_tasks if t["status"] == "todo"    and not t["hidden"]]
    backlog_tasks = [t for t in personal_tasks if t["status"] == "backlog" and not t["hidden"]]
    done_recent   = [t for t in personal_tasks if t["status"] == "done"    and not t["hidden"]
                     and (t["updated_at"] or "")[:10] >= seven_days_ago]

    # Índice de projetos para enriquecimento
    proj_map = {p["id"]: p["name"] for p in projects}

    def enrich(task):
        d = task_to_dict(task)
        d["project_name"] = proj_map.get(d.get("project_id")) or None
        rels = get_relations(d["id"])
        d["relations"] = {
            "blocked_by": [r["id"] for r in rels["origins"]],
            "unblocks":   [r["id"] for r in rels["continuations"]],
        }
        return d

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "projects":     [task_to_dict(p) for p in projects],
        "tasks": {
            "todo":        [enrich(t) for t in todo_tasks],
            "backlog":     [enrich(t) for t in backlog_tasks],
            "done_recent": [enrich(t) for t in done_recent],
        },
        "summary": {
            "todo_count":        len(todo_tasks),
            "backlog_count":     len(backlog_tasks),
            "done_recent_count": len(done_recent),
        },
    }


def _resolve_project(value):
    """Resolve project_id a partir de um número (ID) ou nome do projeto."""
    try:
        pid = int(value)
        if get_project(pid):
            return pid
        err(f"Projeto #{pid} não encontrado.")
        return None
    except ValueError:
        proj = get_project_by_name(value)
        if proj:
            return proj["id"]
        err(f'Projeto "{value}" não encontrado.')
        return None


IMPORTANCE_COLORS = {
    "backend":    RED,
    "frontend":   CYAN,
    "structural":  YELLOW,
    "other":      GRAY,
}

IMPORTANCE_LABELS = {
    "backend":    "BACKEND",
    "frontend":   "FRONTEND",
    "structural": "STRUCTURAL",
    "other":      "OTHER",
}


def _handle_approve(args: list, json_mode: bool):
    """Handle the approve command."""
    flags = _parse_flags(args[1:])

    title = flags.get("title", "")
    plan = flags.get("plan", "")
    task_id = None
    project_id = None
    project_path = flags.get("path", "")
    priority = flags.get("priority", "")
    importance = flags.get("importance", None)
    link = flags.get("link", "")

    if len(args) > 1 and not args[1].startswith("--"):
        try:
            task_id = int(args[1])
        except ValueError:
            err(f"ID de task inválido: {args[1]}")
            return
        task = get_task(task_id)
        if not task:
            err(f"Tarefa #{task_id} não encontrada.")
            return
        if not task["plan"]:
            err(f"Tarefa #{task_id} não tem plano definido. Use --plan para definir.")
            return
        if not title:
            title = task["title"]
        if not plan:
            plan = task["plan"]
        if not priority:
            priority = task["priority"] or ""
        if not link:
            link = task["link"] or ""
        if task["project_id"]:
            project_id = task["project_id"]

    if not title and not plan:
        err("Informe --title e --plan, ou um <task_id> com plano definido.")
        return

    if not title:
        err("Título é obrigatório. Use --title.")
        return

    if not plan:
        err("Plano é obrigatório. Use --plan.")
        return

    if importance and importance not in VALID_IMPORTANCE:
        err(f'Importance inválida: "{importance}". Use: {", ".join(VALID_IMPORTANCE)}')
        return

    task_status_str = ""
    if task_id:
        task_for_status = get_task(task_id)
        if task_for_status:
            task_status_str = task_for_status["status"]

    new_id = add_approved_plan(
        title=title,
        plan=plan,
        task_id=task_id,
        project_id=project_id,
        project_path=project_path,
        priority=priority,
        importance_level=importance,
        task_status=task_status_str,
        link=link,
    )

    subtask_ids = create_subtasks_from_plan(
        plan_id=new_id,
        plan_title=title,
        project_id=project_id,
        priority=priority,
        parent_task_id=task_id,
    )

    if json_mode:
        plan_record = get_approved_plan(new_id)
        print(json.dumps({
            "ok": True,
            "id": new_id,
            "plan": task_to_dict(plan_record) if plan_record else None,
            "subtasks_created": subtask_ids,
        }, default=str, ensure_ascii=False, indent=2))
    else:
        imp_level = importance or "auto"
        imp_color = IMPORTANCE_COLORS.get(importance, GRAY)
        imp_label = IMPORTANCE_LABELS.get(importance, importance or "AUTO")
        ok(f"Plano #{new_id} aprovado — importance: {imp_color}{imp_label}{RESET}")
        if subtask_ids:
            subtask_ids_str = ", ".join(f"#{sid}" for sid in subtask_ids)
            ok(f"{len(subtask_ids)} tasks criadas: {subtask_ids_str}")
        if task_id:
            ok(f"Task #{task_id} vinculada ao plano aprovado.")


def _handle_plans_list(flags: dict, json_mode: bool):
    """Handle the plans list command."""
    project_id = None
    if "project" in flags:
        project_id = _resolve_project(flags["project"])
        if project_id is None:
            return

    importance = flags.get("importance")
    if importance and importance not in VALID_IMPORTANCE:
        err(f'Importance inválida: "{importance}". Use: {", ".join(VALID_IMPORTANCE)}')
        return

    priority = flags.get("priority")
    if priority and priority not in VALID_PRIORITIES:
        err(f'Prioridade inválida: "{priority}". Use: alta, media, baixa')
        return

    since = flags.get("since")
    if since:
        try:
            datetime.strptime(since, "%Y-%m-%d")
        except ValueError:
            err('Formato de data inválido. Use: YYYY-MM-DD')
            return

    plans = get_all_approved_plans(
        project_id=project_id,
        importance=importance,
        priority=priority,
        since=since,
    )

    if json_mode:
        projects = get_all_projects(include_archived=True)
        proj_map = {p["id"]: p["name"] for p in projects}

        def enrich(p):
            d = task_to_dict(p)
            d["project_name"] = proj_map.get(d.get("project_id")) or ""
            return d

        print(json.dumps({
            "count": len(plans),
            "plans": [enrich(p) for p in plans],
        }, default=str, ensure_ascii=False, indent=2))
        return

    if not plans:
        print(f"\n  {GRAY}Nenhum plano aprovado encontrado.{RESET}\n")
        return

    projects = get_all_projects(include_archived=True)
    proj_map = {p["id"]: p["name"] for p in projects}

    print(f"\n  {BOLD}Planos Aprovados{RESET}{GRAY} — {len(plans)} plano(s){RESET}\n")

    for p in plans:
        imp = p["importance_level"] or "other"
        imp_color = IMPORTANCE_COLORS.get(imp, GRAY)
        imp_label = IMPORTANCE_LABELS.get(imp, imp.upper())
        imp_badge = f"{imp_color}[{imp_label}]{RESET}"

        proj_name = proj_map.get(p["project_id"]) if p["project_id"] else ""
        proj_fmt = f"{CYAN}{proj_name}{RESET}" if proj_name else GRAY + "—" + RESET

        task_ref = f"{GRAY}← task #{p['task_id']}{RESET}" if p["task_id"] else ""

        prio = p["priority"] or ""
        prio_fmt = f"{PRIORITY_COLOR.get(prio, GRAY)}{prio}{RESET}" if prio else GRAY + "—" + RESET

        approved_at = (p["approved_at"] or "")[:10]

        print(f"  {BOLD}#{p['id']}{RESET}  {p['title']}")
        print(f"  {GRAY}Importance:{RESET} {imp_badge}  {GRAY}Projeto:{RESET} {proj_fmt}  {GRAY}Prioridade:{RESET} {prio_fmt}")
        print(f"  {GRAY}Aprovado em:{RESET} {approved_at}  {task_ref}")
        print(f"  {GRAY}{'─' * 60}{RESET}")

    print()


def _handle_plans_show(plan_id: int, json_mode: bool):
    """Handle the plans show command."""
    plan = get_approved_plan(plan_id)
    if not plan:
        err(f"Plano #{plan_id} não encontrado.")
        return

    projects = get_all_projects(include_archived=True)
    proj_map = {p["id"]: p["name"] for p in projects}

    if json_mode:
        proj_name = proj_map.get(plan["project_id"]) if plan["project_id"] else ""
        d = task_to_dict(plan)
        d["project_name"] = proj_name
        print(json.dumps({"ok": True, "plan": d}, default=str, ensure_ascii=False, indent=2))
        return

    imp = plan["importance_level"] or "other"
    imp_color = IMPORTANCE_COLORS.get(imp, GRAY)
    imp_label = IMPORTANCE_LABELS.get(imp, imp.upper())

    proj_name = proj_map.get(plan["project_id"]) if plan["project_id"] else ""
    proj_fmt = f"{CYAN}{proj_name}{RESET}" if proj_name else GRAY + "—" + RESET

    prio = plan["priority"] or ""
    prio_fmt = f"{PRIORITY_COLOR.get(prio, GRAY)}{prio}{RESET}" if prio else GRAY + "—" + RESET

    plan_raw = (plan["plan"] or "").replace("\\n", "\n")
    plan_lines = plan_raw.split("\n")
    plan_fmt = "\n".join(f"    {s.strip()}" for s in plan_lines if s.strip()) if plan_lines else GRAY + "—" + RESET

    task_ref = ""
    if plan["task_id"]:
        task = get_task(plan["task_id"])
        if task:
            task_ref = f"#{task['id']} — {task['title']} ({task['status']})"
        else:
            task_ref = f"#{plan['task_id']} (task não encontrada)"

    print(f"""
  {BOLD}#{plan['id']} — {plan['title']}{RESET}
  {GRAY}Importance:{RESET}     {imp_color}{imp_label}{RESET}
  {GRAY}Projeto:{RESET}        {proj_fmt}
  {GRAY}Prioridade:{RESET}      {prio_fmt}
  {GRAY}Aprovado em:{RESET}     {plan['approved_at']}
  {GRAY}Task vinculada:{RESET}  {task_ref if task_ref else GRAY + '—' + RESET}
  {GRAY}Project path:{RESET}   {plan['project_path'] or GRAY + '—' + RESET}
  {GRAY}Link:{RESET}            {CYAN}{plan['link'] or '—'}{RESET}
  {GRAY}Plano:{RESET}
{plan_fmt}
  {GRAY}Criado em:{RESET}       {plan['created_at']}
""")


def _handle_plans_rm(plan_id: int, json_mode: bool):
    """Handle the plans rm command."""
    plan = get_approved_plan(plan_id)
    if not plan:
        err(f"Plano #{plan_id} não encontrado.")
        return

    if delete_approved_plan(plan_id):
        if json_mode:
            print(json.dumps({"ok": True, "id": plan_id}))
        else:
            ok(f"Plano #{plan_id} removido.")
    else:
        err(f"Erro ao remover plano #{plan_id}.")


def main():
    init_db()
    auto_promote_due()
    hidden_count = auto_hide_stale(days=14)
    args = sys.argv[1:]

    # Flag global --json: pode ser passada em qualquer posição
    JSON_MODE = "--json" in args
    args = [a for a in args if a != "--json"]

    if not args:
        render_list_focused()
        return

    cmd = args[0].lower()

    if cmd in ("help", "--help", "-h"):
        help_text()

    elif cmd in ("context", "ctx"):
        cmd_context(json_mode=JSON_MODE)

    elif cmd == "board":
        tag = args[1] if len(args) > 1 else ""
        render_board(tag_filter=tag)

    elif cmd == "tui":
        import curses
        curses.wrapper(run_tui)

    elif cmd == "add":
        if len(args) < 2:
            err('Uso: taskflow add "título" [--desc "..."] [--tag "tag"] [--project id|nome] [--link "..."] [--plan "..."] [--priority alta|media|baixa] [--due YYYY-MM-DD]')
            return
        title = args[1]
        flags = _parse_flags(args[2:])

        desc     = flags.get("desc", "")
        tag      = flags.get("tag", "")
        link     = flags.get("link", "")
        plan     = flags.get("plan", "")
        priority = flags.get("priority", "")
        due      = flags.get("due", "")

        if priority and priority not in VALID_PRIORITIES:
            err(f'Prioridade inválida: "{priority}". Use: alta, media, baixa')
            return
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                err('Formato de data inválido. Use: YYYY-MM-DD (ex: 2026-03-25)')
                return

        project_id = None
        if "project" in flags:
            project_id = _resolve_project(flags["project"])
            if project_id is None:
                return

        status = flags.get("status", "backlog")
        valid_statuses = ("backlog", "todo", "done")
        if status not in valid_statuses:
            err(f'Status inválido: "{status}". Use: backlog, todo, done')
            return

        new_id = add_task(title, desc, status=status, tags=tag, priority=priority,
                          due_date=due, link=link, plan=plan, project_id=project_id)
        if JSON_MODE:
            print(json.dumps({"ok": True, "id": new_id, "task": task_to_dict(get_task(new_id))},
                             default=str, ensure_ascii=False))
        else:
            ok(f'Tarefa #{new_id} "{title}" adicionada ao {status}.')
            render_board()

    elif cmd in ("todo", "done", "back"):
        if len(args) < 2:
            err(f"Uso: taskflow {cmd} <id> [<id2> <id3> ...]")
            return
        status_map = {"todo": "todo", "done": "done", "back": "backlog"}
        new_status = status_map[cmd]
        moved = []
        failed_ids = []
        for id_str in args[1:]:
            try:
                task_id = int(id_str)
            except ValueError:
                continue
            if move_task(task_id, new_status):
                moved.append(task_id)
            else:
                failed_ids.append(task_id)
        if JSON_MODE:
            print(json.dumps({"ok": True, "moved": moved, "not_found": failed_ids}))
        else:
            if moved:
                ids_str = ", ".join(f"#{i}" for i in moved)
                ok(f"Tasks {ids_str} movidas para {new_status}.")
            for i in failed_ids:
                err(f"Tarefa #{i} não encontrada.")
            if moved:
                render_board()

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
        if JSON_MODE:
            results = search_tasks(args[1])
            print(json.dumps([task_to_dict(t) for t in results], default=str, ensure_ascii=False, indent=2))
        else:
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
        task = get_task(task_id)
        if not task:
            err(f"Tarefa #{task_id} não encontrada.")
            return
        if task["is_agent"]:
            err(f"Tarefa #{task_id} é uma agent task. Use: taskflow agent rm {task_id}")
            return
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
            if JSON_MODE:
                tasks = get_personal_tasks()
                print(json.dumps([task_to_dict(t) for t in tasks], default=str, ensure_ascii=False, indent=2))
            else:
                cmd_show_all()
        else:
            task_id = int(args[1])
            if JSON_MODE:
                task = get_task(task_id)
                if not task:
                    print(json.dumps({"ok": False, "error": f"Tarefa #{task_id} não encontrada."}))
                else:
                    print(json.dumps({"ok": True, "task": task_to_dict(task)}, default=str, ensure_ascii=False, indent=2))
            else:
                cmd_show(task_id)

    elif cmd == "update":
        if len(args) < 2:
            err('Uso: taskflow update <id> [--title "..."] [--desc "..."] [--priority alta|media|baixa] [--due YYYY-MM-DD] [--plan "..."] [--link "..."] [--tag "..."] [--project id|nome] [--status todo|backlog|done]')
            return
        task_id = int(args[1])
        task = get_task(task_id)
        if not task:
            if JSON_MODE:
                print(json.dumps({"ok": False, "error": f"Tarefa #{task_id} não encontrada."}))
            else:
                err(f"Tarefa #{task_id} não encontrada.")
            return

        flags = _parse_flags(args[2:])
        fields = {}

        if "title" in flags:
            fields["title"] = flags["title"]
        if "desc" in flags:
            fields["description"] = flags["desc"]
        if "plan" in flags:
            fields["plan"] = flags["plan"]
        if "link" in flags:
            fields["link"] = flags["link"]
        if "tag" in flags:
            fields["tags"] = flags["tag"].split(",")[0].strip()
        if "priority" in flags:
            if flags["priority"] not in VALID_PRIORITIES:
                err(f'Prioridade inválida: "{flags["priority"]}". Use: alta, media, baixa')
                return
            fields["priority"] = flags["priority"]
        if "due" in flags:
            if flags["due"].lower() == "clear":
                fields["due_date"] = ""
            else:
                try:
                    datetime.strptime(flags["due"], "%Y-%m-%d")
                except ValueError:
                    err('Formato de data inválido. Use: YYYY-MM-DD')
                    return
                fields["due_date"] = flags["due"]
        if "status" in flags:
            if flags["status"] not in ("backlog", "todo", "done"):
                err(f'Status inválido: "{flags["status"]}". Use: backlog, todo, done')
                return
            fields["status"] = flags["status"]
        if "project" in flags:
            pid = _resolve_project(flags["project"])
            if pid is None:
                return
            fields["project_id"] = pid

        if not fields:
            err("Nenhum campo para atualizar. Use --title, --desc, --priority, --due, --plan, --link, --tag, --project, --status")
            return

        if update_task(task_id, fields):
            updated = get_task(task_id)
            if JSON_MODE:
                print(json.dumps({"ok": True, "id": task_id, "task": task_to_dict(updated)},
                                 default=str, ensure_ascii=False, indent=2))
            else:
                ok(f"Tarefa #{task_id} atualizada ({', '.join(fields.keys())}).")
                render_board()
        else:
            if JSON_MODE:
                print(json.dumps({"ok": False, "error": f"Tarefa #{task_id} não encontrada."}))
            else:
                err(f"Tarefa #{task_id} não encontrada.")

    elif cmd == "list":
        flags = _parse_flags(args[1:])
        status  = flags.get("status")
        tag     = flags.get("tag")
        include_hidden = "hidden" in flags

        project_id = None
        if "project" in flags:
            project_id = _resolve_project(flags["project"])
            if project_id is None:
                return

        tasks = get_tasks_filtered(status=status, project_id=project_id,
                                   tag=tag, include_hidden=include_hidden)
        if JSON_MODE:
            print(json.dumps([task_to_dict(t) for t in tasks], default=str, ensure_ascii=False, indent=2))
        else:
            if not tasks:
                print(f"\n  {GRAY}Nenhuma tarefa encontrada.{RESET}\n")
            else:
                cmd_show_all(tasks)

    elif cmd == "query":
        cmd_query(args[1:], json_mode=JSON_MODE)

    elif cmd == "sql":
        if len(args) < 2:
            err('Uso: taskflow sql "SELECT ..."')
            return
        cmd_sql(" ".join(args[1:]), json_mode=JSON_MODE)

    elif cmd == "approve":
        _handle_approve(args, JSON_MODE)

    elif cmd == "plans":
        if len(args) < 2:
            _handle_plans_list({}, JSON_MODE)
            return
        sub = args[1].lower()
        if sub == "show":
            if len(args) < 3:
                err("Uso: taskflow plans show <id>")
            else:
                _handle_plans_show(int(args[2]), JSON_MODE)
        elif sub == "rm":
            if len(args) < 3:
                err("Uso: taskflow plans rm <id>")
            else:
                _handle_plans_rm(int(args[2]), JSON_MODE)
        else:
            flags = _parse_flags(args[1:])
            _handle_plans_list(flags, JSON_MODE)

    else:
        err(f'Comando desconhecido: "{cmd}"')
        help_text()


if __name__ == "__main__":
    main()
