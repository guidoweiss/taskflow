# taskflow

Gerenciador de tarefas pessoal no terminal com suporte a projetos, relações entre tasks, agendamento e execução autónoma via Claude Code.

---

## Funcionalidades

- Board kanban no terminal (BACKLOG / TO DO / DONE)
- Projetos com marcação de favoritos
- Relações entre tasks com desbloqueio automático (fila encadeada)
- Promoção automática para TO DO quando há prazo definido
- Board compacto (`mini`)
- **Agent tasks** — tasks agendadas executadas automaticamente pelo Claude Code

---

## Requisitos

| Componente | Versão mínima |
|---|---|
| Python | 3.10+ |
| SQLite | incluído no Python |
| Claude Code CLI | qualquer versão recente |

---

## Instalação

### Linux / macOS

```bash
# 1. Clonar o repositório
git clone https://github.com/guidoweiss/taskflow.git ~/Projetos/.pessoal/taskflow
cd ~/Projetos/.pessoal/taskflow

# 2. Inicializar o banco de dados
python3 taskflow.py

# 3. Adicionar alias no shell (bash ou zsh)
echo 'alias taskflow="python3 ~/Projetos/.pessoal/taskflow/taskflow.py"' >> ~/.bashrc
source ~/.bashrc
# Para zsh:
# echo 'alias taskflow="python3 ~/Projetos/.pessoal/taskflow/taskflow.py"' >> ~/.zshrc
```

### Windows

```powershell
# 1. Clonar o repositório
git clone https://github.com/guidoweiss/taskflow.git "$env:USERPROFILE\Projetos\taskflow"
cd "$env:USERPROFILE\Projetos\taskflow"

# 2. Inicializar o banco de dados
python taskflow.py

# 3. Adicionar alias permanente (PowerShell profile)
notepad $PROFILE
# Adicionar a linha:
# function taskflow { python "$env:USERPROFILE\Projetos\taskflow\taskflow.py" @args }
```

---

## Uso básico

```bash
taskflow                          # Mostra o board kanban pessoal
taskflow mini                     # Board compacto (só IDs e títulos)
taskflow add "título da tarefa"   # Adiciona ao backlog
taskflow todo <id>                # Move para To Do
taskflow done <id>                # Move para Done
taskflow back <id>                # Volta ao Backlog
taskflow show <id>                # Detalhes completos de uma task pessoal
taskflow show all                 # Lista todas as tasks pessoais com detalhes
taskflow rm <id>                  # Remove uma task pessoal
```

> `show all` e `rm` funcionam apenas com tasks pessoais. Para agent tasks, use os subcomandos `taskflow agent show <id>` e `taskflow agent rm <id>`.

---

## Edição de tasks

```bash
taskflow edit <id> title "novo título"
taskflow edit <id> desc "descrição"
taskflow edit <id> priority alta|media|baixa
taskflow edit <id> due 2026-04-01       # Define prazo (YYYY-MM-DD)
taskflow edit <id> due clear            # Remove prazo
taskflow edit <id> link "https://..."
taskflow edit <id> plan "passo 1\npasso 2"
taskflow tag <id> "tag1,tag2"
```

> Tasks com `due_date` definida são automaticamente promovidas para **TO DO** ao abrir o taskflow.

---

## Filtros e busca

```bash
taskflow filter <tag>             # Filtra o board por tag
taskflow search "termo"           # Busca em títulos e descrições
```

---

## Ocultar tasks

```bash
taskflow hide <id>                # Oculta manualmente
taskflow unhide <id>              # Traz de volta ao backlog
taskflow hidden                   # Lista tasks ocultas
```

> Tasks sem atividade há 14 dias no backlog são ocultadas automaticamente.

---

## Projetos

```bash
taskflow project add "Nome" ["descrição"]
taskflow project list             # Lista projetos ativos
taskflow project list all         # Inclui arquivados
taskflow project show <id>        # Detalhes + tasks vinculadas
taskflow project edit <id> name|desc "valor"
taskflow project star <id>        # Marca como favorito (aparece no topo)
taskflow project unstar <id>
taskflow project archive <id>
taskflow project rm <id>

taskflow assign <task_id> <project_id>   # Vincula task a projeto
taskflow unassign <task_id>              # Remove vínculo
```

---

## Relações entre tasks (fila encadeada)

Tasks podem ser continuações de outras. Uma task só aparece no board quando todas as suas origens estiverem em **Done**.

```bash
# Criar task que continua de outra (já vinculada)
taskflow continue <id> "título da nova task"

# Ligar tasks existentes
taskflow link <task_id> <from_id>

# Remover relação
taskflow unlink <task_id> <from_id>
```

**Exemplo:**
```bash
taskflow add "Etapa 1"           # cria #1
taskflow continue 1 "Etapa 2"   # cria #2, só aparece quando #1 for Done
taskflow continue 2 "Etapa 3"   # cria #3, só aparece quando #2 for Done
```

---

## Agent tasks

Tasks executadas automaticamente pelo Claude Code no horário agendado.

