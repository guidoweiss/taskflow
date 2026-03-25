---
name: taskflow
description: Sistema de gestão de tarefas pessoal. Use para criar, editar, mover e gerenciar tasks. Ativado quando usuário menciona tarefas, backlog, prioridades, lembretes, etc.
---

# Skill: taskflow

## Quando usar

Use esta skill **obrigatoriamente** sempre que o usuário:
- Mencionar **tarefa**, **task**, **to do**, **backlog**, **board**, **prioridade**
- Pedir para **lembrar**, **me lembre**, **lembrete**, **reminder**, **não esquecer**
- Pedir para **criar**, **adicionar**, **registrar**, **anotar** algo para fazer
- Quiser **listar**, **ver**, **mostrar** tarefas ou o board
- Quiser **mover**, **marcar como feito**, **remover** uma tarefa
- Mencionar **projetos** no contexto de gestão de trabalho

**NUNCA usar o TaskCreate nativo do Claude** — o taskflow é o único sistema de tarefas do usuário.

O executor correto é sempre: `taskflow` (disponível no PATH via `~/.local/bin/taskflow`)

## Sobre o taskflow
- **Código-fonte:** `~/.claude/skills/taskflow/taskflow.py`
- **Banco de dados:** `~/.local/share/taskflow/taskflow.db` (SQLite, fora do repo)
- **Executável:** `~/.local/bin/taskflow` (wrapper bash que chama o .py)
- **Comando:** `taskflow` (já no PATH)
- **GUI (opcional):** `~/.claude/skills/taskflow/taskflow-gui/` — interface gráfica com Tauri

## Como Claude deve operar

Claude tem autonomia total para ler e modificar o banco taskflow diretamente usando suas ferramentas (Bash, Read, Edit). Não precisa pedir confirmação para operações de rotina como adicionar, mover ou taguear tarefas.

---

## Output JSON — flag global `--json`

**Todos os comandos de leitura e mutação aceitam `--json`** — adicionar em qualquer posição nos args.

```bash
# Leitura estruturada (sem parsear ANSI)
taskflow context --json          # resumo completo do estado — PREFERIR para obter visão geral
taskflow show <id> --json        # task individual completa
taskflow show all --json         # todas as tasks pessoais
taskflow search "termo" --json   # busca com output limpo
taskflow list --json             # listagem com filtros (ver seção abaixo)
taskflow agent show <id> --json
taskflow agent list --json

# Mutações — retornam {"ok": true, "id": N, "task": {...}}
taskflow add "..." --json
taskflow update <id> --json
```

**Padrão de erro:** `{"ok": false, "error": "mensagem"}`

---

## Acesso SQL direto — `taskflow query` e `taskflow sql`

```bash
# Consulta filtrada (com filtros CLI)
taskflow query --status todo --project Driagenda --limit 20
taskflow query --tag bug --priority alta --json
taskflow query --due-soon 7 --search "login"

# SQL direto (formato tabular, cor)
taskflow sql "SELECT id, title, status FROM tasks LIMIT 10"
taskflow sql "SELECT COUNT(*) FROM tasks WHERE status = 'done'"

# SQL direto (formato JSON)
taskflow sql "SELECT id, title FROM tasks LIMIT 5" --json
```

- `query`: filtros CLI + JSON. Ideal para IAs e automação.
- `sql`: SQL direto com SELECT. Saída colorida tabular ou JSON com `--json`.
- Ambos aceitam apenas SELECT (segurança básica contra SQL injection).

---

## Referência de comandos

### Visualização
```bash
taskflow                          # Lista focada (TO DO → BACKLOG → DONE) — view padrão
taskflow board                    # Board kanban (3 colunas: BACKLOG/TO DO/DONE)
taskflow tui                      # Menu interativo completo (curses)
taskflow mini                     # Board compacto — só IDs e títulos
taskflow agent                    # Board de agente (PENDING/RUNNING/DONE/FAILED/CANCELLED)
taskflow context                  # Resumo estruturado texto (sem ANSI)
taskflow context --json           # Resumo completo JSON — PREFERIR para Claude ler
# GUI (opcional): ~/.claude/skills/taskflow/taskflow-gui/src-tauri/target/release/taskflow-gui
```

### Tasks pessoais
```bash
# Criação — todos os campos opcionais inline (preferir sempre este formato)
taskflow add "título" \
  --desc "..."              # descrição
  --tag "tag"               # tag da tarefa
  --project id|nome         # vincula ao projeto (aceita ID numérico ou nome)
  --link "..."              # link de referência
  --plan "passo 1\npasso 2" # plano de execução
  --priority alta|media|baixa
  --status todo|backlog|done  # status inicial (padrão: backlog)
  --due YYYY-MM-DD          # prazo

taskflow todo <id> [<id2> <id3> ...]   # múltiplos IDs suportados
taskflow done <id> [<id2> <id3> ...]
taskflow back <id> [<id2> <id3> ...]
taskflow show <id>
taskflow show all
taskflow rm <id>
taskflow hide <id>
taskflow unhide <id>
taskflow hidden
taskflow filter <tag>
taskflow search "termo"
```

