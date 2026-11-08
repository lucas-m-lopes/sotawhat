# Golden set da triagem — golden_v1 (60 itens)

Como rotular: depois de "Rótulo:", escreva uma destas palavras:
- **incluir**: vai para os principais do digest (IA/ML com aplicação médico-hospitalar plausível);
- **radar**: IA de fronteira sem ponte médica clara (vira 1 linha no radar);
- **excluir**: ruído (pesquisa clínica sem IA, IA genérica, marketing, opinião).
Nota opcional depois de " — ". Ex.: `Rótulo: excluir — só epidemiologia`. Itens sem rótulo ficam fora da avaliação.
Quando terminar: `sotawhat eval golden import` (atualiza `golden_v1.jsonl`).

---

## 1 · geral · semantic_scholar
**SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering**
https://www.semanticscholar.org/paper/1c3c531fc0fbe79f97f367ed3648de8467caeeaa · 2024-05-06
> Language model (LM) agents are increasingly being used to automate complicated tasks in digital environments. Just as humans benefit from powerful software applications, such as integrated development environments, for complex tasks like software engineering, we posit that LM agents represent a new category of end users with their own needs and abilities, and would benefit from specially-built interfaces to the software they use. We investigate how interface design affects the performance of language model agents. As a result of this exploration, we introduce SWE-agent: a system that facilitates LM agents to autonomously use computers to solve software engineering tasks. SWE-agent's custom …
`id: url:https://www.semanticscholar.org/paper/1c3c531fc0fbe79f97f367ed3648de8467caeeaa`
Rótulo: radar

---

## 2 · geral · hf_papers
**BioInsight: Multi-Agent Orchestration for Interactive Biomedical Knowledge Discovery**
https://huggingface.co/papers/2606.20997 · 2026-06-18
> Biomedical researchers increasingly use AI-generated analyses and reports to interpret protein-level signals, but static outputs are often insufficient for research decision-making, where users need to inspect evidence, assess uncertainty, compare mechanisms, and refine hypotheses. We present BioInsight, a multi-agent system that moves from static biomedical report generation to interactive evidence-centered interactive interface generation. Given a disease name, a protein association table, and optional cohort metadata, BioInsight organizes disease-specific evidence through typed intermediate artifacts, including ranked pathways, literature evidence packets, protein-level reasoning notes, …
`id: arxiv:2606.20997`
Rótulo: incluir

---

## 3 · medico · arxiv
**Surflo: Consistent 3D Surface Flow Model with Global State**
https://arxiv.org/abs/2606.13644v1 · 2026-06-11
> Geometry is invariant to viewpoint, which makes any collection of images a redundant encoding of a single 3D state. Existing feed-forward reconstruction models fail to exploit this: per-view methods emit overlapping, unaligned pointmaps that grow linearly with input count, while global-latent methods commit to a fixed, low-resolution output. We introduce Surflo, which compresses a variable number of unposed RGB views into K latent tokens-one global state-and decodes oriented 3D surface points by independently transporting them from noise onto the surface via flow matching. This frees the output from any fixed grid or token budget: the same latent yields from a few thousand to a million poin…
`id: arxiv:2606.13644`
Rótulo: incluir

---

## 4 · geral · rss:simon-willison
**DiffusionGemma**
https://simonwillison.net/2026/Jun/10/diffusiongemma/#atom-everything · 2026-06-10T20:00
> <p><strong><a href="https://blog.google/innovation-and-ai/technology/developers-tools/diffusion-gemma-faster-text-generation/">DiffusionGemma</a></strong></p> Last May Google briefly released an experimental Gemini Diffusion model. I <a href="https://simonwillison.net/2025/May/21/gemini-diffusion/">tried the preview at the time</a> and recorded it running at 857 tokens/second. It was an exciting model, but Google made no further announcements about it.</p> <p>That research has returned in the best possible way: as a new open weight (Apache 2 licensed) Gemma model, <a href="https://huggingface.co/google/diffusiongemma-26B-A4B-it">google/diffusiongemma-26B-A4B-it</a>.</p> <p>NVIDIA are curren…
`id: url:https://simonwillison.net/2026/Jun/10/diffusiongemma`
Rótulo: incluir

---

## 5 · geral · rss:simon-willison
**Now we have a timeline of the OpenAI accidental attack against Hugging Face**
https://simonwillison.net/2026/Aug/8/now-we-have-a-timeline-of-the-openai-accidental-attack-against-h/ · 2026-08-08T14:06
> <p><a href="https://news.ycombinator.com/item?id=49220609#49221745">My comment</a> on <a href="https://news.ycombinator.com/item?id=49220609">Now we have a timeline of the OpenAI accidental attack against Hugging Face</a> &mdash; Hacker News.</p><p>I think one of the most interesting details here might be tucked away in that first bullet point:</p> <blockquote> <p>May 7: OpenAI starts a new training run for an experimental, unreleased model. <em>(Do they mean an evaluation run? They say training run in the video, and later mention a “reward signal to judge how well they’re doing”, so I guess this really was about training a model, not evaluating one that was already trained.)</em></p> </blo…
`id: url:https://simonwillison.net/2026/Aug/8/now-we-have-a-timeline-of-the-openai-accidental-attack-against-h`
Rótulo: incluir

---

## 6 · geral · rss:marktechpost
**Kimi AI and kvcache-ai Open Sources ‘AgentENV’: A Distributed System that Powers Agentic Reinforcement Learning (RL) Training for Kimi K3**
https://www.marktechpost.com/2026/07/27/kimi-ai-and-kvcache-ai-open-sources-agentenv/ · Mon, 27 Jul 2026
> <p>Moonshot AI's Kimi team and kvcache-ai open-sourced AgentENV (AENV) under MIT, as part of Kimi K3 Open Day. It runs agent sandboxes as Firecracker microVMs with millisecond snapshot, resume, and 16-way fork, behind an E2B-compatible API.</p> <p>The post <a href="https://www.marktechpost.com/2026/07/27/kimi-ai-and-kvcache-ai-open-sources-agentenv/">Kimi AI and kvcache-ai Open Sources &#8216;AgentENV&#8217;: A Distributed System that Powers Agentic Reinforcement Learning (RL) Training for Kimi K3</a> appeared first on <a href="https://www.marktechpost.com">MarkTechPost</a>.</p>
`id: url:https://www.marktechpost.com/2026/07/27/kimi-ai-and-kvcache-ai-open-sources-agentenv`
Rótulo: incluir

---

## 7 · geral · semantic_scholar
**LISA: Reasoning Segmentation via Large Language Model**
https://www.semanticscholar.org/paper/ad113d8b6f8f6dace7abd12dc88af520aaaf3fc7 · 2023-08-01
> Finally, we present LISA: large Language Instructed Segmentation Assistant, which inherits the language generation capabilities of multimodal Large Language Models (LLMs) while also possessing the ability to produce segmentation masks. In addition, fine-tuning the model with merely 239 reasoning segmentation data samples results in further performance enhancement
`id: url:https://www.semanticscholar.org/paper/ad113d8b6f8f6dace7abd12dc88af520aaaf3fc7`
Rótulo: incluir

