# Plano — Aulas com 3D híbrido (HyperFrames + three.js livre) e 3D interativo

**Data:** 2026-11-11 · **Pedido:** sobre a aula 7 (TC), o usuário escreveu: "Adorei, porém senti falta da animação
em 3D — tanto no vídeo quanto interativa — que havia sido criada antes. Gostaria que existisse uma mescla entre o
Three.js e a skill que permite essa animação para a construção das próximas aulas."

**Respostas às perguntas de escopo:**
- **Motor 3D: "Híbrido".** O LLM escreve o mecanismo em three.js, e o kit HyperFrames cuida de título, legendas,
  rótulos, enquadramento e checagens. Se a cena falhar, cai para 2D.
- **Interativo: "Aba Aulas + arquivo no Telegram".**

## Diagnóstico

- **Aulas 2 e 5 (motor Manim):** as cenas `three` eram three.js livre, escrito por um LLM contra o `lesson_kit.js`.
  - A aquisição mostrava o gantry, o tubo, o feixe e o detector girando em volta do paciente.
  - A cena "voxels e janela" mostrava uma grade de voxels com a régua de HU.
  - Cada cena virava uma página interativa na aba Aulas: ouvir, arrastar a linha do tempo e girar livremente.
- **Motor HyperFrames (aula 7):**
  - Só há dois modelos 3D fixos: `vectors3d` e `volume3d`.
  - A cena "A aquisição gira e mede" virou um `graph` de caixas (tubo → tórax → detector).
  - As páginas interativas sumiram: a legenda do Telegram diz só "Quiz e revisão logo abaixo", e `scenes3d` da API
    lê `mode == "three"`, que o `MotionScene` não grava.

## Decisões

1. **Novo modelo de cena `mechanism3d`.** Ele mostra o 3D de um mecanismo físico ou de um processo no espaço que
   nenhum outro modelo mostra. Exemplos: o gantry da TC, uma sonda de ultrassom varrendo, uma proteína dobrando, um
   fármaco no seu bolso, um kernel 3D deslizando num volume.
   - **O storyboard dá as peças.** Em `nodes`, as peças físicas (2 a 6) têm id, rótulo, papel/cor, glosa e
     `col`/`row`. As ações `show`, `hide`, `focus`, `unfocus`, `dim`, `pulse`, `note` e `label` usam as mesmas
     regras de tempo das outras cenas, presas à palavra falada.
   - **O LLM escreve só a geometria e o movimento.** O contrato é `build(kit)` → `{ update(t), view? }`. Cada peça é
     registrada com `kit.part(id, objeto, { anchor })`. O movimento é função pura de `t`, com `kit.beats`,
     `kit.progress(t, i)` e `kit.shownAt(id)` para sincronizar com a fala.
   - **O kit (`mountFree` em `scene3d.js`) é dono do resto:**
     - renderer, luz e tone mapping;
     - câmera: enquadramento pela esfera das peças entre o título e as legendas, órbita lenta e aproximação no
       `focus`;
     - rótulos HTML com linha-guia, sem sobreposição;
     - notas na coluna da direita, título, saída e legendas;
     - aparecer, apagar e pulsar cada peça;
     - checagem de layout.
   - **A política de código das cenas Manim-era continua valendo** (`render.js_problems`): sem import, DOM, rede,
     timers, `Date` ou `Math.random`.
2. **Revisão automática da cena 3D** (`sotawhat/lessons/three3d.py`), depois da narração e antes de compor:
   1. Política de código.
   2. Sonda headless (`probe3d.py`, Playwright do ambiente de ferramentas): erros de JavaScript e checagens do kit
      no fim de cada frase (peça do storyboard não registrada, peça fora da tela, sob as legendas ou pequena
      demais).
   3. Até 2 reparos. O primeiro modelo é o MiMo-V2.6-Pro e o segundo o GLM-5.3-Flash, ambos ZDR e com teto de
      preço.
   4. Crítico visual (`lesson_critic_v1`) nos quadros do fim de cada frase.
   5. Uma correção vendo os quadros. Se a correção quebrar a cena, fica a versão anterior.
   - Uma cena que nunca passa vira o `graph` das mesmas peças. A aula sai do mesmo jeito, e o relatório registra.
   - O código fica em `data/lessons/<id>/3d/sNN.js`, com uma chave do briefing: `resume` não paga de novo.
3. **Plano `lesson_plan_v4`.**
   - O texto inclui `mechanism3d`.
   - Quando o passo é um aparelho, uma geometria de aquisição, anatomia ou movimento no espaço, o plano prefere 3D
     (`mechanism3d` ou `volume3d`) a `graph`.
   - Limites: até 4 cenas 3D por aula e até 2 de cada modelo.
   - O storyboard passa para `lesson_storyboard_v3`, com a seção `mechanism3d`.
4. **3D interativo** (`sotawhat/lessons/interactive.py`): um arquivo HTML único por aula, `interativo.html`.
   - **Conteúdo:**
     - todas as cenas 3D da aula (`vectors3d`, `volume3d`, `mechanism3d`), em abas;
     - o mesmo código das cenas do vídeo, com o three.js e o código das cenas num pacote do esbuild do HyperFrames;
     - kit, GSAP, fontes e o áudio de cada cena (MP3 recortado da narração) embutidos.
   - **Controles:** ouvir/pausar, linha do tempo, arrastar para girar, roda ou pinça para zoom, e "câmera da aula"
     para voltar ao enquadramento original.
   - **Órbita própria do kit** (`orbit` em `scene3d.js`): a câmera roteirizada gira em torno do mesmo alvo, então
     os rótulos HTML continuam presos às peças. Com o OrbitControls numa câmera clonada, eles se soltariam. No
     render do vídeo, a órbita é zero.
   - **Onde aparece:**
     - no Telegram, logo após o vídeo, com o novo `send_document`;
     - na aba Aulas, no campo `interactive` da API, como chip "3D interativo".
   - **Sem servidor:** o arquivo abre direto no navegador do celular.
   - **Uma sonda só:** a mesma página, em modo `?probe`, é a da sonda do passo 2.

## Fora de escopo

- Malhas anatômicas reais. Continua pendente o download, que precisa de aprovação.
- Refazer o plano das aulas antigas.

## Piloto

Aula 8: a aula 7 refeita com a cena 2 ("A aquisição gira e mede") em `mechanism3d`.
- A pasta `voz/` é copiada, então a narração não muda e não há crédito novo da ElevenLabs.
- O custo esperado é só de LLM: storyboard e código 3D, cerca de US$ 0,05–0,15.

## Testes

- **Storyboard:** valida `mechanism3d` (2 a 6 peças, ids conhecidos).
- **Plano:** o lint conta até 4 cenas 3D.
- **Compose:** escreve a cena livre como módulo que importa `sNN.js`.
- **Passo de código:**
  - usa o cache pela chave;
  - repara com o erro da sonda;
  - cai para `graph` sem quebrar a aula.
  - Usa sonda e LLM falsos.
- **Interativo:** o HTML único tem as cenas 3D, os dados locais de cada cena e nenhuma URL externa.
- **Entrega:** manda o documento após o vídeo, e a API mostra `interactive`.
