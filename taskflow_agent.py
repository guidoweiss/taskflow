#!/usr/bin/env python3
"""
taskflow_agent.py
Executa agent tasks agendadas no taskflow via `claude -p`.
Deve ser chamado pelo cron a cada 5 minutos.
"""

import subprocess
import sys
import os
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from db import init_db
from tasks import (
    get_due_agent_tasks,
    update_action_status,
    move_task,
    count_agent_done_today,
)

CLAUDE_BIN   = "/home/guidoweiss/.local/bin/claude"
MAX_PER_DAY  = 5
TASK_TIMEOUT = 300  # segundos por task (5 min)

LOG_PATH = os.path.join(os.path.dirname(__file__), "agent.log")

RESULT_MARKER = "---TASKFLOW_RESULT---"

ENRICHED_PROMPT = """\
És um agente a executar uma task agendada do taskflow.

Task ID: #{task_id}
Título: {title}

Instruções:
{action}

---
Executa as instruções acima. Quando terminares, obrigatoriamente termina a tua resposta com o bloco abaixo (sem nada depois):

---TASKFLOW_RESULT---
STATUS: done
SUMMARY: (resume em 1-2 linhas o que foi feito)

Se não conseguires executar a tarefa por qualquer razão, usa:

---TASKFLOW_RESULT---
STATUS: failed
SUMMARY: (explica o que tentaste e por que falhou)
"""


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def parse_result(output: str) -> tuple[str, str]:
    """
    Extrai STATUS e SUMMARY do marcador ---TASKFLOW_RESULT---.
    Retorna (status, summary) onde status é 'done' ou 'failed'.
    Se não encontrar o marcador, assume falha.
    """
    if RESULT_MARKER not in output:
        return "failed", f"Agente não retornou marcador de resultado. Output: {output[:200]}"

    block = output.split(RESULT_MARKER)[-1].strip()

    status_match  = re.search(r"STATUS:\s*(done|failed)", block, re.IGNORECASE)
    summary_match = re.search(r"SUMMARY:\s*(.+)", block, re.IGNORECASE | re.DOTALL)

    status  = status_match.group(1).lower() if status_match else "failed"
    summary = summary_match.group(1).strip() if summary_match else block[:300]

    return status, summary


def run_task(task) -> tuple[str, str]:
    """
    Invoca `claude -p` com prompt enriquecido.
    Retorna (status, summary) onde status é 'done' | 'failed'.
    """
    prompt = ENRICHED_PROMPT.format(
        task_id=task["id"],
        title=task["title"],
        action=task["action"],
    )

    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--dangerously-skip-permissions"],
            capture_output=True,
            text=True,
            timeout=TASK_TIMEOUT,
            cwd=os.path.expanduser("~"),
        )

        if result.returncode != 0:
            error = result.stderr.strip() or f"Exit code {result.returncode}"
            return "failed", f"Erro técnico: {error}"

        return parse_result(result.stdout.strip())

    except subprocess.TimeoutExpired:
        return "failed", f"Timeout após {TASK_TIMEOUT}s"
    except Exception as e:
        return "failed", f"Erro inesperado: {e}"


def main():
    init_db()

    done_today = count_agent_done_today()
    remaining  = MAX_PER_DAY - done_today

    if remaining <= 0:
        log(f"Limite diário atingido ({MAX_PER_DAY} tasks). Nada a executar.")
        return

    due_tasks = get_due_agent_tasks()

    if not due_tasks:
        return  # silêncio se não há nada

    log(f"{len(due_tasks)} task(s) vencida(s). Limite restante hoje: {remaining}.")

    for task in due_tasks[:remaining]:
        log(f"Iniciando task #{task['id']}: {task['title']}")
        update_action_status(task["id"], "running")

        status, summary = run_task(task)

        if status == "done":
            update_action_status(task["id"], "done", summary)
            move_task(task["id"], "done")
            log(f"Task #{task['id']} concluída. {summary[:100]}")
        else:
            update_action_status(task["id"], "failed", summary)
            log(f"Task #{task['id']} falhou. {summary[:100]}")


if __name__ == "__main__":
    main()
