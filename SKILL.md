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

O executor correto é sempre: `python3 ~/.claude/tools/taskflow/taskflow.py`

## Sobre o taskflow
- **Localização:** `~/.claude/tools/taskflow/`
- **Banco de dados:** `~/.claude/tools/taskflow/taskflow.db` (SQLite)
- **Executor:** `python3 ~/.claude/tools/taskflow/taskflow.py`
- **Alias no shell:** `taskflow` (após `source ~/.bashrc`)

## Como Claude deve operar

Claude tem autonomia total para ler e modificar o banco taskflow diretamente usando suas ferramentas (Bash, Read, Edit). Não precisa pedir confirmação para operações de rotina como adicionar, mover ou taguear tarefas.

---

## Referência de comandos

### Board
```bash
taskflow                          # Board kanban pessoal (BACKLOG/TODO/DONE)
taskflow tui                      # Menu interativo completo (curses)
taskflow mini                     # Board compacto — só IDs e títulos
taskflow agent                    # Board de agente (PENDING/RUNNING/DONE/FAILED/CANCELLED)
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
  --due YYYY-MM-DD          # prazo

taskflow todo <id>
taskflow done <id>
taskflow back <id>
taskflow show <id>
taskflow show all
taskflow rm <id>
taskflow hide <id>
taskflow unhide <id>
taskflow hidden
taskflow filter <tag>
taskflow search "termo"
```

### Edição (campos individuais após criação)
```bash
taskflow edit <id> title "valor"
taskflow edit <id> desc "valor"
taskflow edit <id> priority alta|media|baixa
taskflow edit <id> due YYYY-MM-DD
taskflow edit <id> due clear
taskflow edit <id> link "https://..."
taskflow edit <id> plan "passo 1\npasso 2"
taskflow tag <id> "tag"
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
  --project id|nome   # vincula ao projeto

taskflow agent show <id>
taskflow agent list
taskflow agent cancel <id>
taskflow agent rm <id>
```

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
2. Quando o usuário disser "move X para to do / done" → executar e mostrar o board
3. Quando o usuário pedir o board → mostrar output do comando
4. Após qualquer operação, sempre mostrar o board atualizado
5. IDs são numéricos crescentes e nunca se repetem — referenciar sempre pelo ID
6. Ao criar tasks, usar `--project nome` inline no `add` — nunca chamar `assign` separado para tasks recém-criadas
7. Ao adicionar tasks que são claramente continuação de outras, usar `continue` em vez de `add`
8. Usar `taskflow edit` e `taskflow tag` apenas para **editar** tasks já existentes, nunca como passo de criação

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
