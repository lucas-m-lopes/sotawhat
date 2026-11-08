# Insight Engine · P5 Instagram e captura manual — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA — use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para executar este plano tarefa a tarefa. Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** trazer o Instagram e os links enviados ao bot para dentro do pipeline (SDD §7.2 e §7.7):
- **captura manual (T2), sempre ligada:** todo link mandado ao bot do Telegram vira item. Um post ou reel do Instagram é resolvido pelo Apify; qualquer outro link vira um item com título e descrição da página. O item enviado por você não passa pelos filtros automáticos e nunca é rejeitado: no pior caso vai para o radar;
- **varredura diária (T3):** os posts novos das contas públicas de `config/instagram_accounts.yaml`, pelo ator `apify/instagram-scraper`;
- **curadoria da lista:** `sotawhat instagram import following.json` lê a exportação do Accounts Center, busca a bio de cada conta no Apify e pede ao LLM uma classificação ("IA/ML", "saúde/medtech" ou "fora do escopo"). O resultado vai para o YAML, que você revisa;
- **extração multimodal:** legenda mais a descrição das imagens pelo modelo de visão (até 3 por carrossel, ≤ 800 px, baixadas no mesmo run porque as URLs da CDN expiram). A transcrição de reels com `faster-whisper` é opcional e só liga se o pacote estiver instalado.

**Contexto:** fase seguinte à P4, no mesmo pedido do usuário ("direto até o final"). Branch `feature/insight-engine-p5`, a partir do `master` com a P4.

**Decisões:**
- **Provedor: Apify, plano Free.** O plano dá US$ 5/mês de uso, e o ator cobra US$ 0,0027 por resultado. Medido em 2026-11-08: conta `FREE`, uso US$ 0.
  - A API é chamada com o token no cabeçalho `Authorization`, nunca na URL.
  - O run é assíncrono: inicia, espera até 10 min e lê o dataset.
  - Todo run leva `maxTotalChargeUsd` (padrão US$ 0,15), além de `resultsLimit` por perfil.
  - A janela vem de uma marca d'água (o último run bem-sucedido, no máximo 3 dias atrás). Assim nada se perde quando um dia falha, e nada se paga duas vezes.
- **Sem conta da Meta e sem `instagrapi`.** O modo T4 continua fora: nenhuma credencial do Instagram entra no projeto.
- **Itens:**
  - id canônico `ig:<shortcode>`, tipo `instagram_post`, fonte `instagram` (varredura) ou `manual:telegram` (captura), com `extra.manual = true` na captura;
  - o texto do item junta a legenda, a descrição das imagens e, se houver, a transcrição.
- **Prioridade da captura manual:**
  - a triagem pula o filtro de silêncio e o classificador para esses itens;
  - um "reject" vira "radar";
  - o bot confirma o recebimento no chat.
- **Custo esperado:** 50 contas × ≈ 1 post novo por dia ≈ US$ 4/mês no Apify (dentro do crédito grátis), e ≈ US$ 0,3/mês de visão.

---

## Tarefa 0: Branch, plano e linha de base
- Branch `feature/insight-engine-p5` a partir do `master` (P4 integrada) e suíte verde.

## Tarefa 1: Cliente do Apify
- `sotawhat/sources/apify.py`: `ApifyClient.run(actor, input, max_usd, max_items)` com início assíncrono, espera e leitura do dataset; erros de cota viram mensagens claras.
- Testes com `httpx.MockTransport`: cabeçalho de autorização, `maxTotalChargeUsd`, espera até `SUCCEEDED`, falha do run.

## Tarefa 2: Fonte Instagram (varredura)
- `sotawhat/sources/instagram.py`: lê o YAML (contas habilitadas), monta `directUrls` dos perfis, aplica a marca d'água e normaliza cada post no esquema `{shortcode, owner, caption, media[], timestamp, type, provider}`.
- Dedup por shortcode; posts fixados que reaparecem são ignorados.

## Tarefa 3: Visão e mídia
- Download das imagens no mesmo run, redução para ≤ 800 px (Pillow) e envio em base64 à tarefa `vision`, com schema estrito (descrição e texto na imagem).
- Reels: capa mais transcrição opcional (`faster-whisper`, modelo `base` em CPU, se instalado).