```bash
taskflow agent                    # Board de agente (PENDING/RUNNING/DONE/FAILED/CANCELLED)
taskflow agent add "título" "action prompt" "YYYY-MM-DD HH:MM"
taskflow agent show <id>          # Detalhes de uma agent task (action, status, resultado)
taskflow agent list               # Lista todas as agent tasks
taskflow agent cancel <id>        # Cancela uma task pendente
taskflow agent rm <id>            # Remove uma agent task
```

> `taskflow show <id>` e `taskflow rm <id>` são exclusivos de tasks pessoais e rejeitam agent tasks com mensagem de erro.

### Estados do agente

| Estado | Significado |
|---|---|
| `pending` | Agendada, ainda não executou |
| `running` | Claude está a executar agora |
| `done` | Concluída com sucesso |
| `failed` | Claude tentou mas encontrou erro |
| `cancelled` | Cancelada manualmente |

### Configurar o cron (Linux / macOS)

```bash
crontab -e
```

Adicionar a linha:
```
*/5 * * * * cd /caminho/para/taskflow && python3 /caminho/para/taskflow/taskflow_agent.py >> /caminho/para/taskflow/agent.log 2>&1
```

### Configurar o agendador (Windows)

Usar o **Agendador de Tarefas do Windows** (Task Scheduler):

1. Abrir `taskschd.msc`
2. Criar tarefa básica
3. Gatilho: repetir a cada 5 minutos
4. Ação: `python C:\caminho\taskflow\taskflow_agent.py`
5. Iniciar em: `C:\caminho\taskflow\`

### Requisito para agent tasks

O `claude` CLI deve estar instalado e acessível:

```bash
# Linux/macOS
which claude   # deve retornar o caminho

# Windows
where claude
```

Se necessário, editar o caminho em `taskflow_agent.py`:
```python
CLAUDE_BIN = "/home/user/.local/bin/claude"  # Linux/macOS
# CLAUDE_BIN = "claude"                       # Windows (se estiver no PATH)
```

### Como o agente executa uma task

O agente não envia apenas o prompt cru ao Claude. Ele constrói um **prompt enriquecido** com contexto da task e instrui o Claude a terminar sempre com um marcador estruturado:

```
---TASKFLOW_RESULT---
STATUS: done
SUMMARY: resume do que foi feito
```

ou, em caso de falha:

```
---TASKFLOW_RESULT---
STATUS: failed
SUMMARY: o que tentou e por que falhou
```

O agente lê este marcador para determinar o status real — não o exit code do processo. O `SUMMARY` é guardado em `action_result` e visível em `taskflow agent list`.

### Estados e transições

```
PENDING → RUNNING → DONE      (Claude reportou STATUS: done)
                  → FAILED    (qualquer falha: lógica, técnica, timeout, formato inválido)
         (manual) → CANCELLED
```

Tasks em `FAILED` ficam paradas. Não há retry automático — o utilizador decide o que fazer.

### Limites do agente

- Máximo **5 tasks por dia** (configurável em `taskflow_agent.py` via `MAX_PER_DAY`)
- Timeout de **5 minutos** por task (`TASK_TIMEOUT`)
- Log completo em `agent.log`

---

## Estrutura do projeto

```
taskflow/
├── taskflow.py          # CLI principal
├── tasks.py             # Funções de gestão de tasks e projetos
├── db.py                # Conexão e migrações do SQLite
├── board.py             # Renderização do kanban no terminal
├── taskflow_agent.py    # Daemon de execução de agent tasks
├── taskflow.db          # Banco de dados SQLite (gerado automaticamente)
└── agent.log            # Log de execuções do agente (gerado automaticamente)
```

---

## Schema do banco de dados

```sql
-- Tasks (pessoais e de agente)
CREATE TABLE tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL,
    description   TEXT    DEFAULT '',
    tags          TEXT    DEFAULT '',
    status        TEXT    DEFAULT 'backlog',  -- backlog | todo | done
    priority      TEXT    DEFAULT '',         -- alta | media | baixa
    due_date      TEXT    DEFAULT '',
    hidden        INTEGER DEFAULT 0,
    link          TEXT    DEFAULT '',
    plan          TEXT    DEFAULT '',
    project_id    INTEGER DEFAULT NULL,
    scheduled_at  TEXT    DEFAULT NULL,       -- agent tasks
    action        TEXT    DEFAULT NULL,       -- prompt para o Claude
    action_status TEXT    DEFAULT NULL,       -- pending | running | done | failed | cancelled
    action_result TEXT    DEFAULT NULL,
    recurrence    TEXT    DEFAULT NULL,
    created_at    TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- Projetos
CREATE TABLE projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    status      TEXT    DEFAULT 'active',     -- active | archived
    starred     INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

-- Relações entre tasks
CREATE TABLE task_relations (
    from_task_id INTEGER NOT NULL,
    to_task_id   INTEGER NOT NULL,
    type         TEXT    DEFAULT 'continues',
    PRIMARY KEY (from_task_id, to_task_id)
);
```

---

## Comportamentos automáticos

| Comportamento | Condição |
|---|---|
| Task promovida para TO DO | `due_date` definida + status `backlog` |
| Task ocultada automaticamente | 14 dias sem atividade no backlog |
| Task bloqueada no board | Tem origem em relação com status != `done` |
| Agent task executada | `scheduled_at <= agora` + `action_status = pending` |

---

## Licença

MIT
