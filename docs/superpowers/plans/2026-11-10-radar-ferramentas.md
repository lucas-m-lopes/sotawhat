# Plano — Radar de ferramentas (skills, MCPs e afins em alta) e a varredura do Instagram

**Data:** 2026-11-10 · **Pedido:** "cheque o resultado da extração do IG que deixei dentro de /data. Quero implementar
essa varredura e também a varredura do GitHub quanto a novas skills/MCPs que possam ser interessantes e que estão em
tendência de aumento de uso, não ligado a medicina mas que possam auxiliar na montagem de engenharia/arquitetura de
IA, economia de tokens, geração de aulas, enfim..."

## Decisões (respostas do usuário, 2026-11-10)

1. **Instagram:** importar as 625 contas seguidas do export (`data/instagram-…-2026-11-09-….zip`, só
   `following.json`), com o teto de US$ 0,10 por varredura diária até o ciclo da Apify que fecha em 7/12. Depois o teto
   volta a US$ 0,15. A importação usa o comando da P5 (`sotawhat instagram import --yes`); nada novo no código.
2. **Radar:** entrega semanal, com seção no relatório de domingo, mensagens no Telegram e uma aba **Ferramentas** na
   interface.
3. **Sinal de uso:** estrelas por semana, downloads do npm e do PyPI e um ranking de terceiros.
4. **Frentes:**
   - skills, plugins e MCPs;
   - arquitetura de agentes e evals;
   - economia de tokens e contexto;
   - aulas: vídeo, animação e voz.

   Nada de medicina: o radar não entra na triagem, no digest nem no grafo.

## Fatos medidos antes de desenhar (2026-11-10)

- **OSS Insight**, o ranking de terceiros escolhido, não funciona hoje:
  - a API de tendências responde vazio, com `data_quality.status = unavailable` desde 2026-03-01 (a captura de eventos
    do GitHub deles caiu a ~0,3% do normal, segundo a própria resposta);
  - `/v1/collections` responde 500.

  **Substituto:** o Hacker News, pela API pública da Algolia, sem chave. Ela dá as histórias da semana com URL
  `github.com/<dono>/<repo>` e os pontos de cada uma, um sinal de atenção de terceiros. No teste, 50 histórias em 7
  dias; a primeira foi `anthropics/claude-code`, com 1.613 pontos.
- **O `GITHUB_TOKEN` (fine-grained)** lê os dados de um repositório (estrelas, forks, push, releases, arquivos). Não
  lista stargazers com data, nem pelo REST nem pelo GraphQL ("Resource not accessible by personal access token").
  - Por isso a velocidade de estrelas vem de um **retrato diário próprio**, e a primeira semana completa fica pronta 7
    dias depois do início.
  - Até lá, um repositório com menos de 90 dias usa estrelas/dia desde a criação, marcada como estimativa.
  - Com um token clássico sem escopos, o histórico poderia vir de uma vez. Fica como opção do usuário.
  - **Adendo (2026-11-10):** o usuário pediu o guia para criar esse token. A partir dessa data o GitHub exige
    autenticação para listar stargazers: sem token, a resposta é 401.
    - Com `GITHUB_STARS_TOKEN`, um token clássico sem escopos, `sotawhat/radar/history.py` lê pelo GraphQL quem deu
      estrela e quando, dos mais recentes para os mais antigos, até 14 dias atrás (no máximo 5 páginas de 100 por
      repositório).
    - A partir disso reconstrói a contagem de cada dia: as estrelas de agora menos as dadas depois do dia.
    - A varredura diária faz isso para até 300 repositórios sem contagem de uma semana atrás. O
      `sotawhat radar backfill` faz para todos de uma vez.
    - O `doctor` testa o token.
- **npm e PyPI** guardam histórico diário de downloads: `api.npmjs.org/downloads/range/<período>/<pacote>` e
  `pypistats.org/api/packages/<pacote>/overall`. O crescimento semana contra semana sai já no primeiro relatório.
- **A busca do GitHub da P2** pega só repositórios criados nos últimos 7 dias e passa pela triagem de IA ∩ saúde. Ela
  não mede crescimento e tende a descartar ferramenta genérica; o radar é outro caminho.

## Desenho

- **Configuração:** `config/tools_radar.yaml` define:
  - por frente, as buscas do GitHub (tópicos e termos);
  - os limiares de estrelas e de idade;
  - quantos repositórios acompanhar (400), quantos vão ao juiz (30), quantos entram no relatório (10) e o máximo por
    frente (4).
