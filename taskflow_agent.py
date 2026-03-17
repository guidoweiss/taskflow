#!/usr/bin/env python3
"""
taskflow_agent.py
Executa agent tasks agendadas no taskflow via `claude -p`.
Deve ser chamado pelo cron a cada 5 minutos.
"""

import subprocess
import sys
import os
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


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def run_task(task) -> tuple[bool, str]:
    """
    Invoca `claude -p "{action}"` e retorna (sucesso, output).
    """
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", task["action"]],
            capture_output=True,
            text=True,
            timeout=TASK_TIMEOUT,
            cwd=os.path.expanduser("~"),
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip() or f"Exit code {result.returncode}"
            return False, f"ERRO: {error}\n{output}".strip()
        return True, output
    except subprocess.TimeoutExpired:
        return False, f"ERRO: timeout após {TASK_TIMEOUT}s"
    except Exception as e:
        return False, f"ERRO: {e}"


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

        success, output = run_task(task)

        if success:
            update_action_status(task["id"], "done", output)
            move_task(task["id"], "done")
            log(f"Task #{task['id']} concluída.")
        else:
            update_action_status(task["id"], "failed", output)
            log(f"Task #{task['id']} falhou. {output[:100]}")


if __name__ == "__main__":
    main()
