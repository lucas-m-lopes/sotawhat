# Integrações de ingestão para o pipeline diário (Gmail, Instagram, GitHub, registries MCP/skills, Hugging Face) — estado em 2026-11-07

Escopo: pipeline Python pessoal, execução diária não assistida em Windows 11 (Task Scheduler) com opção de GitHub Actions. Contexto do repositório `sotawhat` (deps atuais: `httpx>=0.27`, `feedparser>=6.0`; fontes já existentes: arXiv, Semantic Scholar, HF Daily Papers, PubMed, RSS; perfil `medico` = IA∩medicina).

Método: documentação oficial lida em 2026-11-07; endpoints públicos chamados ao vivo a partir desta máquina (Windows 11, `.venv` do projeto, `httpx`) para confirmar formato de resposta, parâmetros aceitos e contagens; versões de bibliotecas lidas da API JSON do PyPI. Itens não confirmados estão marcados **[INCERTO]**; o que não foi encontrado está em "Gaps". Observação ambiental relevante: nesta máquina, parte das chamadas HTTPS a `huggingface.co` falhou de forma intermitente com `SSL: CERTIFICATE_VERIFY_FAILED ... self-signed certificate in certificate chain` (as demais passaram) — sintoma típico de inspeção TLS por antivírus/proxy local; ver mitigação na seção de Hugging Face.

Divisão do trabalho: as seções de Gmail e de Instagram (API oficial; bibliotecas não oficiais/terceiros/legal) foram produzidas por pesquisadores paralelos e consolidadas aqui; GitHub, Hugging Face, registries MCP e Agent Skills foram pesquisados diretamente, com sondagens ao vivo.

---

## 1. Gmail — Gmail API (OAuth2) vs IMAP + App Password vs Pub/Sub: qual é mais estável para um job diário não assistido?

### Takeaway
Para um job diário sem humano no loop, **IMAP + App Password** (`imapclient.gmail_search`, que usa a extensão `X-GM-RAW` com a sintaxe de busca do Gmail) é o caminho com menos partes móveis; a **Gmail API com OAuth** é o caminho oficial e durável **desde que o app seja publicado "In production"** (mesmo sem verificação) — em status "Testing" o refresh token morre em 7 dias. Pub/Sub exige renovação de `watch()` a cada 7 dias e endpoint/pull; não faz sentido para batch diário.

