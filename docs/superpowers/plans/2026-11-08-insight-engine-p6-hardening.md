# Insight Engine · P6 Endurecimento — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA — use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para executar este plano tarefa a tarefa. Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** fechar o SDD (§11, P6; §12) com o que mede e protege o sistema:
- **backup:** cópia consistente do SQLite (API de backup do `sqlite3`), com rotação, mais o export JSON/CSV. O Neo4j é espelho e se reconstrói com `sotawhat graph sync --rebuild` (D16), então não precisa de dump;
- **avaliações:**
  - triagem contra os votos (precisão por seção, matriz de confusão);
  - extração contra uma amostra anotada à mão (o mesmo fluxo do golden set: rascunho em Markdown, você corrige, `import` calcula a precisão);
  - ideação pelo ledger: taxa "vale explorar" por lente, amostrador e modelo gerador;
- **relatório de metas** G1–G4 (`sotawhat eval report`), em Markdown e no Telegram uma vez por mês;
- **calibração:** com votos suficientes, sugere limiares da rubrica de triagem e pesos da rubrica de ideias. Sem votos suficientes, diz quantos faltam e não muda nada;
- **interface:** a aba Hoje (o último digest com os votos) e o status dos runs;
- **documentação final** e SDD com o status de todas as fases.

**Contexto:** última fase do pedido "direto até o final". Branch `feature/insight-engine-p6`, a partir do `master` com a P5.

**Decisões:**
- **Nada muda sozinho.** A calibração escreve uma proposta (`data/calibration/AAAA-MM-DD.md`) e só aplica com `--apply`, como o bake-off da P1.
- **Mínimos de dados:** 100 votos por perfil (o mesmo do classificador) para a triagem, 40 itens anotados para a extração e 30 decisões de ideias para os pesos.
- **Backup:**
  - `data/backups/insight-AAAAMMDD.db`, guardando os 8 mais recentes;
  - roda no fim do `run weekly`, e `sotawhat backup` roda na hora;
  - o `doctor` avisa se o último backup tem mais de 8 dias.

---

## Tarefa 0: Branch, plano e linha de base
## Tarefa 1: Backup e restauração (`sotawhat backup [--restore ARQUIVO]`), com rotação e checagem de integridade
## Tarefa 2: `sotawhat eval triage`, precisão por votos e matriz de confusão
## Tarefa 3: `sotawhat eval extract draft|import`, amostra anotada e precisão de entidades e relações
## Tarefa 4: `sotawhat eval ideas`, taxa "vale explorar" por lente, amostrador e modelo
## Tarefa 5: `sotawhat eval report` (G1–G4) e envio mensal
## Tarefa 6: `sotawhat calibrate [--apply]`, proposta de limiares e pesos com mínimos de dados
## Tarefa 7: Interface: aba Hoje e status dos runs
## Tarefa 8: `doctor`, documentação final e SDD v2.0
## Tarefa 9: Verificação real, adendo, merge e push

## Adendo: execução (2026-11-08)

Executada na branch `feature/insight-engine-p6`, logo depois da P5. Cada tarefa começou pelos testes. As medições e o reparo rodaram também no banco real.

| Tarefa | Commit | Suíte |
|---|---|---|
| 0 · Plano | `53d30bb` | 311 |
| 1 · Backup e restauração | `14f4d76` | 315 |
| 2–6 · Avaliações (triagem, extração, ideias), relatório das metas, calibração | `195de81` | 321 |
| 7 · Aba Hoje | `03d68e4` | 323 |
| 7 · Correção: `sotawhat repair cjk` | `2f01191` | 324 |
| 5 · Metas no run semanal (envio mensal) | `ea41600` | 325 |
| 8–9 · Documentação, SDD v2.0 e adendo | este commit | 325 |

### Mudanças além do plano
- **`sotawhat repair cjk`.** A aba Hoje mostrou tokens chineses nos resumos ("orientar和质量 improvement"). Eram 17 itens triados pelo MiniMax no run da manhã de 2026-11-08, antes do validador da P1. O reparo pede só os textos ao modelo atual e mantém decisão, notas e total, para que nada seja reenviado. O `doctor` aponta textos assim.
- **Backup num arquivo só.** A cópia herdava o modo WAL do banco e deixava arquivos `-wal`/`-shm` ao lado. Agora ela é gravada com journal DELETE, e a rotação apaga os companheiros.
- **Aba Hoje.** Mostra o último digest de verdade: um run sem triagem (`--no-llm`) é pulado, com aviso.
- **Calibração.** Os cortes da triagem só podem subir: só itens entregues recebem voto, então não há como saber o que se perderia abaixo do corte. Baixar um corte continua sendo trabalho do golden set (`eval models`).

### Tarefa 9: resultados (banco real)
1. **`sotawhat backup`:** 4,8 MB, integridade ok, arquivo único em `data/backups/` (pasta ignorada pelo git). O `doctor` mostra o backup de hoje.
2. **`sotawhat eval report`:**
   - G1: 100% de 3 runs diários;
   - G2: máx. 10 + 5 itens e 4 no radar; precisão de 100% em 19 votos ("poucos dados");
   - G3: grafo de 30 dias em 21 ms e busca em 3 ms; a extração ainda depende da anotação;
   - G4: nenhuma ideia decidida;
   - o Semantic Scholar aparece com 3 falhas seguidas (429, sem chave);
   - custo de LLM no mês: US$ 0,27.
3. **`sotawhat calibrate`:** "faltam 81 votos" e "faltam 30 finalistas decididas"; nada foi alterado.
4. **`sotawhat repair cjk`:** 17 corrigidos, nenhum restante e nenhuma decisão alterada, por ≈ US$ 0,007.
5. **Interface:** a aba Hoje, conferida no Chrome, mostra o digest com os votos e os últimos runs.
