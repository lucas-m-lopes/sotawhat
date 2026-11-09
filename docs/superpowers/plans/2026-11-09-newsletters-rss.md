# Newsletters por RSS (Substack e afins) — plano e adendo

**Pedido (2026-11-09):** "será que conseguimos buscar o substack também? Faça também e insira uma busca nas
principais newsletters de AI de fronteira e AI + Medicina". O usuário criou no Gmail filtros para a Rundown AI e
para The Batch (DeepLearning.AI).

## Decisões

- Substack (e beehiiv, Ghost, WordPress) tem RSS por publicação: a fonte nova lê feeds, sem API não oficial nem
  login. A lista fica em `config/newsletters.yaml` (perfil `ia` ou `saude`, tipo `post` ou `digest`, `enabled`).
- Digests (várias notícias por edição) passam pela mesma separação por LLM das newsletters do Gmail
  (`stories_from_html`, tarefa `segment`); cada notícia guarda o link da fonte, o que deduplica entre newsletters
  que citam o mesmo paper ou anúncio.
- As de saúde falam de muito mais que IA: filtro próprio com termos em inglês e português ("IA" só em maiúsculas,
  porque "ia" é verbo), aplicado antes do teto por newsletter.
- A Rundown fica no Gmail (o RSS dela só traz a manchete). The Batch e AlphaSignal já têm fonte própria, então o
  Gmail ignora os remetentes deles em vez de pedir que o usuário desfaça o filtro.
- Achado ao lado: o run semanal de 2026-11-08 e a etapa do grafo de 2026-11-09 morreram com 0xC000013A (janela de
  console fechada). As tarefas passam a usar `pythonw.exe -m sotawhat.cli`; o que seria impresso vai para
  `data/logs/console.log`.

## Tarefas (TDD)

1. `stories_from_html` compartilhado; Gmail ignora remetentes cobertos (`covered`); `subscribe` nunca é link de notícia.
2. `NewsletterFeedSource`: posts, digests, estado sem releitura, teto por feed, filtro de IA, falha de LLM relida no
   run seguinte, orçamento interrompe.
3. `load_newsletters` valida o YAML; a lista entregue é válida.
4. `sotawhat newsletters add`: descoberta do feed (nome do Substack, site, página de tópico, `<link rel=alternate>`),
   comentários preservados, repetidas recusadas.
5. Perfis: `newsletters-ia` no geral, `newsletters-saude` no médico.
6. `doctor`: feeds que falham e os parados há 90+ dias.
7. CLI sem console: `_console_to_file`; `schedule_daily.ps1` com pythonw.

## Adendo (verificação real, 2026-11-09)

- 46 feeds candidatos conferidos: 34 respondem; 24 ficaram ativos e 10 listados como desligados (diárias repetidas,
  posts enormes, feed só com títulos).
- Run real numa cópia do banco (estado em pasta temporária): 18 itens de IA (DAIR.AI 11, Import AI 5, Latent Space 2)
  e 8 de saúde em 59 s; separação de 3 edições US$ 0,0016. Triagem: 1 IA ∩ Saúde (AuntMinnie), 4 Fronteira (papers
  do DAIR.AI), 6 Radar e 15 rejeitados.
- Limite conhecido: feeds que publicam só o primeiro parágrafo (MedCity, Second Opinion, Out-Of-Pocket) são julgados
  pela introdução e tendem a ser rejeitados. Se fizer falta, o próximo passo é extrair o texto da página (trafilatura).
- `doctor`: 24 de 24 respondem; Lilian Weng e Doctor Penguin sem post há 90+ dias (ficam ativos: entram se voltarem).
- `newsletters add`: `aisupremacy` → aisupremacy.substack.com/feed; página de tópico do STAT → feed do tópico;
  `interconnects.ai` recusada por já estar na lista.
- Suíte: 339 testes.

## Adendo 2 (texto completo, 2026-11-09)

O usuário pediu o texto completo ("pode fazer o texto completo das newsletters também").

- Medição dos 24 feeds ativos (4 entradas mais novas de cada):
  - a maioria já traz o post inteiro (2 mil a 145 mil caracteres);
  - só trazem trecho o Out-Of-Pocket (40–80 caracteres), a MedCity AI (250–480) e a Lilian Weng (500–860);
  - algumas entradas do Second Opinion, Health API Guy, AuntMinnie e Medicina S/A também vêm curtas.
- Regra: com menos de 1.500 caracteres no feed, o leitor (`sotawhat/sources/pages.py`) busca a página e extrai o texto principal com trafilatura 2.3, que tira menus, rodapés e comentários e mantém os links.
  - O texto da página só substitui o trecho quando é maior.
  - O filtro de IA da saúde lê esse texto, não o teaser de poucas palavras.
  - Digests curtos são separados a partir da página.
- O leitor é o mesmo da captura manual (P5):
  - só lê hosts públicos e confere cada salto de redirect (nada de SSRF para 127.0.0.1);
  - aceita só `200 text/html`, até 2 MB e 20 s;
  - nunca levanta exceção, e a falha deixa o trecho.
- Cada post guarda até 8.000 caracteres (antes eram 1.500), o mesmo limite que a triagem lê. Isso dá mais texto à triagem e à extração do grafo, a cerca de US$ 0,0003 a mais por post.
- Verificação real com estado temporário, sem LLM:
  - IA: 5 itens em 6 s;
  - saúde: 9 itens em 17 s;
  - 9 páginas lidas, de 0,3 a 1,1 s cada;
  - MedCity: de cerca de 300 para 5–9 mil caracteres;
  - Out-Of-Pocket: de cerca de 60 para cerca de 15 mil (8 mil guardados);
  - AuntMinnie responde 403 a robôs e fica com o trecho;
  - Health API Guy (post pago) dá só a prévia.
- Efeito colateral aceito: a página do Out-Of-Pocket abre com um anúncio do curso "AI Agents in Healthcare Ops 101". Por isso todo post dele passa no filtro de termos e a triagem decide com o texto completo. São 2–3 posts por semana.
- Dependências fixadas em versões com pelo menos duas semanas de PyPI na instalação local: regex 2026.9.29, python-dateutil 2.9.0.post0, dateparser 1.4.3, lxml_html_clean 0.4.5, tzdata 2026.5.
- Suíte: 344 testes.
