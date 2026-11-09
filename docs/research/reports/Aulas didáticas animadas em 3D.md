# Código anima; vídeo generativo apenas enfeita

Dá para gerar no seu PC atual aulas de cerca de 5 minutos, narradas em pt-BR e com animação 3D, a partir dos tópicos que o grafo elege toda semana. A condição é que a animação seja **escrita por LLMs como código e renderizada de forma determinística**. O Manim CE cuida de fórmulas e diagramas. O three.js cuida do que é espacial, e a mesma cena vira o MP4 do Telegram e a página interativa local. O Blender fica na bancada, só para preparar ativos. O vídeo generativo entra apenas como B-roll decorativo, porque impressiona mas não ensina: no benchmark do Code2Video, o Veo3 tirou **2,5 no TeachQuiz**, contra **86,0** do pipeline por código ([Code2Video](https://arxiv.org/html/2510.01174v1)). No cenário econômico (DeepSeek V4.1 Flash e MiMo-V2.6-Flash pelos endpoints ZDR, narração Qwen3-TTS local e todo o resto local), cada aula custa **cerca de US$ 0,10 de API e 15–30 minutos de PC**, ou **menos de US$ 2,50 por mês** para 8 aulas. O cenário equilibrado, que recomendo como regime, usa Kimi K3.1 Pro no storyboard, MiMo-V2.6-Pro nas cenas three.js, Chirp 3 HD na voz e props da Tripo. Ele fica em **US$ 3–6 por mês** depois que a biblioteca de ativos se paga, e em até cerca de US$ 18 no primeiro mês. O premium, com 30 s de vídeo generativo por aula, sobe para **US$ 57–160 por mês**, de 5 a 15 vezes o orçamento atual de LLM, quase tudo gasto em tomadas que não explicam nada. Comprar sai muito mais caro ou entrega outra coisa: um estúdio cobra **US$ 25 mil–100 mil ou mais por aula de 5 minutos**, e SaaS como Synthesia ou o NotebookLM fazem 2D, não mecanismos em 3D. O custo que sobra está no seu tempo, cerca de 15 minutos de revisão por aula, e no risco de conteúdo errado com aparência de certo. Esse risco exige portões automáticos e um checklist médico antes de qualquer entrega. Um piloto de três aulas, julgado às cegas contra o Video Overview do NotebookLM gerado das mesmas fontes, decide se o projeto continua.

## Benchmarks e pedagogia mandam animar por código e reservar o 3D para o espacial

A pergunta decisiva não é qual ferramenta faz a imagem mais bonita, e sim qual ensina. O benchmark MMMC do Code2Video (ICML 2026) foi montado sobre vídeos do 3Blue1Brown:

- O Veo3 tirou **9,0 em estética e 2,5 no TeachQuiz**.
- O mesmo tema, gerado como código Manim por um agente com planejador, programador e crítico, chegou a **87,9 e 86,0**.
- Os vídeos humanos ficaram em 99,7 e 97,1 ([Code2Video](https://arxiv.org/html/2510.01174v1)).

Tirar o planejador derrubou o quiz de 82,0 para 40,5 (mesma fonte). Logo, o ganho vem de separar roteiro e código, não só do renderizador.

Os geradores de pixels falham justamente onde uma aula médica precisa acertar:

- No Physics-IQ, a compreensão física desses modelos é "severely limited, and unrelated to visual realism" ([Physics-IQ, WACV 2026](https://openaccess.thecvf.com/content/WACV2026/html/Motamed_Do_Generative_Video_Models_Understand_Physical_Principles_WACV_2026_paper.html)).
- No SurgVeo, cirurgiões acharam as continuações do Veo-3 visualmente excelentes, mas as reprovaram em manejo de instrumento, resposta tecidual e intenção cirúrgica ([SurgVeo](https://arxiv.org/abs/2511.01775)).
- Modelos comerciais como Sora, Pika e Hailuo erram anatomia e uso de instrumentos com frequência ([MedGen](https://arxiv.org/abs/2507.05675)).

Na Teaching Monster Challenge de 2026 (77 equipes), o Manim foi o motor de animação mais comum entre os dez primeiros. Os times concluíram que "generated images are unreliable for factual diagrams" ([Teaching Monster](https://arxiv.org/html/2608.08852v1)).

O 3D também não é um bem em si. Na meta-análise de Berney e Bétrancourt (140 comparações, N = 7.036), a animação supera a figura estática por apenas **g = 0,226**. Com representações abstratas o efeito desaparece (**g = 0,006**), e em informática e matemática não é significativo ([Berney & Bétrancourt 2016](https://archive-ouverte.unige.ch/unige:92234)). O 3D rende quando o conteúdo é espacial: em anatomia, o conhecimento espacial ganha **d = 0,50** ([Yammine & Violato 2015](https://laur.lau.edu.lb:8443/xmlui/handle/10725/10914)). O dado que muda a arquitetura vem da meta-análise de Bogomolova e colegas. O 3D estereoscópico **interativo** supera imagens 2D (ES = 0,45). O 3D **não interativo** não mostrou vantagem; a estimativa foi de −0,87 e nem chegou a ser agrupada, por heterogeneidade extrema ([Bogomolova et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC7984401)). Um MP4 com a câmera orbitando é, portanto, a forma mais fraca de 3D. Por isso a mesma cena three.js precisa existir também como página que você gira, pausa e explora.

Os princípios de Mayer viram regras verificáveis do storyboard. Os efeitos mais robustos são ([Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)):

- segmentar em blocos curtos (**d = 0,67**);
- apresentar antes os nomes das peças, o chamado pré-treino (**d = 0,78**);
- sinalizar o elemento ativo (**d = 0,70**);
- sincronizar narração e evento, a contiguidade temporal (**d = 1,31**);
- cortar o supérfluo, a coerência (**d = 0,86**). O efeito é mais forte em aulas no ritmo do sistema e quando o enfeite é "sedutor".

A voz humana conta (**d = 0,74**), mas o rosto não: acrescentar a imagem do apresentador rende **d = 0,19** (mesma fonte). Agentes 2D (g+ = 0,38) ensinam mais que agentes 3D (g+ = 0,11) ([Castro-Alonso et al. 2021](https://research.birmingham.ac.uk/en/publications/effectiveness-of-multimedia-pedagogical-agents-predicted-by-diver/)). O engajamento mediano não passa de **6 minutos**, qualquer que seja a duração do vídeo ([Guo, Kim & Rubin 2014](https://up.csail.mit.edu/other-pubs/las2014-pguo-engagement.pdf)). Testar a lembrança supera reler, e o efeito é maior quando o teste vem mais de um dia depois ([Adesope et al. 2017, resumo](https://www.learningscientists.org/blog/2017/2/9-1)).

Para o sotawhat isso significa aulas de 3 a 6 minutos (padrão de 4,5), sem avatar e sem música por baixo dos mecanismos. Cada aula tem um mini-mapa persistente do processo e termina num quiz, repetido dias depois.

O run semanal 13 do seu grafo (09/11/2026) trouxe em alta "Transformer", "electronic health record", "reinforcement learning", "computed tomography", "CT-RATE", "radiology report generation" e "hallucination". Aplicada a essas tendências, a regra separa os temas assim:

| Tendência no grafo | Processo mais complexo a explicar | Modo visual | Por quê |
|---|---|---|---|
| Transformer, attention mechanism | Atenção: Q, K, V e o mapa de pesos montado célula a célula | 2D passo a passo; no máximo 2,5D (pilha de camadas) | Abstrato e relacional, sem referente espacial |
| reinforcement learning, GRPO | Pós-treino por RL com vantagem relativa ao grupo | 2D: laço com tokens animados | Laço abstrato |
| computed tomography, CT-RATE, 3D chest CT | Reconstrução da TC, segmentação e leitura do volume por um VLM 3D | **3D**: gantry, projeções, sinograma, retroprojeção, voxels e máscaras, com cortes 2D de referência | Geometria intrinsecamente espacial |
| electronic health record, radiology report generation, hallucination | LLM redigindo laudo ou alta a partir do prontuário | 2D: pipeline e telas com dados sintéticos, com os pontos de checagem de alucinação | Fluxo de trabalho |
| diffusion model | Remoção de ruído passo a passo | 2D: trajetória ruído→imagem, mais uma "paisagem" 3D do campo de score rotulada como metáfora | O conteúdo é a mudança no tempo |
| (mecanismo de fármaco, quando surgir) | Ligação fármaco–alvo, mudança conformacional | **3D esquemático** a partir de estrutura do PDB | Espacial, mas com realismo contido |

Só dois dos seis casos justificam 3D de verdade, e isso também pesa no custo. Na medição local, 5 minutos de Manim 2D renderizam em cerca de 4–5 minutos, contra cerca de 14 minutos de captura para uma aula inteira em three.js ([medição local, notas](../research_notes/Aulas%20did%C3%A1ticas%20animadas%20em%203D/animacao_programatica_e_agentes.md)). O planejador deve, portanto, marcar cada cena com uma flag "3D justificado" e o lint deve recusar 3D sem justificativa.

## Nove etapas levam a tendência do grafo ao MP4 e à página local

A aula cabe no sotawhat como mais um estágio, um `run lesson` disparado depois do `run weekly` de domingo. Ele roda de madrugada e entrega junto com o diário das 07:00 de segunda. Proponho a seguinte organização:

- **Código novo:** um pacote `sotawhat/lessons/`.
- **Tarefas de LLM novas** na matriz de [tasks.py](../../../sotawhat/llm/tasks.py): `lesson_plan`, `lesson_code`, `lesson_repair` e `lesson_critique`.
- **Um teto próprio**, `SOTAWHAT_LLM_BUDGET_USD_LESSON`, ao lado dos tetos diário, semanal e mensal que o SDD já define ([SDD §13](../../sdd/2026-11-07-insight-engine-sdd.md)).
- **Dependências pesadas fora do processo principal**, chamadas como subprocessos e não importadas: o Manim num ambiente próprio com versão fixada, o Chromium headless para a captura e o Blender 5.2 com Python 3.13 para o Molecular Nodes.

O fluxo:

```
grafo (run weekly) ─► 1 pacote de fontes ─► 2 planejador: objetivo, storyboard JSON, narração pt-BR, quiz ─► G1 fatos
   ─► 3 TTS por cena ─► 4 alinhamento (tempo de cada palavra) ─► 5 código das cenas (Manim | three.js | Mol*/MN | malhas de TC)
   ─► 6 render + lint geométrico + reparo ─► G3/G4 crítico visual ─► 7 ativos, B-roll e música (opcionais)
   ─► 8 montagem FFmpeg (legenda ASS embutida, alvo de bitrate) ─► G8 revisão humana
   ─► 9 entrega: MP4 + quiz no Telegram e página /aulas/<id> em 127.0.0.1:8765
```

### O grafo entrega tema, pré-requisitos e fontes; o planejador entrega o roteiro

O `run weekly` já produz o que a aula precisa: as 12 tendências do topo, as comunidades rotuladas, as lacunas técnica × problema e as ideias finalistas ([weekly.py](../../../sotawhat/pipeline/weekly.py)). O seletor escolhe a tendência mais forte ainda não ensinada ou uma ideia marcada como "curtida", e um comando no bot permite pedir um tema avulso. Um LLM então decide qual é o "processo mais complexo" do tema, ou seja, o mecanismo e não a notícia.

É aqui que o grafo vira vantagem sobre qualquer SaaS. Os vizinhos da entidade (relações USES, BUILDS_ON, ADDRESSES, EVALUATED_ON) fornecem as 3–5 peças do pré-treino. Os itens que a mencionam, com o texto completo que o coletor já baixa, formam o pacote de fontes. Contra esse pacote se checam fatos e se geram as perguntas do quiz.

O planejador recebe esse pacote e devolve um storyboard em JSON validado por esquema. Cada cena traz:

- objetivo e modo (`manim2d`, `three3d`, `mol`, `ct` ou `broll`);
- a justificativa para usar 3D;
- duração de até 60 s;
- a narração em pt-BR;
- os rótulos, com o termo técnico em inglês e uma glosa em português;
- os elementos com suas âncoras de layout;
- as fontes citadas.

O planejador também gera 3–5 itens de quiz a partir das fontes, não do roteiro.

Para esse papel recomendo o **Kimi K3.1 Pro**. É o melhor modelo aberto no AA-3D (**Elo 1110**) ([AA-3D](https://artificialanalysis.ai/evaluations/aa-3d)) e o melhor no Design Bench da própria Moonshot (957, contra 863 do DeepSeek V4.1 Flash) ([Kimi K3.1 Pro](https://huggingface.co/moonshotai/Kimi-K3.1-Pro)). Como o planejamento consome pouco, custa cerca de US$ 0,15 por aula. No cenário econômico, o DeepSeek V4.1 Flash 1017 assume o papel.

A separação entre planejar e programar é a escolha de projeto mais bem sustentada da literatura. O Code2Video perde metade do quiz e da estética sem ela ([Code2Video](https://arxiv.org/html/2510.01174v1)). Na Teaching Monster, dividir storyboard e código aumentou o sucesso de renderização ([Teaching Monster](https://arxiv.org/html/2608.08852v1)).

Antes de seguir, o roteiro passa pela mesma validação de português que a triagem já usa. No bake-off de 08/11, o MiniMax-M3.1-Flash **inseriu caracteres chineses em 22% dos resumos em pt-BR** ([config/llm.yaml](../../../config/llm.yaml)), e um único caractere CJK contaminaria a narração. Depois disso o roteiro passa pelo portão de fatos, G1, descrito na seção de riscos.

### A narração vem antes da animação e dita o tempo de cada cena

A ordem certa é sintetizar a voz de cada cena primeiro e animar depois. Assim a duração e o instante de cada palavra viram os quadros-chave da animação, o que realiza a contiguidade temporal (d = 1,31) por construção. Foi o que os times da Teaching Monster fizeram, usando os tempos por palavra do faster-whisper para disparar as animações ([Teaching Monster](https://arxiv.org/html/2608.08852v1)).

Os tempos por palavra têm duas origens possíveis:

- **O próprio TTS**, quando ele os fornece. O Azure emite WordBoundary ([Azure](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis?pivots=programming-language-python)) e o MiniMax tem `subtitle_type: "word"` ([MiniMax T2A](https://platform.minimax.io/docs/api-reference/speech-t2a-http)).
- **Um alinhamento forçado do texto conhecido.** É o caso do Chirp 3 HD, que ignora a marcação `<mark>` e não devolve tempos ([Chirp 3 HD](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd)). O alinhador indicado é o **Qwen3-ForcedAligner-0.6B**: Apache-2.0, com português, desvio médio de **42,9 ms contra 133,2 ms do WhisperX**, e limite de 5 minutos de áudio, que o alinhamento por cena respeita ([Qwen3-ForcedAligner](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B)).

Antes da síntese, o roteiro precisa de normalização. Números, unidades e siglas devem ser escritos por extenso, porque o WhisperX não consegue dar tempo a números e moedas ([WhisperX](https://github.com/m-bain/whisperX)). O jargão em inglês exige um glossário único com três colunas (termo, IPA e grafia adaptada), aplicado conforme o motor de voz:

- o Chirp 3 HD aceita `custom_pronunciations` em IPA ([Chirp 3 HD](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd));
- o Azure aceita `<phoneme>` e léxicos ([Azure](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-pronunciation));
- os modelos locais dependem da grafia adaptada.

Um desenvolvedor brasileiro que usou o Qwen3-TTS por dois meses relatou termos ingleses saindo com sotaque e entonação "flat", e precisou reescrever palavras inglesas no roteiro ([Akita on Rails](https://akitaonrails.com/en/2026/04/09/how-elevenlabs-was-not-killed-by-qwen3-tts/)).

A escolha da voz merece um teste cego, porque o princípio da voz tem efeito grande (d = 0,74). Os três candidatos fortes:

- **Google Chirp 3 HD:** tem **30 vozes pt-BR dedicadas** ([vozes](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types)) e **1 milhão de caracteres grátis por mês** ([preços Google](https://cloud.google.com/text-to-speech/pricing)). Oito aulas de 4.500 caracteres somam 36 mil, de modo que o custo é zero.
- **Qwen3-TTS 1.7B local:** Apache-2.0, com WER em português de 1,526 no conjunto de teste multilíngue, contra 1,877 do MiniMax ([Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)). Roda a **1,83× o tempo real numa RTX 4060 no Windows** com CUDA graphs, ou seja, cerca de 3 minutos por aula. Sem eles a velocidade cai para 0,23×, cerca de 22 minutos ([faster-qwen3-tts](https://pypi.org/project/faster-qwen3-tts/)). Ele não tem voz pré-definida em português, então exige uma voz desenhada ou clonada de alguém que consinta, como você.
- **ElevenLabs v4:** o teto de qualidade, nº 1 da arena com Elo 1339 ([AA TTS](https://artificialanalysis.ai/text-to-speech/leaderboard)), a **US$ 0,36 por aula** ([ElevenLabs API](https://elevenlabs.io/pricing/api)).

Todos os passos com GPU cabem em 8 GB isoladamente, mas não juntos. O orquestrador deve rodá-los em sequência (TTS, alinhamento, música, render) e descarregar cada modelo antes do próximo ([notas de narração](../research_notes/Aulas%20did%C3%A1ticas%20animadas%20em%203D/narracao_avatar_audio.md)).

### Manim desenha o abstrato, three.js o espacial e o Blender fica na bancada

O **Manim CE 0.22.1** (MIT, lançado em 27/10/2026) renderiza as cenas abstratas ([Manim CE](https://github.com/ManimCommunity/manim)). Na medição local:

- Instalou com `uv` em cerca de 15 s, sem FFmpeg nem LaTeX no sistema.
- Uma cena 2D de atenção (heatmap 6×6, setas e fórmula) renderizou 10 s de vídeo em 1080p30 em **8,2 s**.
- Uma cena 3D com superfície e câmera girando levou **60,9 s no Cairo e 12,3 s com `--renderer=opengl`** para 6 s de vídeo ([medição local](../research_notes/Aulas%20did%C3%A1ticas%20animadas%20em%203D/animacao_programatica_e_agentes.md)).
- O `MathTex` exige uma distribuição TeX, que ainda não está instalada.

O risco do Manim está no LLM que escreve o código. O ManiBench documenta **145 incompatibilidades entre ManimGL e ManimCE**, e os modelos misturam as duas APIs ([ManiBench](https://huggingface.co/datasets/nabin2004/ManiBench/blob/main/ManiBench_Prompt_Engineering_Guide.md)). No TheoremExplainAgent, a primeira causa de falha foi alucinação de código Manim ([TheoremExplainAgent](https://arxiv.org/html/2502.19400v2)).

O antídoto tem cinco peças, todas com evidência:

1. **Versão fixada**, com uma "cola" só de CE no prompt.
2. **Templates por família de tema** (transformer, difusão, TC, molécula, prontuário) com posições de âncora. É a versão sem treinamento da grade 6×6 do Code2Video.
3. **Um linter geométrico** que lê `get_bounding_box` e reprova sobreposição, saída do quadro e escala ilegível antes de qualquer VLM. No SGA, essa checagem **venceu o crítico VLM em 7 de 8 configurações**, com execução parcial em menos de 5 s contra 30–90 s de render completo ([SGA](https://arxiv.org/html/2607.18116v1)).
4. **Reparo com escopo**, alimentado pelo traceback e por trechos da documentação, com até cinco tentativas como no TheoremExplainAgent. O modelo é trocado por um mais forte depois da segunda falha.
5. **Uma memória de acertos e armadilhas por template.** No ManimAgent ela elevou o Pass@1 de 62,0 para **84,9** e reduziu à metade as rodadas de reflexão ([ManimAgent](https://arxiv.org/html/2606.30296)).

Para o espacial, o renderizador é o **three.js r187 com React Three Fiber 9.8**, ambos MIT ([three.js](https://github.com/mrdoob/three.js); [R3F](https://github.com/pmndrs/react-three-fiber)). A regra é escrever cada cena como **função pura do tempo, `renderAt(t)`**, sem estado guiado por `requestAnimationFrame`. Assim a página interativa converte os tempos da narração em `t`, e a captura avança `t` quadro a quadro.

A captura foi medida neste PC com Puppeteer, um screenshot JPEG por quadro, numa cena com 4.096 cubos instanciados, sombras e PBR:

- **10,8 fps em 1080p, ou cerca de 14 minutos por aula de 5 minutos.**
- O Chromium headless usou a RTX 4060 via ANGLE/Direct3D 11 sem nenhuma flag.
- O render puro chega a 338–409 fps, então o gargalo é a captura.
- A captura em várias abas falhou por timeout ([medição local](../research_notes/Aulas%20did%C3%A1ticas%20animadas%20em%203D/animacao_programatica_e_agentes.md)).

O Remotion faz o mesmo com mais ferramentas de composição. É grátis para pessoa física e empresas de até 3 pessoas; acima disso cobra **US$ 25 por assento-mês** ou um mínimo de US$ 100/mês no plano de automação ([licença Remotion](https://cdn.jsdelivr.net/npm/remotion/LICENSE.md); [preços](https://www.remotion.pro/license)). Recomendo um capturador próprio de cerca de cem linhas com FFmpeg, por três motivos: foi o que se mediu, não cria dependência de licença para a startup e o FFmpeg já é necessário para juntar os trechos do Manim.

Para escrever essas cenas:

- O **MiMo-V2.6-Pro** é o modelo de uso diário: Elo 983 no AA-3D a US$ 0,44 por tarefa.
- O **Kimi K3.1 Pro** (1110) fica para as cenas-herói.
- O **GLM-5.3**, apesar de estar entre os seus modelos fixados, deve ficar fora do código 3D. Sem visão, bateu no limite de 250 turnos em 64% das cenas e marcou 783. O GLM-5.3-Flash, que enxerga, marcou 937 ([artigo AA-3D](https://artificialanalysis.ai/articles/aa-3d); [AA-3D](https://artificialanalysis.ai/evaluations/aa-3d)).

O **Blender 5.2 LTS**, com suporte até julho de 2028, é a melhor ferramenta 3D e a pior para este pipeline ([Phoronix](https://www.phoronix.com/news/Blender-5.2-Released)):

- A cerca de 2,3 s por quadro no EEVEE numa RTX 4060, uma aula de 9.000 quadros levaria **perto de 5,75 horas** ([DatabaseMart](https://www.databasemart.com/blog/blender-gpu-cpu-benchmark-rtx4060-e5-2667v3)).
- Agentes guiados só pelo resultado visual chegaram a **0% de sucesso em cenas completas** ([arXiv 2603.26942](https://arxiv.org/abs/2603.26942)).
- O servidor MCP oficial executa código gerado por LLM "without any guards in place" ([Blender Lab MCP](https://www.blender.org/lab/mcp-server/)).

Por isso ele entra só offline: para limpar malhas, exportar glTF e fazer clipes-herói de até 10–20 s.

Moléculas seguem a mesma lógica. Estruturas do PDB (CC0) e do AlphaFold DB (CC BY 4.0) viram cena por código ([RCSB](https://rcsb.org/pages/policies); [AlphaFold DB](https://alphafold.ebi.ac.uk/assets/License-Disclaimer.pdf)) por dois caminhos:

- O **Mol\*** (MIT) exporta MP4, anima de forma declarativa via MolViewSpec e também serve na página interativa ([Mol\*](https://molstar.org/viewer-docs/tips/movie-export)).
- O **Molecular Nodes** dá o acabamento cinematográfico, mas exige Python 3.13 e por isso roda num ambiente separado do sotawhat, que usa 3.12 ([Molecular Nodes](https://pypi.org/project/molecularnodes/)).

Para TC, a tarefa `total` do **TotalSegmentator** (Apache-2.0, 117 estruturas) segmenta uma TC pública e marching cubes geram as malhas GLB. O modelo de 3 mm usou cerca de 5,2 GB e levou 34 s numa RTX 3090 para uma TC pequena ([TotalSegmentator](https://arxiv.org/pdf/2208.05868)). Órgãos canônicos vêm prontos do HuBMAP/HRA e do BodyParts3D, ambos CC BY 4.0 ([HRA](https://hubmapconsortium.github.io/ccf/pages/ccf-3d-reference-library.html); [BodyParts3D](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/README_e.html)).

### Vídeo generativo, ativos gerados e música têm papéis restritos

O vídeo generativo entra só na camada decorativa: o gancho de abertura, as transições e as metáforas visuais, sempre com o rótulo "ilustração artística". Nunca entra no mecanismo.

A forma mais controlável é gerar o vídeo a partir de imagens renderizadas em código, travando o primeiro e o último quadro. O checkpoint aberto FL2VA do MiniMax H3 aceita um quadro inicial, um final ou ambos ([MiniMax H3](https://huggingface.co/MiniMaxAI/MiniMax-H3)). Os rótulos ficam fora dos pixels gerados e são sobrepostos depois em código, porque a maioria desses modelos não produz texto legível ([T2VTextBench](https://www.emergentmind.com/papers/2505.04946)).

A rota padrão seria o **MiniMax H3 Max Turbo via fal, a US$ 0,04/s em 768p** a partir de 16/11/2026 ([fal](https://fal.ai/models/minimax/h3-max-turbo/text-to-video/llms.txt)). Ele é uma variante da família H3, cujo modelo base (768p) é o 3º colocado em texto-para-vídeo, com **Elo 1161, bem acima do Kling 3.0 (âncora, 1000)**, e custa metade do Kling ([AA T2V](https://artificialanalysis.ai/video/leaderboard/text-to-video)). Três cuidados acompanham essa escolha:

- **Retenção na fal:** ela guarda as requisições por 90 dias por padrão, então todas as chamadas devem levar `X-Fal-Store-IO: 0` ([fal](https://fal.ai/docs/model-apis/data-retention)).
- **Evitar o Kling:** uma análise dos termos de uso indica que ele se reserva uma licença sobre entradas e saídas, inclusive para treinamento ([ConductAtlas](https://conductatlas.com/platform/kling-ai/kling-ai-terms-of-service/user-content-license/)). O Sora não é opção: saiu do ar em 24/09/2026 ([OpenAI](https://developers.openai.com/api/docs/models/sora-2.md)).
- **Descarte e moderação:** o orçamento deve prever cerca de **3 gerações por tomada aproveitável**, e taxas de 1 em 4 a 1 em 10 são comuns ([invideo](https://invideo.io/faq/how-many-ai-video-generations-do-you-need-per-usable/)). Imagens cirúrgicas são um falso positivo frequente da moderação ([Segmind](https://blog.segmind.com/gemini-omni-flash-keeps-rejecting-your-prompts-9-fixes-that-actually-work/)), o que pede enquadramento clínico e um segundo provedor de reserva.

Ativos 3D gerados por IA servem apenas para props: GPU, rack, leito, monitor. Na Tripo:

- uma malha sem textura custa **US$ 0,10**;
- uma com textura a partir de imagem custa **US$ 0,30**;
- o auto-rig custa US$ 0,25;
- a recarga mínima é de US$ 1 ([Tripo](https://developers.tripo3d.ai/en/pricing)).

O modelo H3.1 da Tripo é o 4º em preferência humana, com Elo 1261 ([benchmark.ai](https://www.benchmark.ai/image-to-3d)). O Tencent HY 3D Global dá 200 créditos grátis e cobra US$ 0,30–0,50 por ativo ([Tencent](https://www.tencentcloud.com/document/product/1284/75281)). Localmente, o Hunyuan3D-2mini gera formas em cerca de 6 GB ([Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)), mas os modelos abertos ficam muito atrás: o Hunyuan3D 2.1 marca 750, contra 1144–1366 dos hospedados. Órgãos e moléculas nunca devem vir de geração; vêm das bibliotecas citadas. Cada ativo entra num cache com manifesto de licença (fonte, URL, licença, crédito, uso comercial, share-alike). É esse manifesto que gera os créditos e barra ativos NC ou SA numa versão comercial.

A música, pela evidência de coerência, fica **desligada por baixo dos mecanismos**. Se você quiser uma vinheta no início e no fim, o **ACE-Step 1.5** resolve de graça:

- é MIT e roda na faixa de 6–8 GB;
- o próprio cartão do modelo autoriza o uso comercial das faixas geradas ([ACE-Step 1.5](https://huggingface.co/ACE-Step/Ace-Step1.5); [GitHub](https://github.com/ace-step/ACE-Step-1.5));
- dez a vinte faixas de fundo geradas uma vez bastam para todas as aulas.

Na mixagem, o FFmpeg abaixa a música sob a voz com `sidechaincompress` e normaliza com `loudnorm` ([FFmpeg](https://ffmpeg.org/ffmpeg-filters.html)) para cerca de −16 LUFS, a referência da Apple para voz falada ([Apple](https://podcasters.apple.com/support/audio-requirements)). Ficam fora:

- o MusicGen, cujos pesos são não comerciais ([AudioCraft](https://github.com/facebookresearch/audiocraft));
- o plano grátis do Suno, também não comercial ([Suno](https://suno.com/blog/suno-updates-tos));
- a API de música da MiniMax, fechada a novos usuários desde 20/08/2026 ([MiniMax](https://platform.minimax.io/docs/guides/pricing-paygo)).

Avatar, nenhum. Se um dia a versão da startup pedir um rosto, basta um PiP de 1 minuto no início, com Kling Lip Sync a US$ 0,84/min sobre um clipe seu ([Kling](https://kling.ai/document-api/pricing/base/video.md)), ou com o MuseTalk 1.5 local, que roda em 4 GB e permite uso comercial ([MuseTalk](https://github.com/TMElyralab/MuseTalk)).

### Uma cena, duas saídas: MP4 no Telegram e página interativa local

**Legendas.** No MP4 elas vão gravadas na imagem, em ASS via libass. O player do Telegram não exibe faixas de legenda embutidas no arquivo, e um pedido aberto desde 2021 continua sem resposta ([Telegram bugs](https://bugs.telegram.org/c/8284)). A página usa WebVTT no elemento `<track>` ([MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/track)).

**Tamanho.** A API de bots na nuvem limita o `sendVideo` a **50 MB** ([Bot API](https://core.telegram.org/bots/api)). Cinco minutos cabem nesse limite com cerca de 1,3 Mbps no total:

- 1080p em duas passadas a ~1.100 kbps de vídeo mais 96 kbps de áudio dá cerca de 45 MB;
- 720p a ~900 kbps dá cerca de 37 MB.

A animação comprime bem: a Netflix transmite animação em 1080p com cerca de 1,5 Mbps ([The Register](https://www.theregister.com/2015/12/16/netflix_per_title_encode_optimization/)). Para mandar o master em 1080p, há o servidor local da Bot API, que aceita até **2.000 MB** e exige `api_id`/`api_hash` próprios e um `logOut` no servidor da nuvem ([telegram-bot-api](https://github.com/tdlib/telegram-bot-api)).

**O que falta no bot.** Hoje o bot do sotawhat só chama `sendMessage` em `api.telegram.org` ([telegram.py](../../../sotawhat/notify/telegram.py)). Ele precisa ganhar:

- um `sendVideo` com `supports_streaming`;
- um quiz em botões inline, que reaproveita o laço de callbacks já existente;
- um agendador de re-quiz para 1–3 dias e 1–2 semanas depois.

**A página interativa** é uma rota `/aulas/<id>` no FastAPI que já roda em 127.0.0.1:8765. Ela reúne:

- a cena three.js, com uma linha do tempo que converte os tempos da narração em `t`;
- os trechos do Manim embutidos como WebM;
- o Mol\* para moléculas;
- a legenda VTT e o quiz.

O custo de render é zero: no AA-3D, o quadro mediano das cenas feitas por agentes gasta menos de 1,3 ms de GPU ([artigo AA-3D](https://artificialanalysis.ai/articles/aa-3d)). As referências do gênero podem ser estudadas e adaptadas com o aviso de copyright, porque são todas MIT: Transformer Explainer ([GitHub](https://github.com/poloclub/transformer-explainer)), LLM Visualization de Brendan Bycroft ([GitHub](https://github.com/bbycroft/llm-viz)) e Diffusion Explainer ([GitHub](https://github.com/poloclub/diffusion-explainer)).

A limitação é de alcance: um link para 127.0.0.1 só abre na própria máquina. O MP4 continua sendo o formato do celular, e expor a página para fora é uma decisão de segurança que fica entre as perguntas em aberto.

## Ferramentas e modelos: preço, licença e papel de cada um

As tabelas abaixo consolidam as escolhas. Os preços de LLM são os dos endpoints ZDR elegíveis mais baratos, lidos na API do OpenRouter em 09/11/2026, em US$ por milhão de tokens de entrada/saída ([OpenRouter ZDR](https://openrouter.ai/api/v1/endpoints/zdr)). "Aula" significa 5 minutos com 4.500 caracteres de narração.

**Animação por código e renderização**

| Ferramenta | Licença | Custo | Desempenho (neste PC, salvo indicação) | Uso recomendado |
|---|---|---|---|---|
| Manim CE 0.22.1 | MIT | 0 | 2D: 8,2 s por 10 s em 1080p30. 3D: 2× o tempo real (OpenGL) ou 10× (Cairo) | Padrão para matemática, matrizes, fluxos e 2,5D, com versão fixada |
| three.js r187 + R3F 9.8.2 | MIT | 0 | Captura a 10,8 fps em 1080p (≈ 14 min por aula). Interativo a < 1,3 ms por quadro | Padrão para cenas espaciais; a mesma cena serve à página |
| Capturador Puppeteer + FFmpeg | MIT / LGPL | 0 | Idem | Gerar o MP4 das cenas web |
| Remotion 4.0 + @remotion/three | Própria: grátis para pessoa física e empresa de até 3 pessoas | Acima disso, US$ 25/assento-mês ou mínimo de US$ 100/mês | Não medido; exige `gl: "angle"` | Alternativa, se quiser composição em React |
| Mol\* + MolViewSpec | MIT | 0 | Exporta MP4 no navegador | Moléculas no MP4 e na página |
| Molecular Nodes 520.2 | Conflito: GPL-3.0 no GitHub, MIT no PyPI | 0 | Não medido; exige Python 3.13 | Moléculas cinematográficas, em ambiente separado |
| TotalSegmentator (tarefa `total`) | Apache-2.0 | 0 | 34 s a 2 min 49 s por TC numa RTX 3090; ≈ 5,2 GB no modelo de 3 mm | Malhas de órgãos a partir de TC pública |
| Blender 5.2 LTS | GPL (não verificado nas notas) | 0 | EEVEE ≈ 2,3 s por quadro, ou ≈ 5,75 h por aula | Só preparo de ativos e clipes-herói de até 20 s |
| Godot 4.7 (Movie Maker) | MIT | 0 | Render determinístico | Reserva; os LLMs escrevem GDScript pior |
| Motion Canvas, Revideo, Theatre.js | MIT; Apache-2.0 + AGPL | 0 | — | Evitar: projetos parados |

Fontes: [Manim CE](https://github.com/ManimCommunity/manim), [Remotion](https://www.remotion.pro/license), [Mol\*](https://github.com/molstar/molstar), [Molecular Nodes](https://github.com/BradyAJohnston/MolecularNodes), [TotalSegmentator](https://github.com/wasserth/TotalSegmentator), [Godot](https://docs.godotengine.org/en/stable/tutorials/animation/creating_movies.html), [Motion Canvas](https://github.com/motion-canvas/motion-canvas), [Theatre.js](https://github.com/theatre-js/theatre) e as medições locais nas [notas](../research_notes/Aulas%20did%C3%A1ticas%20animadas%20em%203D/animacao_programatica_e_agentes.md).

**LLMs e VLMs por endpoint ZDR**

| Modelo | US$/1M (entrada/saída) | Evidência | Papel recomendado |
|---|---|---|---|
| DeepSeek V4.1 Flash 1017 | 0,078 / 0,235 (DeepInfra fp8) | AA Index 33; DeepSWE 77,0 na tabela da Moonshot | Programador e reparo do Manim; planejador no econômico |
| Kimi K3.1 Pro | 1,80 / 8,20 (Phala); leitura de cache a 0,18 | Melhor modelo aberto no AA-3D (1110); AA Index 46 | Storyboard e roteiro; cenas-herói; escalonamento depois de 2 falhas |
| MiMo-V2.6-Pro | 0,387 / 0,783 (DeepInfra fp8) | AA-3D 983 a US$ 0,44 por tarefa; aceita texto, imagem, vídeo e áudio | Programador three.js; reserva de outra família |
| MiMo-V2.6-Flash | 0,14 / 0,28 | Aceita vídeo; AA Index 27 a US$ 0,13 por tarefa | Crítico visual que assiste ao clipe renderizado |
| GLM-5.3-Flash | 0,052–0,085 / 0,173–0,25 | Visão nativa; AA-3D 937; raciocínio obrigatório | Crítico alternativo em quadros-chave |
| Qwen3-VL-235B | 0,20 / 0,88 | VLM de uma terceira família | Reserva do crítico |
| GLM-5.3 | 0,14 / 2,10 (Reka) | Só texto; AA-3D 783; raciocínio forçado em `max` | Fora do código 3D |
| MiniMax-M3 / M3.1-Flash | 0,224 / 0,88 e 0,15 / 0,60 | AA-3D 740 (M3); caracteres CJK em 22% dos resumos em pt-BR (M3.1-Flash) | Evitar neste pipeline |
| Gemini Flash (Vertex) | 0,125–0,375 / 0,75–1,875 (flex) | Só endpoints com Safety Retention | Fora, se a conta exige "ZDR only" |

Fontes: [OpenRouter ZDR](https://openrouter.ai/api/v1/endpoints/zdr), [AA Intelligence Index](https://artificialanalysis.ai/leaderboards/models), [AA-3D](https://artificialanalysis.ai/evaluations/aa-3d), [Kimi K3.1 Pro](https://huggingface.co/moonshotai/Kimi-K3.1-Pro), [config/llm.yaml](../../../config/llm.yaml).

**Narração, legendas e música**

| Opção | Custo por aula | Licença e dados | Tempo por palavra | Papel |
|---|---|---|---|---|
| Qwen3-TTS 1.7B local | 0 (≈ 3 min de GPU) | Apache-2.0; nada sai do PC | Não (alinhar) | Econômico e rascunhos |
| Google Chirp 3 HD | 0 até 1 milhão de caracteres/mês; depois US$ 0,135 | Dados do cliente não usados para treino | Não (alinhar) | Voz padrão do equilibrado |
| Azure Neural S0 | US$ 0,068 | Direito de uso da saída só no plano pago; texto não retido | Sim (WordBoundary) | Alternativa com tempos nativos e IPA |
| ElevenLabs v4 | US$ 0,36 (o Starter de US$ 6/mês inclui 75 mil caracteres) | Uso comercial só nos planos pagos; usa entradas para treino, salvo opt-out | Por caractere | Premium |
| Alibaba qwen3-tts-flash | US$ 0,045 | Chamadas de API não usadas para treino | Não documentado | A chinesa mais barata; sem voz pronta em português |
| MiniMax speech-2.8 turbo / hd | US$ 0,27 / 0,45 | Termos de dados não verificados | Sim (por palavra) | Chinesa com tempos nativos |
| ByteDance Seed Speech 2.0 | US$ 0,135 (revenda fal) | Preço oficial não encontrado | Não | A única chinesa com `pt-br` explícito |
| Kokoro-82M / Piper pt_BR | 0 (CPU) | Apache-2.0 / CC0 a CC BY | Não | Reserva quando a GPU está ocupada |
| Qwen3-ForcedAligner-0.6B | 0 | Apache-2.0 | Alinha o texto conhecido (desvio de 42,9 ms) | Legendas e gatilhos de animação |
| ACE-Step 1.5 | 0 | MIT; faixas de uso comercial | — | Vinheta opcional |
| XTTS-v2, F5-TTS pt-BR, Fish S2 Pro, Voxtral, MusicGen | 0 | Não comerciais | — | Evitar |

Fontes: [Google](https://cloud.google.com/text-to-speech/pricing), [termos Google Cloud](https://cloud.google.com/terms/service-terms), [Azure F0 × pago](https://learn.microsoft.com/en-us/answers/questions/5805156/please-clarify-the-conflicting-information-regardi), [ElevenLabs](https://elevenlabs.io/privacy-policy), [Alibaba](https://www.alibabacloud.com/help/en/model-studio/model-pricing), [MiniMax](https://platform.minimax.io/docs/guides/pricing-paygo), [Seed Speech](https://fal.ai/models/fal-ai/bytedance/seed-speech/tts/v2/llms.txt), [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), [XTTS-v2](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt), [Voxtral](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603).

**Vídeo generativo** (sem áudio nativo, porque a narração é dublada à parte)

| Modelo / rota | US$/s | Elo AA texto→vídeo / imagem→vídeo | Licença e dados | Uso |
|---|---|---|---|---|
| MiniMax H3 Max Turbo (fal, 768p) | 0,04 (promoção a 0,028 até 15/11) | Variante do H3 Max (1147 / 1115) | Sem `X-Fal-Store-IO: 0`, a fal guarda 90 dias | Padrão do premium |
| MiniMax H3 oficial (768p) | 0,08 | 1161 / 1133 | Pesos abertos; a licença exclui EUA, UE, Reino Unido e Coreia; a política de uso veda decisões automatizadas em saúde | Imagem→vídeo com primeiro e último quadro |
| Pika H3 Flex | 0,035 | 1124 / 1115 | LoRA sobre o H3 | Alternativa barata |
| HeyGen Video 1 | 0,04 | 1153 / 1124 | Rota de acesso não verificada | Alternativa |
| PixVerse V6 (720p, mudo) | 0,045 | 981 / 959 | — | Estilo `3d_animation` para B-roll estilizado |
| Veo 3.1 Lite (720p) | 0,05 | 949 / 931 | A API paga do Gemini não usa os dados para melhorar produtos | Reserva com termos claros |
| Kling 3.0 Pro | 0,084–0,168 | 1000 / 1000 (âncora) | Os termos licenciam entradas e saídas, inclusive para treino | Evitar |
| Seedance 2.5 | 0,569 | 1155 / 1161 | A BytePlus não treina sem autorização | Só uma tomada-herói rara |
| Wan 2.2 14B "Rapid" local | 0 (PC) | Fora do ranking; qualidade inferior | Apache-2.0 | 480p, ≈ 2 min por clipe de 2 s na RTX 4060 |

Fontes: [AA texto→vídeo](https://artificialanalysis.ai/video/leaderboard/text-to-video), [AA imagem→vídeo](https://artificialanalysis.ai/video/leaderboard/image-to-video), [fal H3 Turbo](https://fal.ai/models/minimax/h3-max-turbo/text-to-video/llms.txt), [preço H3 oficial](https://www.atlascloud.ai/blog/guides/minimax-h3-api-pricing), [licença H3](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE), [PixVerse](https://fal.ai/models/fal-ai/pixverse/v6/text-to-video/llms.txt), [Veo 3.1 Lite](https://the-decoder.com/googles-veo-3-1-lite-cuts-video-generation-costs-by-more-than-half/), [Gemini API](https://aistudio.google.com/docs/pricing), [BytePlus](https://docs.byteplus.com/ja/docs/ModelArk/BytePlus_ModelArk_Data_Processing), [Wan 2.2 na RTX 4060](https://lilting.ch/en/articles/wan22-comfyui-rtx4060-i2v).

**Ativos 3D**

| Fonte ou serviço | Licença | Custo | Uso |
|---|---|---|---|
| HuBMAP/HRA (órgãos em GLB) | CC BY 4.0 | 0 | Órgãos canônicos |
| BodyParts3D (OBJ, com tabelas de IDs) | CC BY 4.0 desde fev/2025 | 0 | Vasos, nervos, músculos e ossos |
| MedShapeNetCore (STL) | CC BY 4.0 | 0 | Anatomia de pacientes reais e patologia |
| TC pública + TotalSegmentator `total` | CC BY 4.0 + Apache-2.0 | 0 | Cenas de TC e segmentação |
| RCSB PDB / AlphaFold DB | CC0 / CC BY 4.0 | 0 | Moléculas |
| Smithsonian 3D, Poly Haven, Kenney, Quaternius | CC0 | 0 | Props |
| Tripo API (H3.1, Elo 1261) | Saídas pagas; direitos do plano grátis em disputa | US$ 0,10–0,30 por ativo; rig + US$ 0,25 | Props que faltam |
| Tencent HY 3D Global (3.1) | — | US$ 0,30–0,50; 200 créditos grátis | Alternativa |
| Hunyuan3D-2mini local | Licença Tencent (exclui UE, Reino Unido e Coreia; política de uso com cláusulas médicas) | 0; formas em ≈ 6 GB | Props esquemáticos offline |
| Z-Anatomy, MSD, ChimeraX, VISTA3D/MAISI, tarefas licenciadas do TotalSegmentator | CC BY-SA ou não comerciais | — | Só no build de estudo pessoal |

Fontes: [HRA](https://hubmapconsortium.github.io/ccf/pages/ccf-3d-reference-library.html), [BodyParts3D](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/README_e.html), [MedShapeNetCore](https://zenodo.org/records/10623506), [Smithsonian](https://dashboard.si.edu/openaccess/faq), [Tripo](https://developers.tripo3d.ai/en/pricing), [Tencent](https://www.tencentcloud.com/document/product/1284/75281), [licença Hunyuan3D](https://raw.githubusercontent.com/Tencent-Hunyuan/Hunyuan3D-2.1/main/LICENSE), [Z-Anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy), [ChimeraX](https://www.cgl.ucsf.edu/chimerax/docs/licensing.html).

## Uma aula custa de dez centavos a vinte dólares, e o vídeo generativo é quase tudo

A conta parte de um orçamento de tokens por aula de 5 minutos com 10 cenas: **cerca de 480 mil tokens de entrada e 165 mil de saída**, distribuídos em 41 chamadas. São o planejador, um programador por cena, cerca de um reparo por cena, a crítica visual e as correções. O número se ancora no único consumo medido de um sistema completo: o TheoremExplainAgent gastou **434 mil de entrada e 154 mil de saída por vídeo de cerca de 5 minutos**, ao custo de US$ 1,16 com o o3-mini em 2025 ([TheoremExplainAgent](https://arxiv.org/html/2502.19400v2)). Esse mesmo consumo, ao preço ZDR de hoje do DeepSeek V4.1 Flash 1017, custaria **cerca de US$ 0,07** ([OpenRouter ZDR](https://openrouter.ai/api/v1/endpoints/zdr)).

Premissas da conta:

- **Volume de referência:** 8 aulas por mês. Com uma por semana, os totais mensais caem pela metade.
- **Fora da tabela:** a taxa de cerca de 5,5% na compra de créditos do OpenRouter, ainda não verificada ([notas LLM 11-07](../2026-11-07-insight-engine/llm_openrouter.md)).
- **Já incluído:** os portões de fatos e de conhecimento, que estimo em uns US$ 0,02 por aula.

| Item | Econômico/local | Equilibrado (recomendado) | Premium com vídeo generativo |
|---|---|---|---|
| LLM/VLM | DeepSeek V4.1 Flash em tudo + MiMo-V2.6-Flash como crítico: US$ 0,08–0,30 | Kimi K3.1 Pro (storyboard) + DeepSeek (Manim) + MiMo-V2.6-Pro (three.js) + MiMo-V2.6-Flash (crítico) + escalonamento: US$ 0,35–0,65 | Kimi K3.1 Pro de ponta a ponta: US$ 1,8–2,2 (até 6,6 com o triplo de tokens) |
| Narração | Qwen3-TTS local: 0 | Chirp 3 HD dentro da franquia: 0 (Azure S0: 0,07) | ElevenLabs v4 dentro do Starter: 0 de custo variável |
| Legendas e música | Alinhador e ACE-Step locais: 0 | 0 | 0 |
| Ativos 3D | Bibliotecas CC0/CC BY e geometria procedural: 0 | 2–5 props Tripo: US$ 0,40–1,50, tendendo a zero com o cache | 5–10 props com rig: US$ 1–5 |
| Vídeo generativo | — | — | 30 s úteis × 3 a 10 tentativas × US$ 0,04/s: US$ 3,60–12,00 |
| **Custo variável por aula** | **≈ US$ 0,10 (0,08–0,30)** | **US$ 0,75–2,20 no início; US$ 0,35–0,70 em regime** | **US$ 6,40–19,20** |
| Custo fixo mensal | 0 | 0 | US$ 6 (ElevenLabs Starter, ≈ 16 aulas) |
| Tempo de PC por aula | 15–30 min | 25–45 min | 45–90 min |
| **Total mensal (8 aulas)** | **US$ 0,80–2,40** | **US$ 6–18 no 1º mês; US$ 3–6 em regime** | **US$ 57–160** |
| Tempo de PC por mês | 2–4 h, de madrugada | 3,5–6 h | 6–12 h |
| Seu tempo | ≈ 15 min de revisão por aula (≈ 2 h/mês) | Idem | Idem, mais a escolha das tomadas |

### Como cada cenário chega aos seus números

**Econômico.** O tempo de máquina vem das medições locais:

- uma aula com 70% de Manim 2D e 30% de 3D em OpenGL renderiza em série em **6–7 minutos**;
- os reparos acrescentam 5–15 minutos, a 30–90 s por render completo de cena ([SGA](https://arxiv.org/html/2607.18116v1));
- o Qwen3-TTS leva cerca de 3 minutos;
- alinhamento e codificação fecham a conta.

As chamadas de API correm em paralelo e não ocupam o PC. O Code2Video leva 8,8–15,4 minutos por tema ([Code2Video](https://arxiv.org/html/2510.01174v1)).

**Equilibrado.** O custo de LLM se compõe assim:

- storyboard no Kimi: US$ 0,15;
- programação dividida entre DeepSeek e MiMo-V2.6-Pro: cerca de US$ 0,15;
- crítica: US$ 0,02;
- duas cenas por aula escalonadas para o Kimi: até US$ 0,28.

A máquina trabalha mais porque o three.js entra para valer. Uma aula meio a meio leva 9–10 minutos de render, e uma aula inteira em three.js chega a 14 minutos de captura. Um clipe molecular custa alguns minutos a mais; o EEVEE leva 1–4 minutos por 10 s, estimativa não medida ([notas de ativos](../research_notes/Aulas%20did%C3%A1ticas%20animadas%20em%203D/ativos_e_geracao_3d.md)).

**Premium.** O custo segue a regra prática das notas: custo = segundos úteis × tentativas por tomada × preço por segundo ([notas de vídeo](../research_notes/Aulas%20did%C3%A1ticas%20animadas%20em%203D/video_generativo.md)). Qualquer tomada que precise ser exata leva para perto de 10 tentativas, porque um erro anatômico visível a desclassifica. Há dois atalhos:

- **Meio-termo:** o equilibrado com apenas 15 s de tomadas-herói fica em **US$ 2,15–6,70 por aula, ou US$ 17–54 por mês**.
- **Modelos abertos em GPU alugada:** uma RTX 4090 comunitária custa US$ 0,34/h na RunPod ([RunPod](https://www.runpod.io/pricing)), o que dá US$ 0,001–0,04 por segundo de vídeo, de 10 a 50 vezes menos que as APIs. O preço é uma qualidade abaixo do H3. Os US$ 30/mês de crédito grátis da Modal pagam a experimentação ([Modal](https://modal.com/pricing)).

**Custos únicos.** Há três, nenhum relevante em dinheiro:

- a recarga mínima de US$ 1 na Tripo;
- uma distribuição TeX para o `MathTex`;
- uma biblioteca de trilhas do ACE-Step, gerada em menos de uma hora.

O investimento que decide o sucesso é de horas de engenharia: a biblioteca de templates por família de tema e o linter. São eles que levam o render sem intervenção para a faixa de 90–99% que a literatura de 2026 já alcança (OmniManim R@F 0,986) ([OmniManim](https://arxiv.org/html/2605.15585v1)).

### Comprar custa milhares de vezes mais, ou entrega outra coisa

| Opção | O que entrega | Custo por aula de 5 min | pt-BR | Mecanismo em 3D |
|---|---|---|---|---|
| Estúdio 3D médico | 3D sob medida, com revisão científica | US$ 25 mil–100 mil ou mais; 6–10 semanas para cada 1–2 min | Por localização | Sim |
| Estúdio 2D | Explicativo 2D | US$ 10–25 mil | Por localização | Não |
| Synthesia Pro (anual) | Avatar e slides | ≈ US$ 5 (≈ US$ 1/min) | Sim, citado | Não; conteúdo sobre tratamentos pode exigir o plano Enterprise |
| HeyGen Creator | Avatar | ≈ US$ 0,7–7 | Não citado na página | Não |
| Pictory | Banco de imagens, TTS e avatar | ≈ US$ 2–5 | Não listado | Não |
| NotebookLM (Gemini Notebook), Video Overview Explainer | Ilustração narrada | R$ 0 marginal (grátis ou AI Pro a R$ 96,99/mês) | Sim | Não; o formato Cinematic é só em inglês |
| Bibliotecas: Osmosis (US$ 249/ano), Ninja Nerd (US$ 168/ano), Visible Body (US$ 24,99) | Aulas prontas e atlas 3D | Não fazem aula sob medida | Quase só inglês | Atlas interativo |
| **Este pipeline** | 2D/3D por código, página interativa e quiz | **US$ 0,10–19** | Sim | Sim |

Fontes: [VOKA](https://voka.io/medical-animation-cost/), [Prolific Studio](https://prolificstudio.co/blog/medical-device-animation-cost/), [Synthesia](https://www.synthesia.io/pricing), [regras médicas da Synthesia](https://help.synthesia.io/en/articles/15396882-medical-advice-and-information), [HeyGen](https://www.heygen.com/pricing), [Pictory](https://pictory.ai/pricing), [Video Overviews](https://support.google.com/notebooklm/answer/16454555), [AI Pro no Brasil](https://tecnoblog.net/noticias/google-surpreende-ao-aumentar-espaco-e-manter-preco-do-one-ai-pro/), [Ninja Nerd](https://www.ninjanerd.org/membership), [Visible Body](https://apps.apple.com/il/app/id1117998129).

**Estúdios.** Um estúdio cobra de **US$ 5 mil a 20 mil por minuto finalizado**, e mecanismo de ação parte de US$ 20 mil por minuto ([VOKA](https://voka.io/medical-animation-cost/)). Contra os US$ 0,35–0,70 do regime equilibrado, comprar custa de dezenas a centenas de milhares de vezes mais. Só faz sentido para uma peça-vitrine da startup, revisada e licenciada.

**SaaS.** Os SaaS custam o mesmo que este pipeline, alguns dólares ou menos por aula, mas vendem principalmente avatar. É justamente o recurso com evidência mais fraca: no estudo de Netland e colegas, vídeos gerados por IA deram notas de prova iguais às dos vídeos humanos e ficaram prontos em horas, em vez de dias ([Netland et al. 2025](https://x-mol.com/paper/1857628113137397760)). Nenhum deles anima mecanismos em 3D.

**NotebookLM.** O concorrente honesto é o Video Overview do NotebookLM, rebatizado de Gemini Notebook. Ele narra em pt-BR nos formatos Explainer e Short e é grátis. Por outro lado, avisa que pode conter imprecisões e pode levar mais de 30 minutos para gerar ([Ajuda do Google](https://support.google.com/notebooklm/answer/16454555)). Desde 02/09/2026 os limites são por capacidade de processamento e se renovam a cada cinco horas ([Google](https://blog.google/innovation-and-ai/products/gemini-notebook/new-flexible-usage-limits/)). Gerado a partir do mesmo pacote de fontes, ele é a linha de base do piloto. O pipeline só se justifica se vencer o NotebookLM em comparação cega e no quiz feito dias depois, oferecendo o que ele não oferece: mecanismo em 3D, portões de exatidão, prática de recuperação e pré-requisitos tirados do seu grafo.

## Oito portões barram o erro com cara de acerto antes da entrega

### Conteúdo errado que parece certo

O risco central não é a aula feia, e sim a aula convincente e errada:

- **Imagens geradas.** Num estudo com 33 profissionais de saúde, **80,8%** das imagens de cardiopatias congênitas do DALL·E 3 foram julgadas anatomicamente incorretas ou inventadas. Os rótulos estavam errados em 85,2% delas, e 78,1% foram consideradas inúteis para ensino ([J Med Syst 2024](https://nchr.elsevierpure.com/en/publications/art-or-artifact-evaluating-the-accuracy-appeal-and-educational-va/)).
- **Texto gerado.** Em notas clínicas geradas por LLMs, **1,47% das frases eram alucinação e 3,45% omissão** ([npj Digital Medicine 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12075489/)).

O render por código é auditável e repetível, mas não é correto por definição: o LLM pode desenhar a seta errada com nitidez perfeita. Por isso o vídeo fotorrealista generativo fica fora dos mecanismos, cada frase do roteiro precisa apontar para uma fonte, e um checklist médico fecha a porta.

### Juízes automáticos discordam dos humanos

Os juízes automáticos são o segundo risco, porque discordam dos humanos com frequência:

- No ManimAgent, a concordância entre VLM e humanos foi **r = −0,17** ([ManimAgent](https://arxiv.org/html/2606.30296)).
- Na Teaching Monster, o ranking do juiz LLM correlacionou ρ = −0,17 com o público ([Teaching Monster](https://arxiv.org/html/2608.08852v1)).
- No SGA, o crítico VLM chegou a introduzir regressões, como elementos empurrados para fora do quadro ([SGA](https://arxiv.org/html/2607.18116v1)).
- O MLLM-as-a-Judge mostra que esses modelos concordam com humanos em **comparações pareadas**, mas divergem em notas absolutas ([MLLM-as-a-Judge](https://arxiv.org/abs/2402.04788)).

A ordem certa é geometria determinística primeiro, depois um VLM julgando pares e, por fim, um humano.

### Riscos de idioma

- **Caracteres chineses no texto.** O vazamento já apareceu no bake-off de triagem.
- **Jargão em inglês.** Sai com sotaque se o glossário falhar.
- **Números.** O alinhador não marca tempo para números.
- **Falta de evidência sobre a voz.** Não existe comparação cega de qualidade de voz em pt-BR entre Chirp 3 HD, Azure, ElevenLabs, Qwen3-TTS e MiniMax ([notas de narração](../research_notes/Aulas%20did%C3%A1ticas%20animadas%20em%203D/narracao_avatar_audio.md)). O teste cego da fase 0 cobre essa lacuna.

### Licenças e dados

São armadilhas que só aparecem quando o material sai do uso pessoal:

| Item | Restrição |
|---|---|
| Remotion | Exige licença paga a partir de 4 pessoas na empresa |
| Licença do MiniMax H3 | Exclui EUA, UE, Reino Unido e Coreia. Obriga a exibir o nome "MiniMax H3" em produtos comerciais. Proíbe usar as saídas para treinar outros modelos. A política de uso veda "high-risk automated decisions" em saúde ([licença H3](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE)) |
| Licença Hunyuan | Proíbe a prática médica não licenciada ([licença Hunyuan3D](https://raw.githubusercontent.com/Tencent-Hunyuan/Hunyuan3D-2.1/main/LICENSE)) |
| Z-Anatomy | É CC BY-SA e embute modelos não comerciais |
| Planos grátis de voz e 3D | Os planos F0 do Azure e grátis da ElevenLabs não dão direito comercial à saída. Os direitos do plano grátis da Tripo estão em disputa |
| Retenção de dados | A fal guarda as requisições por 90 dias, embora sua documentação também mencione 30. A BytePlus guarda por 180 dias, na Malásia, as entradas que disparam o filtro ([BytePlus](https://docs.byteplus.com/ja/docs/ModelArk/BytePlus_ModelArk_Data_Processing)) |

Dados de paciente não entram em nenhuma etapa. Para a LGPD são dados pessoais sensíveis, e o tratamento exige as bases legais do art. 11 ([LGPD](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)). O prontuário das aulas é sempre sintético.

### Regras brasileiras se a aula sair do uso pessoal

Se a aula for para equipes, pacientes ou marketing, quatro regras brasileiras passam a valer:

- **CFM Res. 2.336/2023:**
  - O art. 4º exige nome, CRM com a palavra "MÉDICO" e RQE.
  - O art. 11 proíbe divulgar equipamento ou fármaco sem registro na ANVISA, método não reconhecido pelo CFM e promessa de resultado.
  - O art. 11 também veda representações visuais "abusiva[s], enganosa[s] ou sedutora[s]" que induzam percepção de garantia de resultado ([CFM 2.336/2023](https://sistemas.cfm.org.br/normas/arquivos/resolucoes/BR/2023/2336_2023.pdf)).
- **CFM Res. 2.454/2026:** exige informar o paciente de forma clara quando há uso de IA e mantém a palavra final com o médico. Há uma ação judicial pedindo sua suspensão ([CFM](https://portal.cfm.org.br/noticias/cfm-normatiza-uso-da-ia-na-medicina); [Futuro da Saúde](https://futurodasaude.com.br/acao-judicial-suspender-regras-cfm-inteligencia-artificial/)).
- **ANVISA RDC 96/2008:** o art. 30 exige que ilustrações de **mecanismo de ação** sejam "truthful, accurate, complete, and unbiased", com referência bibliográfica completa ([ANVISA](https://www.gov.br/anvisa/en/rules-and-regulations/arquivos/rdc-96-2008-e.pdf)). A norma está em revisão desde 05/08/2026 ([Agência Gov](https://agenciagov.ebc.com.br/noticias/202608/anvisa-aprova-abertura-de-processo-para-revisar-normas-da-propaganda-de-alimentos-e-de-medicamentos)).
- **Lei 9.610/1998:** pelo art. 11, autor é a pessoa física criadora. Imagem e voz geradas por IA tendem a não ter proteção, então o valor protegível está no roteiro, na seleção e no arranjo humanos. Daí a importância de registrar a proveniência de cada aula ([Lei 9.610](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm)).

O YouTube não exige rótulo de IA para animação ([YouTube](https://support.google.com/youtube/answer/14328491)).

### Os oito portões

| Portão | Quando | O que bloqueia | Como | Custo |
|---|---|---|---|---|
| G1 Fatos | Depois do planejador | Frase sem trecho de fonte; número, unidade ou dose sem fonte; caractere CJK; dado pessoal; no nível C, termos como "cura", "garantido", "100%" ou marca de fármaco | Um LLM barato liga cada frase a uma passagem do pacote de fontes; regex | ≈ US$ 0,01 (estimativa) |
| G2 Storyboard | Antes do código | Aula com mais de 6 min; bloco com mais de 60 s; 3D sem justificativa; música ou B-roll em mecanismo; falta de pré-treino, recapitulação ou quiz | Lint determinístico do JSON | 0 |
| G3 Render e geometria | Em cada cena | Erro de execução; sobreposição; elemento fora do quadro; texto abaixo da escala mínima | Render mais linter de caixas delimitadoras (`get_bounding_box` no Manim, `Box3` projetado no three.js); reparo com escopo, até 5 tentativas | Tempo de máquina |
| G4 Crítico visual | Em cada cena | Rótulo que não bate com a narração; oclusão; lateralidade e orientação | O MiMo-V2.6-Flash assiste ao clipe e o compara com a versão anterior | ≈ US$ 0,02 por aula |
| G5 Sincronia | Na montagem | Evento visual fora da janela da palavra que o nomeia | Comparação entre os tempos do TTS e os eventos da cena | 0 |
| G6 Sonda de conhecimento | Com a aula pronta | Ganho insuficiente em relação a "sem vídeo"; erro em fato crítico | Um VLM responde 8–10 itens gerados das fontes, com e sem a aula, no estilo do TeachQuiz | ≈ US$ 0,01 (estimativa) |
| G7 Entrega | Antes do envio | Arquivo acima de 50 MB pela nuvem; legenda fora da área segura; ativo NC ou SA num build comercial; crédito ausente | ffprobe mais o manifesto de licenças | 0 |
| G8 Humano | Antes de liberar | Qualquer item do checklist de 12 pontos | Você no nível A; especialista e jurídico nos níveis B e C | ≈ 10–15 min |

O G6 segue o desenho do TeachQuiz ([Code2Video](https://arxiv.org/html/2510.01174v1)) e do PresentQuiz ([Paper2Video](https://arxiv.org/abs/2510.05096)). Ele mede se a informação está na aula, não se alguém aprende. Seus limiares precisam ser calibrados contra o seu próprio desempenho no quiz.

### Três níveis de revisão humana

- **Nível A, só você.** Assiste a cada aula a 1,5× com um botão de sinalizar. Audita a fundo uma em cada cinco aulas e todas as que tratam de mecanismo médico.
- **Nível B, equipe hospitalar.** Exige aprovação de 100% por especialista, com versão, revisor, data e fontes registrados, e aviso de uso de IA.
- **Nível C, pacientes, clientes ou marketing.** Soma revisão jurídica e regulatória, as checagens da CFM 2.336 e da RDC 96 e a escala PEMAT-A/V de compreensibilidade. A PEMAT não avalia exatidão ([AHRQ](https://www.ahrq.gov/health-literacy/patient-education/pemat.html)).

O checklist de 12 pontos é o mesmo nos três níveis:

1. Toda afirmação é rastreável e não é mais forte que sua fonte.
2. A anatomia está correta em orientação, lateralidade, proporção, contagem, conexões e rótulos.
3. O alvo e o sítio de ligação da molécula estão certos, com IDs do PDB, e as simplificações aparecem declaradas.
4. A ordem causal dos passos está correta, sem estados intermediários impossíveis.
5. Números, unidades e escalas estão corretos.
6. O status regulatório e o uso off-label estão sinalizados.
7. O conteúdo de IA bate com os artigos, e as metáforas aparecem rotuladas como metáforas.
8. Não há nenhum dado de paciente.
9. As licenças e os créditos estão em ordem.
10. O uso de IA está declarado.
11. O template pedagógico foi seguido.
12. A aula é acessível: legendas e paleta segura para daltônicos.

## Um piloto de três aulas decide se o projeto continua

O piloto usa três temas que o seu grafo pôs em alta nesta semana. Cada um testa uma parte diferente do sistema:

| Aula | Tendências de origem | O que testa |
|---|---|---|
| "Atenção no Transformer" | Transformer, attention mechanism | O caminho 2D do Manim, com uma referência pública forte para comparar |
| "Da TC ao volume" | computed tomography, CT-RATE, 3D chest CT interpretation | O caminho 3D: reconstrução, segmentação com TotalSegmentator e órgãos do HRA em three.js, com a página interativa |
| "Onde nasce a alucinação no laudo gerado por LLM" | electronic health record, radiology report generation, hallucination | A automação de ponta a ponta: o seletor escolhe e o planejador decide o mecanismo, sem ajuda manual |

O piloto roda no cenário econômico, cerca de US$ 0,30 em API para as três aulas, e com o teste cego de vozes. Cada aula é comparada às cegas com o Video Overview do NotebookLM gerado do mesmo pacote de fontes.

As durações abaixo são metas que proponho. Os critérios de passagem são deliberadamente binários.

| Fase | Duração-alvo | Entregáveis | Critério para seguir |
|---|---|---|---|
| F0 Fundação | 1 semana | Ambientes isolados: Manim 0.22.1 fixado com TeX; Chromium, Puppeteer e FFmpeg; Qwen3-TTS com CUDA graphs; Qwen3-ForcedAligner. Glossário termo → IPA → grafia adaptada. Teste cego de 3–4 vozes num roteiro cheio de jargão. Codificação de teste de 30 s de uma cena 3D | Voz escolhida; tamanho projetado de 5 minutos ≤ 50 MB em 720p ou 1080p de duas passadas |
| F1 Piloto | 2–3 semanas | As três aulas acima, com MP4 no Telegram, página `/aulas` e quiz; o Video Overview do NotebookLM das mesmas fontes | ≥ 90% das cenas renderizam sem intervenção; LLM ≤ US$ 0,50 por aula, medido por `usage.cost`; ≤ 45 min de PC por aula; nenhum erro factual depois do checklist; vitória sobre o NotebookLM em pelo menos 2 de 3 comparações cegas; ≥ 80% de acerto no quiz feito 2–3 dias depois |
| F2 Rotina semanal | 4 semanas | `run lesson` depois do weekly, com 1–2 aulas por semana; ledger de aulas; memória de templates; re-quiz espaçado; teto `SOTAWHAT_LLM_BUDGET_USD_LESSON` | ≥ 3 de 4 aulas entregues com até 15 min de retrabalho seu; custo mensal ≤ US$ 6 |
| F3 3D avançado e premium (opcional) | 4 semanas | Mol\* e Molecular Nodes; kit de TC (TotalSegmentator + HRA + BodyParts3D); props da Tripo; teste de B-roll H3 Turbo com teto de US$ 10 por aula | B-roll aprovado em até 3 tentativas por tomada; você prefere às cegas a versão com B-roll; nenhum mecanismo em pixels gerados |
| F4 Trilha da startup (sob demanda) | — | Build comercial-seguro a partir do manifesto; revisão nos níveis B e C; licenças do Remotion, do H3 e do TotalSegmentator conferidas; checklist CFM/ANVISA | Auditoria de licenças limpa e parecer jurídico |

O critério de saída também vale. Se o pipeline perder para o NotebookLM em duas das três comparações, a alternativa barata é usar o NotebookLM para a narrativa e investir só na página 3D interativa dos temas espaciais (TC, anatomia, moléculas), que é onde a evidência favorece o 3D.

O piloto também existe para medir o que a literatura ainda não mediu:

- Nenhum sistema publicado em 2026 informa a taxa de render na primeira tentativa do DeepSeek V4.1 Flash ou do MiMo em Manim ou three.js.
- Nenhum sistema agêntico publicado mira vídeo educacional em 3D; todos os sistemas medidos fazem Manim 2D ou slides ([notas de animação](../research_notes/Aulas%20did%C3%A1ticas%20animadas%20em%203D/animacao_programatica_e_agentes.md)).
- Os tempos do TotalSegmentator, do Molecular Nodes e do ACE-Step na RTX 4060 são estimativas.
- A captura paralela em várias abas falhou e ainda não tem alternativa testada.
- Toda a estatística de descarte de vídeo generativo vem de entretenimento, não de conteúdo científico ([notas de vídeo](../research_notes/Aulas%20did%C3%A1ticas%20animadas%20em%203D/video_generativo.md)).

Registrar custo, tokens, tentativas e tempo por cena desde a primeira aula transforma essas lacunas em dados próprios.

## Perguntas em aberto, cada uma com a suposição adotada

| # | Pergunta | Suposição padrão adotada |
|---|---|---|
| 1 | Quantas aulas por mês você quer? | 8 nas contas (duas por semana); a rotina começa com uma por semana |
| 2 | Qual a duração de cada aula? | 4,5 min, na faixa de 3–6; acima de 6, a aula é dividida em partes |
| 3 | Quem escolhe o tema? | A tendência mais forte do weekly ainda não ensinada, mais as ideias "curtida"; tema avulso por comando no bot |
| 4 | A voz deve ser sintética ou a sua, clonada? | Chirp 3 HD (grátis) nas aulas e Qwen3-TTS local nos rascunhos; clonagem só com o seu consentimento gravado |
| 5 | Haverá avatar ou apresentador? | Nenhum |
| 6 | Haverá música? | Desligada sob os mecanismos; vinheta ACE-Step opcional na abertura e no fim |
| 7 | Qual o teto de gasto com aulas? | US$ 5/mês, separado dos US$ 8–11 atuais, com o teto `SOTAWHAT_LLM_BUDGET_USD_LESSON` |
| 8 | Vídeo generativo entra? | Desligado até a F3; quando ligado, teto de US$ 10 por aula e só pela fal com `X-Fal-Store-IO: 0` |
| 9 | O Telegram recebe 720p pela nuvem ou 1080p por servidor local da Bot API? | Duas passadas ≤ 50 MB pela nuvem; servidor local só se a qualidade incomodar |
| 10 | A página interativa sai do 127.0.0.1? | Não: MP4 no celular, página no desktop |
| 11 | O material vai para a startup? | Build pessoal, mas com manifesto de licenças e só ativos comercialmente seguros desde o primeiro dia; Z-Anatomy e afins só no build de estudo |
| 12 | Como tratar os termos técnicos em inglês? | Termo em inglês na tela com glosa em pt-BR; narração com a grafia adaptada do glossário |
| 13 | Quem revisa? | Você, no nível A, com auditoria profunda de uma em cada cinco aulas e de todas com mecanismo médico |
| 14 | Você assina o Google AI Pro? | Não; a linha de base do NotebookLM usa o plano grátis |
| 15 | Aceita instalar Node.js e Chromium headless para a captura three.js? | Sim, como subprocessos fora do Python 3.12 do sotawhat; o Playwright em Python é a alternativa, não medida |

## Conclusão

A economia da "aula 3D" é o contrário do que parece. O caro não é o 3D: são os pixels que ninguém precisa e a atenção humana que revisa. Quando a animação vira código, o LLM custa centavos, e as restrições que importam passam a ser a qualidade dos templates e os minutos de revisão. As duas se acumulam a seu favor. Cada template validado, cada armadilha registrada e cada ativo com manifesto de licença barateiam a aula seguinte. É o mesmo efeito de memória que levou o Pass@1 do ManimAgent de 62 para 85, e o mesmo ciclo que o ledger de ideias já faz no sotawhat.

O que distingue este pipeline de um NotebookLM caseiro é o grafo. Ele já sabe quais conceitos são pré-requisitos (os vizinhos), quais fontes sustentam cada afirmação (os itens) e o que está subindo (as tendências). Somado ao quiz e ao re-quiz espaçado, isso transforma o sotawhat de um motor que conta o que há de novo num sistema que verifica se você entendeu. E como os ativos são CC0 ou CC BY com manifesto desde o primeiro dia, a opção da startup fica aberta sem custo extra: passar do uso pessoal ao comercial vira uma flag de build e um nível de revisão, não uma reescrita.
