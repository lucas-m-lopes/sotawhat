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


## Adendo: execução (2026-11-08)

Executada na branch `feature/insight-engine-p4`, logo depois da P2. Cada tarefa começou pelos testes; o motor de ideias roda contra um gateway falso nos testes e contra o OpenRouter na verificação real.

| Tarefa | Commit | Suíte |
|---|---|---|
| 0 · Plano | `779c743` | 251 |
| 1 · Schema 4 (ledger de ideias, comunidades, relatórios) | `647ed28` | 254 |
| 2–3 · Inteligência semanal (tendências, Louvain, lacunas) | `f94dd23` | 257 |
| 4–8 · Motor de ideias (candidatos, lentes, dedup, crítica, prior art, juízes, rubrica, portfólio, dossiê) | `fb56d39` | 264 |
| 9–10 · Votos de ideias no Telegram, relatório semanal, `run weekly` e `ideate` | `5645c3f` | 273 |
| 11 · Abas Ideias e Tendências, ferramentas do MCP | `6523702` | 278 |
| 12 · Agendamento semanal e `doctor` | `b8685fc` | 280 |
| 13 · Correção: pares novos a cada run, sem repetir ideias anteriores | `679e2f2` | 281 |
| 13 · Correção: dedup semântico por par, gates por concordância, prior art do GitHub | `6cea073` | 284 |
| 13 · Correção: dono em linha própria no card | `c81cb22` | 284 |
| 13 · Documentação, SDD v1.6 | `6812dbf`, `074d4e2` | 284 |
| 13 · Rótulos das comunidades com a cadeia `judge` | `5c3b0b5` | 284 |
| 13 · Correção: setor certo (prompt `ideate_v2`) e confiança pela média dos juízes | `ccf8551` | 285 |
| 13 · Adendo | este commit | 285 |

### Mudanças além do plano
- **Modo econômico mais enxuto que o planejado.** O plano previa 20 candidatos × 6 lentes e 8 finalistas; ficou com 12 candidatos × 3 lentes (em rotação pelas 6), mais a contrária em 25% do lote, crítica e juízes nos 10 melhores e 6 finalistas. O motivo é a chave do OpenRouter: o limite de US$ 5 não renova (`limit_reset` vazio), e o `doctor` agora avisa disso. `--modo completo` e `config/ideation.yaml` ampliam tudo.
- **`ideate --n N`** gera N finalistas a partir de N candidatos, com crítica e juízes em N + 2 ideias. O `ideate` não rotula comunidades nem roda o meta-review, e usa as regras já guardadas.
- **Ledger de leitura único** (`sotawhat/ideation/ledger.py`): o relatório, a interface e o MCP montam o card da mesma forma.
- **MCP:** além de `trends`, `gaps` e `list_ideas`, entrou `idea` (o card completo com fatos do grafo e histórico de votos).
- **Votos pela interface:** além de explorar, testar, engavetar e não (com motivo), há "🛠️ construí".

### Tarefa 13: resultados
1. **Primeiro run real** (`ideate --n 4 --no-notify`, run 7):
   - 4 candidatos, 13 rascunhos e 34 chamadas, por US$ 0,038 em 717 s;
   - por tarefa: geração 13 (US$ 0,018, 50 s em média), crítica 4 (US$ 0,005, 59 s), juízes 16 (US$ 0,014, 14 s), dossiê 1;
   - por modelo: MiMo-V2.6-Pro 10 chamadas por US$ 0,021, o dobro do DeepSeek por chamada; GLM-5.3-Flash é o mais barato.
2. **O que o run mostrou, e as correções:**
   - **dedup:** manteve só 4 de 13. Com o EmbeddingGemma, duas ideias diferentes do mesmo domínio têm cosseno ≈ 0,81 (mediana do lote; 50 dos 78 pares ≥ 0,80), e até um par claramente diferente chegou a 0,908. Centralizar os vetores também não separou duplicatas de ideias distintas. Agora um juiz barato decide por par técnica × problema (mesmo produto = mesmo usuário, tarefa e mecanismo), inclusive contra as ideias anteriores do par no ledger; o embedding só pega textos quase idênticos (0,95). Nos mesmos 13 rascunhos, o juiz achou 1 repetição de verdade, por US$ 0,001;
   - **gates:** a união dos gates dos dois juízes descartou 3 das 4 sobreviventes. Agora um gate só descarta com todos os juízes; o de um juiz só fica "em disputa" (−0,1 na confiança) e aparece no card;
   - **prior art do GitHub:** a busca por estrelas no README trazia listas "awesome" genéricas; agora é por relevância no nome e na descrição;
   - **repetição entre semanas:** a mesma semente e os mesmos pares fariam o `run weekly` repropor as ideias do `ideate`. Agora a semente é o id do run, os pares usados nas últimas 4 semanas só completam o lote, e uma ideia parecida com uma finalista ou já votada é descartada como "já proposta antes".
3. **Segundo run real** (run 9, com as correções):
   - 4 candidatos, todos pares novos (nenhum do run 7): LLM × planejamento de leitos de UTI, × seleção de protocolo de RM, × predição de invasão perineural;
   - 13 rascunhos, 12 depois do dedup (o juiz achou 1 duplicata real), 6 criticados e **4 finalistas**, por US$ 0,062 em 1.253 s;
   - nenhum gate teve a concordância dos dois juízes. Três ideias ficaram com gates "em disputa" (`duplica_incumbente`, `sem_base_lgpd`), visíveis no card;
   - **finalistas:**
     - auditoria por LLM das prorrogações de UTI (evita glosa e antecipa a liberação do leito);
     - copiloto de protocolo de RM para clínicos;
     - pré-triagem de protocolo de RM na agenda de imagem;
     - extração das razões farmacoterapêuticas que retêm pacientes na UTI, para projetar a ocupação;
   - **dois problemas, corrigidos em seguida:**
     - setor errado: o gerador só via os códigos A01–A23 e chutava. O prompt `ideate_v2` traz a lista com os rótulos;
     - confiança 0,50 em todos os cards: um juiz sempre responde 5. A confiança passou a ser a média dos juízes.
4. **Interface:** as abas Ideias e Tendências foram conferidas no Chrome com os dados reais (64 itens aprovados, 388 entidades). As lacunas passaram a ser agrupadas por técnica. O grafo agora carrega só quando sua aba é aberta, porque o sigma não aceita contêiner oculto.
5. **Projeção do `run weekly` econômico:** ≈ US$ 0,13 por semana (≈ US$ 0,55/mês) e ≈ 30 min. Ele roda hoje às 20:00 pela primeira vez (tarefa `sotawhat-weekly`).
