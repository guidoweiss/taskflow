# taskflow

Gerenciador de tarefas pessoal no terminal com suporte a projetos, relações entre tasks, agendamento e execução autônoma via Claude Code.

---

## Funcionalidades

- Board kanban no terminal (BACKLOG / TO DO / DONE)
- **Menu interativo TUI** (`taskflow tui`) — navegação completa com teclado
- **Interface gráfica GUI** (Tauri) — visualização e gestão com mouse
- Projetos com marcação de favoritos
- Relações entre tasks com desbloqueio automático (fila encadeada)
- Promoção automática para TO DO quando há prazo definido
- Board compacto (`mini`)
- **Agent tasks** — tasks agendadas executadas automaticamente pelo Claude Code
- **Skill para Claude Code** — o Claude usa o taskflow automaticamente ao conversar
- **Consulta SQL direta** — acesso ao banco com queries `SELECT` em formato tabular ou JSON

---

## Requisitos

| Componente | Versão mínima |
|---|---|
| Python | 3.10+ |
| SQLite | incluído no Python |
| Claude Code CLI | qualquer versão recente (opcional, para a skill) |

---

## Instalação

### Linux / macOS

```bash
# 1. Clonar em ~/.claude/skills/taskflow (recomendado — ativa a skill automaticamente)
git clone https://github.com/guidoweiss/taskflow.git ~/.claude/skills/taskflow

# 2. Inicializar o banco de dados (criado em ~/.local/share/taskflow/taskflow.db)
python3 ~/.claude/skills/taskflow/taskflow.py

# 3. Criar executável global
echo '#!/bin/bash' > ~/.local/bin/taskflow
echo 'python3 ~/.claude/skills/taskflow/taskflow.py "$@"' >> ~/.local/bin/taskflow
chmod +x ~/.local/bin/taskflow

# Ou adicionar alias no shell
echo 'alias taskflow="python3 ~/.claude/skills/taskflow/taskflow.py"' >> ~/.bashrc
source ~/.bashrc
```

> **Nota:** O banco de dados fica em `~/.local/share/taskflow/taskflow.db` — fora do repositório e não versionado.

### Interface Gráfica (GUI)

Opcionalmente, você pode usar a interface gráfica Tauri:

```bash
# Entrar no diretório do projeto
cd ~/.claude/skills/taskflow/taskflow-gui

# Build (requer Rust e Node.js)
npm install && npm run tauri build

# Executar
./src-tauri/target/release/taskflow-gui
```

A GUI exibe o kanban em 3 colunas, atualiza automaticamente e permite visualizar todas as tasks.

**Requisitos para a GUI:**
- Node.js 18+
- Rust 1.70+
- GTK 3 + WebKit2GTK

### Windows

```powershell
# 1. Clonar o repositório
git clone https://github.com/guidoweiss/taskflow.git "$env:USERPROFILE\.claude\skills\taskflow"

# 2. Inicializar o banco de dados
python "$env:USERPROFILE\.claude\skills\taskflow\taskflow.py"

# 3. Adicionar alias permanente (PowerShell profile)
notepad $PROFILE
# Adicionar a linha:
# function taskflow { python "$env:USERPROFILE\.claude\skills\taskflow\taskflow.py" @args }
```

---

## Integração com Claude Code

O taskflow inclui um arquivo `SKILL.md` que instrui o Claude Code a usar o taskflow automaticamente sempre que o usuário mencionar tarefas, backlog, prioridades, lembretes, etc.

Clonando em `~/.claude/skills/taskflow/`, a skill é carregada automaticamente — nenhuma configuração extra é necessária.

Se clonou em outro diretório, mova para o caminho correto:

```bash
mv /caminho/do/clone ~/.claude/skills/taskflow
```

Com a skill ativa, você pode dizer ao Claude coisas como:

- *"Cria uma task para implementar autenticação no Driagenda com prazo sexta"*
- *"Move a #12 para done"*
- *"Mostra o backlog"*

E o Claude opera o taskflow diretamente, sem precisar de comandos manuais.

---

## Uso básico

```bash
taskflow                          # Mostra o board kanban pessoal
taskflow mini                     # Board compacto (só IDs e títulos)
taskflow add "título da tarefa"   # Adiciona ao backlog
taskflow todo <id>                # Move para To Do
taskflow done <id>                # Move para Done
taskflow back <id>                # Volta ao Backlog
taskflow show <id>                # Detalhes completos de uma task
taskflow show all                 # Lista todas as tasks com detalhes
taskflow rm <id>                  # Remove uma task
```

---

## Criação completa em um comando

O `add` aceita flags opcionais para preencher todos os campos na criação:

```bash
taskflow add "título" \
  --desc "descrição da task" \
  --tag "NomeDoProjeto" \
  --project "NomeDoProjeto" \   # aceita ID numérico ou nome
  --link "/caminho/ou/url" \
  --plan "1. Passo um\n2. Passo dois" \
  --priority alta \             # alta | media | baixa
  --due 2026-04-01              # YYYY-MM-DD
```

Exemplo real:

```bash
taskflow add "Implementar autenticação JWT" \
  --desc "Criar rota /auth com geração e validação de tokens JWT" \
  --tag "Driagenda" \
  --project Driagenda \
  --priority alta \
  --due 2026-03-28
```

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
taskflow tag <id> "tag"
```

> Tasks com `due_date` definida são automaticamente promovidas para **TO DO** ao abrir o taskflow.

---

## Filtros e busca

```bash
taskflow filter <tag>             # Filtra o board por tag
taskflow search "termo"           # Busca em títulos e descrições
```

---

## Consulta SQL direta

Para queries avançadas que os comandos CLI não cobrem:

```bash
# Formato tabular colorizado
taskflow sql "SELECT id, title, status FROM tasks LIMIT 10"

