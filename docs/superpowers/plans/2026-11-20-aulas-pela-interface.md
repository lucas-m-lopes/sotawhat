# Plano — Aulas pela interface (F1)

**Design:** `docs/superpowers/specs/2026-11-20-aulas-pela-interface-design.md` · **Branch:** `feat/aulas-gui`

Cada tarefa: teste primeiro, depois o código, e a suíte inteira verde antes do commit.

## 1. Estado das tarefas (schema 8)

- `store/db.py`: `_SCHEMA_V8` com `lesson_jobs`; `SCHEMA_VERSION = 8`.
- `lessons/jobs.py`:
  - `Tracker`: `claim()`, adoção por token, `Busy` e `JobGone`, `beat()` com uma thread, `attach`, `expect`,
    `stage`, `log` (guarda a última linha) e `finish`;
  - `live`, `current`, `last_for`, `payload`;
  - `create_pending` (a interface) e `mark_cancelled`;
  - tarefa sem batimento: `interrompida`, com o run da aula fechado.
- Testes (`tests/test_lesson_jobs.py`), com relógio injetado e sem thread:
  - pedido e recusa;
  - adoção pelo token e token que sumiu;
  - tarefa sem batimento: não bloqueia e é marcada;
  - etapas e tempos;
  - motivo da falha;
  - cancelamento: o batimento não revive a tarefa.

## 2. Processos

- `jobs.spawn_process(args, log_path, cwd)`:
  - `python.exe` ao lado do `pythonw.exe`;
  - `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB`, e sem o último se o job recusar;
  - `PYTHONIOENCODING=utf-8` e `PYTHONUNBUFFERED=1`;
  - fora do Windows, `start_new_session`.
- `jobs.kill_tree(pid)`: `taskkill /T /F` e espera o processo sumir (`WaitForSingleObject`); fora do Windows,
  `killpg`.
- `jobs.tail(path, n)`.
- Teste: `tail` e a montagem do comando, com `Popen` falso.

## 3. Motor

- `run_motion_lesson(..., until=None, progress=None)`:
  - `attach`, `expect` e `stage` em cada etapa;
  - `until="roteiro"` para depois do roteiro: grava `llm_usd`, fecha o run e pula as checagens de produção;
  - `report["mode"]`.
- `engine_of`: aula sem roteiro e sem motor → HyperFrames.
- Testes no `engine` de `test_lessons_motion.py`:
  - só o roteiro;
  - as etapas de uma produção, com 3D e envio;
  - `engine_of`.

## 4. CLI

- `--so-roteiro` e `--job` (oculto).
- `make`, `resume`, `hf` e `send` registram a tarefa; com outra viva, o comando recusa (código 2).
- Testes: os argumentos chegam ao motor; a recusa.

## 5. Sugestões, créditos e estimativa

- `pack.suggest_topics`; `pick_topic` usa a primeira; `taught_entities` ignora `descartada`.
- `eleven.ElevenLabs.subscription()` e `eleven.credit_balance(key)`.
- `lessons/estimate.py`.
- Testes de cada um.

## 6. Web

- `Launcher`: spawn, kill, créditos (60 s de cache), prontidão, cwd e raiz das aulas. `main_serve` o constrói.
- Rotas:
  - `GET /api/lessons/state`;
  - `GET /api/lessons` sem descartadas;
  - `POST /api/lessons`;
  - `POST /api/lessons/{id}/plan`, `/produce`, `/send`, `/cancel` e `/discard`.
- `lesson_payload`: `has_plan`, `delivered_at`, `mode`, `job` e, na revisão, `estimate`.
- Testes com lançador falso:
  - os argumentos;
  - 409, 422, 403, 415 e 503;
  - a lista;
  - o estado.

## 7. Página

- Renomear as classes do compositor (`.ask-form` → `.composer`, e assim por diante), porque agora servem a duas
  telas.
- Aulas:
  - leituras;
  - compositor com busca de entidades e modelos;
  - sugestões;
  - cards por estado;
  - etapas;
  - consulta a cada 2,5 s;
  - botões de dois toques.
- Teste da página: os elementos e as rotas no `app.js`.

## 8. De verdade

- Leitura dos créditos.
- Um roteiro pela interface, com reinício da tarefa `sotawhat-web` no meio: a tarefa precisa sobreviver.
- Um cancelamento.
- A tela de produção desenhada com uma tarefa simulada no navegador.
- Nenhuma voz e nenhum envio.

## 9. Documentação

- README (aba Aulas).
- SDD v3.0.
- Memória.