---

## 8 · medico · pubmed
**Performance of multimodal large language models in interpreting lateral cephalometric superimpositions: A comparative observer-performance study.**
https://pubmed.ncbi.nlm.nih.gov/42508094/ · 2026
> Multimodal large language models (LLMs) can generate free-text interpretations of clinical images, but their performance on orthodontic cephalometric superimpositions is unknown. This study compared zero-shot interpretations from three LLMs with those of a second-year orthodontic resident. Ninety lateral cephalometric superimposition images from a private orthodontic practice were analyzed, including 30 nongrowing, 30 growing, and 30 orthognathic cases. Each image included overall maxillary regional, and mandibular regional superimpositions. ChatGPT 5.5, Gemini 3.1 Pro, Claude Opus 4.8, and the resident interpreted the same images using the same prompt, with no case context provided. Two se…
`id: pmid:42508094`
Rótulo: incluir

---

## 9 · geral · rss:bair
**2026 BAIR Graduate Showcase**
http://bair.berkeley.edu/blog/2026/07/01/grads-2026/ · Wed, 01 Jul 2026
> <!-- twitter --> <p>Congratulations to the Berkeley Artificial Intelligence Research (BAIR) Lab class of 2026! This year, BAIR celebrates another remarkable group of Ph.D. graduates whose curiosity, creativity, and perseverance have pushed the frontiers of artificial intelligence and machine learning.</p> <p>Their work spans the breadth of modern AI — robotics and embodied intelligence, large language models and reasoning, computer vision, generative modeling, AI safety, human-AI interaction, AI for science and healthcare, and much more. Along the way, they have published influential research, built systems with real-world impact, mentored their peers, and shaped the BAIR community for the …
`id: url:http://bair.berkeley.edu/blog/2026/07/01/grads-2026`
Rótulo: excluir

---

## 10 · geral · semantic_scholar
**CodeGen: An Open Large Language Model for Code with Multi-Turn Program Synthesis**
https://www.semanticscholar.org/paper/38115e80d805fb0fb8f090dc88ced4b24be07878 · 2022-03-25
> The prevalence of large language models advances the state-of-the-art for program synthesis, though limited training resources and data impede open access to such models. To this end, we construct an open benchmark, Multi-Turn Programming Benchmark (MTPB), consisting of 115 diverse problem sets that are factorized into multi-turn prompts
`id: url:https://www.semanticscholar.org/paper/38115e80d805fb0fb8f090dc88ced4b24be07878`
Rótulo: incluir

---

## 11 · geral · rss:marktechpost
**Hugging Face Unveils Microduck: A $399 Open-Source 25 cm Biped You Train with Reinforcement Learning**
https://www.marktechpost.com/2026/08/28/pollen-robotics-hugging-face-microduck-399-open-source-rl-biped-robot/ · Sat, 29 Aug 2026
> <p>Pollen Robotics, the Bordeaux robotics team at Hugging Face, opened pre-orders for Microduck — a 25 cm bipedal robot where every movement is a neural policy trained in MuJoCo and exported to ONNX. At $399, it puts the full sim-to-real loop on a desk: 15 motors, camera, LiDAR, two IMUs, and an Apache-2.0 training stack you can retrain yourself.</p> <p>The post <a href="https://www.marktechpost.com/2026/08/28/pollen-robotics-hugging-face-microduck-399-open-source-rl-biped-robot/">Hugging Face Unveils Microduck: A $399 Open-Source 25 cm Biped You Train with Reinforcement Learning</a> appeared first on <a href="https://www.marktechpost.com">MarkTechPost</a>.</p>
`id: url:https://www.marktechpost.com/2026/08/28/pollen-robotics-hugging-face-microduck-399-open-source-rl-biped-robot`
Rótulo: incluir

---

## 12 · medico · pubmed
**[Current applications and future perspectives of automation technologies and devices in oral diagnosis and treatment].**
https://pubmed.ncbi.nlm.nih.gov/42576763/ · 2026
> Automation technologies and devices are becoming an increasingly important component of the digital and intelligent transformation of oral healthcare. With on-going advances in artificial intelligence, robotics, and advanced manufacturing, their applications have expanded across oral diagnosis, surgery and treatment, prosthodontics, and orthodontics, as well as oral care and maintenance. These technologies have shown considerable potential for improving diagnostic and therapeutic accuracy, efficiency, consistency, and reproducibility. Importantly, automation in oral healthcare should not be understood simply as the replacement of manual procedures by standalone devices. Rather, it represent…
`id: pmid:42576763`
Rótulo: incluir

---

## 13 · medico · arxiv
**CorporateBench: Large-Scale Q&A Benchmarking with Temporal Knowledge Bases**
https://arxiv.org/abs/2608.27391v1 · 2026-08-27
> LLMs are increasingly able to answer complex questions about enterprise-scale document collections. But evaluation is hard: companies don't want to share internal communications, and synthetic datasets have been overly simple. We present CorporateBench (CB), a human-validated multi-task Q&A benchmark whose scale approaches the conditions LLMs encounter in corporate communication networks, with evaluation corpora surpassing 230,000 documents. CB evaluates LLMs across two dimensions (information extraction and knowledge base querying) through four synthetically generated firms ranging from 12 to 10,000 employees. Each corpus is sampled from a temporally evolving knowledge base describing a co…
`id: arxiv:2608.27391`
Rótulo: incluir

---

## 14 · geral · rss:marktechpost
**NVIDIA AI Releases Molt: A PyTorch-Native Agentic Reinforcement Learning Framework**
https://www.marktechpost.com/2026/08/01/nvidia-ai-releases-molt-a-pytorch-native-agentic-reinforcement-learning-framework/ · Sun, 02 Aug 2026
> <p>Agentic RL research is constant algorithm modification, and in mainstream frameworks every change threads through trainer, distributed backend, and rollout glue. NVIDIA's Molt targets that cost with about 8.6K lines of RL code, composing Ray, vLLM, and NeMo AutoModel around one asynchronous loop. The agent stays ordinary Python, trajectories stay token-exact, and throughput comes out statistically comparable to a Megatron-based stack.</p> <p>The post <a href="https://www.marktechpost.com/2026/08/01/nvidia-ai-releases-molt-a-pytorch-native-agentic-reinforcement-learning-framework/">NVIDIA AI Releases Molt: A PyTorch-Native Agentic Reinforcement Learning Framework</a> appeared first on <a …
`id: url:https://www.marktechpost.com/2026/08/01/nvidia-ai-releases-molt-a-pytorch-native-agentic-reinforcement-learning-framework`
Rótulo: incluir

---

