# Plano — Aulas no motor HyperFrames (migração do `lessons make`)

**Data:** 2026-11-10 · **Pedido:** o usuário aprovou a aula 6, o protótipo HyperFrames ("Absolute cinema! ficou
excelente."). Em seguida respondeu "Quero sim" à proposta de passar o `lessons make` para esse motor. A proposta
incluía três pontos:
- o planejador escolhe os modelos de cena;
- os modelos que faltam são criados;
- o relatório soma o custo da voz.

Ele pediu também: "pegue a cotação do dólar numa fonte oficial do BC".

## Objetivo

`sotawhat lessons make --tema "…"` (e `--auto`, `resume`) produz a aula no motor da aula 6, do tema até o Telegram
com quiz:
- **Visual:** HyperFrames, com os modelos de cena do kit e cenas 3D em three.js.
- **Voz:** ElevenLabs v4, voz Klaus.
- **Custo no relatório:** LLM + voz, em US$ e em R$, convertido pela PTAX do Banco Central.

## Decisões

1. **Um motor para as aulas novas.**
   - `make` usa só o HyperFrames.
   - `resume <id>` segue o motor gravado no relatório da aula (`report.engine`). As aulas 1–5, em Manim, continuam
     retomáveis, reenviáveis e reempacotáveis.
   - O caminho Manim fica no código só para elas. Não há opção para criar aulas novas em Manim, porque o visual foi
     rejeitado.
   - `lessons hf <id>` continua refazendo uma aula antiga no motor novo.
2. **O plano já escolhe o modelo de cena.**
   - O prompt `lesson_plan_v3` e o esquema `MotionPlan` dão a cada cena um `template` e pedem a narração escrita
     para ele. Exemplos: numa cena `bars`, a narração diz os scores; numa `chart`, diz os eixos; numa `volume3d`,
     fala de fatias e volume.
   - O plano ganha `example`: o exemplo único que atravessa a aula, com os seus números.
   - O lint G2 conta no máximo 3 cenas 3D (`vectors3d` e `volume3d`) e no máximo 2 de cada.
   - O storyboard precisa usar o modelo planejado.
3. **O storyboard vem antes da voz.** O storyboard só depende das frases. Se ele falhar, nenhum crédito da
   ElevenLabs foi gasto. A voz é o último passo pago antes do render.
4. **Quatro modelos de cena novos no kit:**
   - `chart`: curvas em eixos (curva ROC com a área da AUC, curva de aprendizado, dose-resposta, desempenho por
     dados). Ações:
     - `show` desenha as curvas;
     - `area` preenche a área sob uma curva;
     - `mark` marca um ponto, com guias até os eixos.
   - `timeline`: marcos no tempo (história, versões, fases de um estudo). `show` estende o eixo até cada marco.
   - `compare`: duas ou três alternativas lado a lado nos mesmos atributos. `show` revela por linha ou por coluna, e
     `pick` destaca a célula vencedora.
   - `volume3d`: imagem médica em 3D, em three.js.
     - Um campo implícito define o órgão (pulmão, fígado, cérebro, rim, coração ou corpo) e o achado.
     - As fatias de TC sintéticas são cortes desse campo.
     - A malha 3D sai do mesmo campo pelo `MarchingCubes` do three.js, então fatias e superfície concordam.
     - Ações:
       - `show` traz as fatias;
       - `stack` empilha as fatias, separadas, no volume (reconstrução);
       - `slice` passa um plano pelo volume e mostra o corte num quadro ao lado;
       - `segment` colore o órgão nas fatias e faz surgir a superfície;
       - `focus` destaca o achado.
     - Nada vem de paciente real.
5. **A curva ROC sai da AUC.**
   - Uma série `chart` pode trazer `auc` em vez de pontos. O validador gera a curva binormal com exatamente essa área:
     `y = Φ(a + Φ⁻¹(x))`, com `a = √2 · Φ⁻¹(AUC)`.
   - Assim o número dito, a área pintada e a curva desenhada concordam.
6. **Custo da voz e câmbio oficial.**
   - **Créditos:** vale o cabeçalho `character-cost` da resposta da ElevenLabs. Se ele faltar, conta o número de
     caracteres enviados (na aula 6 foram 2.730 créditos para 2.722 caracteres).
   - **Preço do crédito:** valor mensal do plano ÷ créditos do mês, definidos por
     `SOTAWHAT_ELEVENLABS_PLAN_USD=5` e `SOTAWHAT_ELEVENLABS_PLAN_CREDITS=30000`. Os 90 mil créditos que a conta mostra
     incluem o saldo acumulado de meses anteriores, não a cota do mês.
   - **Câmbio:** `sotawhat/fx.py` lê a PTAX de venda do boletim de fechamento na API de dados abertos do BCB
     (Olinda, `CotacaoDolarPeriodo`) e pega o último dia útil.
   - **Cache:** a cotação fica no `meta` por 6 horas. Sem rede, vale a última vista. Sem nenhuma, o relatório mostra
     só US$.
   - **Relatório:** grava `llm_usd`, `voice` (créditos, US$), `cost_usd` (total), `cost_brl` e `ptax` (taxa e data).
   - **Teto de LLM por aula** (`SOTAWHAT_LLM_BUDGET_USD_LESSON`): continua contando só o LLM.
7. **O render é pulado quando nada mudou.** Uma chave reúne storyboard, narração, arquivos do kit e versão do
   HyperFrames. Num `resume` sem mudança, o vídeo existente vale; `--refazer video` força o render.
8. **Entrega:**
   - aula nova: vídeo, quiz e botões de revisão, como antes;
   - legenda: custo em US$ e R$;
   - o link das cenas 3D interativas sai, porque no motor novo o 3D está dentro do vídeo.
9. **Fora do escopo, a combinar:**
   - malhas anatômicas reais (Z-Anatomy, CC BY-SA 4.0): exigem baixar arquivos e dar atribuição;
   - teste cego de vozes ElevenLabs: gasta créditos;
   - rotina semanal (F2).

## Tarefas (TDD, um commit cada)

1. `fx.py`: PTAX do BCB, com teste por fixture, cache no `meta` e queda para a última cotação.
2. **ElevenLabs:**
   - créditos cobrados por cena, gravados no cache;
   - custo da voz e configurações do plano;
   - `.env.example`.
3. **Plano v3:**
   - `MotionPlan` e `lesson_plan_v3`;
   - lint G2 dos modelos;
   - fatos G1 com revisão, como hoje;
   - `load_plan` lê os dois formatos.
4. **Storyboard v2:**
   - esquema dos modelos novos;
   - validação e reparos: pontos ordenados e presos aos eixos, células por coluna, ROC pela AUC, modelo planejado;
   - prompt v2.
5. **Kit:**
   - `chart`, `timeline` e `compare` em `kit.js`/`kit.css`;
   - `volume3d` em `scene3d.js`, com o `MarchingCubes` copiado e o import reescrito.
6. **Pipeline:**
   - `make` e `resume` no motor novo, com passos retomáveis e o custo no relatório;
   - entrega com quiz;
   - CLI (`--refazer plano,storyboard,voz,video`);
   - página `/aulas`: custo em R$, modelos no lugar de 2D/3D, portões do motor novo.
7. **Docs:** README, SDD e um adendo a este plano.
8. **Verificação:**
   - uma galeria com todos os modelos de cena: quadros conferidos um a um;
   - uma aula real pelo `make`, entregue no Telegram.

## Critérios

- Os testes passam sem rede, e os antigos continuam passando.
- O `hyperframes check` termina sem erros na aula real.
- A aula chega ao Telegram com quiz, e o relatório mostra LLM + voz em US$ e R$ pela PTAX.
