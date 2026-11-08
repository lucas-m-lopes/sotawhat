# Insight Engine · P4 Inteligência + ideação — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA — use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para executar este plano tarefa a tarefa. Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** fazer o grafo da P3 produzir conhecimento e ideias (SDD §6.9 e §8), no **modo econômico** do §8.6:
- **inteligência semanal:** tendências (7 dias × 28 anteriores), comunidades (Louvain), rótulo e resumo de cada comunidade (mapa semanal) e lacunas;
- **pipeline de ideias** (§8.3):
  - amostragem de candidatos técnica × problema, com cotas, controle sem grafo e subgrafo compacto;
  - geração independente por lentes, sempre com a lente negativa;
  - dedup e portfólio por nichos;
  - crítica multipapel com critérios de descarte;
  - prior art em camadas, com matriz de facetas e juízes de famílias diferentes;
  - rubrica com gates duros, dossiê e seleção final de 5–10 ideias;
- **ledger e feedback:** ledger de ideias com versão e status; votos pelo Telegram (👍 explorar · 👎 · 🧪 testar · 🗄️ engavetar) e pela interface; meta-review que transforma as decisões em regras para os prompts;
- **entrega:** relatório semanal (arquivo, Telegram e e-mail), `sotawhat run weekly` agendado para domingo às 20:00, `sotawhat ideate --tema "UTI" --n 10`, e as ideias e tendências também na interface e no MCP.

**Contexto:** fase seguinte à P2, no mesmo pedido do usuário ("direto até o final"). Branch `feature/insight-engine-p4`, a partir do `master` com a P2.

**Decisões:**
- **Algoritmos sobre o SQLite.** Comunidades e caminhos usam NetworkX 3.7, numa projeção das entidades e coocorrências dos últimos 90 dias. Assim o GDS do Neo4j não é necessário, e o espelho continua opcional (D16).
- **Modo econômico** (`config/ideation.yaml`):
  - 20 candidatos, cotas 40/30/30 e 10% sem grafo;
  - 6 lentes por candidato: *tech-push*, JTBD/HMW, SCAMPER, TRIZ, analogia, cenário 2029, mais a negativa;
  - críticas, prior art e juízes nos 12 melhores;
  - 2 juízes de famílias diferentes;
  - 8 finalistas, no máximo 2 por nicho e pelo menos 1 aposta contrária.
  - O modo completo existe na configuração, mas fica desligado.
- **Modelos:** as tarefas `ideate` (geração; rotação DeepSeek V4.1 Flash · GLM-5.3 · MiMo-V2.6-Pro, raciocínio alto), `critique` (crítico sempre de família diferente do gerador), `judge` (dois juízes de famílias diferentes) e `synth` (rótulos do mapa, dossiê e meta-review).
- **Prior art, quatro camadas:**
  - o grafo interno;
  - a literatura: OpenAlex (polite pool) e Semantic Scholar (sem chave, tolerando 429);
  - o código: busca do GitHub;
  - o mercado: Exa, se houver `EXA_API_KEY`.

  Patentes (Lens.org e EPO OPS) ficam como "não verificado" até haver chave, sem bloquear.
- **Orçamento:** o gateway do run semanal usa o teto `SOTAWHAT_LLM_BUDGET_USD_RUN_WEEKLY` (padrão US$ 8). O custo esperado no modo econômico é ≈ US$ 0,8 por semana, e um orçamento estourado encerra a etapa de forma graciosa.

---

## Tarefa 0: Branch, plano e linha de base

## Tarefa 1: Schema 4 (ideias, comunidades, tendências)
- Tabelas:
  - `ideas`: id, version, parent_id, run_id, created_at, status, title, lens, persona, niche, card_json, scores_json, novelty_json, score, embedding;
  - `communities`: run_id, community, label, summary, size e o membro de maior grau;
  - `entity_communities`;
  - `weekly_reports`.
- Votos de ideias em `feedback` com `target_type = 'idea'`; o status da ideia segue o último voto.

## Tarefa 2: Inteligência (tendências, comunidades, lacunas)
- `graph/intelligence.py`:
  - `trends(store, now)`: z-score e velocidade por entidade, 7 dias contra os 28 anteriores, e as entidades novas;
  - `communities(store, now)`: Louvain ponderado, com semente fixa;
  - `gaps(store, now)`: técnicas recentes sem ligação com problemas frequentes, pares de comunidades importantes pouco conectados, caminhos aleatórios entre nós distantes.
- Testes com um grafo sintético no SQLite.

## Tarefa 3: Candidatos e subgrafo compacto
- `ideation/candidates.py`: os três amostradores com cotas, 10% de controle sem grafo, e 20–50 triplas datadas por candidato (relações, coocorrências e títulos dos itens).

## Tarefa 4: Geração por lentes
- Schemas `IdeaDraft` e prompts `ideate_v1` (um bloco por lente e persona; few-shot das ideias curtidas; regras da meta-review; lista de rejeitadas).
- `ideation/generate.py`, com chamadas independentes e rotação de famílias.

## Tarefa 5: Dedup, rejeitadas e portfólio
- Cosseno ≥ 0,80 no lote.
- Ideias parecidas (≥ 0,85) com rejeitadas pelo mesmo motivo saem.
- Nichos `domínio × família de técnica × forma`.

## Tarefa 6: Crítica multipapel
- `IdeaCritique` com seis papéis, veredito, critérios de descarte e "o que mudaria". O gate NASSS rebaixa a ideia.

## Tarefa 7: Prior art por facetas
- `ideation/prior_art.py`: OpenAlex, Semantic Scholar, GitHub e Exa, como vizinhos por camada.
- `NoveltyMatrix` por juiz: facetas igual / parcial / não encontrado. Sem concordância, a faceta fica "a verificar".

## Tarefa 8: Rubrica, gates, dossiê e seleção
- Eixos 1–10 pelos juízes, agregados só com concordância, com os pesos do §8.4 e o multiplicador de confiança.
- Gates duros; dossiê dos finalistas; seleção por portfólio.

## Tarefa 9: Ledger, meta-review e feedback
- Os votos de ideias vêm do Telegram (callback `f:<chave>:u|d|t|a`) e da interface.
- O meta-review gera até 10 regras, guardadas em `meta`.

## Tarefa 10: Relatório semanal e `run weekly`
- Markdown e HTML com tendências, mapa, lacunas, ideias e descartadas, mais Telegram (uma mensagem por ideia, com botões) e e-mail.
- `run weekly` faz: sincronização e inteligência, depois ideação, depois relatório. `sotawhat ideate --tema --n --modo` existe também.

## Tarefa 11: Interface e MCP
- Página de ideias e painel de tendências na interface.
- Ferramentas `trends`, `gaps` e `list_ideas` no MCP.

## Tarefa 12: Agendamento, `doctor` e documentação
- `schedule_daily.ps1 -Weekly` (domingo às 20:00).
- `doctor`: o último run semanal.
- README e SDD.

## Tarefa 13: Verificação real
- `sotawhat ideate --n 4` no grafo real, em modo econômico reduzido: custo, tempo e qualidade dos cards.
- Relatório gerado, sem envio.
- Adendo, merge e push.