### Edição em batch — `taskflow update` (PREFERIR sobre `edit` para múltiplos campos)
```bash
# Atualiza múltiplos campos em um único comando
taskflow update <id> \
  --title "novo título" \
  --desc "nova desc" \
  --priority alta|media|baixa \
  --due YYYY-MM-DD \         # ou --due clear para remover
  --plan "passo 1\npasso 2" \
  --link "https://..." \
  --tag "tag" \
  --project id|nome \
  --status todo|backlog|done

# Exemplos
taskflow update 42 --priority alta --due 2026-04-01 --plan "1. X\n2. Y"
taskflow update 42 --status todo --desc "nova descrição"
```

### Edição de campo único (quando só 1 campo mudar)
```bash
taskflow edit <id> title "valor"
taskflow edit <id> desc "valor"
taskflow edit <id> priority alta|media|baixa
taskflow edit <id> due YYYY-MM-DD   (due clear para remover)
taskflow edit <id> link "https://..."
taskflow edit <id> plan "passo 1\npasso 2"
taskflow tag <id> "tag"
```

### Listagem com filtros — `taskflow list`
```bash
# Filtros combinados (todos opcionais)
taskflow list \
  --status todo|backlog|done \
  --project id|nome \
  --tag "tag" \
  --hidden           # inclui tasks ocultas

# Exemplos
taskflow list --status todo --project Driagenda --json
taskflow list --tag bug --json
taskflow list --status backlog --project 3
```

### Projetos
```bash
taskflow project add "nome" ["desc"]
taskflow project list
taskflow project list all
taskflow project show <id>
taskflow project edit <id> name|desc "valor"
taskflow project star <id>
taskflow project unstar <id>
taskflow project archive <id>
taskflow project rm <id>
taskflow assign <task_id> <project_id>
taskflow unassign <task_id>
```

### Relações (fila encadeada)
```bash
taskflow continue <id> "título"   # Cria task que só aparece quando <id> estiver done
taskflow link <id> <from_id>      # Liga tasks existentes
taskflow unlink <id> <from_id>
```

### Agent tasks
```bash
# Criação — desc, tag e project opcionais inline
taskflow agent add "título" "action prompt" "YYYY-MM-DD HH:MM" \
  --desc "..."        # descrição
  --tag "tag"         # tag da task
  --project id|name   # vincula ao projeto

taskflow agent show <id>
taskflow agent list
taskflow agent cancel <id>
taskflow agent rm <id>
taskflow agent retry <id> [YYYY-MM-DD HH:MM]   # reagenda task 'failed' para 'pending'
```

### Planos Aprovados
```bash
# Aprovar plano de uma task existente — CRIA subtasks automaticamente
taskflow approve <task_id> [--importance backend|frontend|structural|other]

# Criar plano aprovado sem task vinculada
taskflow approve --title "título" --plan "passo 1\npasso 2" \
  [--project id|name] [--importance ...] [--priority alta|media|baixa]

# Listar planos aprovados
taskflow plans [--project id] [--importance ...] [--priority ...] [--since YYYY-MM-DD]

# Ver detalhes de um plano
taskflow plans show <id>

# Remover plano da lista
taskflow plans rm <id>
```

**Fluxo de aprovação:**
1. Task com plano é criada pelo agente
2. Ao aprovar (`taskflow approve <task_id>`):
   - O plano é salvo na tabela `approved_plans`
   - Cada passo do plano vira uma **subtask** vinculada
   - As subtasks herdam projeto e prioridade da task original
   - Tasks são encadeadas via relação "continua de"

**Importance levels:**
- `backend` — APIs, banco de dados, migrations, infraestrutura
- `frontend` — UI, componentes, layouts, páginas
- `structural` — arquitetura, refatoração, pipelines, setup
- `other` — quando não se encaixa nas anteriores

Se `--importance` não for fornecido, o sistema decide automaticamente baseado no conteúdo do plano.

---

## Separação entre tasks pessoais e agent tasks

- `taskflow show <id>` → apenas tasks pessoais. Para agent tasks: `taskflow agent show <id>`
- `taskflow rm <id>` → apenas tasks pessoais. Para agent tasks: `taskflow agent rm <id>`
- `taskflow show all` → lista apenas tasks pessoais (is_agent = 0)
- `taskflow agent` (sem args) → board do agente
- `taskflow agent cancel <id>` → só funciona em agent tasks

---

## Comportamentos automáticos (importantes)

- Tasks com `due_date` → promovidas automaticamente para **TO DO** ao abrir o taskflow
- Tasks no backlog sem atividade há **14 dias** → ocultadas automaticamente
- Tasks com relação de continuação → **bloqueadas** no board até a origem estar `done`
- Board pessoal **não mostra** agent tasks (tasks com `action` preenchido)
- Board de agente **só mostra** agent tasks