### Cited Findings
- Motivos documentados para um refresh token parar de funcionar: revogação pelo usuário; **não uso por 6 meses**; **troca de senha quando o token tem escopos Gmail**; estouro do número máximo de refresh tokens; política de admin; limite de sessão — [Fonte](https://developers.google.com/identity/protocols/oauth2#expiration).
- **Limite de 100 refresh tokens por client OAuth por Conta Google**; o mais antigo é invalidado silenciosamente ao criar um novo — [Fonte](https://developers.google.com/identity/protocols/oauth2#expiration).
- Projeto **External + publishing status "Testing" → refresh tokens expiram em 7 dias** (exceção: só escopos básicos de perfil) — [Fonte](https://developers.google.com/identity/protocols/oauth2#expiration).
- Página "Audience" (Google Auth Platform): Testing = até 100 test users; "Test user authorizations expire seven days after consent. If a refresh token was issued, it also expires." In production com escopos sensíveis/restritos **não aprovados**: tela "Unverified apps" + **cap vitalício de 100 novos usuários por projeto**; a página não afirma que apps não verificados deixem de funcionar — [Fonte](https://support.google.com/cloud/answer/15549945).
- User type **Internal** exige Google Cloud Organization (Workspace/Cloud Identity) e restringe a membros da organização — [Fonte](https://support.google.com/cloud/answer/15549945).
- Escopos sensíveis/restritos exigem verificação para distribuição; apps com escopos restritos passam por **re-verificação anual** — [Fonte](https://support.google.com/cloud/answer/13463073). Classificação: `gmail.readonly`, `gmail.modify`, `gmail.metadata` e `https://mail.google.com/` = **Restricted**; `gmail.labels` = Non-sensitive; apps que armazenam dados de escopo restrito "must go through a security assessment" — [Fonte](https://developers.google.com/workspace/gmail/api/auth/scopes).
- Nova UI do Console: "Google Auth Platform" com seções **Branding**, **Audience** e **Clients** — [Fonte](https://support.google.com/cloud/answer/15544987).
- **App Passwords continuam existindo (nov/2026)**: senha de 16 caracteres; "aren't recommended and are unnecessary in most cases"; exigem 2-Step Verification; indisponíveis quando a 2SV usa só chaves de segurança, em contas de organização e com Advanced Protection; **trocar a senha da conta revoga todos os app passwords**; nenhum aviso de descontinuação — [Fonte](https://support.google.com/accounts/answer/185833).
- Workspace: "Starting May 1, 2025, Google Workspace accounts no longer support less secure apps"; a orientação para dispositivos SMTP/IMAP é "either configure them to use OAuth or create an app password" — ou seja, App Passwords permanecem um caminho suportado — [Fonte](https://knowledge.workspace.google.com/admin/apps/control-access-to-less-secure-apps?hl=en).
- Extensões IMAP do Gmail (`X-GM-EXT-1`): `SEARCH X-GM-RAW "..."` (sintaxe de busca do Gmail), `X-GM-MSGID` (ID de 64 bits, igual ao id da API), `X-GM-THRID`, `X-GM-LABELS` — [Fonte](https://developers.google.com/workspace/gmail/imap/imap-extensions).
- Limites de banda IMAP (Workspace): download 2.500 MB/dia, upload 500 MB/dia — [Fonte](https://knowledge.workspace.google.com/admin/gmail/gmail-bandwidth-limits?hl=en). Limite de **15 conexões simultâneas**: só fontes terceiras — **[INCERTO]** [Fonte](https://support.getmailbird.com/hc/en-us/articles/16298148976279).
- `imapclient` 4.1.0 (2026-09-18): `gmail_search(query, charset='UTF-8')` usa `X-GM-RAW`; `IMAPClient(host, port=None, ssl=True, timeout=None)`; `login()`, `oauth2_login()` (XOAUTH2); `select_folder(folder, readonly=False)`; labels via `get_gmail_labels`/`add_gmail_labels` — [Fonte](https://imapclient.readthedocs.io/en/master/api.html), [PyPI](https://pypi.org/project/IMAPClient/).
- `imap-tools` 1.16.0 (2026-10-14): critério `A(gmail_label='x')` → `X-GM-LABELS`; `fetch(mark_seen=True)` por padrão (usar `mark_seen=False`); não documenta `X-GM-RAW` — [Fonte](https://github.com/ikvk/imap_tools), [PyPI](https://pypi.org/project/imap-tools/).
- Pub/Sub: `users.watch` precisa ser renovado "at least once every 7 days"; topic com permissão `publish` para `gmail-api-push@system.gserviceaccount.com`; entrega push (webhook) ou pull; payload só `emailAddress` + `historyId` (exige `history.list` depois); notificações podem atrasar/sumir — [Fonte](https://developers.google.com/workspace/gmail/api/guides/push).
- **Quotas da Gmail API mudaram em 2026** (página lida hoje): **80.000.000 unidades/dia/projeto**; 1.200.000/min/projeto e **6.000/min/usuário/projeto**; `messages.list` = 5; **`messages.get` = 20 (60 com `format=full|raw|html`)**; `labels.list` = 1; `history.list` = 2; `watch` = 100; projetos que usaram a API entre nov/2025 e abr/2026 mantêm quotas antigas; **projetos criados a partir de 2026-05-01 recebem as novas** — [Fonte](https://developers.google.com/workspace/gmail/api/reference/quota).
- Bibliotecas (PyPI, 2026-11-07): `google-api-python-client` 2.201.0 (2026-09-30) [PyPI](https://pypi.org/project/google-api-python-client/); `google-auth` 2.62.1 (2026-11-03) [PyPI](https://pypi.org/project/google-auth/); `google-auth-oauthlib` 1.5.0 (2026-09-29) [PyPI](https://pypi.org/project/google-auth-oauthlib/); `google-auth-httplib2` 0.4.4 (2026-10-01) [PyPI](https://pypi.org/project/google-auth-httplib2/).

### Inferences
- Fluxo recomendado com OAuth para uso pessoal: **External → "Publish app" (In production) sem verificação → só então consentir e gravar `token.json`**. Isso tira a expiração de 7 dias (regra "External + Testing"); você verá "Google hasn't verified this app" (Avançado → prosseguir) e o cap de 100 usuários é irrelevante. Publicar **antes** de gerar o token: não há garantia documentada de que um token emitido em Testing sobreviva à publicação **[INCERTO]**.
- O refresh token do Google não é rotacionado a cada refresh → em GitHub Actions basta guardar o `token.json` (ou só `refresh_token` + client id/secret) uma vez como secret; o job só faz `creds.refresh()` e deve falhar ruidosamente em `invalid_grant` (nunca tentar `run_local_server` em CI).
- IMAP via XOAUTH2 exigiria o escopo `https://mail.google.com/` (restrito) — herda a burocracia do OAuth sem os benefícios da API; não recomendado **[INCERTO quanto ao escopo exato]**.
- Esboço A (Gmail API): `InstalledAppFlow.from_client_secrets_file(GOOGLE_CLIENT_SECRET_FILE, ["https://www.googleapis.com/auth/gmail.readonly"]).run_local_server(port=0)` uma vez → `creds.to_json()` em `GMAIL_TOKEN_FILE`; no job: `Credentials.from_authorized_user_file(...)`, `creds.refresh(Request())`; `svc.users().messages().list(userId="me", q=GMAIL_QUERY, maxResults=100, pageToken=...)` → `messages().get(userId="me", id=..., format="raw")` (60 unidades na quota nova) → `email.message_from_bytes(base64.urlsafe_b64decode(raw), policy=email.policy.default)`. Variante CI sem arquivo: `Credentials(None, refresh_token=GMAIL_REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=..., client_secret=..., scopes=SCOPES)`.
- Esboço B (IMAP): `with IMAPClient("imap.gmail.com", port=993, ssl=True, timeout=60) as c: c.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD); c.select_folder("[Gmail]/All Mail", readonly=True); uids = c.gmail_search(GMAIL_QUERY); c.fetch(uids, ["RFC822", "X-GM-MSGID", "X-GM-THRID", "X-GM-LABELS"])` — `readonly=True` evita marcar `\Seen`; `X-GM-MSGID` é a chave de dedupe estável; o nome da pasta "All Mail" é localizado (`[Gmail]/Todos os e-mails`) — prefira operar via label própria.
- Custo de quota (API nova) para ~50 e-mails/dia com `format=raw`: ≈ 3.000 unidades/dia, irrelevante frente a 80 M/dia; o limite por minuto (6.000/usuário) permite ≤100 `get` por minuto.

### Ranking de opções (job diário não assistido)
1. **IMAP + App Password** — prós: zero Cloud project/consent screen, 1 secret, mesma sintaxe de busca via `X-GM-RAW`, `X-GM-MSGID` = id da API; contras: desaconselhado pelo Google, exige 2SV, indisponível com Advanced Protection/2SV só com chaves/algumas contas Workspace, revogado ao trocar a senha, risco (não anunciado) de descontinuação.
2. **Gmail API + OAuth (Desktop app, External, "In production" não verificado)** — prós: oficial, somente leitura, labels/ids/history nativos, quota folgada; contras: setup no Console, tela "unverified", refresh token morre com troca de senha/6 meses sem uso/>100 tokens/status Testing; re-consentimento exige navegador.
3. **Pub/Sub** — só para near-real-time; renovação semanal do `watch`, infraestrutura extra, notificações sem corpo.

### Passo a passo de setup (OAuth; UI "Google Auth Platform")
1. `console.cloud.google.com` → novo projeto (ex.: `sotawhat-gmail`). 2. *APIs & Services → Library* → "Gmail API" → Enable. 3. *OAuth consent screen* (redireciona ao **Google Auth Platform**) → *Get started*: nome, e-mail de suporte, **Audience: External**, e-mail de contato. 4. *Audience* → adicionar seu Gmail em Test users. 5. *Data Access* → adicionar `https://www.googleapis.com/auth/gmail.readonly` (marcado Restricted) — nome da seção **[INCERTO]**. 6. *Clients → Create client* → **Desktop app** → Download JSON → `client_secret.json` (fora do git). 7. *Audience → Publish app* → In production (aceitar o aviso de verificação). 8. Rodar o script uma vez localmente → navegador → "Google hasn't verified this app" → *Advanced → Go to …* → conceder `gmail.readonly` → `token.json` gravado. 9. GitHub Actions: secrets com o conteúdo de `client_secret.json` e `token.json`; step que os escreve em disco; `schedule: cron`.
Para IMAP: `myaccount.google.com/security` → ativar 2-Step Verification → `myaccount.google.com/apppasswords` → nome "sotawhat" → copiar 16 caracteres → `GMAIL_APP_PASSWORD`.

### Modos de falha e mitigações
- `invalid_grant` / "Token has been expired or revoked" → Testing (7 dias), troca de senha, 6 meses sem uso, >100 tokens, revogação manual → publicar antes de consentir; alerta + re-consentimento local; nunca `run_local_server` em CI.
- `[AUTHENTICATIONFAILED]` no IMAP → senha trocada, 2SV desligada, Advanced Protection → regenerar App Password; manter os dois backends atrás de uma interface `fetch_messages(query)` com `GMAIL_BACKEND=api|imap`.
- "Too many simultaneous connections" → 1 conexão por run (context manager), sem IDLE.
- Mensagens marcadas como lidas → `readonly=True` / `mark_seen=False`; `gmail.readonly` na API nunca altera estado.
- Duplicatas (edição reenviada, label aplicada tarde) → dedupe por `X-GM-MSGID`/`id` + `Message-ID`; janela `newer_than:2d` tolera um dia perdido.
- 429/403 `rateLimitExceeded` → backoff exponencial; ≤100 `get`/min.

### Gaps
- Página oficial atual com o limite de conexões IMAP simultâneas: não encontrada.
- Não confirmado se `run_local_server` envia `prompt=consent` por padrão (necessário para garantir refresh token em re-consentimentos).
- Não confirmado se passkey-only desabilita App Passwords (a página só cita 2SV só com chaves, Advanced Protection e contas de organização).

---

## 2. Gmail — parsing do HTML de newsletters e desembrulho de links de rastreamento

### Takeaway
`email` stdlib (`get_body(preferencelist=('html','plain'))`) + `html2text` (preserva links e tabelas em Markdown) cobrem newsletters; `trafilatura` serve como "segunda opinião" para remover boilerplate e `readability-lxml` tende a descartar layouts tabulares. Resolva redirects com `httpx` apenas nos links que você vai usar, limpe parâmetros com `w3lib.url.url_query_cleaner` e **nunca** siga links de unsubscribe/preferências (cada resolução conta como clique no ESP).

### Cited Findings
- `html2text` 2025.4.15 (2025-04-15) — [PyPI](https://pypi.org/project/html2text/); `trafilatura` 2.3.1 (2026-10-06) — [PyPI](https://pypi.org/project/trafilatura/); `readability-lxml` 0.9 (2026-08-27) — [PyPI](https://pypi.org/project/readability-lxml/); `mail-parser` 4.10.0 (2026-10-30) — [PyPI](https://pypi.org/project/mail-parser/); `url-normalize` 3.1.0 (2026-10-29) — [PyPI](https://pypi.org/project/url-normalize/); `w3lib` 2.6.0 (2026-11-05) — [PyPI](https://pypi.org/project/w3lib/); `unalix` 0.9 — **último release 2021-10-30** — [PyPI](https://pypi.org/project/unalix/); `clearurls` não existe no PyPI — [Fonte](https://pypi.org/pypi/clearurls/json).
- API stdlib: `EmailMessage.get_body(preferencelist=('related','html','plain'))`, `walk()`, `get_content()` — [Fonte](https://docs.python.org/3/library/email.message.html#email.message.EmailMessage.get_body).
- Substack reescreve todos os links em redirects de rastreamento (fonte secundária) — [Fonte](https://cutt.ly/resources/blog/url-shortener-for-newsletters-2026); beehiiv usa domínio de clique próprio e oferece domínios de link customizados (o host de rastreamento pode ser do publisher) — [Fonte](https://www.beehiiv.com/support/article/35633518133783-custom-domains-and-branded-links-faq), [Fonte](https://www.gblock.app/articles/is-beehiiv-tracking-your-email-block-2026); Mailchimp: pixel de abertura + redirect em `list-manage.com` (terceiro) — [Fonte](https://www.gblock.app/articles/is-beehiiv-tracking-your-email-block-2026).

### Inferences
- Hosts de rastreamento conhecidos (beehiiv `link.mail.beehiiv.com`, Substack `substack.com/redirect/...`/`open.substack.com`, Mailchimp `*.list-manage.com/track/click`, SendGrid `*.ct.sendgrid.net/ls/click`, Kit `click.convertkit-mail*.com`, HubSpot `*.hubspotlinks.com`, Customer.io `e.customeriomail.com`, Klaviyo `trk.klclick*.com`, Iterable `links.iterable.com`) são consistentes com o que se observa, mas **nenhuma doc primária de ESP foi lida** → **[INCERTO]**; não dependa de lista fixa: trate como candidato a redirect qualquer link cujo host difira do domínio do remetente ou contenha `/track/`, `/click`, `/ls/`, `/redirect/`, `/CL0/` ou tokens opacos longos.
- Conversão: `h = html2text.HTML2Text(); h.body_width = 0; h.ignore_images = True; h.bypass_tables = False; md = h.handle(html)`; `trafilatura.extract(html, output_format="markdown", include_links=True, include_tables=True)` para remover cabeçalho/rodapé/"view in browser" (pode cortar newsletters multi-item; nomes exatos dos kwargs na 2.3.1 **[INCERTO]**).
- Resolução: `httpx.Client(follow_redirects=True, max_redirects=10, timeout=10.0, headers={"User-Agent": "sotawhat-newsletter-bot/1.0 (+contato)"})` → `head()` e fallback `get()` em 405/403 → `str(r.url)`; detectar meta-refresh e `window.location` nos primeiros KB; cache em SQLite; concorrência baixa.
- Limpeza: `w3lib.url.url_query_cleaner(u, TRACKING_PARAMS, remove=True)` com `utm_*`, `ref`, `fbclid`, `gclid`, `dclid`, `msclkid`, `twclid`, `ttclid`, `mc_cid`, `mc_eid`, `_hsenc`, `_hsmi`, `_bhlid`, `mkt_tok`, `vero_id`, `ck_subscriber_id`, `oly_enc_id`, `oly_anon_id`, `_kx`, `ss_email_id`, `ss_campaign_id`, `igshid`, `yclid`; parâmetros de 1 letra do Substack (`r`, `j`, `s`) só em `*.substack.com`.
- Nunca seguir: URL de `List-Unsubscribe` (e `List-Unsubscribe-Post: List-Unsubscribe=One-Click`, RFC 8058 — um GET/POST descadastra), âncoras com "unsubscribe"/"manage preferences"/"opt out"/"cancelar inscrição", `<img>` (pixels), `mailto:`. "View in browser"/"read online" são seguros e dão a versão web canônica.

### Gaps
- Docs oficiais de formato de URL de rastreamento dos ESPs não lidas; validar heurísticas com e-mails reais.

---

## 3. Gmail — remetentes (AlphaSignal, DeepLearning.AI The Batch, Runway) e regras de filtro

### Takeaway
Não foi possível confirmar os endereços exatos de nenhum dos três remetentes; use `from:@dominio` e/ou o operador `list:`, e confirme pelo header `From`/`List-Id` do primeiro e-mail recebido. "Runway newsletter" é ambíguo (várias publicações chamadas Runway; não há página de assinatura encontrada para a RunwayML).

### Cited Findings
- AlphaSignal tem presença no Substack (`alphasignalai.substack.com`, "three emails a week"); diretório terceiro lista o ESP como Mailgun (não oficial); domínio principal `alphasignal.ai` — [Fonte](https://alphasignalai.substack.com/about), [Fonte](https://inboxreads.co/n/alpha-signals/tools).
- The Batch: preferências pelos links do rodapé; knowledge base e versões web em `info.deeplearning.ai` — [Fonte](https://info.deeplearning.ai/knowledge-base/how-can-i-update-my-deeplearning.ai-email-preferences), [Fonte](https://deeplearning.ai/the-batch/about).
- "Runway": resultados apontam Runway Magazine (moda), "Rethink the Runway"/"The Digital Runway" (Substack), "The Runway Ventures" (beehiiv); RunwayML só tem `runwayml.com/news`, sem assinatura encontrada — [Fonte](https://www.runwaylive.com/subscribe), [Fonte](https://www.runwayml.com/news).

### Inferences
- `info.<domínio>/knowledge-base/` é o padrão HubSpot → The Batch provavelmente sai por HubSpot (`*.hubspotlinks.com`, `_hsenc`/`_hsmi`), remetente `@deeplearning.ai` **[INCERTO]**. AlphaSignal via Substack teria `From` `…@substack.com` e links `substack.com/redirect/…`; via Mailgun/próprio, `@alphasignal.ai` **[INCERTO]** — cubra ambos.
- Filtro Gmail: *Has the words* `from:(@alphasignal.ai OR alphasignal@substack.com OR @deeplearning.ai OR @runwayml.com)` → Skip the Inbox, Apply label `newsletters/ai`, Never send to Spam. Alternativa: `list:(alphasignal.ai OR deeplearning.ai)`. Query de ingestão: `label:newsletters-ai newer_than:2d` (o Gmail converte `newsletters/ai` em `newsletters-ai`); na API é mais robusto `labels.list` → `messages.list(labelIds=[ID], q="newer_than:2d")`.

### Gaps
- Endereços exatos e ESP de AlphaSignal/Runway: não encontrados.

---

## 4. Instagram — plataforma oficial (2025-2026): o que existe e o que não existe (feed de seguidos)

### Takeaway
Dois sabores oficiais — **Instagram API with Instagram Login** (`graph.instagram.com`, sem Página do Facebook) e **Instagram API with Facebook Login** (`graph.facebook.com`, exige Página) — mais o "Unified Login" (token de System User). **Nenhum endpoint devolve o feed principal (posts das contas que você segue)**; a única porta para posts de terceiros é `business_discovery` (por username, só alvos profissionais), hashtags, menções/tags e oEmbed. A Basic Display API foi desligada em 2024-12-04.

### Cited Findings
- Instagram Login: contas profissionais "without requiring a linked Facebook Page", host `graph.instagram.com`, permissões `instagram_business_*`; Facebook Login: contas "linked to a Facebook Page", host `graph.facebook.com`, permissões `instagram_*` + de Página — [Fonte](https://developers.facebook.com/docs/instagram-platform/overview).
- Tabela de capacidades (Instagram Login / Facebook Login): **hashtag search Não/Sim**; product tagging Não/Sim; partnership ads Não/Sim; comentários, publishing, insights, mentions, messaging Sim/Sim — [Fonte](https://developers.facebook.com/docs/instagram-platform/overview).
- "a permission only allows access to data created by the app user who granted the permission"; dados de terceiros são "limited and public"; "your app users must have an Instagram professional account" — [Fonte](https://developers.facebook.com/docs/instagram-platform/overview).
- "December 4, 2024: The Instagram Basic Display API has been deprecated. All requests now return errors." — [Fonte](https://developers.facebook.com/docs/instagram-platform/changelog).
- Três modos na tabela de requisitos do IG Media: Unified Login (System User token, `graph.facebook.com`, `instagram_basic`), Instagram Login (`instagram_business_basic`), Facebook Login (`instagram_basic` + `pages_read_engagement` [+ `ads_management`/`ads_read` se o papel na Página veio via Business Manager]) — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media).
- Índice oficial de páginas (`llms.txt`) lista `/reference/me`, `/ig-user/media`, `/ig-user/business_discovery`, `/ig-hashtag-search`, `/ig-hashtag/top-media`, `/ig-hashtag/recent-media`, `/oembed`, `/reference/access_token`, `/reference/refresh_access_token`, `/app-review`, `/changelog` — [Fonte](https://developers.facebook.com/documentation/instagram-platform/llms.txt).

### Inferences
- O "feed de seguidos" não aparece em nenhuma página, tabela ou índice: não existe endpoint oficial. Endpoints úteis: `GET /me`, `GET /{ig-user-id}/media` (própria conta), `business_discovery`, `ig_hashtag_search` + `top_media|recent_media` (só Facebook Login), `mentioned_media`/`tags`, `instagram_oembed`, `/insights`, Messaging, publishing.

### Gaps
- Não há frase oficial dizendo textualmente "não é possível ler o feed de seguidos"; a conclusão é por ausência em toda a documentação atual.

---

## 5. Instagram — Business Discovery: requisitos, permissões, App Review, campos, limites e ciclo de vida de tokens

### Takeaway
Business Discovery é o único caminho oficial para posts públicos de outras contas, **só para alvos Business/Creator**, e a documentação atual o descreve **apenas para Facebook Login e Unified Login** (nenhuma seção para Instagram Login) — planeje com conta profissional **vinculada a uma Página do Facebook**, token de Facebook Login e teste o Instagram Login empiricamente antes de apostar. Para uso próprio (Standard Access, app em desenvolvimento) **não é preciso App Review**. Limite prático: Platform Rate Limit ≈ 200 chamadas/hora para um app com 1 usuário.

### Cited Findings
- Sintaxe: `GET /<IG_USER_ID>?fields=business_discovery.username(<USERNAME>){followers_count,media_count,media{comments_count,like_count,view_count}}`; create/update/delete "not supported" — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery).
- "Available for the Instagram API with Facebook Login"; token de usuário do Facebook com `instagram_basic`, `instagram_manage_insights` e `pages_read_engagement` (+ `ads_management`/`ads_read` via Business Manager); alvo deve ser Business ou Creator; contas age-gated não são retornadas — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery).
- Guia nomeia os produtos com o recurso: "Instagram API with Facebook Login and Instagram API with Unified Login"; e "performing a GET on any returned IG Media will fail due to insufficient permissions" (tudo tem de vir na expansão aninhada) — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery).
- Paginação do edge `media`: cursores `before`/`after`, sem `next`/`previous` — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery).
- Campos "Public" de IG Media (legíveis em mídia de terceiros): `alt_text`, `caption`, `comments_count`, `id`, `is_shared_to_feed`, `media_audio_type`, `media_product_type` (Facebook Login only), `media_type` (`CAROUSEL_ALBUM`/`IMAGE`/`VIDEO`), `media_url`, `owner`, `permalink`, `shortcode`, `thumbnail_url` (só VIDEO), `timestamp`, `username`, `view_count` (Business Discovery only), `reposts_count`, `total_comments_count`, `total_like_count` (Facebook Login only); `saved_count`, `shares_count`, `total_views_count` **não** disponíveis via BD; `like_count` omitido se o dono escondeu curtidas ou "if queried indirectly through another endpoint or field expansion" — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media).
- `media_url` omitido para vídeo com áudio licenciado e para reels com download desativado quando lidos via BD/tags/mentions/hashtag; "treat it as optional and fall back to `permalink` or `thumbnail_url`" — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media); changelog 2026-07-30 confirma `200` sem o campo — [Fonte](https://developers.facebook.com/docs/instagram-platform/changelog).
- Rate limits: todos os endpoints sob BUC **exceto Business Discovery e Hashtag Search (Platform Rate Limiting)**; BUC: "Calls within 24 hours = 4800 * Number of Impressions" — [Fonte](https://developers.facebook.com/docs/instagram-platform/overview); Platform: "Calls within one hour = 200 * Number of Users"; headers `X-App-Usage`/`X-Business-Use-Case-Usage`; códigos de throttling 4, 17, 32, 613, 80002 — [Fonte](https://developers.facebook.com/docs/graph-api/overview/rate-limiting).
- App Review: "My app is only for a business I own or manage" → Standard Access, App Review "Not required" — [Fonte](https://developers.facebook.com/docs/instagram-platform/app-review); "Standard Access is the default access level for all apps" para quem tem papel no app — [Fonte](https://developers.facebook.com/docs/instagram-platform/overview); "Standard Access is sufficient if you own or manage those accounts and have added them to your app in the App Dashboard" — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login).
- Tokens (Instagram Login): autorização em `https://www.instagram.com/oauth/authorize`; código válido 1 h; troca em `POST https://api.instagram.com/oauth/access_token`; token longo via `GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=…&access_token=…` (60 dias, `expires_in` 5183944); refresh via `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=…` com token ≥24 h, não expirado; não renovado em 60 dias "can no longer be refreshed" — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login). Tokens do Dashboard nascem longos (60 dias); teste `GET https://graph.instagram.com/v27.0/me?fields=user_id,username&access_token=…` — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started).
- Facebook Login: `fb_exchange_token` server-side; "A long-lived token generally lasts about 60 days"; token expirado não pode ser trocado; Page token longo via `GET {user-id}/accounts`: "do not have an expiration date" — [Fonte](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived).
- Escopos novos `instagram_business_basic|content_publish|manage_comments|manage_messages` (2024-09-17; antigos depreciados 2025-01-27) — [Fonte](https://developers.facebook.com/docs/instagram-platform/changelog).
- Setup: app tipo **Business** ("Your app must be a business type app to be able to add the Instagram product"), caso de uso Other; conta de teste pública; papéis em App Roles > Roles ou Instagram > API setup — [Fonte](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app); "Generate token" no Dashboard — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started).

### Inferences
- Teto prático para app pessoal: ~200 req/h; cada `GET` com expansão aninhada deveria contar como 1 chamada (não explicitado). Com `media.limit(10)` e parada pelo `timestamp` da última varredura, 50 alvos/dia cabem com folga.
- Paginação aninhada consistente com o Graph API: `business_discovery.username(x){media.limit(25).after(<CURSOR>){...}}`.
- Reels: `thumbnail_url` existe, `media_url` pode faltar → persistir `permalink` + `thumbnail_url`; URLs de CDN provavelmente expiram **[INCERTO]** → baixar na mesma execução.
- Automação do refresh (Instagram Login): guardar `{access_token, expires_in, obtained_at}`; refresh quando `age ≥ 24h` e restante < 30 dias; em GitHub Actions o `GITHUB_TOKEN` não grava secrets (usar `gh secret set` com PAT ou arquivo cifrado). Facebook Login: usar Page token longo (sem expiração; **[INCERTO]** se BD aceita Page token — a referência fala em Facebook User token) ou re-trocar o user token antes dos 60 dias.
- Teste decisivo antes de escolher o modo: `GET https://graph.instagram.com/v27.0/me?fields=business_discovery.username(instagram){id,username,media_count}` com o token do Dashboard; se falhar por campo/permissão, usar Facebook Login + Página.
- Esboço (httpx): montar `fields` com `PROFILE_FIELDS = "id,username,name,biography,website,profile_picture_url,followers_count,follows_count,media_count"` e `MEDIA_FIELDS = "id,shortcode,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count,view_count,children{id,media_type,media_url,thumbnail_url}"`; tratar `error.code` 190 (token), 4/17/32/613/80002 (rate limit, dormir `estimated_time_to_regain_access`), 110/100/24 (alvo não profissional/inexistente — **[INCERTO]**, registrar mensagem literal); `time.sleep(1.0)` entre alvos.

### Gaps
- Código de erro exato para alvo pessoal/inexistente: não documentado (relatos apontam `(#110) Incorrect user id`, não verificado).
- Lista completa de campos de perfil via BD (referência "IG User" não lida); limite máximo de `media.limit()`; contagem de chamadas por expansão; expiração de `media_url`.
- Invalidação de tokens por troca de senha/logout (página de depuração retornou 404); System User tokens sem expiração (não lidos).

---

## 6. Instagram — Hashtag Search, oEmbed, deprecações 2025-2026 e "Saved"/exportação

### Takeaway
Hashtag Search só com Facebook Login, **30 hashtags únicas por 7 dias**, `recent_media` só últimas 24 h e sem `username`. O oEmbed **perdeu `author_name`/`author_url`/`thumbnail_url` em 2025-11-03** e pode ser chamado **sem token desde 2026-05-15** (1.000 req/h), mas só devolve `html` e os termos proíbem extrair/persistir metadados — **não serve para resolver links em autor + thumbnail**. Não existe endpoint para "Saved"/coleções; a exportação JSON do Accounts Center é a fonte viável para a lista de seguidos como seed manual.

### Cited Findings
- `GET /ig_hashtag_search?user_id=<USER_ID>&q=<QUERY>`; feature Instagram Public Content Access; "You can query a maximum of 30 unique hashtags within a 7 day period" — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-hashtag-search). `recent_media`: só mídia publicada nas 24 h anteriores, só pública, sem promovida; pedir o edge "counts against the limit even if you already have the hashtag ID"; `username` não pode ser pedido; `limit` máx. 50; só cursor `after` — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-hashtag/recent-media).
- oEmbed: `GET /instagram_oembed` em `graph.facebook.com`; parâmetros `url`, `fields`, `maxwidth` (320–658), `omitscript`, `hidecaption`; URLs aceitas `/p/{shortcode}/`, `/reel/{shortcode}/`, `/{username}`; limite "1,000 requests per hour"; uso "restricted to providing a front-end view", proíbe "extracting or persisting" metadados — [Fonte](https://developers.facebook.com/docs/instagram-platform/oembed); campos de resposta `html`, `provider_name`, `provider_url`, `type`, `version`, `width`; erros 200/100/190/368 — [Fonte](https://developers.facebook.com/docs/graph-api/reference/instagram-oembed/); changelog: 2025-04-08 "Meta oEmbed Read" substitui "oEmbed Read"; `author_name`, `author_url`, `thumbnail_url`, `thumbnail_width`, `thumbnail_height` "removed on November 3, 2025"; 2026-05-15 "The oEmbed API can be called without an access token" — [Fonte](https://developers.facebook.com/docs/instagram-platform/changelog).
- Versões do Graph API: v26.0 (2026-07-29), v25.0 (2026-02-18, até 2028-07-29), v24.0 (2025-10-08), v23.0 (2025-05-29), v22.0 (2025-01-21), v21.0 (2024-10-02, até 2027-01-21), v20.0 expirou 2026-09-24, v19.0 expirou 2026-05-21; a página diz que a mais recente é "v27.0" mas a tabela termina em v26.0 — [Fonte](https://developers.facebook.com/docs/graph-api/changelog); amostras oficiais atuais usam `v27.0` — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started).
- Changelog Instagram Platform 2025-2026 (seleção): 2026-07-30 `media_url` opcional; 2026-06-22 `is_ai_generated`; 2026-06-01 Audio API/`media_audio_type`; 2026-04-22 `reposts_count`/`saved_count`/`shares_count`, `total_*`, BD `view_count` combinado, `/collaborative_media`, `/likes` + `instagram_manage_engagement`; 2026-02-06 `enable_fb_login`; 2025-12-03 `DELETE /{ig_media_id}`; 2025-06-16 `view_count` só via BD (Reels); 2025-01-21 Insights para Instagram Login, métricas `impressions`/`plays` depreciadas a partir de v22.0; 2024-07-23 lançamento do Instagram Login — [Fonte](https://developers.facebook.com/docs/instagram-platform/changelog).
- `saved_count`: "Visible only to the owner or an accepted collaborator. Not available via Business Discovery"; nenhum edge de saved/collections na referência ou no índice — [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media), [Fonte](https://developers.facebook.com/documentation/instagram-platform/llms.txt).
- Exportação: Accounts Center → Your information and permissions → **Export your information** (ex-"Download your information") → perfil, "Export to device", "Customize information", intervalo (padrão "Last year", opção "All time"), formato padrão HTML / JSON "raw data", qualidade de mídia; Meta diz "can take up to 30 days" (pequenos chegam antes); download disponível por 4 dias (fonte terceira) — [Fonte](https://redact.dev/blog/instagram-data-file-download). Ferramentas de terceiros apontam `connections/followers_and_following/following.json` e `followers_1.json` — [Fonte](https://unplugme.pages.dev/export-instagram.html), [Fonte](https://instatrack-250.pages.dev/how-to-export), [Fonte](https://redact.dev/tools/instagram-data-viewer).

### Inferences
- `GRAPH_API_VERSION=v27.0` (coerente com as amostras), fallback `v26.0`; nunca < v21.0.
- Em `/me/media` com Instagram Login não conte com `media_product_type`; use `media_type` + `permalink` (`/reel/` vs `/p/`).
- Seed de seguidos: exportar JSON ("Followers and following", "All time"), ler `following.json` (estrutura típica `relationships_following[] → string_list_data[0].value|href|timestamp` — de memória, validar no próprio export), filtrar pelos usernames que respondem ao BD, repetir mensalmente. `your_instagram_activity/saved/saved_posts.json` **[INCERTO]** — verificar no ZIP.

### Gaps
- Data de lançamento da v27.0 (página 404); requisito de App Review da feature "Meta oEmbed Read" após 2026-05-15; limite "5.000.000/dia" do oEmbed (não encontrado; só 1.000/h); página oficial do Help Center sobre a exportação não renderizou (JS).

---

## 7. Instagram — bibliotecas não oficiais (instagrapi, instaloader, yt-dlp, gallery-dl): manutenção, risco de checkpoint/ban e boas práticas

### Takeaway
`instagrapi` (3.2.7, release em 2026-11-07, py≥3.11) e `instaloader` (4.16, 2026-10-26) estão vivos, mas o próprio README do instagrapi classifica a automação via Private API como "fragile in production" e empurra para o SaaS HikerAPI, enquanto o instaloader acumula issues abertas de `429`/`401` em 2026 e acabou de endurecer `LoginRequiredException`. Para um job diário não assistido são fallback de último recurso: conta **secundária** só-leitura, sessão persistida, sempre do mesmo IP doméstico, **nunca** a partir de GitHub Actions.

### Cited Findings
- instagrapi: `3.2.7` em 2026-11-07 (cinco releases 3.2.3→3.2.7 entre 05 e 07/11), `requires_python >=3.11` — [PyPI](https://pypi.org/pypi/instagrapi/json); 7.074★, README exige Python 3.11+ e Pillow 13+; texto atual: "Private API automation is fragile in production because account trust, proxies, device state, challenges, and rate limits" mudam; "best suited for testing, research, and controlled internal automation"; "prefer official Instagram APIs where they cover your use case"; "a hosted provider such as HikerAPI may be a better fit"; tagline "Python library for Instagram Private API 2026 with HikerAPI SaaS" (com programa de afiliados) — [Fonte](https://github.com/subzeroid/instagrapi).
- Sessão: `cl.dump_settings("session.json")` / `cl.load_settings("session.json")` ("Dump the settings after login so a refreshed session is persisted") — [Fonte](https://github.com/subzeroid/instagrapi). Best practices oficiais: "one account per stable proxy/IP"; casar `set_country(...)`, `set_locale(...)`, device settings e sessão salva com o "ambiente normal" da conta; `cl.delay_range = [1, 3]`; "Persist sessions and device identifiers; avoid password login from scratch on every run"; "Increase volume slowly over days, not minutes"; monitoramento com polling de "several minutes rather than seconds"; `ClientThrottledError` (429) → parar o burst e recuar; `PleaseWaitFewMinutes` → não retentar em loop; `ChallengeRequired` → `challenge_resolve(...)` só com handlers funcionais; `LoginRequired` → relogin com o mesmo device/sessão; "Avoid treating any proxy type as a universal fix" — [Fonte](https://subzeroid.github.io/instagrapi/latest/usage-guide/best-practices/).
- Issues abertas do instagrapi em 2026-11-07: #2890 (2026-10-18) "CAA login succeeds but post-login warmup (reels_tray) hits challenge_required"; #2805 "CAA TOTP verification returns HTTP 200 without a completed login session"; #2807 "Your version of Instagram is out of date…" (429) — [Fonte](https://github.com/subzeroid/instagrapi/issues).
- instaloader: `4.16` (2026-10-26, py≥3.10) — [PyPI](https://pypi.org/pypi/instaloader/json); 13.805★, 45 issues abertas; último commit 2026-11-01 "Raise LoginRequiredException for Profile fields that require login" — [Fonte](https://github.com/instaloader/instaloader); issues abertas: "401 Unauthorized" 8, "Please wait a few minutes" 9, `429` 8 — ex.: #2786 (2026-10-21) "Is Instaloader still working reliably in 2026? Persistent 429 errors", #2750, #2726, #2738 (`doc_id` errors), #2803 (2026-11-07) "Download is aborted with 302 Found" — [Fonte](https://github.com/instaloader/instaloader/issues).
- Troubleshooting instaloader: acesso anônimo "might be subject to significantly stricter limits"; "We recommend to always keep the session file which Instaloader creates when using --login"; com session file, `--login` não usa "the failure-prone login procedure"; alternativa `615_import_firefox_session.py` — [Fonte](https://instaloader.github.io/troubleshooting.html). CLI: `--login`, `--load-cookies BROWSER`, `--cookiefile`, `--sessionfile` (Windows: `%LOCALAPPDATA%\Instaloader\session-<user>`), `--fast-update`, `--latest-stamps`, `--post-filter`, `--abort-on` (ex.: 429) — [Fonte](https://instaloader.github.io/cli-options.html), [Fonte](https://github.com/instaloader/instaloader/blob/master/instaloader/instaloader.py).
- yt-dlp `2026.10.26` (py≥3.11) — [PyPI](https://pypi.org/pypi/yt-dlp/json); extrator Instagram alterado em 2026-07-21 "[ie/instagram] Fix logged-in extraction (#17278)"; usa cookie `sessionid`, API `i.instagram.com/api/v1` (logado) / `www.instagram.com/api/v1` (anônimo) e GraphQL `doc_id`; mensagens: "Main webpage is locked behind the login page", "You have exceeded the rate-limit for accessing posts anonymously", "The provided Instagram account cookies are no longer valid" — [Fonte](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/instagram.py). gallery-dl `1.32.19` (2026-10-31) com `"instagram": {"cookies": "…/cookies.txt"}` — [PyPI](https://pypi.org/pypi/gallery-dl/json).
- Proxies residenciais: IPRoyal US$7,35/GB (PAYG 1 GB, "traffic never expires", sticky até 7 dias) — [Fonte](https://iproyal.com/residential-proxies/); Apify Proxy residencial US$8/GB — [Fonte](https://apify.com/pricing). Bright Data/Decodo/Oxylabs: sem fonte verificada.

### Inferences
- Cinco releases em três dias sinalizam churn de correção (quebras de login CAA/TOTP), não estabilidade.
- A doc do instagrapi não prescreve literalmente "proxy residencial"/"conta secundária", mas "one account per stable proxy/IP" + separar leitura de escrita implica: conta dedicada só-leitura, mesmo IP doméstico, sessão em arquivo; GitHub Actions (IP de datacenter variável) quebra o "ambiente normal da conta".
- Acesso anônimo hoje é limitado e redirecionado para login (strings do yt-dlp e commit do instaloader); para reels, `yt-dlp --cookies-from-browser` funciona com cookies de conta secundária, com risco de invalidação. Não há evidência documental de bloqueio de IP doméstico por leitura de baixo volume; o padrão é checkpoint/desativação da conta usada.

### Gaps
- Taxa real de challenge para 50 contas/dia não medida; limites numéricos diários não publicados; preços de Bright Data/Decodo/Oxylabs e endpoint "user medias" do HikerAPI não verificados.

---

## 8. Instagram — postura legal e anti-scraping da Meta (2024-2026)

### Takeaway
A jurisprudência americana (hiQ v. LinkedIn; Meta v. Bright Data, jan/2024; X v. Bright Data, mai/2024) favorece a coleta de dados **públicos sem login**, mas os Termos do Instagram (2026) proíbem coleta automatizada "independentemente de … estar conectado", e a Meta aplica isso por desativação de contas, cease-and-desist e processos contra operações comerciais (Octopus, Voyager Labs, clone sites com 350 k perfis). Para 50 contas/5 posts por dia o risco de litígio é desprezível; o risco real é técnico (checkpoint/ban da conta que fizer login).

### Cited Findings
- Meta v. Bright Data (N.D. Cal., 3:23-cv-00077): em 2024-01-23/24 o tribunal negou summary judgment à Meta por quebra de contrato — Bright Data coletou dados públicos como "visitor" deslogada, não "user"; contornar CAPTCHA "is different from accessing a password-protected website" — [Fonte](https://techcrunch.com/2024/01/24/court-rules-in-favor-of-a-web-scraper-bright-data-which-meta-had-used-and-then-sued/); X Corp v. Bright Data rejeitado em maio/2024 — [Fonte](https://www.reuters.com/legal/musks-x-corp-loses-lawsuit-against-israeli-data-scraping-company-2024-05-10/), [Fonte](https://en.wikipedia.org/wiki/Bright_Data).
- hiQ v. LinkedIn: 9º Circuito reafirmou em 2022-04-18 após o GVR pós-Van Buren; em nov/2022 o distrito concluiu que a hiQ violou o User Agreement; acordo em dez/2022 — [Fonte](https://cdn.ca9.uscourts.gov/datastore/opinions/2022/04/18/17-16783.pdf), [Fonte](https://www.natlawreview.com/article/hiq-and-linkedin-reach-proposed-settlement-landmark-scraping-case), [Fonte](https://en.wikipedia.org/wiki/HiQ_Labs_v._LinkedIn).
- Meta v. Voyager Labs (2023-01-12; contas falsas para raspar dados visíveis a usuário logado; "We disabled Voyager's accounts"; acordo com injunção permanente em 2024-12-13) — [Fonte](https://about.fb.com/news/2023/01/leading-the-fight-against-scraping-for-hire/). Meta v. Octopus e Ekrem Ateş (2022-07-05; scraping a partir de contas logadas de clientes; Ateş "used automated Instagram accounts to scrape data from the profiles of over 350,000 Instagram users"; Meta desativou contas, enviou cease-and-desist e revogou acesso) — [Fonte](https://about.fb.com/news/2022/07/actions-against-scraping-for-hire/); posts anteriores "How We Combat Scraping" (2021) e "Taking Legal Action Against Data Scraping" (2020) — [Fonte](https://about.fb.com/news/2021/04/how-we-combat-scraping/), [Fonte](https://about.fb.com/news/2020/10/taking-legal-action-against-data-scraping/). Nenhum post de 2024-2026 sobre novos processos encontrado no newsroom.
- Termos de Uso do Instagram (pt-BR, © 2026, seção 4.2): "Você não pode … acessar ou coletar informações de forma automatizada sem nossa permissão expressa, independentemente desse acesso ou dessa coleta automatizada ser realizada enquanto estiver conectado a uma conta do Instagram"; "você não pode criar uma conta para outra pessoa"; proíbe vender/licenciar dados — [Fonte](https://help.instagram.com/581066165581870). "Automated Data Collection Terms" da Meta (vigentes desde 2024-10-07): "You will not engage in Automated Data Collection without first obtaining Meta's express written permission" — [Fonte](https://www.facebook.com/apps/site_scraping_tos_terms.php).
- Medidas técnicas (evidência em código): yt-dlp trata redirecionamento para `/accounts/login` como rate-limit anônimo — [Fonte](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/instagram.py); instaloader documenta limites "significantly stricter" para anônimos — [Fonte](https://instaloader.github.io/troubleshooting.html); RSSHub marca a rota como `antiCrawler: true` — [Fonte](https://github.com/DIYgod/RSSHub/blob/master/lib/routes/instagram/index.ts); `picuki.com` e `imginn.com` responderam HTTP 403 a um GET simples em 2026-11-07 (verificação própria do pesquisador).

### Inferences
- A cláusula "independentemente de … estar conectado" parece resposta ao fundamento de Bright Data; para quem não faz login a tese contratual da Meta segue fraca nos EUA, mas como o Instagram quase não entrega conteúdo sem login, todo caminho não oficial implica uma conta logada → violação contratual com sanção típica = desativação dessa conta.
- Risco realista (50 contas, 5 posts/dia): litígio ≈ zero; checkpoint/ban da conta secundária baixo-médio; impacto na conta principal baixo se ela nunca for usada pelo script e dispositivo/IP não forem compartilhados de forma suspeita **[INCERTO]**. LGPD/Brasil: sem fonte; não avaliado.

### Gaps
- Desfecho final de Meta v. Bright Data após jan/2024 e data exata do "login wall" para perfis/posts: não verificados.

---

## 9. Instagram — serviços de terceiros (Apify, HikerAPI, Bright Data, ScrapeCreators, EnsembleData, RapidAPI), RSSHub/RSS-Bridge e espelhos

### Takeaway
Apify `apify/instagram-scraper` (pay-per-event, **US$0,0027/resultado no plano Free**, 99,6% de runs bem-sucedidos em 19 M runs/30 dias) e HikerAPI (**US$0,001/request** pré-pago, saldo não expira) são os fallbacks mais baratos e maduros; Bright Data tem free tier de 5 k registros/mês (KYC); RSSHub self-hosted segue mantido (commit 2026-11-05) mas exige cookie `sessionid`/`ds_user_id`; RSS-Bridge usa `query_hash` legado e está sem mantenedor; espelhos (Picuki/Imginn) bloqueiam bots.

### Cited Findings
- Apify planos: Free US$0 com US$5/mês de uso incluído; **Starter US$19/mês**; Scale US$199; Business US$999; CU (1 GB-RAM-hora) US$0,20; proxy residencial US$8/GB; Free: 5 runs concorrentes, uso não acumula — [Fonte](https://apify.com/pricing).
- `apify/instagram-scraper`: `pricingModel: PAY_PER_EVENT`, evento "Result" = "Each result written to the dataset": FREE US$0,0027, BRONZE 0,0023, SILVER 0,0019, GOLD 0,0015, PLATINUM 0,0009, DIAMOND 0,0005; 30 dias: 19.154.201 runs, 99,59% SUCCEEDED; 472.172 usuários; nota 4,67 (605 avaliações) — [Fonte](https://api.apify.com/v2/store?search=instagram); Store: "starts at $1.50 per 1,000 results" (Free US$2,70/1k, Starter 2,30, Scale 1,90, Business 1,50) — [Fonte](https://apify.com/apify/instagram-scraper). Outros atores (preço FREE / sucesso 30 d): `apify/instagram-profile-scraper` US$0,0026/profile, 99,62%; `apify/instagram-post-scraper` US$0,0017/post, 99,88%; `apify/instagram-reel-scraper` US$0,0026/reel (+ evento `actor-start`), 99,85%; `apify/instagram-api-scraper` US$0,0023, 98,94% — [Fonte](https://api.apify.com/v2/store?search=instagram).
- Inputs do `instagram-scraper`: `directUrls` (URL deve casar com o tipo: `/p/`, `/reel/`, `/username/`), `resultsType` (`posts`|`details`|`comments`), `resultsLimit` (por URL), `onlyPostsNewerThan` ("YYYY-MM-DD", ISO ou relativo como `1 day`, UTC), `addParentData`, `search`/`searchType`/`searchLimit`; saída (posts): `id`, `type`, `shortCode`, `caption`, `hashtags`, `mentions`, `url`, `commentsCount`, `firstComment`, `latestComments`, `displayUrl`, `images`, `videoUrl`, `timestamp`, `likesCount`, `ownerUsername`, `ownerFullName`, `ownerId`, `childPosts`, `isCommentsDisabled`; Free: só 15 comentários/1 página por post — [Fonte](https://apify.com/apify/instagram-scraper).
- `apify-client` 3.4.0 (2026-10-27, py≥3.11); token no construtor `ApifyClient('MY-APIFY-TOKEN')`, sem menção a variável de ambiente — [PyPI](https://pypi.org/pypi/apify-client/json). Exemplo (Store): `client.actor("apify/instagram-scraper").call(run_input={"directUrls": [...], "resultsType": "posts", "resultsLimit": 3, "onlyPostsNewerThan": "1 day"})` → `client.dataset(run["defaultDatasetId"]).iterate_items()` — [Fonte](https://apify.com/apify/instagram-scraper).
- HikerAPI: "Pay-as-you-go from $0.0006 per request" (volume) e US$1/1k ("popular"); 100 requisições grátis; saldo pré-pago "never expires"; cobra respostas 200/400/403/404, não 50x/410; base `https://api.hikerapi.com`, header `x-access-key`; endpoints `/v2/user/by/username`, `/v2/media/info/by/url`, `/v2/media/comments?code=`, `/v1/user/following/chunk` — [Fonte](https://hikerapi.com/pricing), [Fonte](https://hikerapi.com/).
- Bright Data Instagram Scraper API: PAYG US$1,5/1k registros, "Pay only for success"; free tier 5 k registros/mês sem cartão (renova dia 1); datasets profiles/posts/reels/comments; KYC + compliance review; "Only publicly available data" — [Fonte](https://brightdata.com/products/web-scraper/instagram).
- ScrapeCreators: Free 100 créditos; Freelance US$47 = 25.000 créditos (~US$1,88/1k); Business US$497 = 500.000; "credits never expire"; base `https://api.scrapecreators.com`, header `x-api-key`, ex. `GET /v1/instagram/profile?handle=…` — [Fonte](https://scrapecreators.com/). EnsembleData: trial 50 unidades/dia; Wood US$100/mês (1.500/dia) … Platinum US$1.400; user info 3 unidades, post info 2 — [Fonte](https://ensembledata.com/pricing).
- RSSHub: rota `/instagram/:category/:key` (`user | stories | highlights | tags`), `requireConfig: INSTAGRAM_COOKIE` (só `sessionid` e `ds_user_id`), `antiCrawler: true`; stories/highlights/hashtags e contas privadas exigem cookie; recomenda Redis; último commit na rota 2026-11-05 "fix(route/instagram): use api on non-image posts" — [Fonte](https://github.com/DIYgod/RSSHub/blob/master/lib/routes/instagram/index.ts), [Fonte](https://github.com/DIYgod/RSSHub/blob/master/lib/config.ts). RSS-Bridge `InstagramBridge.php`: config `session_id`, `ds_user_id`; `graphql/query/?query_hash=` com hashes fixos; `MAINTAINER` comentado; última alteração 2026-10-04 (cosmética); último release do projeto 2025-08-05 — [Fonte](https://github.com/RSS-Bridge/rss-bridge/blob/master/bridges/InstagramBridge.php). Espelhos: `picuki.com`, `imginn.com` → 403; `dumpor.io` → 200 (verificação do pesquisador em 2026-11-07).

### Inferences
- Pay-per-event cobra por item retornado: 50 perfis/dia com `resultsLimit: 3` = 4.500 resultados/mês (~US$12) — combine `onlyPostsNewerThan: "1 day"` + `resultsLimit` baixo + dedupe por `shortCode` para pagar só pelos posts novos (~US$0,4/mês no cenário de 150 posts).
- RSS-Bridge depende de `query_hash` que o Instagram substituiu por `doc_id` (o que yt-dlp e RSSHub usam) → tratar como quebrado **[INCERTO]**. RapidAPI (`instagram-scraper-api2`, `instagram120`, "Instagram Scraper Stable API"): não verificado; checar latência/uptime, data de atualização e assinantes na página.
- `?__a=1&__d=dis` não é mais caminho confiável (migração geral para `api/v1`/`doc_id`) **[INCERTO]**.

### Gaps
- Preço do evento `actor-start` do reel-scraper e cobrança mínima por run; custos por endpoint do ScrapeCreators; validade do free tier da Bright Data para a Scraper API sem contrato; validade do cookie `sessionid`.

---

## 10. Instagram — recomendação híbrida ("varrer as páginas que sigo todo dia") e estimativa de custo mensal

### Takeaway
Arquitetura recomendada: **(a)** Business Discovery oficial para alvos Business/Creator (seção 5); **(b)** HikerAPI (ou Apify com `onlyPostsNewerThan`) só para contas pessoais; **(c)** inbox "share to" (bot do Telegram ou e-mail para si mesmo, reaproveitando o canal Gmail) para o que você quiser marcar manualmente; **(d)** extração multimodal: caption + visão com Claude (Haiku por padrão; tokens = ⌈w/28⌉×⌈h/28⌉) + transcrição local com `faster-whisper`. Custo total ≈ **US$1,6–3/mês** nos cenários de 150–1.500 posts/mês.

### Cited Findings
- Telegram Bot API: updates "will not be kept longer than 24 hours"; `offset` confirma updates; `timeout` default 0 (short polling); `getUpdates` não funciona com webhook ativo; links chegam em `message.text` com `entities[].type == "url"` — [Fonte](https://core.telegram.org/bots/api#getupdates). Libs: `python-telegram-bot` 22.8 (2026-06-12, py≥3.10) — [PyPI](https://pypi.org/pypi/python-telegram-bot/json); `aiogram` 3.31.0 (2026-08-26) — [PyPI](https://pypi.org/pypi/aiogram/json); `telethon` 1.45.0 (2026-09-10) — [PyPI](https://pypi.org/pypi/telethon/json).
- Resolução de link por URL: Apify `directUrls: ["https://www.instagram.com/p/<shortcode>/"]` + `resultsType: "posts"` — [Fonte](https://apify.com/apify/instagram-scraper); HikerAPI `/v2/media/info/by/url` — [Fonte](https://hikerapi.com/); yt-dlp com cookies — [Fonte](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/instagram.py). O oEmbed oficial **não** devolve mais autor/thumbnail (seção 6).
- Visão Claude (doc atual): "Each patch is a 28×28-pixel block … An image, therefore, costs ⌈width / 28⌉ × ⌈height / 28⌉ visual tokens"; tiers Standard (lado longo 1.568 px / 1.568 tokens) e High-resolution (Claude 4.7+: 2.576 px / 4.784 tokens); 1000×1000 = 1.296 tokens; limites 8000×8000 px, 10 MB/imagem, até 600 imagens/request; "downsample images before sending to control token costs" — [Fonte](https://platform.claude.com/docs/en/build-with-claude/vision). Preços por 1 M tokens (tabela da skill `claude-api`, referência 2026-10-06): Haiku 5.5 US$0,10/0,50; Sonnet 5.5 US$2/10; Opus 5.5 US$4/20 — [Fonte](https://claude.com/pricing).
- Transcrição local: `faster-whisper` 1.2.1 (2025-10-31) — [PyPI](https://pypi.org/pypi/faster-whisper/json); `openai-whisper` 20250625 — [PyPI](https://pypi.org/pypi/openai-whisper/json). Preço de APIs de transcrição (OpenAI/Deepgram): sem fonte acessível nesta sessão.
- Exportação DYI (ajuda oficial pt-BR): Central de Contas → "Suas informações e permissões" → "Exportar suas informações" → "Criar exportação" → perfil → "Exportar para o dispositivo" → personalizar (tipos, intervalo, formato, qualidade) → "Iniciar a exportação"; "pode levar até 30 dias"; "quatro dias para exportar as informações na seção Downloads disponíveis" — [Fonte](https://help.instagram.com/181231772500920); parser terceiro confirma opções "Followers and following" + JSON e que "This is a manual process that cannot be automated" — [Fonte](https://github.com/cecobask/instagram-insights).

### Inferences
- Fluxo "share to": no app, Compartilhar → Telegram → chat do seu bot (iniciado com `/start`); o texto chega como `https://www.instagram.com/p/<shortcode>/?igsh=…` ou `/reel/<shortcode>/` **[INCERTO quanto ao parâmetro]** → normalizar com `instagram\.com/(p|reel|reels)/([A-Za-z0-9_-]+)`. Como updates expiram em 24 h, rodar o coletor a cada 6–12 h (1 `getUpdates`), ou usar webhook, ou compartilhar para um canal privado e ler o histórico via Telethon; a variante por e-mail (compartilhar para si mesmo) não expira e reaproveita a ingestão do Gmail.
- Tokens de visão por imagem do Instagram: 1080×1080 → 39×39 = 1.521; 1080×1350 → 1.911; 1080×566 → 819; reduzir para ~800 px de lado maior corta ~45% sem perder legibilidade. Reels: usar o `videoUrl` devolvido por Apify/HikerAPI (evita yt-dlp + cookies), extrair áudio com ffmpeg e transcrever com `faster-whisper` (`base`/`small` em CPU bastam para 30–90 s).
- Esquema interno único para todos os provedores: `{shortcode, owner, caption, media[], timestamp, type, source}`; camada de adaptação por fornecedor; dedupe por `shortcode`.
- Ranking (prós/contras/risco/custo, cenário 150 posts/mês): 1) API oficial — zero risco, só Business/Creator, US$0; 2) share-to (Telegram/e-mail) + resolução por URL — alta precisão, 1 toque por post, updates expiram em 24 h, US$0–0,50; 3) terceiros pagos (HikerAPI/Apify/ScrapeCreators/Bright Data free) — barato, sem conta própria em risco, roda em Actions, US$0,4–3; 4) RSSHub self-hosted — grátis, `antiCrawler`, cookie da secundária, Redis; 5) instagrapi — grátis, dados completos (inclui Salvos via `collections()` **[INCERTO]**), frágil, não roda em Actions; 6) instaloader — anônimo = 429/login wall; 7) RSS-Bridge/espelhos — quebra silenciosa.

### Estimativa de custo mensal
Premissas: cenário A = 150 posts/mês (5/dia); cenário B = 1.500 posts/mês (50 contas × 1/dia); 1 varredura diária de 50 perfis; imagem 1080×1080 = 1.521 tokens + ~700 tokens de prompt/caption + ~300 de saída por post.

| Componente | Base de preço | Cenário A (150) | Cenário B (1.500) |
|---|---|---|---|
| Apify `instagram-scraper`, 50 URLs/dia, `resultsLimit: 3` | US$0,0027/resultado (Free) → 4.500 res./mês | US$12,15 (excede os US$5 grátis → Starter US$19) | US$12,15 |
| Apify com `onlyPostsNewerThan: "1 day"` | US$0,0027/resultado | US$0,41 (dentro dos US$5 do Free) | US$4,05 |
| Apify `instagram-post-scraper` | US$0,0017/post | US$0,26 | US$2,55 |
| HikerAPI (1 request/perfil/dia + resoluções de URL) | US$0,001/req (US$0,0006 em volume) | US$1,50–1,65 | US$1,50–1,65 |
| ScrapeCreators (pacote 25 k créditos/US$47) | ~US$0,00188/crédito | ~US$2,80 amortizado | ~US$2,80 |
| Bright Data | US$1,5/1k; 5 k grátis/mês | US$0 (free tier) | US$0 (free tier) / US$2,25 |
| EnsembleData | mínimo Wood US$100/mês | US$100 (inviável) | US$100 |
| Visão Claude — Haiku 5.5 | ~US$0,00037/post | US$0,06 | US$0,56 |
| Visão Claude — Sonnet 5.5 | ~US$0,0074/post | US$1,12 | US$11,2 |
| Visão Claude — Opus 5.5 | ~US$0,0149/post | US$2,23 | US$22,3 |
| Transcrição (faster-whisper local) | US$0 | US$0 | US$0 |
| Proxy residencial (só rota instagrapi) | US$7,35–8/GB | ~US$7–8 | ~US$7–8 |
| **Total recomendado** (BD oficial + HikerAPI p/ pessoais + share-to + Haiku 5.5) | — | **≈ US$1,6–2/mês** | **≈ US$2–3/mês** (Sonnet: +US$11) |

### Modos de falha e mitigações (Instagram não oficial/terceiros)
- `challenge_required`/`LoginRequired` (instagrapi; issue #2890) → conta secundária só-leitura, `load_settings` antes de `login`, `delay_range=[1,3]`, polling de minutos, nunca em Actions; TOTP automatizado; pausar e alertar em vez de retentar.
- 429 / "Please wait a few minutes" (instaloader #2786/#2750/#2726) → uma instância, `--latest-stamps`, `--abort-on 429`, backoff ≥1 h; migrar para HikerAPI/Apify.
- Login wall / cookie inválido (yt-dlp, RSSHub) → rotacionar `sessionid`/`ds_user_id`; preferir `videoUrl` já retornado pelo fornecedor.
- Custo Apify por resultado explode → `onlyPostsNewerThan` + `resultsLimit` baixo + dedupe por `shortCode` + alerta de gasto.
- Bot do Telegram perde links (>24 h) → coletor a cada 6–12 h, webhook, ou canal privado + Telethon; fallback por e-mail.
- Fornecedor muda endpoint/preço (HTTP 410 etc.) → camada de adaptação + schema interno.
- Export DYI atrasa (até 30 dias, link válido 4 dias) → pedido mensal agendado; cache do último `following.json`; nunca depender dele no diário.
- Conta principal afetada → nunca usar credenciais/cookies da principal; secundária em dispositivo/IP próprio, só leitura.
- Carrosséis multiplicam custo de visão → ≤800 px, 3–4 imagens por carrossel, Haiku por padrão.

### Gaps
- Formato exato do texto compartilhado pelo app do Instagram para o Telegram (parâmetro `igsh`) — validar com teste; custo por minuto de APIs de transcrição; estrutura exata dos arquivos do export (`following.json`, `saved_posts.json`) — validar no próprio ZIP (parser tolerante: `**/following*.json`, `**/saved_posts*.json`).

---

## 11. GitHub — REST Search API, GraphQL, rate limits, cabeçalhos e token

### Takeaway
`GET /search/repositories` com qualificadores `created:>…`, `pushed:>…`, `stars:>=n`, `topic:…`, `language:…`, `archived:false` e `sort=stars|updated` resolve "repositórios novos/quentes por tópico" dentro de 30 req/min autenticado (10 não autenticado), máx. 1.000 resultados e 100 por página. Um fine-grained PAT sem nenhuma permissão extra já lê todos os repositórios públicos; em GitHub Actions `GITHUB_TOKEN` dá 1.000 req/h por repositório.

### Cited Findings
- Search: "you can make up to 30 requests per minute for all search endpoints except for the Search code endpoint"; não autenticado "up to 10 requests per minute"; code search exige auth e "limits you to 10 requests per minute"; "up to 1,000 results for each search"; `per_page` "(max 100)"; `sort` = `stars`, `forks`, `help-wanted-issues`, `updated` (default best match); `order` `desc`/`asc` "ignored unless you provide sort"; timeouts → `incomplete_results: true`; 422 "Validation failed, or the endpoint has been spammed"; `Accept: application/vnd.github+json` recomendado; exemplos usam `X-GitHub-Api-Version: 2026-03-10` — [Fonte](https://docs.github.com/en/rest/search/search).
- Versões da REST API suportadas: `2026-03-10` (sem fim de suporte agendado) e `2022-11-28` (fim 2028-03-10); "API versions are supported for 24 months after a newer API version is released"; sem header → `2022-11-28`; versão não suportada → `410 Gone` — [Fonte](https://docs.github.com/en/rest/about-the-rest-api/api-versions).
- Rate limits primários: não autenticado 60 req/h; PAT "personal rate limit of 5,000 requests per hour"; "The rate limit for `GITHUB_TOKEN` is 1,000 requests per hour per repository"; secundários: ≤100 requisições concorrentes, 900 pontos/min REST (GET = 1 ponto), 90 s de CPU por 60 s; estouro → 403/429 + `retry-after` / `x-ratelimit-reset` — [Fonte](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).
- "Making a conditional request does not count against your primary rate limit if a `304` response is returned" (requer `Authorization`); fazer requisições em série, não concorrentes; usar `link` headers para paginar — [Fonte](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api).
- GraphQL: "5,000 points per hour per user"; `GITHUB_TOKEN` "1,000 points per hour per repository"; custo = requisições necessárias ÷ 100 (mín. 1); `first`/`last` 1–100; ≤500.000 nós; consultar `rateLimit { cost remaining resetAt }` — [Fonte](https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api).
- Qualificadores de repositório (exemplos oficiais): `created:<2011-01-01` (com hora opcional), `pushed:>2013-02-01`, `pushed:>=2013-03-06`, `stars:>=500`, `stars:10..20`, `topic:jekyll`, `topics:>3`, `language:javascript`, `archived:false`, `is:public`, `fork:true|only` (forks excluídos por padrão), `in:name,description`, `in:topics`, `in:readme`, `license:apache-2.0`, `mirror:false`; qualificadores combináveis "in any combination" — [Fonte](https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories).
- Fine-grained PAT: "Tokens always include read-only access to all public repositories on GitHub"; expiração padrão 30 dias; `expires_in` "Integer between 1 and 366, or `none`"; "Infinite lifetimes are allowed but may be blocked by a maximum lifetime policy"; classic tokens sem uso por 1 ano são removidos; criação: Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token — [Fonte](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
- Sondagem ao vivo (2026-11-07): consultas `search/repositories?q=topic:<x>&per_page=3&sort=stars` com PAT devolvem `x-ratelimit-remaining` decrescendo de 30 por minuto (janela de search); sem token, após poucas chamadas de outros processos, `api.github.com` devolveu "API rate limit exceeded for <IP>" — limite por IP compartilhado entre todas as ferramentas da máquina.

### Inferences
- Para um job diário, 10–30 queries de search (uma por tópico/segmento) + `per_page=100` ficam muito abaixo dos limites; serializar as chamadas e respeitar `retry-after`.
- Pinar `X-GitHub-Api-Version: 2026-03-10` (ou manter `2022-11-28`, válido até 2028-03-10) e tratar `410`.
- Queries prontas: `topic:medical-imaging created:>2026-11-01 stars:>5 sort:stars` (via `sort=stars` no parâmetro); `topic:mcp-server created:>2026-11-06` (ordenar por `stars`); `fhir language:python pushed:>2026-11-06 stars:>50` (`sort=updated`); `"model context protocol" in:name,description,topics created:>2026-11-06`.
- Token: fine-grained PAT com "Public repositories (read-only)" e **nenhuma** permissão, expiração 366 dias com lembrete; variável `GITHUB_TOKEN` (o `gh` também lê `GH_TOKEN`). Em Actions, `secrets.GITHUB_TOKEN` basta (1.000 req/h/repo).

### Gaps
- A página da Search API não documenta limites secundários específicos de search além do 422 "spammed".

---

## 12. GitHub — "Trending": alternativas ao github.com/trending (sem API oficial)

### Takeaway
Não há API oficial de Trending; **a API pública do OSS Insight para trending está inoperante desde 2026-03-01** (resposta ao vivo com `data_quality.status: "unavailable"`), o proxy comunitário `gh-trending-no-cors` está offline, e os scrapers pagos (Apify) parseiam HTML. A alternativa estável é compor "trending" com a própria Search API (`created:>N dias stars:>X sort=stars` para novos; `pushed:>1d stars:>1000 sort=updated` para ativos), velocidade de estrelas via GH Archive/BigQuery (`WatchEvent`) para uma lista de candidatos, e diff diário de "awesome lists".

### Cited Findings
- "As of 2026, GitHub publishes no official API or bulk-export endpoint for the Trending page" (post comunitário) — [Fonte](https://dev.to/agenthustler/free-github-scraping-api-in-2026-no-signup-required-4ihb); `gh-trending-no-cors`: "the API is temporarily offline" (Heroku) — [Fonte](https://github.com/lissy93/gh-trending-no-cors); atores Apify de trending cobram aprox. US$0,30–US$20 por 1.000 resultados (preços da Store, não verificados individualmente) — [Fonte](https://apify.com/nexgendata/github-trending-scraper), [Fonte](https://apify.com/trepanat0r/github-trending), [Fonte](https://apify.com/gazidev/github-repo-data).
- OSS Insight: base `https://api.ossinsight.io/v1`; sem chave (beta); 600 req/h por IP e 1.000 req/min globais, com headers `x-ratelimit-*`; endpoint "List trending repos" `GET https://api.ossinsight.io/v1/trends/repos/?period=past_24_hours&language=All` — [Fonte](https://ossinsight.io/docs/api), [Fonte](https://ossinsight.io/docs/api/list-trending-repos).
- **Resposta ao vivo em 2026-11-07** a esse endpoint: `rows: []` com `data_quality: {status: "unavailable", metric: "github_event_derived_ranking", unavailable_since: "2026-03-01", reason: "…our capture of those events fell to roughly 0.3% of baseline, so the ordering would be noise…", alternative: "use /gh/repos/{owner}/{repo} for star and fork counts, or /v1/collections/{id}/repos", docs: "https://ossinsight.io/docs/data-quality"}` — (sondagem direta; ver também [Fonte](https://ossinsight.io/docs/data-quality)).
- OSS Insight ainda oferece coleções: `list-collections`, `list-hot-collections`, `collection-repo-ranking-by-stars|prs|issues`, `list-repos-of-collection` — [Fonte](https://ossinsight.io/docs/api).
- GH Archive: arquivos horários `https://data.gharchive.org/YYYY-MM-DD-H.json.gz` (desde 2011-02-12); BigQuery dataset público `githubarchive` com tabelas `day.YYYYMMDD`, `month.YYYYMM`, `year.YYYY`, atualizado de hora em hora; "1 TB of data processed per month free of charge"; `payload` é string JSON — [Fonte](https://www.gharchive.org/).
- Tipos de evento: `WatchEvent` = "A user stars a repository (historically referred to as 'watching')" (payload `action: started`); `CreateEvent` = branch/tag criada; `ReleaseEvent`; `ForkEvent`; `PublicEvent`; `PushEvent` etc. — [Fonte](https://docs.github.com/en/rest/using-the-rest-api/github-event-types).
- Feeds Atom sem autenticação: `https://github.com/{owner}/{repo}/releases.atom` respondeu `200 application/atom+xml` (sondagem ao vivo em `modelcontextprotocol/python-sdk`); `feedparser` 6.0.14 (2026-07-30) — [PyPI](https://pypi.org/project/feedparser/).

### Inferences
- Ranking recomendado: (1) Search API como proxy de trending (estável, oficial, grátis); (2) BigQuery/GH Archive para "star velocity" — contar `WatchEvent` por `repo.name` nas tabelas `githubarchive.day.*` dos últimos 1–7 dias, filtrando por uma lista de candidatos (GH Archive não tem tópicos; cruzar com a Search API) — custo zero dentro de 1 TB/mês se restringir o intervalo; (3) diff diário de awesome lists via `raw.githubusercontent.com` (links novos = sinal); (4) scraping de `github.com/trending?since=daily` só como último recurso (HTML sem contrato, sujeito a bloqueio); (5) atores Apify se quiser pagar pela conveniência.
- Para releases de repositórios-chave, os feeds Atom (`releases.atom`, `tags.atom`, `commits/{branch}.atom`) não gastam rate limit e já se encaixam na fonte RSS existente do `sotawhat`; a REST `GET /repos/{owner}/{repo}/releases` / `/releases/latest` ([doc](https://docs.github.com/en/rest/releases/releases), não re-lida nesta sessão) serve quando precisar de `published_at`/`prerelease` estruturados, com `If-None-Match` para não gastar quota.

### Gaps
- Nenhuma fonte oficial do OSS Insight anunciando a quebra além do próprio payload `data_quality`; a página `docs/data-quality` não foi lida.
- Preços exatos/atuais dos atores Apify de trending não verificados nas páginas individuais.

---

## 13. GitHub — tópicos e queries relevantes (IA∩medicina; agentes/MCP/skills), contagens em 2026-11-07

### Takeaway
Tópicos populados (contagem via `search/repositories?q=topic:<x>`, 2026-11-07): IA∩medicina — `medical-imaging` 7.085, `healthcare-ai` 3.316, `fhir` 2.361, `medical-ai` 2.258, `ehr` 731, `medical-image-analysis` 700, `radiology` 650, `biomedical` 596, `pathology` 495, `clinical-nlp` 429, `digital-pathology` 346, `monai` 248; `medical-llm` 39 e `healthcare-llm` 1 são inúteis. Agentes — `mcp` 113.544, `claude-code` 112.858, `model-context-protocol` 42.253, `mcp-server` 41.322, `agent-skills` 40.437, `claude-skills` 14.791, `claude-code-plugin` 14.284, `claude-skill` 7.103, `agent-skill` 6.502, `mcp-servers` 1.376, `claude-code-plugins` 977.

### Cited Findings
- Contagens acima: sondagem ao vivo com PAT em 2026-11-07 (endpoint [search/repositories](https://docs.github.com/en/rest/search/search)); repositório mais estrelado por tópico: `Project-MONAI/MONAI` (monai), `TorchIO-project/torchio` (medical-image-analysis), `maziyarpanahi/openmed` (clinical-nlp), `openemr/openemr` (fhir, ehr), `mahmoodlab/CLAM` (pathology, digital-pathology), `allenai/scispacy` (biomedical), `sunlabuiuc/PyHealth` (medical-ai), `the-momentum/open-wearables` (healthcare-ai), `n8n-io/n8n` (mcp-server), `PrefectHQ/fastmcp` (mcp-servers), `HKUDS/nanobot` (model-context-protocol), `thedotmack/claude-mem` (claude-skills).
- Volume de novidades: `topic:mcp-server created:>2026-11-05` → 373 repositórios em ~2 dias; `topic:agent-skills created:>2026-10-25` → 4.393; `topic:claude-skills created:>2026-10-25` → 1.758; `topic:medical-imaging created:>2026-10-01 stars:>5` → 8 (ex.: `MIC-DKFZ/nninteractive-agent` 78★, `MedMLX/medmlx` 28★, `gyorgysh/openradview` 24★) — sondagem ao vivo.
- Code search: `q=filename:SKILL.md` → 7.159.808 resultados; `q=path:SKILL.md` (sintaxe nova) → 103 (a REST code search usa a sintaxe legada) — sondagem ao vivo com PAT ([doc](https://docs.github.com/en/rest/search/search)).

### Inferences
- Para o perfil `medico`, combinar tópicos com termos e um piso de estrelas: `(topic:medical-imaging OR topic:medical-ai OR topic:healthcare-ai OR topic:fhir OR topic:clinical-nlp OR topic:radiology OR topic:pathology OR topic:digital-pathology OR topic:biomedical OR topic:monai OR topic:ehr) created:>{D-7} stars:>3` (uma query por tópico é mais simples do que `OR` longo; o GitHub limita operadores por query) e um segundo passe por termos: `"medical" "LLM" in:name,description created:>{D-7}`.
- Para agentes/MCP/skills, o volume (centenas/dia) exige piso de estrelas/forks e dedupe contra o registry oficial e marketplaces (seções 15–18); `filename:SKILL.md <palavra-chave>` (ex.: `fhir filename:SKILL.md`) é útil para achar skills de domínio, mas 10 req/min.

### Gaps
- O limite de operadores/tamanho de query da Search não consta na página lida (de memória: 256 caracteres e 5 `AND/OR/NOT`) — **[INCERTO]**.

---

## 14. GitHub — ferramentas (`gh` CLI, PyGithub, ghapi, httpx) e rastreamento de releases

### Takeaway
Para o `sotawhat` (já em `httpx` + `feedparser`), chame a REST diretamente com `httpx` (3 headers, `ETag`, backoff) e use feeds Atom para releases; `gh` (2.101.0 instalado localmente) é ótimo para prototipar (`gh search repos --topic … --created ">2026-11-01" --sort stars --json …`); PyGithub 2.10.0 (2026-08-20) só compensa se quiser objetos e paginação prontos.

### Cited Findings
- PyGithub 2.10.0 (2026-08-20, py≥3.10) — [PyPI](https://pypi.org/project/PyGithub/); ghapi 2.1.5 (2026-10-27) — [PyPI](https://pypi.org/project/ghapi/); httpx 0.28.1 (2024-12-06) — [PyPI](https://pypi.org/project/httpx/); `gh version 2.101.0 (2026-09-15)` instalado nesta máquina (sondagem local).
- Conditional requests com `etag`/`if-none-match` → `304` não conta na quota; paginar pelos `link` headers — [Fonte](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api).
- `releases.atom` público e sem auth (sondagem ao vivo, `200 application/atom+xml`).

### Inferences
- `httpx.Client(headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10", "Authorization": f"Bearer {GITHUB_TOKEN}", "User-Agent": "sotawhat/2.0"})`; guardar `ETag` por URL em SQLite; respeitar `retry-after`; nunca paralelizar.
- Lista de repositórios-chave (ex.: `Project-MONAI/MONAI`, `modelcontextprotocol/*`, `anthropics/skills`, `anthropics/claude-plugins-official`, `huggingface/huggingface_hub`) → `releases.atom` via a fonte RSS existente; para "novo repositório ganhou release" use `ReleaseEvent` no GH Archive.

### Gaps
- Nenhum.

---

## 15. Registry oficial MCP (registry.modelcontextprotocol.io): API v0.1, polling diário e código

### Takeaway
A API viva é **`/v0.1`** (o `/v0` legado responde igual), leitura pública sem autenticação: `GET /v0.1/servers?limit≤100&cursor=…&updated_since=<RFC3339>&search=<≥3 chars>&version=latest`, resposta `servers[]{server{...}, _meta{"io.modelcontextprotocol.registry/official"{status, publishedAt, updatedAt, isLatest,...}}}` + `metadata{count, nextCursor}`. O serviço se declara **preview** ("breaking changes or data resets may occur before GA"), com API freeze da v0.1 desde 2025-10-24; servidor em produção na versão 1.8.8 (build 2026-11-06). Polling diário = `updated_since` do último checkpoint + paginação por cursor.

### Cited Findings
- OpenAPI (título "Official MCP Registry", `info.version` 1.0.0): paths `/v0.1/servers` (GET), `/v0.1/servers/{serverName}/versions` (GET), `/v0.1/servers/{serverName}/versions/{version}` (GET/PUT), `/publish`, `/auth/*`, `/health`, `/ping`, `/version`; `/v0` com os mesmos paths (operationIds `-v0`); parâmetros de `GET /v0.1/servers`: `cursor`, `limit` (default 30, mín. 1, máx. 100), `updated_since` (RFC3339), `search` ("nonempty searches require at least 3 characters"), `version` (`latest` ou exata), `include_deleted` (default false; "always true when updated_since is provided"); `ServerJSON` exige `$schema`, `name`, `description`, `version` (opcionais `title`, `websiteUrl`, `icons`, `packages`, `remotes`, `repository`, `_meta`); `_meta["io.modelcontextprotocol.registry/official"]` exige `status`, `statusChangedAt`, `publishedAt`, `isLatest` (opcionais `updatedAt`, `statusMessage`); `metadata.count` + `metadata.nextCursor`; `status` ∈ {`active`, `deprecated`, `deleted`}; GETs sem `Authorization`; publish/edit exigem JWT do registry; `$schema` exemplo `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json` — [Fonte](https://registry.modelcontextprotocol.io/openapi.yaml).
- Sondagem ao vivo 2026-11-07: `GET /v0.1/servers?limit=1` e `GET /v0/servers?limit=1` → 200 com registros idênticos (`$schema` 2025-12-11, `remotes[]{type: streamable-http, url}`, `_meta` com `status: active`, `isLatest`), `metadata.nextCursor` no formato `<name>:<version>`; `GET /v0.1/servers?limit=1&updated_since=2026-11-05T00:00:00Z&version=latest` → registro publicado em 2026-11-05; `GET /v0.1/version` → `{"version":"1.8.8","git_commit":"d6b071e…","build_time":"2026-11-06T14:12:43Z"}`.
- Guia para agregadores: "an unauthenticated read-only REST API"; paginar com `limit=100` e `cursor=<nextCursor>`; incremental com `updated_since=2025-10-23T00:00:00.000Z`, "Keep the same timestamp while following every `nextCursor`", "save a new checkpoint only after all pages have been applied successfully", manter sobreposição e deduplicar por nome+versão; resultados incrementais "include deleted servers; apply those status changes"; `status: deleted` tipicamente = violação de moderação; agregadores "expected to scrape data on a regular but infrequent basis (e.g., once per hour)"; sem limites numéricos, "retry with backoff"; usar compressão; "does not provide uptime or data durability guarantees"; preview: "Breaking changes or data resets may occur before general availability"; `serverName` deve ser URL-encoded (`io.modelcontextprotocol%2Feverything`) — [Fonte](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/registry-aggregators.mdx).
- README: preview em 2025-09-08 ("breaking changes or data resets may occur"); "The Registry API has entered an API freeze (v0.1)" em 2025-10-24; namespaces validados na publicação (`io.github.<user>/…` via login GitHub; domínio reverso via DNS/HTTP); publicação pelo `mcp-publisher`, não por PR — [Fonte](https://github.com/modelcontextprotocol/registry). Anúncio do preview — [Fonte](https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/).
- Especificação genérica (subregistries): mesmos três GETs; `_meta` sob namespace `io.modelcontextprotocol.registry/official`; subregistries podem exigir auth — [Fonte](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/generic-registry-api.md).

### Inferences
- Polling diário (httpx):

```python
import json, os, httpx
BASE = os.getenv("MCP_REGISTRY_BASE_URL", "https://registry.modelcontextprotocol.io/v0.1")
STATE = "mcp_registry_state.json"            # {"checkpoint": "2026-11-06T00:00:00Z"}
state = json.load(open(STATE)) if os.path.exists(STATE) else {"checkpoint": "2026-11-05T00:00:00Z"}
since, cursor, seen, new_checkpoint = state["checkpoint"], None, {}, None
with httpx.Client(timeout=30, headers={"User-Agent": "sotawhat/2.0", "Accept-Encoding": "gzip"}) as c:
    while True:
        params = {"limit": 100, "updated_since": since, "version": "latest"}
        if cursor: params["cursor"] = cursor
        r = c.get(f"{BASE}/servers", params=params); r.raise_for_status()
        d = r.json()
        for item in d["servers"]:
            s, m = item["server"], item["_meta"]["io.modelcontextprotocol.registry/official"]
            key = f'{s["name"]}:{s["version"]}'
            seen[key] = {"name": s["name"], "version": s["version"], "status": m["status"],
                         "updatedAt": m.get("updatedAt"), "isLatest": m.get("isLatest"),
                         "description": s.get("description"), "repo": (s.get("repository") or {}).get("url"),
                         "remotes": s.get("remotes"), "packages": s.get("packages")}
            new_checkpoint = max(new_checkpoint or "", m.get("updatedAt") or m["publishedAt"])
        cursor = d.get("metadata", {}).get("nextCursor")
        if not cursor: break
# aplicar status (active/deprecated/deleted) ao índice local; só então gravar o checkpoint
json.dump({"checkpoint": new_checkpoint or since}, open(STATE, "w"))
```
- Ordenação: a lista é por nome (cursor `<name>:<version>`); "novo" = `publishedAt ≥ ontem`; "atualizado" = `updatedAt ≥ ontem`; filtrar `status == "active"` e `isLatest`.
- Filtros de domínio: `search=fhir|pubmed|clinical|medical|dicom|health` (substring em nome/título) são baratos (≤1 página cada hoje) e cabem no job diário; `search` com `updated_since` também funciona.

### Gaps
- Nenhum anúncio de GA encontrado até 2026-11-07 (busca retornou só o preview de 2025-09-08 e o freeze de 2025-10-24); a doc do repo continua dizendo "preview".
- Rate limits numéricos de leitura: não publicados.

---

## 16. Outros registries MCP: Smithery, Glama, PulseMCP, mcp.so, Docker MCP Catalog, awesome-mcp-servers

### Takeaway
Dos registries terceiros, **só o Docker MCP Catalog é machine-readable sem chave** (`https://desktop.docker.com/mcp/catalog/v2/catalog.yaml`, 510 KB, + `docker/mcp-registry/servers/*/server.yaml` + Docker Hub API do namespace `mcp`); Smithery e Glama exigem API key (Glama ainda impõe licença de atribuição visível); **a API pública v0beta do PulseMCP foi descontinuada (HTTP 410 `API_SUNSET`, 100% sunset em set/2026)** e a v0.1 é só para parceiros; mcp.so não tem API documentada; `punkpeye/awesome-mcp-servers` (97 k★, push em 2026-11-06) é a awesome list viva.

### Cited Findings
- Smithery: base `https://api.smithery.ai`, `GET /servers` (busca full-text/semântica por `q`; filtros de namespace, remote, deployed, verified, smithery-managed; `qualifiedName` depreciado em favor de `GET /servers/:namespace/:server`), auth Bearer; `GET /servers/{qualifiedName}/releases/{id}`, `PUT /servers/{qualifiedName}/releases` — [Fonte](https://smithery.ai/docs/api-reference/servers/list-all-servers) (página só renderiza via JS; a leitura direta retornou 404/redirect; conteúdo via resumo de busca). Sondagem ao vivo: `GET https://registry.smithery.ai/servers?q=fhir&pageSize=2` sem chave → `500 {"error":"An unexpected error occurred"}`.
- Glama: `GET https://glama.ai/api/mcp/v1/servers?first=2&query=fhir` → `401 {"code":"unauthorized","message":"This endpoint requires an API key. Create one at https://glama.ai/settings/api-keys. Use of this data is governed by the API Data License, which requires visible attribution to Glama on every page that displays it, and a link to a record's Glama listing…"}` — sondagem ao vivo; termos em [Fonte](https://glama.ai/policies/terms-of-service). Índice terceiro: Glama agrega >23.000 servidores open source, planos US$9/26/80 por mês — [Fonte](https://github.com/api-evangelist/glama) (não oficial).
- PulseMCP: `GET https://api.pulsemcp.com/v0beta/servers?query=fhir&count_per_page=3` → `410 {"error":{"code":"API_SUNSET","message":"The v0beta API is deprecated and being sunset… Starting January 2026: 1% of requests fail. Starting April 2026: 10%. Starting June 2026: 50%. September 2026: Fully sunset (100%). Please migrate to our v0.1 API at /api…"}}` — sondagem ao vivo. API v0.1: base `https://api.pulsemcp.com`, `GET /v0.1/servers` com `cursor`, `limit` (1–100, default 30), `updated_since`, `search` (substring em nomes/títulos), `version=latest`; `_meta["com.pulsemcp/server"]{visitorsEstimateMostRecentWeek, visitorsEstimateLastFourWeeks, visitorsEstimateTotal, isOfficial}` e `com.pulsemcp/server-version{source, status, publishedAt, updatedAt, isLatest}`; auth `X-API-Key` + `X-Tenant-ID`, "private B2B integration" para "trusted partners" via hello@pulsemcp.com; 200 req/min, 5.000/h, 10.000/dia; sem SLA 24/7; soft-delete com `status: deleted` — [Fonte](https://www.pulsemcp.com/api/docs/v0.1), [Fonte](https://www.pulsemcp.com/api).
- Docker: catálogo publicado em `https://hub.docker.com/mcp` e no MCP Toolkit do Docker Desktop; repo `docker/mcp-registry` com `servers/<Nome>/server.yaml` (campos observados: `name`, `image`, `type: server`, `meta.category`, `meta.tags[]`, `about.title|description|icon`, `source.project|branch|commit|directory`, `run.command|volumes`) — [Fonte](https://github.com/docker/mcp-registry), sondagem ao vivo em `servers/SQLite/server.yaml`; feed machine-readable `https://desktop.docker.com/mcp/catalog/v2/catalog.yaml` → `200 application/yaml` (510.469 bytes) com `version: 2`, `name: docker-mcp`, `registry{<id>: {description, title, type, dateAdded, image@sha256, readme, toolsUrl, source}}` — sondagem ao vivo; Docker Hub API `GET https://hub.docker.com/v2/repositories/mcp/?page_size=N` → `count: 245` repositórios no namespace `mcp` (com `pull_count`, `last_updated`) — sondagem ao vivo.
- Awesome lists (sondagem ao vivo, 2026-11-07): `punkpeye/awesome-mcp-servers` 97.433★ (push 2026-11-06); `appcypher/awesome-mcp-servers` 5.825★ (2026-05-06); `wong2/awesome-mcp-servers` 4.405★ (2026-07-13).

### Inferences
- Ranking para o job diário: (1) registry oficial (grátis, sem chave, `updated_since`); (2) Docker catalog YAML (grátis; `dateAdded` permite "novos de hoje"; `toolsUrl` dá a lista de tools); (3) diff diário do README de `punkpeye/awesome-mcp-servers` (categorias incluem healthcare?) via `raw.githubusercontent.com`; (4) Smithery com `SMITHERY_API_KEY` se quiser `useCount`/popularidade; (5) Glama só se aceitar a licença de atribuição; PulseMCP fora (parceiros).
- mcp.so: sem API encontrada; não incluir.

### Gaps
- Página da Smithery com os parâmetros exatos (`page`, `pageSize`, sintaxe `is:verified`) não pôde ser lida (JS); campos de resposta não confirmados. Afirmação terceira de que o "Smithery MCP Proxy" foi desligado em 31/out não verificada.
- Documentação oficial da API do Glama (parâmetros `first`/`after`/`query`) não encontrada; só o erro 401 informativo.
- Frequência de rebuild do catálogo Docker não documentada.

---

## 17. Servidores MCP de saúde existentes em 2026 (FHIR, PubMed, ClinicalTrials.gov, Medplum, OpenEMR, Epic/Oracle, AWS, BioMCP)

### Takeaway
O registry oficial já lista dezenas de servidores de saúde (FHIR, PubMed, ClinicalTrials.gov, DICOM), a Medplum publica um MCP oficial hospedado (`https://api.medplum.com/mcp/stream`, OAuth 2.0), a AWS mantém servidores para HealthLake (FHIR), HealthImaging (DICOM) e HealthOmics, BioMCP (genomoncology) é o hub biomédico mais completo (72 fontes) e a própria Anthropic mantém marketplaces `healthcare` e `life-sciences` com skills+MCP de FHIR/ICD-10/PubMed/ClinicalTrials. **Epic e Oracle Health não publicam MCP oficial** (só pontes de terceiros testadas no sandbox da Epic).

### Cited Findings
- Registry oficial, `search=fhir` (2026-11-07, 9 itens): `io.github.wso2/fhir-mcp-server` 0.11.0 (ativo, 2026-10-29, [repo](https://github.com/wso2/fhir-mcp-server)); `io.github.pcmedsinge/mcp-fhir` 1.1.1 ("FHIR R4 read/search/validate… US Core/IPS, SMART-on-FHIR", [repo](https://github.com/pcmedsinge/fhir-mcp-suite)); `io.github.faulkj/fhirhydrant` 0.17.3 ("SMART Backend Services, FHIRPath", [repo](https://github.com/faulkj/fhirHydrant)); `io.github.langcare/langcare-mcp-fhir` 2.0.4 ("MCP FHIR server written in Go for EMR systems like Epic and Cerner", [repo](https://github.com/langcare/langcare-mcp-fhir)); `io.fhirfly/mcp-server` 0.9.0 (dados de referência: providers, drugs, diagnoses, labs, [repo](https://github.com/FHIRfly-io/fhirfly-mcp-server)); `com.anpheros/fhir` 0.3.0 (sandbox com 30 pacientes sintéticos); `io.github.ChelseaKR/fhir-scorecard`; dois `io.github.CSOAI-ORG/*` com status `deprecated` — sondagem ao vivo em [registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=fhir&version=latest).
- `search=pubmed` (10 itens): `io.github.cyanheads/pubmed-mcp-server` 2.12.0 (2026-11-03, PubMed/Europe PMC + texto completo PMC/Unpaywall, [repo](https://github.com/cyanheads/pubmed-mcp-server)); `io.github.pipeworx-io/pubmed` 1.2.1 (E-utilities, sem chave, [repo](https://github.com/pipeworx-io/mcp-pubmed)); `io.github.u9401066/pubmed-search-mcp` 0.8.0 (PubMed + Europe PMC + OpenAlex); `io.github.melhzy/pubmed-stream` 0.4.4 ("build Obsidian knowledge…", [repo](https://github.com/melhzy/pubmed-stream)); `io.github.Taru0208/pubmed-mcp-server` (PubMed + ClinicalTrials.gov); `io.usefulapi/pubmed-ncbi-e-utilities` 1.2.4 (2026-11-07) — sondagem ao vivo.
- `search=clinical` (27 itens) inclui `io.github.cyanheads/clinicaltrialsgov-mcp-server` 2.11.1 (2026-11-04, [repo](https://github.com/cyanheads/clinicaltrialsgov-mcp-server)), `io.github.agentstructure/clinical` (ClinicalTrials.gov + registro europeu), `ai.hipa/clinical-trials`; `search=dicom` (6): `io.github.PantelisGeorgiadis/dicomweb-mcp-server` (QIDO-RS/WADO-RS), `io.github.NyxToolsDev/dicom-hl7-mcp-server`, `io.github.arunmk-ms/dicom-agent-mcp` (2026-11-02); `search=medical` (33) e `search=health` (50+, paginado) — sondagem ao vivo.
- Medplum: entrada oficial `com.medplum/mcp` 1.0.0 (ativo, publicado 2026-07-25, [repo](https://github.com/medplum/medplum)) — sondagem ao vivo; docs: endpoint `https://api.medplum.com/mcp/stream`, "OAuth 2.0 with the 6/18 auth spec", tools `fhir-request`, `search`, `fetch`, "You will need a paid plan to add integrations" (Claude.ai) — [Fonte](https://www.medplum.com/docs/ai/mcp); comunidade: `pymedplum` MCP local read-only por padrão (`uvx --from "pymedplum[mcp]" pymedplum-mcp`; `MEDPLUM_CLIENT_ID`/`MEDPLUM_CLIENT_SECRET` obrigatórios; `MEDPLUM_BASE_URL`, `MEDPLUM_ENABLE_WRITES` opcionais; tools FHIR CRUD, `$everything`, terminologia, GraphQL, bots) — [Fonte](https://pymedplum.readthedocs.io/en/latest/mcp/).
- BioMCP (genomoncology): CLI + servidor MCP, "72 biomedical sources" (PubMed/PubTator3, Europe PMC, ClinicalTrials.gov, MyVariant, cBioPortal, OpenFDA, NCI CTS, ClinVar, OncoKB, Reactome); instalação `uv tool install biomcp-cli` / `pip install biomcp-cli` (o pacote PyPI `biomcp` "is unrelated"), Homebrew, Docker `ghcr.io/genomoncology/biomcp`; MIT; 674★; README traz `mcp-name: io.github.genomoncology/biomcp` — [Fonte](https://github.com/genomoncology/biomcp). A busca `search=biomcp` no registry oficial retornou apenas `io.github.gucci10248/biomcp` e `io.github.yeyuan98/biomcp-ts` → o BioMCP da genomoncology **não aparece publicado** no registry oficial em 2026-11-07 (sondagem ao vivo).
- AWS (`awslabs/mcp`, 63 servidores listados): "AWS HealthOmics MCP Server", "HealthImaging MCP Server" ("21 tools for DICOM operations"), "HealthLake MCP Server" (FHIR) — [Fonte](https://awslabs.github.io/mcp/).
- Epic/athenahealth: guia terceiro (revisado 2026-11-02) afirma não ter encontrado MCP público documentado da Epic ou athenahealth; `wso2/fhir-mcp-server` demonstra OAuth 2.0 Authorization Code contra o sandbox da Epic; Momentum FHIR MCP testado com Epic sandbox, HAPI, Medplum; LangCare lista Epic/Oracle Health — [Fonte](https://eseospace.com/blog/best-mcp-servers-for-healthcare/), [Fonte](https://www.fast.io/resources/best-mcp-servers-for-healthcare.md) (agregadores; não verificados nos repositórios).
- Anthropic: marketplace `healthcare` (`github.com/anthropics/healthcare`, `metadata.version` 2.1.0): "Claude for Healthcare — one plugin bundling payer, provider, pharma, and general healthcare skills over hosted MCP servers"; plugin `healthcare`: "Prior auth, ICD-10-CM medical coding, clinical trial protocols, FHIR development — with CMS Coverage, ICD-10, NPI Registry, Clinical Trials, and PubMed connected"; plugins antigos (`clinical-trial-protocol`, `prior-auth-review`) marcados "Deprecated — install healthcare@healthcare instead" — [Fonte](https://raw.githubusercontent.com/anthropics/healthcare/main/.claude-plugin/marketplace.json); marketplace `life-sciences` (`github.com/anthropics/life-sciences`, 1.0.0): `clinical-trial-protocol`, `scientific-problem-selection`, `clinical-trial-forecast` ("Runs in Claude Science") etc. — [Fonte](https://raw.githubusercontent.com/anthropics/life-sciences/main/.claude-plugin/marketplace.json). Nomes `healthcare` e `life-sciences` constam na lista de nomes reservados de marketplaces — [Fonte](https://code.claude.com/docs/en/plugins/marketplace-reference.md).

### Inferences
- Para o perfil `medico`, monitorar diariamente: registry oficial com `search=` em {fhir, pubmed, clinical, medical, dicom, health, hl7, radiology, pathology, genomic}; marketplaces `anthropics/healthcare` e `anthropics/life-sciences` (diff do `marketplace.json`); releases de `wso2/fhir-mcp-server`, `cyanheads/pubmed-mcp-server`, `cyanheads/clinicaltrialsgov-mcp-server`, `genomoncology/biomcp`, `medplum/medplum`, `awslabs/mcp` via `releases.atom`.
- OpenEMR/Oracle Health: nenhuma entrada oficial encontrada nas sondagens; `openemr/openemr` é o repositório mais estrelado dos tópicos `fhir`/`ehr`, mas um MCP próprio não foi verificado — **[INCERTO]**.

### Gaps
- Servidores MCP oficiais de Epic, Oracle Health, OpenEMR, Google Cloud Healthcare API: não encontrados em fontes primárias.
- Qualidade/manutenção individual dos servidores comunitários listados: não auditada.

---

## 18. Agent Skills: especificação (agentskills.io), anthropics/skills, skills.sh, marketplaces do Claude Code e descoberta diária

### Takeaway
A spec Agent Skills (criada pela Anthropic, aberta, repo `agentskills/agentskills`, Apache-2.0, 27 k★) define `SKILL.md` com frontmatter `name` (≤64, kebab-case, = nome da pasta) e `description` (≤1024) obrigatórios e `license`, `compatibility` (≤500), `metadata`, `allowed-tools` opcionais. `anthropics/skills` (188,6 k★) é um marketplace (`anthropic-agent-skills`); `anthropics/claude-plugins-official` (46 k★) é o diretório oficial de plugins com `.claude-plugin/marketplace.json` diffável; **a API do skills.sh exige token OIDC da Vercel** (401 sem ele), então a descoberta diária prática é: diff dos `marketplace.json` (oficial + `healthcare` + `life-sciences` + `anthropics/skills`), Search API por tópicos `agent-skills`/`claude-skills`/`claude-code-plugin` com `created:>`, code search `filename:SKILL.md <termo>`, e diff das awesome lists.

### Cited Findings
- Spec: layout `SKILL.md` (obrigatório) + `scripts/`, `references/`, `assets/` (opcionais); frontmatter `name` (máx. 64, `a-z0-9-`, sem hífen inicial/final/duplo, "Must match the parent directory name"), `description` (1–1024), `license`, `compatibility` (1–500), `metadata` (mapa string→string), `allowed-tools` (string separada por espaço, experimental); progressive disclosure: metadata (~100 tokens) → instruções (<5.000 tokens recomendados) → recursos; "Keep your main `SKILL.md` under 500 lines"; validação `skills-ref validate ./my-skill` — [Fonte](https://agentskills.io/specification). "The Agent Skills format was originally developed by Anthropic, released as an open standard"; lista de clientes em "Client Showcase" (`https://agentskills.io/clients.md`) — [Fonte](https://agentskills.io/). Repo `agentskills/agentskills`: 27.046★, Apache-2.0, push 2026-11-04 — sondagem ao vivo (GitHub API).
- `anthropics/skills`: 188.645★, push 2026-11-06; diretórios `.claude-plugin/`, `skills/` (docx, pdf, pptx, xlsx e outros), `spec/`, `template/`; "Many skills in this repo are open source (Apache 2.0)"; instalação `/plugin marketplace add anthropics/skills` → `/plugin install document-skills@anthropic-agent-skills` ou `example-skills@anthropic-agent-skills`; badge para `https://skills.sh/anthropics/skills` — [Fonte](https://github.com/anthropics/skills), sondagem ao vivo.
- skills.sh/`vercel-labs/skills` (38.492★, MIT, push 2026-11-06): CLI `npx skills add <owner/repo>` (`--skill`, `-a claude-code`, `-g`), `npx skills find [query]`, `list`, `use`, `check`, `update`, `remove`, `init`; Node ≥22.20; suporta "OpenCode, Claude Code, Codex, Cursor, and 75 more"; telemetria anônima (`DISABLE_TELEMETRY=1`) — [Fonte](https://github.com/vercel-labs/skills). Vercel: "skills.sh is a leaderboard for agent skills… It's a leaderboard, not a registry"; skills suspeitas ficam fora do ranking/busca — [Fonte](https://vercel.com/blog/building-a-self-driving-skills-sh-leaderboard). API: `GET https://skills.sh/api/v1/skills` (views `all-time`|`trending`|`hot`; `page`, `per_page` 1–500, `source=owner/repo`), `/api/v1/skills/search?q=` (≥2 chars, `limit` ≤200, `owner`), `/api/v1/skills/curated`, `/api/v1/skills/{source}/{skill}` (instalações + árvore de arquivos), `/api/v1/skills/audit/{source}/{skill}` (parceiros Gen Agent Trust Hub, Socket, Snyk, Runlayer, ZeroLeaks); auth por **Vercel OIDC token** (`Authorization: Bearer` ou `x-vercel-oidc-token`, rotacionado ~12 h, "no signup, no key to generate" para projetos na Vercel); 600 req/min; cache 30–60 s — [Fonte](https://skills.sh/docs/api). Sondagem ao vivo: `GET /api/v1/skills?limit=2` e `/api/v1/skills/search?q=fhir` sem token → `401 authentication_required … Pass a Vercel OIDC token`.
- Marketplaces do Claude Code: arquivo `.claude-plugin/marketplace.json` com `name`, `owner{name, email?, url?}`, `plugins[]` obrigatórios; `description`, `version`, `metadata.pluginRoot`, `renames`, `forceRemoveDeletedPlugins`; entrada de plugin: `name`, `source` (string relativa `./…` ou objeto `{source: github|url|git-subdir|npm|archive|command, …}` com `ref`/`sha`), `description`, `version`, `category`, `tags`, `strict`, `displayName`, `dependencies`, `skills`/`commands`/`agents`/`hooks`/`mcpServers`…; nomes reservados oficiais: `claude-code-marketplace`, `claude-code-plugins`, `claude-plugins-official`, `anthropic-marketplace`, `anthropic-plugins`, `agent-skills`, `anthropic-agent-skills`, `life-sciences`, `knowledge-work-plugins`, `claude-for-legal`, `claude-for-financial-services`, `financial-services-plugins`, `first-party-plugins`, `claude-tag-plugins`; comunitários: `claude-community`, `claude-plugins-community`, `healthcare` — [Fonte](https://code.claude.com/docs/en/plugins/marketplace-reference.md); criação/registro: `claude plugin marketplace add <owner>/<repo>`, `claude plugin install <name>@<marketplace>`, `claude plugin validate` — [Fonte](https://code.claude.com/docs/en/plugin-marketplaces). Diretório da Anthropic em `https://claude.ai/directory` (submissão pelo portal `claude.ai/directory/manage`, plano pago); `claude-plugins-official` "doesn't take submissions through the directory portal" — [Fonte](https://code.claude.com/docs/en/plugins/publish.md).
- `anthropics/claude-plugins-official`: 46.349★, Apache-2.0, push 2026-11-07; `marketplace.json` ao vivo com `"$schema": "https://anthropic.com/claude-code/marketplace.schema.json"`, `"name": "claude-plugins-official"`, mapa `renames` (ex.: `"azure-skills": "azure"`) e `plugins[]` (ex.: `42crunch-api-security-testing`) — [Fonte](https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json). `anthropics/claude-code-plugins` não existe (404).
- Awesome lists (sondagem ao vivo): `ComposioHQ/awesome-claude-skills` 78.989★ (push 2026-09-18); `hesreallyhim/awesome-claude-code` 57.466★ (2026-11-07); `sickn33/agentic-awesome-skills` 49.320★ (2026-11-06); `VoltAgent/awesome-agent-skills` 36.960★ (2026-11-05); `travisvn/awesome-claude-skills` 15.736★ (2026-04-28); `ccplugins/awesome-claude-code-plugins` 998★ (2026-08-12). Repositórios com `claude-code-marketplace` no nome/descrição: 7.057 (ex.: `wshobson/agents` 42.282★).
- Contagens de tópicos e code search: seção 13.

### Inferences
- Descoberta diária de skills (ordem de custo/benefício): (1) diff de `marketplace.json` de `anthropics/claude-plugins-official`, `anthropics/skills`, `anthropics/healthcare`, `anthropics/life-sciences`, `anthropics/knowledge-work-plugins` (nome reservado; existência **[INCERTO]**, sondagem bloqueada por rate limit) — comparar `plugins[].name`/`version`, honrar `renames`; (2) Search API `topic:agent-skills created:>{D-1} stars:>2`, `topic:claude-skills …`, `topic:claude-code-plugin …` (volume alto: milhares/semana); (3) code search `fhir filename:SKILL.md`, `radiology filename:SKILL.md` (10 req/min; devolve `repository.full_name` + `path`); (4) diff dos READMEs das awesome lists; (5) skills.sh só se o job rodar em um projeto Vercel com OIDC (ou via a página HTML — fora do escopo de API).
- Para cada repositório candidato, baixar `SKILL.md` via `raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>` e validar frontmatter com as regras da spec (nome kebab-case = pasta; descrição ≤1024).

### Gaps
- Lista nominal de adotantes da spec (página `clients.md`) não lida.
- skills.sh: não documentado se pessoas sem projeto Vercel conseguem token; limite não autenticado não informado.
- `anthropics/knowledge-work-plugins` e outros nomes reservados: existência não verificada (rate limit).

---

## 19. Hugging Face Hub: `huggingface_hub` (v2.x), REST, daily papers, trending, filtros médicos, token e rate limits

### Takeaway
`huggingface_hub` está em **2.4.0** (2026-10-29; v1.0 migrou para `httpx`, v2.0 para `httpx2` e passou a usar o trust store do SO); `HfApi().list_models(filter=..., search=..., author=..., pipeline_tag=..., sort="trending_score"|"last_modified"|"created_at"|"downloads"|"likes", limit=...)` e `list_datasets(filter=..., task_categories=..., language=..., size_categories=..., sort=...)` são a interface; na REST os nomes são camelCase (`sort=trendingScore|lastModified|createdAt`; snake_case → 400). `GET /api/daily_papers` (`date|week|month`, `sort=publishedAt|trending`, `limit`) e `GET /api/trending?type=model|dataset|space|all&limit=` constam no OpenAPI oficial. Sem token funciona (500 req/5 min por IP), mas passe `HF_TOKEN` (1.000 req/5 min; retry automático de 429 na lib ≥1.2.0).

### Cited Findings
- PyPI: `huggingface_hub` 2.4.0 (2026-10-29, py≥3.10) — [PyPI](https://pypi.org/project/huggingface_hub/); `main` em `2.5.0.dev0` (sondagem no repositório).
- v1.0 (migração): `requests` → `httpx`; erros herdam de `httpx.HTTPError` (capturar `huggingface_hub.utils.HfHubHTTPError`); `configure_http_backend` → `set_client_factory()`; proxies só via `HTTP_PROXY`/`HTTPS_PROXY`; `huggingface-cli` → `hf`; "`library`, `language`, `tags`, and `task` parameters have been removed from `list_models`" — [Fonte](https://huggingface.co/docs/huggingface_hub/concepts/migration). v2.0.0 (release "24 Sep", ano não exibido — provavelmente 2026 **[INCERTO]**): "huggingface_hub v2.0 replaces its HTTP dependency with `httpx2`"; "httpx2 uses the operating system's certificate trust store by default" (CA custom via `SSL_CERT_FILE`/`SSL_CERT_DIR`); `list_models(model_name=...)` removido → `list_models(search=...)`; `huggingface-cli` removido — [Fonte](https://github.com/huggingface/huggingface_hub/releases/tag/v2.0.0).
- Assinatura atual (`main`): `list_models(*, filter: str | Iterable[str] | None, author, apps, gated, inference, inference_provider, trained_dataset, search, pipeline_tag, num_parameters, emissions_thresholds, sort: ModelSort_T | None, limit, expand, full, cardData, fetch_config, token) -> Iterable[ModelInfo]`; `ModelSort_T = Literal["created_at", "downloads", "last_modified", "likes", "trending_score"]`; docstring: "Models can be filtered by library, language, task, tags, and more" via `filter`; `list_datasets(*, filter, author, benchmark, dataset_name, gated, language_creators, language, multilinguality, size_categories, task_categories, task_ids, search, sort: DatasetSort_T, limit, expand, full, token)`; `DatasetSort_T` idêntico; `CollectionSort_T = Literal["lastModified", "trending", "upvotes"]`; `DailyPapersSort_T = Literal["publishedAt", "trending"]`; `ModelInfo.trending_score` mapeado de `trendingScore` — [Fonte](https://raw.githubusercontent.com/huggingface/huggingface_hub/main/src/huggingface_hub/hf_api.py).
- REST (sondagem ao vivo 2026-11-07): `GET https://huggingface.co/api/models?filter=medical&sort=createdAt&direction=-1&limit=2` → 200, itens com `_id, id, createdAt, lastModified, likes, downloads, private, tags, pipeline_tag, library_name, modelId` (ex.: `Amaljith/medgemma-decide-4b-v2`, tags `['transformers','safetensors','gemma3','image-text-to-text','medical',…]`); `sort=lastModified` → 200 (ex.: `GOVINDFROM/surgical-world-model`); `sort=downloads|likes` → 200; **`sort=trending_score|last_modified|created_at` → `400 {"error":"✖ Invalid sort parameter: …"}`**; `GET /api/datasets?filter=task_categories:image-segmentation&sort=trendingScore&limit=2` → 200 com campo `trendingScore` (ex.: `MahmoodLab/hest`, tags `task_categories:image-segmentation`, `language:en`, `license:cc-by-nc-sa-4.0`, `size_categories:100B<n<1T`); `GET /api/daily_papers?limit=2` → 200, itens `{paper{id…}, publishedAt, submittedBy, summary, thumbnail, title, numComments, organization, isAuthorParticipating}`; `GET /api/trending?type=model&limit=2` → `{"recentlyTrending":[{repoType, repoData{id, author, downloads, likes, pipeline_tag, lastModified, gated, …}}]}`; `GET /api/collections?sort=trending&limit=1` → 200.
- OpenAPI oficial (`https://huggingface.co/.well-known/openapi.json`): `GET /api/daily_papers` com parâmetros `p`, `limit`, `date`, `week`, `month`, `submitter`, `sort[publishedAt,trending]`; `GET /api/trending` com `type[all,model,space,dataset]`, `limit`; `GET /api/papers/search` com `q`, `limit`; `/api/models` e `/api/datasets` não constam nesse spec (documentados via a lib) — [Fonte](https://huggingface.co/.well-known/openapi.json); a página de endpoints remete ao OpenAPI Playground e ao `openapi.md` — [Fonte](https://huggingface.co/docs/hub/api).
- Rate limits (set/2025, janelas fixas de 5 min; bucket "API" = busca de modelos/datasets etc.): anônimo (por IP) 500, Free user 1.000, PRO 2.500, Team 3.000, Enterprise 6.000; 429 com headers `RateLimit`/`RateLimit-Policy`; "make sure you always pass a `HF_TOKEN`"; `huggingface_hub` ≥1.2.0 "automatically parses the `RateLimit` header… then waits precisely that duration before retrying" para downloads e chamadas paginadas (list models/datasets) — [Fonte](https://huggingface.co/docs/hub/rate-limits).
- Sondagem ambiental: nesta máquina, 3 de 7 e depois ~6 de 9 chamadas a `huggingface.co` falharam com `httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] … self-signed certificate in certificate chain`, enquanto outras à mesma origem passaram — comportamento intermitente típico de inspeção TLS local (antivírus/proxy).

### Inferences
- Uso recomendado (lib): `HfApi().list_models(filter=["medical"], sort="trending_score", limit=50)`; `list_models(search="radiology", sort="created_at", limit=100)` (a lib inverte a ordem para decrescente; na REST usar `direction=-1`); `list_datasets(filter="medical", sort="last_modified", limit=50)`; `list_datasets(task_categories="image-segmentation", sort="trending_score")`; `HfApi().list_papers(...)`/`get_daily_papers` **[INCERTO quanto ao nome na 2.4.0]** — na dúvida, chamar `GET /api/daily_papers?date=YYYY-MM-DD&sort=trending` com `httpx` (já é o que o `sotawhat` faz). Filtrar por data no cliente (`createdAt ≥ ontem`) após `sort=createdAt&direction=-1`.
- Tags médicas verificadas como populadas: `medical` (modelos e datasets); `task_categories:image-segmentation` (datasets); para outras (`biology`, `clinical`, `radiology`, `healthcare`, `chemistry`) usar `search=` como fallback — **[INCERTO]** quais existem como tags.
- Token: criar em `https://huggingface.co/settings/tokens` (fine-grained, somente leitura) e expor como `HF_TOKEN` (lido automaticamente pela lib); nunca expira por tempo, revogável manualmente.
- Mitigação do erro SSL no Windows: `pip install truststore` + `truststore.inject_into_ssl()` antes de criar o `httpx.Client` (ou `huggingface_hub` ≥2.0, que já usa o trust store do SO); como alternativa, `SSL_CERT_FILE` apontando para o bundle do AV/proxy; **não** usar `verify=False`. Reproduzir com `python -c "import httpx; print(httpx.get('https://huggingface.co/api/models?limit=1').status_code)"` e `certutil -store Root` para achar o emissor interceptador.

### Gaps
- Data exata do release v2.0.0 (página sem ano) e guia `migration_v2.md` não lidos.
- Documentação REST oficial de `/api/models` (parâmetros) não existe no OpenAPI; nomes confirmados só por sondagem.
- Nome do método da lib para daily papers na 2.4.0 não verificado.

---

## 20. Tabela consolidada de variáveis `.env` (todos os canais)

### Takeaway
Um único `.env` (local: `D:\Lucas\code_projects\sotawhat\.env`, fora do git; CI: secrets com os mesmos nomes) cobre os cinco canais; a maioria das credenciais são somente leitura e sem expiração temporal, exceto OAuth do Google (depende do status do app), tokens do Instagram (60 dias, renováveis) e PATs do GitHub (escolha 366 dias). Mínimo para começar: `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` (ou o trio OAuth), `IG_ACCESS_TOKEN` + `IG_USER_ID`, `HIKERAPI_TOKEN` ou `APIFY_TOKEN`, `TELEGRAM_BOT_TOKEN`, `GITHUB_TOKEN`, `HF_TOKEN`; o registry MCP, o catálogo Docker e os feeds Atom do GitHub não precisam de credencial.

| Variável | Finalidade | Como obter | Rotação / expiração |
|---|---|---|---|
| `GMAIL_BACKEND` | `api` ou `imap` (fallback) | decisão | — |
| `GMAIL_ADDRESS` | login IMAP (`imap.gmail.com:993`) | seu endereço | nunca |
| `GMAIL_APP_PASSWORD` | senha de 16 chars para IMAP | `myaccount.google.com/apppasswords` (exige 2SV) [Fonte](https://support.google.com/accounts/answer/185833) | revogada ao trocar senha/desligar 2SV/Advanced Protection; sem expiração temporal documentada |
| `GOOGLE_CLIENT_SECRET_FILE` | caminho do `client_secret.json` (Desktop app) | Google Auth Platform → Clients → Download JSON | não expira; recriar se vazar |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | alternativa sem arquivo (CI) | campos `installed.client_id`/`client_secret` do JSON | idem |
| `GMAIL_TOKEN_FILE` | `token.json` (access + refresh) | gerado por `run_local_server` local | refresh token: 7 dias se app em Testing; senão até troca de senha / 6 meses sem uso / >100 tokens / revogação [Fonte](https://developers.google.com/identity/protocols/oauth2#expiration) |
| `GMAIL_REFRESH_TOKEN` | alternativa sem arquivo (CI) | campo `refresh_token` do `token.json` | idem |
| `GMAIL_QUERY` | query de ingestão | ex. `label:newsletters-ai newer_than:2d` | — |
| `GMAIL_LABEL` | nome/ID da label (API `labelIds`) | `newsletters/ai` ou `Label_xxx` via `labels.list` | — |
| `IG_LOGIN_MODE` | `instagram` (`graph.instagram.com`) ou `facebook` (`graph.facebook.com`) | decisão após teste de Business Discovery (seção 5) | fixa |
| `GRAPH_API_VERSION` | prefixo de versão | `v27.0` (amostras oficiais) / `v26.0` | versões expiram ~2 anos após o lançamento [Fonte](https://developers.facebook.com/docs/graph-api/changelog) |
| `IG_APP_ID` / `IG_APP_SECRET` | `client_id`/secret do Business Login e troca `ig_exchange_token` | Meta App Dashboard → Instagram → API setup with Instagram login | fixos; rotacionar se vazar |
| `IG_ACCESS_TOKEN` | token longo inicial | "Generate token" no Dashboard (60 dias) [Fonte](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started) | renovar via `refresh_access_token` (≥24 h de idade, antes de 60 dias) |
| `IG_TOKEN_FILE` | token rotacionado + `obtained_at` | criado pelo job | sobrescrito a cada refresh; fora do git |
| `IG_USER_ID` | ID da conta profissional chamadora | `GET /me?fields=user_id,username` (IG Login) ou `GET /me/accounts?fields=instagram_business_account` (FB Login) | fixo |
| `IG_TARGETS` | usernames a varrer (CSV) | seed do export "Export your information" (`following.json`) filtrado pelos que respondem ao BD | manual, mensal |
| `FB_APP_ID` / `FB_APP_SECRET` / `FB_PAGE_ID` | só modo `facebook`: `fb_exchange_token`, Page token | App Dashboard → Settings → Basic; `GET /me/accounts` | user token ~60 dias; Page token longo sem expiração [Fonte](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived) |
| `APIFY_TOKEN` | `ApifyClient(token=...)` (o cliente não lê env sozinho) | Apify Console → Settings → API & Integrations (caminho exato **[INCERTO]**) [Fonte](https://pypi.org/pypi/apify-client/json) | sem expiração documentada; um token por projeto, revogável no Console |
| `HIKERAPI_TOKEN` | header `x-access-key` em `https://api.hikerapi.com` | dashboard hikerapi.com (100 req grátis) [Fonte](https://hikerapi.com/) | saldo pré-pago "never expires"; regenerar no dashboard |
| `SCRAPECREATORS_API_KEY` (opcional) | header `x-api-key` em `https://api.scrapecreators.com` | dashboard (100 créditos grátis) [Fonte](https://scrapecreators.com/) | créditos "never expire"; regenerar no dashboard |
| `BRIGHTDATA_API_TOKEN` (opcional) | Instagram Scraper API | painel Bright Data após KYC [Fonte](https://brightdata.com/products/web-scraper/instagram) | free tier 5 k/mês renova dia 1 |
| `IG_USERNAME` / `IG_PASSWORD` | login da conta **secundária** (instagrapi) — nunca a principal | criar conta dedicada só-leitura | trocar senha se houver challenge |
| `IG_SESSION_FILE` | `session.json` (`dump_settings`/`load_settings`) | gerado no 1º login bem-sucedido [Fonte](https://github.com/subzeroid/instagrapi) | válido até `LoginRequired`; relogin com o mesmo device state; tratar como segredo |
| `IG_PROXY_URL` (opcional) | `cl.set_proxy("http://user:pass@host:port")` só se não rodar do IP doméstico | IPRoyal (US$7,35/GB) ou Apify Proxy (US$8/GB) | manter o mesmo IP/sticky session por conta |
| `IG_TOTP_SECRET` (opcional) | gerar código 2FA no login (`totp_generate_code`) **[INCERTO]** | ativar 2FA por app na secundária e guardar o seed | não expira |
| `INSTAGRAM_COOKIE` (RSSHub) | `sessionid=…; ds_user_id=…` | DevTools do navegador logado na secundária [Fonte](https://github.com/DIYgod/RSSHub/blob/master/lib/config.ts) | expira ao deslogar/rotacionar; monitorar "Invalid cookie" |
| `TELEGRAM_BOT_TOKEN` | `getUpdates` do bot da inbox "share to" | @BotFather → `/newbot` [Fonte](https://core.telegram.org/bots/api#getupdates) | sem expiração; `/revoke` no BotFather |
| `TELEGRAM_ALLOWED_USER_ID` / `TELEGRAM_CHAT_ID` | ignorar terceiros; enviar digest/alertas | `message.from.id` / `message.chat.id` no 1º `getUpdates` | fixos |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` (opcional, Telethon) | ler histórico de canal privado sem o limite de 24 h | my.telegram.org | sessão Telethon persistida (`.session`) |
| `GITHUB_TOKEN` (o `gh` também lê `GH_TOKEN`) | Search/REST/GraphQL/code search; 5.000 req/h | Settings → Developer settings → Fine-grained tokens → Generate (sem permissões extras: "Tokens always include read-only access to all public repositories") [Fonte](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) | escolher 1–366 dias ou `none`; em Actions usar `secrets.GITHUB_TOKEN` (1.000 req/h/repo) |
| `GOOGLE_APPLICATION_CREDENTIALS` / `BIGQUERY_PROJECT` (opcional) | star velocity via GH Archive no BigQuery | service account JSON no projeto GCP; 1 TB/mês grátis [Fonte](https://www.gharchive.org/) | chave de SA não expira; rotacionar anualmente |
| `MCP_REGISTRY_BASE_URL` (opcional) | base do registry oficial (`https://registry.modelcontextprotocol.io/v0.1`) | — | — (leitura pública, sem chave) |
| `SMITHERY_API_KEY` (opcional) | `GET https://api.smithery.ai/servers?q=…` | chave de API na conta Smithery (página exata **[INCERTO]**) | sem expiração documentada |
| `GLAMA_API_KEY` (opcional) | `GET https://glama.ai/api/mcp/v1/servers` | `https://glama.ai/settings/api-keys`; exige atribuição visível a Glama (API Data License) | sem expiração documentada |
| `PULSEMCP_API_KEY` / `PULSEMCP_TENANT_ID` (não disponível) | API v0.1 do PulseMCP (`X-API-Key`, `X-Tenant-ID`) | só parceiros via hello@pulsemcp.com [Fonte](https://www.pulsemcp.com/api/docs/v0.1) | — |
| `DOCKER_MCP_CATALOG_URL` (opcional) | `https://desktop.docker.com/mcp/catalog/v2/catalog.yaml` | — | — (público) |
| `VERCEL_OIDC_TOKEN` (impraticável) | API do skills.sh | só apps implantados na Vercel com OIDC; rotacionado ~12 h [Fonte](https://skills.sh/docs/api) | 12 h |
| `HF_TOKEN` | Hub API (1.000 req/5 min vs 500 anônimo); lido automaticamente pela lib | `https://huggingface.co/settings/tokens` (fine-grained, read) [Fonte](https://huggingface.co/docs/hub/rate-limits) | sem expiração temporal; revogável |
| `HF_HUB_DISABLE_TELEMETRY=1` (opcional) | desliga telemetria da lib | — | — |
| `SSL_CERT_FILE` (opcional, Windows) | bundle CA quando há inspeção TLS local | exportar o certificado raiz do AV/proxy | — |
| `ANTHROPIC_API_KEY` (opcional) | extração multimodal (visão em imagens de posts) | console da Anthropic | rotacionar se vazar |

### Gaps
- Caminho exato de criação do token no Console da Apify e política de expiração de tokens Apify/HikerAPI/ScrapeCreators: não documentados nas páginas lidas.
- Nome do método/variável para TOTP no instagrapi (`totp_generate_code`) não verificado.