# Formato JSON
taskflow sql "SELECT id, title FROM tasks LIMIT 5" --json
```

> Apenas queries `SELECT` são permitidas (proteção contra modificações acidentais).

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

## Menu interativo (TUI)

```bash
taskflow tui
```

Abre um menu navegável com teclado. Sem dependências externas — usa `curses` da stdlib do Python.

| Tela | Acesso | O que faz |
|---|---|---|
| Menu principal | — | Mostra stats e lista as opções |
| Tasks pessoais | `k` | Kanban navegável: mover, adicionar, remover tasks |
| Agent tasks | `a` | Lista com status, resultado e opção de cancelar |
| Projetos | `p` | Lista projetos; Enter abre detalhes com tasks vinculadas |
| Filtrar por tag | `f` | Pede uma tag e mostra o kanban filtrado |
| Buscar tasks | `s` | Pesquisa por título ou descrição |
| Tasks ocultas | `h` | Lista tasks com `hidden = 1` |

**Atalhos globais:** `↑↓` navegar · `Enter` selecionar · `ESC` voltar ao menu · `q` sair

**Atalhos no kanban:** `←→` mudar coluna · `t/d/b` mover task · `a` adicionar · `x` remover

> **Nota:** `taskflow tui` requer um terminal real (TTY). Não funciona dentro de ambientes sem TTY como pipes ou alguns emuladores de terminal embutidos.

---

## Agent tasks

Tasks executadas automaticamente pelo Claude Code no horário agendado.

```bash
taskflow agent                    # Board de agente (PENDING/RUNNING/DONE/FAILED/CANCELLED)
taskflow agent add "título" "action prompt" "YYYY-MM-DD HH:MM" \
  --desc "descrição opcional" \
  --tag "tag" \
  --project "NomeDoProjeto"
taskflow agent show <id>          # Detalhes de uma agent task
taskflow agent list               # Lista todas as agent tasks
taskflow agent cancel <id>        # Cancela uma task pendente
taskflow agent rm <id>            # Remove uma agent task
```

> `taskflow show <id>` e `taskflow rm <id>` são exclusivos de tasks pessoais e rejeitam agent tasks com mensagem de erro.

### Estados do agente

| Estado | Significado |
|---|---|
| `pending` | Agendada, ainda não executou |
| `running` | Claude está executando agora |
| `done` | Concluída com sucesso |
| `failed` | Claude tentou mas encontrou erro |
| `cancelled` | Cancelada manualmente |

### Configurar o cron (Linux / macOS)

```bash
crontab -e
```

Adicionar a linha:
```
*/5 * * * * python3 ~/.claude/skills/taskflow/taskflow_agent.py >> ~/.local/share/taskflow/agent.log 2>&1
```

### Configurar o agendador (Windows)

Usar o **Agendador de Tarefas do Windows** (Task Scheduler):

1. Abrir `taskschd.msc`
2. Criar tarefa básica
3. Gatilho: repetir a cada 5 minutos
4. Ação: `python %USERPROFILE%\.claude\skills\taskflow\taskflow_agent.py`

### Requisito para agent tasks

O `claude` CLI deve estar instalado e acessível:

```bash
which claude   # deve retornar o caminho
```

### Como o agente executa uma task

O agente constrói um **prompt enriquecido** com contexto da task e instrui o Claude a terminar com um marcador estruturado:

```
---TASKFLOW_RESULT---
STATUS: done
SUMMARY: resumo do que foi feito
```

O `SUMMARY` é guardado em `action_result` e visível em `taskflow agent list`.

### Estados e transições

```
PENDING → RUNNING → DONE      (Claude reportou STATUS: done)
                  → FAILED    (qualquer falha: lógica, técnica, timeout, formato inválido)
         (manual) → CANCELLED
```

Tasks em `FAILED` ficam paradas. Não há retry automático.

### Limites do agente

- Máximo **5 tasks por dia** (configurável em `taskflow_agent.py` via `MAX_PER_DAY`)
- Timeout de **5 minutos** por task (`TASK_TIMEOUT`)
- Log em `~/.local/share/taskflow/agent.log`

---

## Estrutura do projeto

```
~/.claude/skills/taskflow/
├── SKILL.md             # Instruções para o Claude Code (skill)
├── taskflow.py          # CLI principal
├── tasks.py             # Funções de gestão de tasks e projetos
├── db.py                # Conexão e migrações do SQLite
├── board.py             # Renderização do kanban no terminal
├── tui.py               # Menu interativo completo (curses)
├── taskflow_agent.py    # Daemon de execução de agent tasks
├── taskflow-gui/        # Interface gráfica (Tauri + React)
│   ├── src/             # Frontend React
│   └── src-tauri/        # Backend Rust
└── README.md            # Este arquivo

~/.local/share/taskflow/
├── taskflow.db          # Banco de dados SQLite (gerado automaticamente)
└── agent.log            # Log de execuções do agente (gerado automaticamente)
```

---

## Schema do banco de dados

```sql
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
    scheduled_at  TEXT    DEFAULT NULL,
    action        TEXT    DEFAULT NULL,
    action_status TEXT    DEFAULT NULL,       -- pending | running | done | failed | cancelled
    action_result TEXT    DEFAULT NULL,
    recurrence    TEXT    DEFAULT NULL,
    is_agent      INTEGER DEFAULT 0,
    created_at    TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    status      TEXT    DEFAULT 'active',     -- active | archived
    starred     INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

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