---

## Estrutura do banco

```sql
tasks (id, title, description, tags, status, priority, due_date, hidden, link, plan,
       project_id, scheduled_at, action, action_status, action_result, recurrence,
       created_at, updated_at)

projects (id, name, description, status, starred, created_at, updated_at)

task_relations (from_task_id, to_task_id, type)

approved_plans (id, task_id, project_id, project_path, title, plan, priority,
                importance_level, approved_at, task_status, link, created_at, updated_at)
```

### action_status (agent tasks)

```
PENDING → RUNNING → DONE      (Claude reportou STATUS: done no marcador)
                  → FAILED    (falha lógica, técnica, timeout ou marcador ausente)
         (manual) → CANCELLED
```

- **done** = Claude executou e reportou `STATUS: done` no marcador estruturado
- **failed** = qualquer falha — Claude reportou `STATUS: failed`, crash, timeout, ou não incluiu o marcador
- **cancelled** = cancelado manualmente com `taskflow agent cancel <id>`

Tasks em `FAILED` ficam paradas indefinidamente. Sem retry automático.

### Como o agente executa

O agente envia ao Claude um **prompt enriquecido** (não o `action` cru) que inclui contexto da task e instrução obrigatória de terminar com:

```
---TASKFLOW_RESULT---
STATUS: done|failed
SUMMARY: descrição do resultado
```

O `SUMMARY` é guardado em `action_result` e visível em `taskflow agent list`.

---

## Comportamento esperado de Claude

1. Quando o usuário disser "adiciona X" → executar `add` com todas as flags disponíveis em um único comando e mostrar o board
2. Quando o usuário disser "move X para to do / done" → executar e mostrar o board (múltiplos IDs: `taskflow done 1 2 3`)
3. Quando o usuário pedir o board → mostrar output do comando
4. Após qualquer operação, sempre mostrar o board atualizado
5. IDs são numéricos crescentes e nunca se repetem — referenciar sempre pelo ID
6. Ao criar tasks, usar `--project nome` inline no `add` — nunca chamar `assign` separado para tasks recém-criadas
7. Ao adicionar tasks que são claramente continuação de outras, usar `continue` em vez de `add`
8. **Usar `taskflow update` para editar múltiplos campos** — nunca encadear vários `edit` para a mesma task
9. Para obter visão geral do estado: `taskflow context --json` (JSON completo, sem truncamento)
10. Para queries não cobertas pela CLI: `taskflow query "SELECT ..."` (sempre retorna JSON)

---

## Fluxo guiado de criação de tasks

Quando o usuário quiser criar uma task (mesmo que forneça apenas o título), Claude deve **guiar ativamente a criação** perguntando pelos campos em falta — mas de forma inteligente, não mecânica.

### Campos obrigatórios (sempre preencher)
- **Título** — claro e no imperativo (ex: "Ajustar IA de atendimento")
- **Descrição** — contexto suficiente para entender o que fazer e por quê
- **Plano** — passo a passo gerado automaticamente por Claude. Sempre criar, mesmo que genérico.

### Campos opcionais (perguntar se não foram informados)
- **Projeto** — listar os projetos disponíveis se o usuário não souber
- **Data de vencimento** — perguntar se tem prazo
- **Prioridade** — alta / média / baixa
- **Link** — caminho local ou URL de referência
- **Tags** — para facilitar filtros futuros
- **Continuação de outra task** — perguntar se depende de uma task anterior

### Regras do fluxo

1. Se o usuário fornecer título + informações suficientes → criar direto em **um único comando** com todas as flags disponíveis, e perguntar apenas o que estiver claramente faltando
2. Se o usuário disser só "quero criar uma task" ou algo vago → perguntar pelo título e descrição primeiro, depois os opcionais
3. **Nunca fazer mais de 2 perguntas de uma vez** — agrupar campos relacionados
4. Após criar, mostrar o `taskflow show <id>` para confirmar o resultado
5. Se o usuário disser "não" ou "não sei" para um campo opcional → seguir sem ele, sem insistir

### Criação em comando único (preferido)

Sempre que possível, consolidar tudo em um único `add` com flags em vez de múltiplos comandos separados:

```bash
# ✅ Preferido — criação completa em um comando
taskflow add "Implementar autenticação" \
  --desc "Adicionar login com JWT no backend" \
  --tag "Driagenda" \
  --project Driagenda \
  --plan "1. Criar rota /auth\n2. Implementar JWT\n3. Testar" \
  --priority alta \
  --due 2026-03-28

# ❌ Evitar — múltiplos comandos para o que pode ser feito inline
taskflow add "Implementar autenticação"
taskflow tag <id> "Driagenda"
taskflow assign <id> 3
taskflow edit <id> plan "..."
```

Usar `taskflow edit` ou `taskflow tag` apenas para **editar** campos de tasks já existentes.