- **Descoberta**, todo dia, no `run daily`, depois do digest, com cerca de 40 buscas:
  - **GitHub Search**, duas buscas por consulta, cada uma devolvendo os 30 primeiros:
    - `<q> stars:>=50 pushed:>=<hoje−14d> fork:false archived:false`, por estrelas: os ativos que já são usados;
    - `<q> created:>=<hoje−45d> stars:>=20`: os novos que sobem.
  - **Hacker News:** histórias dos últimos 7 dias com URL de repositório e pelo menos 20 pontos. Um repositório que só
    o HN trouxe precisa parecer ferramenta de IA (termos na descrição, nos tópicos ou no título) para ser medido.
  - **O registro oficial MCP fica de fora:** em 2026-11-10, mais de 6.000 servidores tinham mudado em 14 dias, 570 deles
    com GitHub e pacote. Mudança no registro não diz nada sobre uso. Os MCPs vêm das buscas por tópico (`mcp-server`,
    `model-context-protocol`, `mcp`), e o uso de cada um vem dos downloads do seu pacote.
- **Retrato diário:** para cada repositório acompanhado, guarda estrelas, forks e último push (`GET /repos/{r}`).
  - Isso dá cerca de 400 pedidos por dia, e a cota é de 5.000 por hora.
  - Um repositório que nenhuma descoberta trouxe nos últimos 60 dias sai do acompanhamento.
- **Semanal**, no `run weekly`, antes do relatório (ou `sotawhat radar` sob demanda):
  1. **Métricas:** Δ de estrelas em 7 dias e nos 7 anteriores (aceleração), crescimento relativo, downloads da
     semana e da anterior, e pontos no HN. Os pacotes vêm do registro MCP ou do `package.json`/`pyproject.toml` da
     raiz, que só se lê para os candidatos.
  2. **Pontuação:** média dos percentis dos sinais que o repositório tem, entre Δ de estrelas, crescimento
     relativo, crescimento de downloads e pontos no HN. Precisa de um sinal mínimo: 30 estrelas na semana, 1.000
     downloads ou 50 pontos.
  3. **Juiz** (LLM barato, tarefa `radar`, endpoints ZDR): avalia os 30 melhores e diz:
     - a frente, ou "fora";
     - a relevância de 0 a 5 para o stack do usuário;
     - o que a ferramenta faz e por que serve;
     - os riscos: licença, se executa código ou pede chaves, maturidade.

     O código acrescenta "testar a partir de": a data da última release mais 14 dias, que é a regra de dependências.
  4. **Relatório:** seção "Ferramentas em alta" no relatório semanal, com os 10 primeiros de relevância ≥ 3 e no
     máximo 4 por frente.
     - No Telegram vai uma mensagem por ferramenta, com 🧪 testar · 👍 · 👎 · 🗄️ depois.
     - Os votos vão para o ledger do radar, pelo prefixo `tool:` das entregas, como `idea:` nas ideias.
  5. **Interface:** aba Ferramentas, com a semana por frente, as métricas, o veredito, os links, os votos e o
     histórico de estrelas.
- **Custo:** GitHub, npm, PyPI e HN não cobram. O juiz faz cerca de 30 chamadas baratas por semana, menos de US$ 0,05.

## Tarefas (TDD, uma por commit)

1. **Store:** esquema v6, com `radar_repos`, `radar_stars`, `radar_hn`, `radar_picks` e `radar_votes`.
2. **`sotawhat/radar/discover.py`:** GitHub Search, registro MCP e HN, com o nome `dono/repo` normalizado e as
   frentes de cada achado.
3. **`sotawhat/radar/measure.py`:** o retrato diário, a descoberta de pacotes e os downloads do npm e do PyPI.
4. **`sotawhat/radar/score.py`:** as métricas da semana e a pontuação.
5. **Juiz:** prompt `radar_v1.md`, esquema `RadarVerdict` e a tarefa `radar` em `sotawhat/llm/tasks.py`.
6. **Relatório, Telegram e votos:** a seção no relatório semanal, as mensagens com botões e a rota `tool:` no
   `feedback`.
7. **Interface:** `/api/radar` e a aba Ferramentas.
8. **CLI e rotinas:**
   - `sotawhat radar scan|report [--no-notify]`;
   - o `run daily` faz o scan e o `run weekly` faz o relatório;
   - o `doctor` checa as fontes.
9. **Documentação:** README e SDD (o radar não pede chave nova).
