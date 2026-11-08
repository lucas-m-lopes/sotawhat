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