## 15 · medico · pubmed
**Artificial Intelligence in Pre-anaesthetic Evaluation and Perioperative Planning: A Narrative Review.**
https://pubmed.ncbi.nlm.nih.gov/42994619/ · 2026
> Preanesthetic evaluation is essential for perioperative safety, yet it remains time-consuming, heavily reliant on documentation, and vulnerable to variability in data collection, risk assessment, and clinical decision-making. The increase in surgical cases, patient complexity, and digital health records has created opportunities for artificial intelligence (AI) to assist anesthesiologists in preoperative screening, risk assessment, and perioperative planning. New AI applications in anesthesiology include machine learning models for predicting perioperative risks, natural language processing (NLP) systems for extracting key information from unstructured records, and large language model (LLM…
`id: pmid:42994619`
Rótulo: incluir

---

## 16 · geral · rss:marktechpost
**Mistral AI Releases Robostral Navigate: An 8B Model Enabling Robots to Navigate Complex Environments Using a Single RGB Camera**
https://www.marktechpost.com/2026/07/14/mistral-ai-releases-robostral-navigate-an-8b-model-enabling-robots-to-navigate-complex-environments-using-a-single-rgb-camera/ · Tue, 14 Jul 2026
> <p>Mistral AI introduced Robostral Navigate, an 8B embodied navigation model. It moves robots from a plain-language instruction using only a single RGB camera, with no LiDAR or depth sensors. The model reaches 76.6% success on R2R-CE validation unseen through a pointing method, prefix-caching training, and CISPO online reinforcement learning.</p> <p>The post <a href="https://www.marktechpost.com/2026/07/14/mistral-ai-releases-robostral-navigate-an-8b-model-enabling-robots-to-navigate-complex-environments-using-a-single-rgb-camera/">Mistral AI Releases Robostral Navigate: An 8B Model Enabling Robots to Navigate Complex Environments Using a Single RGB Camera</a> appeared first on <a href="htt…
`id: url:https://www.marktechpost.com/2026/07/14/mistral-ai-releases-robostral-navigate-an-8b-model-enabling-robots-to-navigate-complex-environments-using-a-single-rgb-camera`
Rótulo: incluir

---

## 17 · medico · rss:jmir-ai
**Improving Clinical Validity in Synthetic Electronic Health Record Generation Using Best-of-N Sampling: Comparative Evaluation Study**
https://ai.jmir.org/2026/1/e90590 · 2026-07-30T15:00
> Background: Synthetic electronic health record generation is limited not only by statistical fidelity but also by clinical validity. Records that appear statistically plausible may still violate hard structural, physiological, or relational constraints. Objective: This study evaluated best-of-N constraint-minimizing selection as an inference-time strategy for improving clinical validity and characterized when such selection succeeds or fails as a function of the generator’s valid support mass (). Methods: We evaluated Wasserstein generative adversarial network with gradient penalty (WGAN-GP) and conditional tabular generative adversarial network (CTGAN) on 3 public clinical tabular datasets…
`id: url:https://ai.jmir.org/2026/1/e90590`
Rótulo: incluir

---

## 18 · medico · arxiv
**StreamPI: Streaming Multimodal Temporal Modeling for Vision-Language-Action Models**
https://arxiv.org/abs/2608.26067v1 · 2026-08-26
> Vision-Language-Action (VLA) models have demonstrated effectiveness in robot manipulation, yet state-of-the-art models such as pi0.5 operate under a single-frame paradigm, limiting their ability to retain past observations and develop precise spatial perception. In this paper, we propose StreamPI, a streaming multimodal temporal modeling framework that equips single-frame VLA with temporal reasoning capability without introducing any additional parameters. One core design is instruction-anchored temporal modeling. It treats each (visual observation, language instruction) pair as an atomic temporal unit: bidirectional attention within each pair enables cross-modal fusion, while causal attent…
`id: arxiv:2608.26067`
Rótulo: incluir

---

## 19 · geral · semantic_scholar
**DeepSeek-Coder: When the Large Language Model Meets Programming - The Rise of Code Intelligence**
https://www.semanticscholar.org/paper/1f2a20a6efaf83214861dddae4a38a83ae18fe32 · 2024-01-25
> The rapid development of large language models has revolutionized code intelligence in software development. To address this, we introduce the DeepSeek-Coder series, a range of open-source code models with sizes from 1.3B to 33B, trained from scratch on 2 trillion tokens. Our extensive evaluations demonstrate that DeepSeek-Coder not only achieves state-of-the-art performance among open-source code models across multiple benchmarks but also surpasses existing closed-source models like Codex and GPT-3.5
`id: url:https://www.semanticscholar.org/paper/1f2a20a6efaf83214861dddae4a38a83ae18fe32`
Rótulo: incluir

---

## 20 · medico · crossref:npj-digital-medicine
**Predicting persistent fever in patients with cancer receiving antibiotics: a machine learning approach**
https://doi.org/10.1038/s41746-026-03449-w · 2026-10-31
> Persistent fever after initiating intravenous antibiotics is common in hospitalized patients with cancer and often leads to additional imaging and antimicrobial escalation. Early identification of patients unlikely to remain febrile could provide additional information during clinical reassessment. We developed and externally validated machine learning models to predict persistent fever 48–72 h after antibiotic initiation using electronic health records from two academic hospitals. Adult cancer patients with fever within 24–48 h of treatment were included. Models incorporated demographics, comorbidities, laboratory results, vital signs, and temperature patterns. The best-performing model ac…
`id: doi:10.1038/s41746-026-03449-w`
Rótulo: incluir

---

## 21 · medico · rss:jmir-medinform
**GPT-4o–Powered Preanesthetic AI: Development and Validation Study**
https://medinform.jmir.org/2026/1/e83893 · 2026-08-25T17:15
> Background: Accurate preanesthetic assessment is essential for perioperative risk stratification, but conventional tools such as the American Society of Anesthesiologists (ASA) physical status classification and postoperative nausea and vomiting (PONV) risk scores may be affected by subjective judgment, incomplete documentation, and fragmented clinical data. Large language models may support preanesthetic assessment by integrating structured and unstructured clinical information. Objective: This study aimed to develop and retrospectively validate a GPT-4o (OpenAI)–powered AI system for preanesthetic assessment. The primary validation focus was the agreement between AI-generated and clinicia…
`id: url:https://medinform.jmir.org/2026/1/e83893`
Rótulo: incluir

---

## 22 · geral · rss:simon-willison
**Ornith-1.0: Self-Scaffolding LLMs for Agentic Coding**
https://simonwillison.net/2026/Jun/29/ornith/#atom-everything · 2026-06-29T16:17
> <p><strong><a href="https://deep-reinforce.com/ornith_1_0.html">Ornith-1.0: Self-Scaffolding LLMs for Agentic Coding</a></strong></p> This is an interesting new open weights (MIT licensed) model, the first model release from DeepReinforce.</p> <blockquote> <p>[...] with variants including 9B Dense, 31B Dense, 35B MoE, and 397B MoE. Built on top of pretrained Gemma 4 and Qwen 3.5, it achieves state-of-the-art performance among open-source models of comparable size on coding benchmarks.</p> </blockquote> <p>As far as I can tell the licenses of those underlying models is compatible with being used in this way - Gemma 4 is Apache 2.0 licensed (and not bound by the janky additional <a href="http…
`id: url:https://simonwillison.net/2026/Jun/29/ornith`
Rótulo: incluir

---

## 23 · geral · rss:bair
**Identifying Interactions at Scale for LLMs**
http://bair.berkeley.edu/blog/2026/03/13/spex/ · Fri, 13 Mar 2026
> <!-- twitter --> <p style="text-align: center;"> <!-- <img src="https://bair.berkeley.edu/static/blog/spex/image1.png" alt="different_tests" width="600"><br> --> <img alt="different_tests" src="https://bair.berkeley.edu/static/blog/spex/image1.png" width="600" /><br /> <i style="font-size: 0.9em;"> </i> </p> <p>Understanding the behavior of complex machine learning systems, particularly Large Language Models (LLMs), is a critical challenge in modern artificial intelligence. Interpretability research aims to make the decision-making process more transparent to model builders and impacted humans, a step toward safer and more trustworthy AI. To gain a comprehensive understanding, we can analyz…
`id: url:http://bair.berkeley.edu/blog/2026/03/13/spex`
Rótulo: incluir

---

## 24 · geral · rss:simon-willison
**OpenAI's rogue agents were caught communicating via public wikis**
https://simonwillison.net/2026/Sep/4/rogue-agent-wikis/ · 2026-09-04T17:38
> <p>Here we go again... <a href="https://collusion.wiki">Discovery of a new OpenAI agent message board</a> by Sydney Von Arx, Cormac Slade Byrd, Spencer Kitts, and Thomas Larsen describes the <em>latest</em> <a href="https://simonwillison.net/tags/accidental-cyberattacks/">accidental cyberattack</a> by models being trained by OpenAI. This time it was agents engaged in some sort of web research benchmark, so they had (supposedly) controlled access to the Web. The agents figured out they could update public Wikis and spent weeks exchanging thousands of messages with each other to collaborate on the benchmark.</p> <p>This story only broke a few hours ago. There are <a href="https://x.com/xeopho…
`id: url:https://simonwillison.net/2026/Sep/4/rogue-agent-wikis`
Rótulo: radar

---

## 25 · medico · rss:jmir-medinform
**Natural Language Processing Applied to Psychiatric Clinical Notes: Scoping Review**
https://medinform.jmir.org/2026/1/e91249 · 2026-07-10T16:30
> Background: Psychiatric clinical notes in electronic health records (EHRs) provide rich longitudinal information that can support clinical decision-making. Using historical medical data can enable earlier identification of mental illness, better characterization of disease trajectories, and more personalized treatment planning. Natural language processing (NLP) transforms these unstructured notes into analyzable representations for research and care. Objective: This study aims to systematically summarize NLP methodologies for psychiatric clinical notes, compare major modeling paradigms and application areas, and highlight emerging large language model (LLM) trends, key challenges, and futur…
`id: url:https://medinform.jmir.org/2026/1/e91249`
Rótulo: incluir

---

## 26 · geral · rss:marktechpost
**OpenAI Details GPT-Red: An Internal Automated Red-Teaming Model That Beat Human Red-Teamers 84% To 13% On Prompt Injection**
https://www.marktechpost.com/2026/07/16/openai-details-gpt-red-an-internal-automated-red-teaming-model-that-beat-human-red-teamers-84-to-13-on-prompt-injection/ · Thu, 16 Jul 2026
> <p>OpenAI trained GPT-Red, an internal-only attacker model, using self-play reinforcement learning against a population of defender LLMs. It beat human red-teamers 84% to 13% on a replicated indirect prompt injection arena, found a novel "Fake Chain-of-Thought" attack class, and cut GPT-5.6 Sol's failures 6x on OpenAI's hardest direct injection benchmark. OpenAI concedes it still struggles with multi-turn and image-based attacks.</p> <p>The post <a href="https://www.marktechpost.com/2026/07/16/openai-details-gpt-red-an-internal-automated-red-teaming-model-that-beat-human-red-teamers-84-to-13-on-prompt-injection/">OpenAI Details GPT-Red: An Internal Automated Red-Teaming Model That Beat Huma…
`id: url:https://www.marktechpost.com/2026/07/16/openai-details-gpt-red-an-internal-automated-red-teaming-model-that-beat-human-red-teamers-84-to-13-on-prompt-injection`
Rótulo: incluir

---

## 27 · geral · arxiv
**Cognitive-structured Multimodal Agent for Multimodal Understanding, Generation, and Editing**
https://arxiv.org/abs/2607.08497v1 · 2026-07-09
> Recent unified multimodal models show a single architecture can jointly perform vision/language understanding and image generation/editing. However, they repeatedly feed all historical visual and textual inputs into a shared context window, limiting long-horizon multimodal dialogue due to visual token explosion and unreliable cross-turn referencing. We propose a Cognitive-structured Multimodal Agent that externalizes visual information into an Episodic Visual Memory and selectively reactivates relevant episodes during reasoning. The agent consists of a Perceptual Abstraction Engine for structured visual abstraction, a Cognitive Retrieval Engine for cross-turn memory retrieval, and a Multimo…
`id: arxiv:2607.08497`
Rótulo: incluir

---

## 28 · medico · arxiv
**MedGraph: Maintaining Patient State with Graph Memory for Long-Term Medical Dialogue**
https://arxiv.org/abs/2611.08433v1 · 2026-11-05
> LLM-based medical assistants that follow a patient across visits need a memory that keeps the patient's clinical state correct as it changes. We examine the errors of five memory systems on longitudinal medical dialogue and find three recurring causes: the retrieved evidence gives an outdated state, includes another person's health facts, or lacks a safety fact the answer depends on. We present MedGraph, a graph memory built for these three cases. Construction extracts dated facts from each session, attributes each fact to the person it describes, and links medication, diagnosis, and measurement records into chains that keep earlier states. Retrieval ranks the patient's chains as units, rea…
`id: arxiv:2611.08433`
Rótulo: incluir

---

## 29 · geral · semantic_scholar
**DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving**
https://www.semanticscholar.org/paper/72f77a393079431e4207b3afe678ee80b420e6f8 · 2024-01-18
> DistServe improves the performance of large language models (LLMs) serving by disaggregating the prefill and decoding computation. Our evaluations show that on various popular LLMs, applications, and latency requirements, DistServe can serve 7.4x more requests or 12.6x tighter SLO, compared to state-of-the-art systems, while staying within latency constraints for>90% of requests.
`id: url:https://www.semanticscholar.org/paper/72f77a393079431e4207b3afe678ee80b420e6f8`
Rótulo: incluir

---

## 30 · geral · arxiv
**Distill Globally, Adapt Locally: Reasoning Distillation and Product-Type Test-Time Training for Scalable Trade-Up Recommendation**
https://arxiv.org/abs/2609.05363v1 · 2026-09-04
> Large language models (LLMs) can reason about such distinctions, but applying them directly to hundreds of millions of product pairs is operationally impractical. At Level 1, a retrieval-augmented few-shot LLM teacher generates structured relation labels and natural-language rationales. These rationales supervise a compact embedding-pair classifier through alignment and contrastive objectives; at inference, the student uses only two precomputed 768-dimensional product embeddings, with no LLM calls or text generation. On a fixed human-annotated benchmark of 8,352 pairs, a 15.5M-parameter four-class reasoning-distilled student achieves AUC 0.924 (95% CI [0.918, 0.929]), compared with 0.912 fo…
`id: arxiv:2609.05363`
Rótulo: incluir

---

## 31 · medico · pubmed
**Population effects and cross-population generalisability of the third molar maturity index for 18-year age classification: a multi-centre study with machine learning validation.**
https://pubmed.ncbi.nlm.nih.gov/42618662/ · 2026
> Accurate forensic age estimation is critical in legal contexts where documentation is unavailable. The Third Molar Maturity Index (I3M) is a quantitative, reproducible method based on the ratio of the open apical width to the length of the mandibular third molar. This multicentre, cross-sectional study evaluated I3M performance for age-threshold classification at 18 years across five populations. A total of 3000 orthopantomograms from individuals aged 13-22 years were collected in Brazil, China, Croatia, Portugal and Sweden. Teeth 38 and 48 were measured, and binary classification (≥ 18 vs. <18 years) was assessed using ROC analysis, hierarchical logistic regression with likelihood ratio te…
`id: pmid:42618662`
Rótulo: excluir

---

## 32 · medico · rss:jmir-ai
**Simulated Reasoning and Self-Verification for Psychiatric Diagnosis in Generalist Large Language Models: Comparative Evaluation**
https://ai.jmir.org/2026/1/e83927 · 2026-06-08T14:00
> Background: Large language models (LLMs) and, more recently, large reasoning models (LRMs) have rapidly garnered significant interest for application in psychiatry and behavioral health. However, recent studies have identified significant shortcomings and potential risks in the performance of LLM-based systems, complicating their application to psychiatric diagnosis. Two promising approaches to addressing these challenges and improving the efficacy of these models are simulated reasoning (SR) and self-verification (SV), in which additional “reasoning tokens” are used to guide model output, either during or after inference. Objective: We aimed to explore how the use of SR (via LRMs) and SV (…
`id: url:https://ai.jmir.org/2026/1/e83927`
Rótulo: incluir

---

## 33 · medico · arxiv
**What Makes Deep Learning Work for Traditional Chinese Medicine Tongue Diagnosis? A Comprehensive Ablation Study**
https://arxiv.org/abs/2607.28148v1 · 2026-07-30
> Deep learning has shown promise for automated tongue diagnosis in traditional Chinese medicine (TCM), yet the design space remains underexplored. We conducted a systematic ablation study spanning 20+ model versions under rigorous 5-fold cross-validation on TongueDx2 (5,109 images, 976 expert-annotated) and a merged dataset of 11,101 samples. We compared six backbone architectures, four loss functions, five augmentation strategies, and six training strategies. The best 976-sample model achieved weighted-F1 of 0.6625 using ConvNeXt-Tiny with restrained augmentation and weak-group ensemble, while the best 11,101-sample model reached weighted-F1 of 0.7761. Six key design principles emerged: (1)…
`id: arxiv:2607.28148`
Rótulo: incluir

---

## 34 · geral · hf_papers
**LooseControlVideo: Directorial Video Control using Spatial Blocking**
https://huggingface.co/papers/2606.19495 · 2026-06-16
> Precise 3D spatial orchestration in text-to-video generation remains a significant challenge, particularly for multi-object scenes where semantic layout and temporal dynamics are often entangled. While existing depth-conditioned models achieve good structural fidelity, they necessitate dense, frame-accurate guidance that is labor-intensive to author for dynamic events involving deformable objects. We present LooseControlVideo, a framework that enables intuitive and expressive control by using sparse, oriented 3D boxes as a "blocking" proxy. This allows users to author high-level layout and trajectory while leveraging a video generative model to generate realistic occlusions, dynamics and in…
`id: arxiv:2606.19495`
Rótulo: incluir

---

## 35 · medico · pubmed
**Case-matched retrieval improves textual alignment of LLM-generated radiology impressions.**
https://pubmed.ncbi.nlm.nih.gov/42536636/ · 2026
> Radiology impressions guide clinical care. Large Language Models (LLMs)-drafted impressions can drift into generic, off-style text. Retrieval-augmented generation (RAG) enables context-aware few-shot prompting during inference. This retrospective IRB-approved study included 11,998 CT pulmonary angiography (CTPA) reports. We built a retrieval bank from 11,399 reports and reserved 599 reports for testing. GPT-4o and LLaMA 3.1-70B generated impressions from the "findings" section using three setups: zero-shot, fixed random few-shot, and dynamic retrieval-selected few-shot (top-k semantic matches; k = 3/5/10). We ran temperatures 0, 0.7, 1. We scored outputs against the original impressions wit…
`id: pmid:42536636`
Rótulo: incluir

---

## 36 · medico · arxiv
**Ab initio-based Deep-Learning Prediction of Carrier Mobility in Strongly Anharmonic Materials**
https://arxiv.org/abs/2608.19053v1 · 2026-08-19
> Predicting charge transport in strongly anharmonic materials, particularly ultralow thermal conductors, remains a major challenge for first-principles methods. In such systems, perturbative treatments of electron-phonon interactions and the harmonic phonon picture often break down, necessitating non-perturbative approaches. The ab initio Kubo-Greenwood(aiKG) formalism provides a rigorous framework for evaluating temperature-dependent carrier transport beyond the harmonic approximation. Nevertheless, its practical application is computationally demanding because it requires large supercells, extensive statistical sampling, and extrapolation to the zero-frequency limit. In this work, we intro…
`id: arxiv:2608.19053`
Rótulo: excluir

---

## 37 · medico · rss:jmir-ai
**Centralized Digital Surveillance for Abdominal Aortic Aneurysm Detection, Longitudinal Tracking, and Management Within an Integrated Health System: Retrospective Cohort Study**
https://ai.jmir.org/2026/1/e93443 · 2026-08-19T15:00
> Background: Incidental detection of abdominal aortic aneurysms (AAAs) has increased with widespread cross-sectional imaging, while traditional surveillance remains fragmented and clinician-dependent. Real-world descriptions of centralized digital surveillance programs combining structured electronic health record (EHR) queries with natural language processing (NLP) of radiology reports remain limited. Objective: This study aimed to describe the design, implementation, and operational performance of the System to Track Abnormalities of Importance Reliably (STAIR), a centralized digital surveillance program combining structured EHR queries, an internally developed NLP model, clinician referra…
`id: url:https://ai.jmir.org/2026/1/e93443`
Rótulo: incluir

---

## 38 · geral · rss:bair
**Repurposing Protein Folding Models for Generation with Latent Diffusion**
http://bair.berkeley.edu/blog/2025/04/08/plaid/ · Tue, 08 Apr 2025
> <!-- twitter --> <!-- The actual text for the post content appears below. Text will appear on the homepage, i.e., https://bair.berkeley.edu/blog/ but we only show part of theac posts on the homepage. The rest is accessed via clicking 'Continue'. This is enforced with the `more` excerpt separator. --> <p style="text-align: center;"> <img src="https://bair.berkeley.edu/static/blog/plaid/image1.jpg" width="75%" /> <br /> <i style="font-size: 0.9em;"><a href="https://www.biorxiv.org/content/10.1101/2024.12.02.626353v2" target="_blank">PLAID</a> is a multimodal generative model that simultaneously generates protein 1D sequence and 3D structure, by learning the latent space of protein folding mod…
`id: url:http://bair.berkeley.edu/blog/2025/04/08/plaid`
Rótulo: incluir

---

## 39 · geral · hf_papers
**Agentic ESOpt: Fine-Tuning Long-Horizon LLM Agents with Minimal GPU Requirements**
https://huggingface.co/papers/2608.17310 · 2026-08-17
> Reinforcement Learning (RL) has been promising in single-turn LLM fine-tuning. However, long-horizon agentic reasoning introduces increasingly branching interactions and sparse rewards, exposing several limitations of RL: its heavyweight backpropagation-based training stack makes it impractical to fine-tune larger LLMs, and longer-horizon trajectories make credit assignment in RL substantially harder. This paper argues that evolution strategies (ES) can be a better choice for fine-tuning long-horizon LLM agents. Compared with agentic RL, ES offers three key advantages: 1) Model Scalability: ES enables full-parameter optimization with only minimal, inference-level GPU memory, making it possi…
`id: arxiv:2608.17310`
Rótulo: incluir

---

## 40 · medico · rss:jmir-ai
**Application of Language Models for the Analysis of Adverse Drug Events in Pharmaceutical Research and Development: Scoping Review**
https://ai.jmir.org/2026/1/e77732 · 2026-06-16T17:15
> Background: Adverse drug events (ADEs) remain a critical safety issue in pharmaceutical research and development (Pharma R&amp;D), necessitating robust methods for early detection and surveillance. Language models (LMs) are increasingly used in ADE analysis, addressing safety challenges during drug development and postmarket surveillance. Language modeling approaches, ranging from static embeddings to large language models (LLMs), capitalize on diverse data sources, such as clinical trial datasets, electronic health records, and social media posts, to predict ADEs, analyze real-world evidence, and improve drug screening and pharmacovigilance systems. Objective: This scoping review aims to m…
`id: url:https://ai.jmir.org/2026/1/e77732`
Rótulo: incluir

---

## 41 · geral · rss:simon-willison
**Better Models: Worse Tools**
https://simonwillison.net/2026/Jul/4/better-models-worse-tools/#atom-everything · 2026-07-04T22:53
> <p><strong><a href="https://lucumr.pocoo.org/2026/7/4/better-models-worse-tools/">Better Models: Worse Tools</a></strong></p> Armin reports on a weird problem he ran into while hacking on Pi:</p> <blockquote> <p>The short version is that newer Claude models sometimes call Pi’s edit tool with extra, invented fields in the nested <code>edits[]</code> array. And not Haiku or some small model: Opus 4.8. The edit itself is usually correct but the arguments do not match the schema as the model invents made-up keys and Pi thus rejects the tool call and asks to try again.</p> <p>That alone is not too surprising as models emit malformed tool calls sometimes. Particularly small ones. What surprised m…
`id: url:https://simonwillison.net/2026/Jul/4/better-models-worse-tools`
Rótulo: incluir

---

## 42 · geral · hf_papers
**Parallel Decoding Distillation for Fast Image and Video Generation**
https://huggingface.co/papers/2607.26004 · 2026-07-27
> Generation in video diffusion or flow models is computationally expensive due to the slow and iterative sampling process. Current state-of-the-art (SOTA) acceleration methods heavily rely on variational score distillation (VSD) and adversarial losses to distill diffusion models into few-step generators. Albeit achieving high-quality video generation, these training losses are notoriously hard to optimize and suffer from mode collapse, leading to loss of video diversity and lack of motion. In this paper, we introduce Parallel Decoding Distillation (PDD), a simplified and scalable trajectory-based distillation method for fast inference of diffusion and flow matching models. Our architecture a…
`id: arxiv:2607.26004`
Rótulo: incluir

---

## 43 · geral · rss:bair
**Scaling Up Reinforcement Learning for Traffic Smoothing: A 100-AV Highway Deployment**
http://bair.berkeley.edu/blog/2025/03/25/rl-av-smoothing/ · Tue, 25 Mar 2025
> <!-- twitter --> Training Diffusion Models with Reinforcement Learning <video loop="" style="width: 100%; margin: 0; padding: 0; border: none; background: transparent; display: block; border-radius: 5px;"> <source src="https://bair.berkeley.edu/static/blog/rl_av_smoothing/megavandertest.mp4" type="video/mp4" /> </video> <p style="margin-top: 20px;"> <b>We deployed 100 reinforcement learning (RL)-controlled cars into rush-hour highway traffic to smooth congestion and reduce fuel consumption for everyone.</b> Our goal is to tackle <a href="https://www.youtube.com/watch?v=TNokBgtSUvQ" target="_blank">"stop-and-go" waves</a>, those frustrating slowdowns and speedups that usually have no clear c…
`id: url:http://bair.berkeley.edu/blog/2025/03/25/rl-av-smoothing`
Rótulo: radar

---

## 44 · medico · rss:jmir-medinform
**Clinically Interpretable Deep Learning for Differentiating Vitiligo and Postinflammatory Hypopigmentation: Diagnostic Accuracy Study**
https://medinform.jmir.org/2026/1/e81942 · 2026-07-24T15:30
> Background: Distinguishing vitiligo from postinflammatory hypopigmentation (PIH) is clinically challenging because both conditions may present with similar depigmented lesions. Although deep learning has shown strong potential for dermatologic image classification, limited interpretability remains a barrier to clinical adoption. Objective: This study aimed to develop an interpretable deep learning framework for accurate differentiation between vitiligo and PIH using a lightweight convolutional neural network and an ensemble of explainability methods. Methods: A total of 332 clinical images (176 vitiligo and 156 PIH) were collected from King Abdullah University Hospital and publicly availabl…
`id: url:https://medinform.jmir.org/2026/1/e81942`
Rótulo: incluir

---

## 45 · geral · arxiv
**SKooP: Symmetric Koopman Predictions for Faster and More Generalizable Legged Robot Locomotion with Reinforcement Learning**
https://arxiv.org/abs/2607.11624v1 · 2026-07-13
> Reinforcement learning (RL) algorithms classically suffer from poor sample efficiency. In robotics, a recent line of work has emerged addressing this problem by encoding physics priors in the learning process. However, most of these approaches are validated on well-defined, low-dimensional benchmark systems rather than high-dimensional robots with complex nonlinear dynamics. In this paper, we introduce \textit{SKooP (Symmetric Koopman Predictions)}, an approach combining the advantages of morphological symmetries with those of a Koopman model learned via autoencoder to enhance policy learning. SKooP learns a Koopman model of the system dynamics alongside the policy. The resulting Koopman pr…
`id: arxiv:2607.11624`
Rótulo: radar

---

## 46 · geral · arxiv
**Unveiling Invariant and Transferable Latent Factors Across Heterogeneous Environments via ATLAS**
https://arxiv.org/abs/2607.18209v1 · 2026-07-20
> This paper considers a multi-environment factor model in which high-dimensional covariates are collected from heterogeneous environments, with auxiliary labels available in a subset of these environments. The joint distribution of the covariates may vary across environments, whereas the latent structure is decomposed into invariant factors with shared loadings and heterogeneous factors with environment-specific loadings. Such a model is motivated by transfer learning and latent factor regression, where one seeks stable low-dimensional representations for both interpretation and robust out-of-sample prediction of the response $Y$. Leveraging the invariance principle, we show that the invaria…
`id: arxiv:2607.18209`
Rótulo: radar

---

## 47 · medico · rss:jmir-ai
**AI Adoption, Adaptation, and Workforce Sustainability in Medical Imaging: Systematic Review and Conceptual Framework**
https://ai.jmir.org/2026/1/e101944 · 2026-11-03T16:45
> Background: Despite growing recognition that AI-driven systems offer transformative benefits for diagnostic imaging, insufficient evidence exists regarding how medical imaging workforces adapt to AI technology to support workforce sustainability. Objective: The aim of this study is to systematically review the existing literature on perceptions and attitudes toward AI adoption in medical imaging, postadoption adaptation behaviors within the workforce, and the implications of these processes for workforce sustainability. Methods: Following the PRISMA (Preferred Reporting Items for Systematic Reviews and Meta-Analyses) guidelines, a systematic search was carried out across 7 databases. Themat…
`id: url:https://ai.jmir.org/2026/1/e101944`
Rótulo: incluir

---

## 48 · medico · rss:jmir-medinform
**From Data Poverty to Data Sovereignty: Operationalizing Gold-Standard Biomedical Datasets in Low- and Middle-Income Countries**
https://medinform.jmir.org/2026/1/e82360 · 2026-08-10T15:15
> Artificial Intelligence (AI) is rapidly expanding in healthcare. However, there is a significant underrepresentation of low- and middle-income countries (LMICs) in datasets used to train the AI applications. Current FDA-approved AI tools predominantly utilize data from high-income nations, with fewer than 4% reporting geographic or racial diversity. This geographic skew leads to significant performance degradation when used in LMIC populations, perpetuating an equity crisis where health burdens are highest. Addressing this disparity, we highlight Medical Imaging Datasets for India (MIDAS) initiative as a viable model to transition LMICs from "data poverty" to "data sovereignty." MIDAS emplo…
`id: url:https://medinform.jmir.org/2026/1/e82360`
Rótulo: incluir

---

## 49 · medico · rss:jmir-medinform
**Machine Learning for Intraoperative Bleeding Prediction in Patients Undergoing Surgery: Scoping Review**
https://medinform.jmir.org/2026/1/e80930 · 2026-06-10T15:15
> Background: Intraoperative bleeding is a critical event that impacts surgical safety and patient outcomes. Machine learning (ML) has demonstrated potential in prediction tasks, yet its methodological rigor and clinical translation face challenges. Objective: This scoping review aims to systematically synthesize the current state of development, performance, and validation of ML models for predicting intraoperative bleeding, and to identify key barriers to their clinical implementation. Methods: Following the PRISMA-ScR (Preferred Reporting Items for Systematic Reviews and Meta-Analyses extension for Scoping Reviews) guidelines, we systematically searched 7 databases (PubMed, Web of Science,…
`id: url:https://medinform.jmir.org/2026/1/e80930`
Rótulo: incluir

---

## 50 · geral · arxiv
**Scaling Behavior Foundation Model for Humanoid Robots**
https://arxiv.org/abs/2607.15163v1 · 2026-07-16
> Humanoid control requires natural whole-body coordination, precise real-time responses to control signals, and robust generalization across diverse environmental contexts, making it a cornerstone for generalist embodied agents. Behavior Foundation Models (BFMs) have recently emerged as a promising solution to address these challenges by leveraging large-scale behavioral data to achieve superior expressiveness, versatility and generalization. However, despite growing interest in scaling BFMs to further improve their capabilities, it remains unclear how key factors, including the learning paradigm, behavioral data and model architecture should be coordinated to enable effective scaling. In th…
`id: arxiv:2607.15163`
Rótulo: incluir

---

## 51 · geral · hf_papers
**Self in Space: Benchmarking Self-Awareness and Spatial Cognition in UAV Embodied Intelligence**
https://huggingface.co/papers/2607.12477 · 2026-07-13
> Autonomous UAV systems increasingly rely on multimodal large language models (MLLMs) to operate in complex real-world environments. It contains 4,856 question--answer pairs across 13 tasks derived from 1,646 real-world UAV videos through a task-conditioned construction pipeline with expert verification.Extensive evaluations reveal that current MLLMs exhibit fundamental limitations in modeling dynamic and agent-centered processes
`id: arxiv:2607.12477`
Rótulo: radar

---

## 52 · medico · rss:jmir-ai
**Ambient AI Scribes and Emergency Department Documentation Burden: Retrospective Cohort Study**
https://ai.jmir.org/2026/1/e92193 · 2026-07-02T11:45
> <strong>Background:</strong> Clinician burnout has reached crisis levels in emergency medicine, with clinical documentation burden identified as a central contributing factor. Ambient artificial intelligence (AI) scribes offer a promising approach to reduce this burden, but objective evidence in the emergency department (ED) setting remains limited, and prior reports have been constrained by short observation windows and low adoption. <strong>Objective:</strong> This study aimed to evaluate the association between ambient AI scribe use and on-shift documentation time during a 13-month staged rollout in a busy ED, accounting for physician- and patient-level factors. <strong>Methods:</strong>…
`id: url:https://ai.jmir.org/2026/1/e92193`
Rótulo: incluir

---

## 53 · medico · arxiv
**Harrison.Rad 1.5 Technical Report: A radiology foundation model that can draft reports from images, priors and clinical context**
https://arxiv.org/abs/2607.05880v1 · 2026-07-07
> Imaging demand is growing faster than the radiology workforce can expand, and reporting backlogs cannot be resolved through training and recruitment alone. The most direct opportunity is reducing the time and effort radiologists spend producing reports, a task that requires interpreting images, integrating clinical history and prior studies, and drafting structured findings. We present Harrison.Rad 1.5 (HR1.5), a radiology-specific multimodal large language model that accepts interleaved text and visual inputs and generates structured and unstructured text across plain-film radiology, spanning computed radiography, chest, musculoskeletal, abdominal, spine, and pelvic x-rays, and mammography…
`id: arxiv:2607.05880`
Rótulo: incluir

---

## 54 · geral · rss:bair
**RL without TD learning**
http://bair.berkeley.edu/blog/2025/11/01/rl-without-td-learning/ · Sat, 01 Nov 2025
> <!-- twitter --> <p>In this post, I’ll introduce a reinforcement learning (RL) algorithm based on an “alternative” paradigm: <strong>divide and conquer</strong>. Unlike traditional methods, this algorithm is <em>not</em> based on temporal difference (TD) learning (which has <a href="https://seohong.me/blog/q-learning-is-not-yet-scalable/">scalability challenges</a>), and scales well to long-horizon tasks.</p> <p style="text-align: center;"> <img alt="" src="https://bair.berkeley.edu/static/blog/rl-without-td-learning/teaser_short.png" width="100%" /> <br /> <i style="font-size: 0.9em;">We can do Reinforcement Learning (RL) based on divide and conquer, instead of temporal difference (TD) lea…
`id: url:http://bair.berkeley.edu/blog/2025/11/01/rl-without-td-learning`
Rótulo: incluir

---

## 55 · medico · rss:jmir-ai
**Knowledge-Augmented Large Language Model for Multimodal Electronic Health Record–Based Risk Prediction: Development and Validation Study**
https://ai.jmir.org/2026/1/e88356 · 2026-06-12T15:30
> <strong>Background:</strong> Accurate clinical outcome prediction using electronic health records (EHRs) is crucial for patient care and resource allocation. EHRs include both structured data and rich, unstructured clinical notes. However, prior machine learning methods struggle with the multimodality, long context of notes, and severe class imbalance in clinical tasks. <strong>Objective:</strong> This study aimed to introduce and evaluate KAMELEON (Knowledge-Augmented Multimodal EHR Learning for Outcome Prediction), a unified, 2-stage hybrid framework that integrates diverse EHR modalities and external biomedical knowledge to enhance clinical risk prediction. <strong>Methods:</strong> This…
`id: url:https://ai.jmir.org/2026/1/e88356`
Rótulo: incluir

---

## 56 · medico · rss:jmir-medinform
**Predicting Laboratory Test Ordering in Emergency Departments Using Integrated Structured and Unstructured Electronic Health Records: Machine Learning Study**
https://medinform.jmir.org/2026/1/e85255 · 2026-06-15T17:15
> Background: Laboratory testing is a cornerstone of diagnostic decision-making in emergency departments (EDs), yet its overuse contributes substantially to unnecessary health care costs and inefficiencies. Predictive approaches that leverage electronic health record data may help optimize and guide more appropriate test use. Objective: This study aims to develop and evaluate machine learning models that predict laboratory test use during ED visits by integrating structured clinical data and unstructured text from electronic health records. Methods: We analyzed 13,115 adult ED visits from the 2021 National Hospital Ambulatory Medical Care Survey–Emergency Department dataset. Structured predic…
`id: url:https://medinform.jmir.org/2026/1/e85255`
Rótulo: incluir

---

## 57 · medico · rss:jmir-medinform
**Balancing Privacy Protection and Reproducible Entity Extraction in Real-World Data in the Development of a Framework for Deidentified Japanese Electronic Health Record Narratives Using BERT: Retrospective Observational Study**
https://medinform.jmir.org/2026/1/e97411 · 2026-11-06T15:30
> Background: Pharmacoepidemiologic studies using real-world data often lack clinical context embedded in free-text electronic health records (EHRs). However, sharing EHR narratives is restricted by privacy requirements, and conventional deidentification approaches may reduce analytic utility and limit auditability. Objective: This study aims to develop and evaluate a framework that (1) extracts structured cancer-related entities from Japanese EHR free text using BERT (Bidirectional Encoder Representations from Transformers)–based natural language processing and (2) generates deidentified analytic text that preserves contextual information for post hoc auditing under privacy constraints. Meth…
`id: url:https://medinform.jmir.org/2026/1/e97411`
Rótulo: incluir

---

## 58 · medico · arxiv
**Compositional Reasoning Depth Predicts Clinical AI Failure: Empirical Evidence Consistent with Transformer Compositionality Limits in Electronic Health Record Question Answering**
https://arxiv.org/abs/2606.16890v1 · 2026-06-15
> Aggregate accuracy benchmarks conceal a systematic structure in how large language models fail at electronic health record (EHR) question answering: questions requiring more inferential steps produce disproportionately more errors. Motivated by theoretical results on transformer compositionality limits, we introduce a pre-specified hop-count taxonomy -- the number of distinct reasoning steps required to answer a clinical question from an EHR -- as a principled predictor of model failure. We annotate 313 clinician-generated MedAlign EHR question-answer pairs across four hop levels and evaluate 301 questions in a within-model ablation (claude-sonnet-4-6, zero-shot vs. extended thinking) and c…
`id: arxiv:2606.16890`
Rótulo: incluir

---

## 59 · medico · pubmed
**Nailfold capillary phenotypes distinguish juvenile myositis subtypes and associate with disease activity.**
https://pubmed.ncbi.nlm.nih.gov/42681940/ · 2026
> Nailfold capillaroscopy is a non-invasive method to visualize altered microcirculation in pediatric rheumatic disease, with potential to aid in diagnostic differentiation and disease monitoring. We used nailfold video capillaroscopy (NVC) and machine learning to identify patterns of capillaroscopic features in juvenile dermatomyositis (JDM) and associations of capillaroscopic features with clinical data. NVC features were quantified using automated neural network-based software in 76 individuals, including 18 controls, 33 JDM, 17 childhood-onset systemic lupus erythematosus (cSLE), and 8 overlap myositis (OM) patients. Unsupervised cluster analysis by capillaroscopic features was performed,…
`id: pmid:42681940`
Rótulo: incluir

---

## 60 · medico · pubmed
**Real-World Implementation of Large Language Models for Writing Clinical Discharge Summaries Within a Secure Data Environment: Development and Expert Evaluation Study.**
https://pubmed.ncbi.nlm.nih.gov/42398933/ · 2026
> A discharge summary should be a clinical report that documents a patient's hospital stay, including test results, diagnoses, management, and follow-up. Currently, discharge summaries are written by clinicians who manually locate pertinent information across the electronic health record, of which approximately 80% is free text. This process is time-consuming and may be suitable for automation using large language models. This study developed a template-based prompting system that can produce clinically acceptable discharge summaries, specifically the "clinical summary" and "plan and requested actions" sections, from routinely collected electronic patient records. This study used electronic h…
`id: pmid:42398933`
Rótulo: incluir