## Tarefa 4: Captura manual
- O ouvinte confirma o link recebido.
- `process_inbox` no run diário transforma cada link da caixa de entrada em item: Instagram pelo Apify (`directUrls` do post) e os demais pela página (título e descrição, com limite de tamanho e tempo).
- A triagem dá prioridade a esses itens.

## Tarefa 5: Curadoria das contas
- `sotawhat instagram import <following.json> [--max 50]`: lê a exportação, busca os perfis (`resultsType: details`) dentro do teto de custo e classifica em lotes de 20 por chamada.
- Escreve `config/instagram_accounts.yaml` com as contas no escopo habilitadas e as demais desabilitadas, e manda um resumo no Telegram.

## Tarefa 6: `run daily`, `doctor` e documentação
- A varredura entra no perfil de IA, e a caixa de entrada é processada no começo do run.
- O `doctor` confere o token do Apify, o uso no mês contra o limite, o arquivo de contas e a última varredura.
- README, SDD e `.env.example`.

## Tarefa 7: Verificação real
- Uma captura manual de verdade: um link de post público mandado ao bot.
- Uma varredura com 2 ou 3 contas de teste, com custo medido.
- Adendo, merge e push.

## Adendo: execução (2026-11-08)

Executada na branch `feature/insight-engine-p5`, logo depois da P4. Cada tarefa começou pelos testes. O Apify, o LLM e a web entram por fakes nos testes e de verdade na verificação real.

| Tarefa | Commit | Suíte |
|---|---|---|
| 0 · Plano | `552f2f9` | 285 |
| 1 · Cliente do Apify | `01696ba` | 288 |
| 2 · Fonte Instagram (varredura) | `1bdec90` | 291 |
| 3 · Visão e mídia | `e0b9f9f` | 295 |
| 4 · Captura manual, triagem v3 | `5ebc5c9` | 302 |
| 5 · `sotawhat instagram import` | `f2cb4d2` | 307 |
| 6 · Run diário e `doctor` | `5bf975f` | 309 |
| 7 · Correção: item conhecido mandado ao bot volta para a triagem | `52c0b70` | 311 |
| 7 · Documentação, SDD v1.7 e adendo | este commit | 311 |

### Mudanças além do plano
- **Links escondidos.** O ouvinte também lê os links embutidos no texto (entidades `text_link` do Telegram), que o regex não via.
- **Redirecionamentos.** A página de um link é buscada sem seguir redirecionamentos às cegas: cada salto precisa resolver para endereço público (até 3 saltos).
- **Visão sem orçamento.** Estourar o orçamento desliga só a visão pelo resto do run: os posts, já pagos no Apify, entram com a legenda.
- **Transcrição de reels.** Fica opcional no extra `[audio]` (`faster-whisper`), sem `ffmpeg`, porque o PyAV decodifica o áudio.
- **HikerAPI.** Fica como alternativa ainda não implementada.

### Tarefa 7: resultados
1. **Verificação real** num banco temporário, com 2 contas públicas de teste (`openai` como "ia" e `mayoclinic` como "saude"), até 2 posts por conta:
   - varredura: 2 posts por categoria, em 26 s e 19 s (num deles, um post em colaboração com outra conta);
   - visão: descrições em pt-BR que leem as telas do carrossel e o texto dos slides (por exemplo, "What are microRNAs?" na capa de um reel);
   - captura manual: o post resolvido pelo Apify, e um link do arXiv com o título e o resumo da página;
   - triagem v3: os 4 posts de marca foram rejeitados com razão (história de usuária do ChatGPT, dicas de exercício, divulgação sobre microRNA, robô amador), e o "Attention Is All You Need" mandado à mão foi para "Fronteira de IA" (4,25);
   - custo: US$ 0,011 no Apify (do crédito grátis de US$ 5) e US$ 0,0014 de triagem.
2. **O que a verificação mostrou:** o post mandado ao bot já estava no banco pela varredura, e o upsert ignorava ids conhecidos, então ele ficava com a rejeição antiga. Agora o item passa a ser do leitor (fonte `manual:telegram`) e, se não estava aprovado, volta para a triagem (`52c0b70`).
3. **Banco real:** a 1 mensagem pendente na caixa de entrada (um texto curto sem link) ficou para o run das 07:00. O arquivo `config/instagram_accounts.yaml` ainda não existe, porque depende da sua exportação "Seguidores e seguindo"; até lá a varredura não roda, e o `doctor` avisa. A captura manual já funciona.
