# Animated (3D) explainer lessons on complex processes: learning science, buy-vs-build benchmarks, and risks

*Research notes compiled 2026-11-09. Product, price and policy facts were checked on the web on 2026-11-09 unless another date is given. "(official page, 2026-11-09)" means the vendor's own page was fetched that day. "(third-party)" means an aggregator or blog. Classic learning-science findings are cited to primary or near-primary sources.*

## Q1. What lesson structure, length and visual style maximize learning of complex processes, and when is 3D worth it over 2D?

### Takeaway
The best-supported design is short and segmented: no more than 6 minutes, narrated with a conversational, human-like voice, using schematic visuals, signaling, and labels placed next to and timed with the narration, with no decoration. It should start with pre-training on the key parts and end with retrieval practice. Across meta-analyses, animation beats static pictures only modestly (g ≈ 0.23; d ≈ 0.37). The advantage concentrates where the change itself must be learned and where the visuals are iconic rather than abstract. 3D pays off mainly for genuinely spatial content: spatial knowledge d ≈ 0.50, strongest when the 3D is interactive and stereoscopic, which a flat video is not. For abstract processes such as transformer attention, RL loops or LLM pipelines, a 2D schematic is the evidence-based default.

### Cited Findings

#### Mayer's multimedia principles: median effect sizes (Mayer's 2021 meta-analysis, as summarized by Mayer 2023)
Source for this block: R. E. Mayer, "Research-Based Principles for Designing Multimedia Instruction," in *In Their Own Words* (APA Division 2, 2023; Overson, Hakala, Kordonowy & Benassi, eds.).
- **Multimedia** (words plus graphics beat words alone): 13 comparisons, median d = 1.35. [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Coherence** (delete extraneous material): 18 of 19 tests, d = 0.86. Boundary conditions: the effect is strongest for learners with low working-memory capacity, for **system-paced** lessons, and when the extraneous material is **highly interesting** ("seductive"). [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Signaling**: 26 of 28 tests, d = 0.70. Verbal signals (outline, headings, pointer words such as "first/second", vocal stress) gave 15/16 and d = 0.69. Visual signals (arrows, flashing, spotlighting, pointing) gave 11/12 and d = 0.71. Signaling works best for low-knowledge learners and complex material, and when signals are used sparingly. [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Redundancy** (don't add on-screen captions that duplicate the narration): only 8 of 12 tests, d = 0.10. The effect shrinks or reverses when:
  - the on-screen text is short or reworded,
  - the lesson is slow-paced or learner-controlled,
  - the words are in the learner's second language.

  [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Spatial contiguity** (printed words next to the corresponding graphic): 9/9, d = 0.82. **Temporal contiguity** (narration at the same time as the corresponding graphic): 8/8, d = 1.31. Spatial contiguity is strongest for low prior knowledge, complex lessons and interactive formats. [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Segmenting** (learner-paced segments): 7/7, d = 0.67. The classic test split a narrated lightning animation into 16 ten-second segments with a "continue" button. Segmenting is stronger when the material is complex or the lesson is otherwise fast-paced. [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Pre-training** (names and characteristics of key components first): 10/10, d = 0.78. It may not apply to **high-prior-knowledge** learners, to simple material, or to slow or learner-paced lessons. [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Modality** (spoken rather than printed words): 18/19, d = 1.00. Printed words can be better when the verbal material contains **technical terms**, is in the learner's second language, or the lesson is learner-paced. [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Personalization** (conversational style): 13/15, d = 1.00. **Voice** (appealing human voice rather than a machine voice): 6/7, d = 0.74. Mayer notes that modern text-to-speech can be human-like (Craig & Schroeder 2017, 2018) and quotes Schroeder & Adesope (2014): "voice may be critical, whereas the image of the agent is not." [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Embodiment** (on-screen agent with human-like gesture, gaze and expression, versus a static agent): 16/17, d = 0.58. Gestures and first-person camera views also help. The effect may vanish when there are negative social cues such as a machine voice. [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Image principle**: just adding the speaker's static image does not help. Of 7 tests, only 4 favored the image and 3 were negative; median d = 0.19. [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Generative activity** (summarizing, practice tests, self-explanation): 37/44, d = 0.71. [Mayer 2023](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)
- **Edition caveat**: medians differ across syntheses, so tables from different editions should not be mixed.
  - The 2014 Cambridge Handbook chapter reports segmenting d = 0.79 (10 tests), pre-training d = 0.75 (16 tests) and modality d = 0.76 (61 tests). [Cambridge Handbook, Mayer & Pilegard chapter](https://cambridge.org/core/books/cambridge-handbook-of-multimedia-learning/principles-for-managing-essential-processing-in-multimedia-learning-segmenting-pretraining-and-modality-principles/DD24C2F48B9B1277CE59F78276110258)
  - Catalogue abstracts of Mayer's 2017 e-learning review list, for example, redundancy d = 0.87 and embodiment d = 0.36. [Mayer 2017, JCAL record](https://zendy.io/title/10.1111/jcal.12197)

#### Cognitive load theory and the "transience" problem of animation
- The canonical update of cognitive load theory is Sweller, van Merriënboer & Paas, "Cognitive architecture and instructional design: 20 years later," *Educational Psychology Review* 31:261–292 (2019). [DOI](https://doi.org/10.1007/s10648-019-09465-5)
- **Transient information effect**: information that disappears once presented, such as speech or animation frames, is harder to learn from than permanent information, and this can erode animation's advantage over static graphics. [Cambridge Handbook chapter, "Transient information principle"](https://resolve-he.cambridge.org/core/books/abs/cambridge-handbook-of-multimedia-learning/transient-information-principle-in-multimedia-learning/670D96C3B9520320CE558AA855A49EE9)
- Ng, Kalyuga & Sweller (2013) tested remedies: pause/play and a "tracing" feature that keeps earlier states visible. They concluded that restructuring dynamic information can counteract transience. [Record: "Reducing transience during animation"](https://vufind-test.katalog.k.utb.cz/SummonRecord/FETCH-eric_primary_EJ10309063)

#### Animation vs static pictures (meta-analyses)
- **Höffler & Leutner 2007** (*Learning and Instruction* 17:722–738): 26 studies, 76 comparisons, overall d = 0.37 (95% CI 0.25–0.49). Subgroups:
  - representational animations: d = 0.40,
  - highly realistic, e.g. video-based: d = 0.76,
  - procedural-motor knowledge: d = 1.06.

  [IPN record](https://www.leibniz-ipn.de/en/research/publications/instructional-animation-versus-static-pictures-a-meta-analysis)
- **Berney & Bétrancourt 2016** (*Computers & Education* 101:150–167): 50 papers, 61 studies (N = 7,036), 140 comparisons, random effects, overall **g = 0.226** (95% CI 0.12–0.33). [UNIGE archive, full text](https://archive-ouverte.unige.ch/unige:92234) Moderators from Table 3 of the paper:
  - *Pacing*: system-paced g = 0.309 (k = 96). Light, regular and full learner control were not significant (full control g = −0.120).
  - *Accompanying words*: narration g = 0.320 (k = 28; the abstract gives 0.336). Written text g = 0.105 (not significant, k = 58). No accompanying text g = 0.886 (k = 14).
  - *Cueing*: did not moderate the effect (with cues g = 0.204; without cues g = 0.228).
  - *Abstraction*: **iconic representations** (schematic, realistic or photo-realistic pictures) g = 0.245 (k = 91). **Abstract representations** (analytical or formal pictures) g = 0.006 (not significant, k = 26).
  - *Domain*: natural phenomena g = 1.26, chemistry 0.77, biology 0.20. Informatics 0.11, mathematics −0.07 and mechanics −0.11 were not significant.
- **Reanalysis** of the same data (Ploetzner, Berney & Bétrancourt 2020): animations were significantly more effective when the specifics of the depicted change had to be learned (simple features g = 0.340; complex features g = 0.647). A follow-up experiment was published in 2021. [Instructional Science 2021](https://link.springer.com/article/10.1007/s11251-021-09541-w)
- **Tversky, Morrison & Bétrancourt 2002** proposed two principles for when animation helps:
  - *Congruence*: the graphic's content and format should match the concept to be conveyed.
  - *Apprehension*: the graphic must be accurately perceived and understood.

  They argue that animations are often too fast or complex to perceive, and that many continuous events are mentally conceived as discrete steps. Many studies that favored animation were confounded with extra information or interactivity. [Paper PDF](https://hci.stanford.edu/courses/cs448b/papers/Tversky_AnimationFacilitate_IJHCS02.pdf)
- **Mayer, Hegarty, Mayer & Campbell 2005** (*Journal of Experimental Psychology: Applied* 11:256–265): paper-based static illustrations with printed text matched or beat computer-based narrated animations across lessons such as lightning, the toilet tank and ocean waves. This is the "static media hypothesis": static frames prompt active mental animation. [Record](https://data.zhenzhi.com/details/1/864596096)

#### Realism vs schematic
- Berney & Bétrancourt's discussion cites several studies showing that highly realistic pictures were less effective than less realistic ones: Imhof, Scheiter & Gerjets 2007; Kühl, Scheiter & Gerjets 2012; Scheiter, Gerjets, Huk, Imhof & Kammerer 2009. [UNIGE full text](https://archive-ouverte.unige.ch/unige:92234)
- A mitosis experiment (Nugteren, Tabbers, Scheiter & Paas; n = 92 biology students) compared schematic and realistic animations. The realistic-only group scored lower on schematic visual-recognition questions; other outcomes did not differ. [Springer chapter](https://link.springer.com/chapter/10.1007/978-1-4614-7485-2_24)
- **Conflict**: Höffler & Leutner found larger effects for realistic, video-based animations (d = 0.76), but those were largely procedural-motor tasks. [IPN record](https://www.leibniz-ipn.de/en/research/publications/instructional-animation-versus-static-pictures-a-meta-analysis)

#### 3D visualization in anatomy and medical education
- **Yammine & Violato 2015** (*Anatomical Sciences Education* 8:525–538): 36 studies (28 randomized), 2,226 participants. Compared with other methods, 3D visualization technology improved:
  - factual knowledge, d = 0.30,
  - **spatial knowledge, d = 0.50**,
  - satisfaction and perceived usefulness, d ≈ 0.28 (as reported in the abstract and catalogue).

  [LAU repository](https://laur.lau.edu.lb:8443/xmlui/handle/10725/10914)
- **Triepels et al. 2020** (*Clinical Anatomy* 33:25–33): a systematic review with no pooling. Of 21 studies comparing 3D with 2D, 12 found 3D significantly more effective and 9 found no difference. Students prefer 3D. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6916638/)
- **Bogomolova et al.** (*Medical Education* 2020/2021, 55(3):317–327): 16 studies (1,695 participants), 13 meta-analyzed. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7984401)
  - Interactive stereoscopic vs interactive monoscopic 3D: ES = 0.53 (0.26–0.80).
  - Interactive stereoscopic 3D vs 2D images: ES = 0.45 (0.10–0.81), with possible publication bias.
  - **Non-interactive** stereoscopic vs 2D: ES = −0.87 (−2.09 to 0.35). This was not pooled because heterogeneity was extreme (I² = 97%).
  - In 3 studies, students with lower visual-spatial ability benefited more from stereoscopic viewing.
  - Authors' conclusion: stereopsis helps "especially when utilised in an interactive 3D environment."
- **Spatial ability (conflicting evidence)**:
  - Huk 2006 (*JCAL* 22:392–404): only high-spatial-ability students benefited from interactive 3D cell models; low-spatial learners were described as cognitively overloaded. [Scilit record](https://www.scilit.net/publications/eef4277a964ed2b221b506ef4e15e3e1)
  - Höffler's 2010 meta-analysis found that low-spatial learners *can* be supported by dynamic rather than static, and 3D rather than 2D, visualizations. [Record](https://www.bohrium.com/paper-details/spatial-ability-its-influence-on-learning-with-visualizations-a-meta-analytic-review/811792669750591488-10463)

#### Video length and engagement
- **Guo, Kim & Rubin 2014** (ACM Learning@Scale) analyzed 6.9 million viewing sessions from 4 edX courses. [Paper PDF](https://up.csail.mit.edu/other-pubs/las2014-pguo-engagement.pdf)
  - The **median engagement time is at most 6 minutes regardless of video length**, and students "often make it less than halfway through videos longer than 9 minutes."
  - 0–3-minute videos had the highest engagement: 75% of sessions watched more than three-quarters of the video.
  - The authors' recommendation: plan segments shorter than 6 minutes.
  - Interleaving the instructor's talking head with slides was more engaging than slides alone.
  - Khan-style tablet drawing held students 1.5–2× longer than slides or screencasts.
  - A "personal feel" was more engaging than high-fidelity studio production.
  - Speaking rates ranged from 48 to 254 words per minute (mean 156). Within a length band, faster, enthusiastic speakers drew up to 2× more engagement; the authors tell instructors they "do not need to purposely slow down".
- **Caveat**: engagement here means watch time and problem attempts, not learning outcomes. [Paper PDF](https://up.csail.mit.edu/other-pubs/las2014-pguo-engagement.pdf)

#### On-screen instructor, avatar or pedagogical agent
- **Castro-Alonso et al. 2021** (*Educational Psychology Review*): 32 effect sizes, 2,104 participants. Learning with multimedia agents gave a small effect, g+ = 0.20. **2D agents (g+ = 0.38) were more effective than 3D agents (g+ = 0.11)**. Nonverbal communication, motion and voice did not moderate the effect. [Birmingham record](https://research.birmingham.ac.uk/en/publications/effectiveness-of-multimedia-pedagogical-agents-predicted-by-diver/)
- Schroeder, Adesope & Gilbert 2013 (43 studies, 3,088 participants) also found a small but significant effect. [WSU record](https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/How-Effective-are-Pedagogical-Agents-for/99900601056901842)
- **Alemdag 2022** (20 experiments): having the instructor on screen had no significant effect on learning or social presence. It significantly raised **cognitive load** and **motivation**. [METU record](https://avesis.metu.edu.tr/yayin/8df0f0a3-6154-4f4b-9333-5108f1e4b1f1/effects-of-instructor-present-videos-on-learning-cognitive-load-motivation-and-social-presence-a-meta-analysis)
- A series of meta-analyses on the instructor-presence effect (35 studies, 46 comparisons, 6,339 participants) found:
  - a small positive effect on retention and none on transfer,
  - higher social presence, affect and motivation,
  - lower subjective extraneous load, but also less dwell time on the relevant visuals.

  [DDB record](https://www.deutsche-digitale-bibliothek.de/item/PBOMPA7MBJFP5UZOZIZ5TTKBWQG7UUP3)
- **AI-generated teaching videos**:
  - Netland et al. 2025 (*Computers & Education* 224:105164; 447 participants; four short videos from a management course) found no significant exam differences between AI-generated and human-made videos. Learners rated the human-made videos slightly but significantly better on learning experience. The AI videos took hours to make; the human ones took several days. [x-mol record](https://x-mol.com/paper/1857628113137397760); [Media & Learning summary](https://media-and-learning.eu/subject/artificial-intelligence/when-ai-took-over-my-teaching-videos-students-enjoyed-them-less-but-learned-the-same/)
  - Leiker et al. 2023 found no significant difference in learning outcomes with a synthetic AI instructor. [arXiv](https://arxiv.org/pdf/2304.03784)

#### Ending with retrieval practice (a quiz)
- **Adesope, Trevisan & Sundararajan 2017** (*Review of Educational Research*; the blog's title reports 217 studies). [Learning Scientists summary](https://www.learningscientists.org/blog/2017/2/9-1)
  - Practice testing consistently beat restudying, and beat no activity or filler tasks by much more.
  - Feedback was only slightly more effective than no feedback.
  - Benefits were stronger when the final test came more than 1 day later.
  - It worked in classrooms as well as in the lab.
  - Secondary summaries disagree on the exact pooled g (about 0.6–0.7) and on the number of studies.
- **Szpunar, Khan & Schacter 2013** (*PNAS* 110:6313–6317): memory tests interpolated into an online lecture reduced mind wandering, increased note-taking and improved learning. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3631699) Students who were never tested during the lecture reported mind wandering about 40% of the time. [Author interview](https://medicalresearch.com/?p=546)
- A 2016 follow-up was more mixed: mind-wandering rates did not differ between groups. [Jing, Szpunar & Schacter 2016](https://sites.harvard.edu/schacter-memory/files/2022/08/jing2016-1-1.pdf)

### Inferences

#### When 3D is worth it (decision rules)
- **Use 3D only when the mental model to be built is itself spatial**: geometry, orientation, depth, occlusion, or 3D relations between parts. The evidence for 3D is strongest for spatial knowledge (d = 0.50) and comes mostly from anatomy.
- A rendered video is **monoscopic and non-interactive**, which is the *weakest* form of 3D in the Bogomolova meta-analysis. If a topic truly needs 3D, ship a small interactive web viewer next to the video (for example three.js for organs or CT geometry, or Mol* for PDB structures), rather than relying on camera orbits alone.
- **Use 2D schematics for abstract or relational processes**: matrices, information flow, loss landscapes, pipelines and loops. In Berney & Bétrancourt, abstract representations showed no advantage for animation at all (g = 0.006), and informatics, mathematics and mechanics domains were not significant. Tversky's congruence principle points the same way.
- Prefer **schematic over photoreal** (realism findings plus the coherence/seductive-details boundary). Allow realism only when *recognizing the real appearance* is the learning goal, for example what a CT artifact looks like.
- **Low-spatial-ability learners**: the evidence conflicts (Huk vs Höffler 2010 and Bogomolova). The safe design is to pair any 3D view with 2D "key views" (canonical cross-sections or orthographic frames) and keep labels anchored.
- **Mapping to the user's example topics:**

| Topic | Recommended visual mode | Why |
|---|---|---|
| Attention in a transformer | 2D step-wise schematic (Q/K/V blocks, attention-weight heatmap built cell by cell); at most a 2.5D "stack of layers" | Abstract and relational; no spatial referent |
| Diffusion denoising | 2D animation of the noise→image trajectory plus a 2D/3D "landscape" metaphor of the score field, flagged as a metaphor | The change over time is the content; a landscape is congruent with the gradient idea |
| RL post-training (RLHF, GRPO, etc.) | 2D loop/flow diagram with animated data tokens | Abstract loop |
| CT reconstruction + AI segmentation | **3D justified**: gantry rotation, projections, sinogram, back-projection, voxel volume, segmentation masks; add 2D slice key views | Inherently spatial geometry |
| LLM drafting a discharge summary from the EHR | 2D pipeline plus screen mock-ups using synthetic data; show hallucination and omission checkpoints | Workflow; no spatial content |
| Molecular mechanism of a therapy | **3D justified but schematic**: PDB-derived structure simplified to surfaces and colored domains; animate binding or conformational change slowly | Spatial; realism should be limited |

#### Should there be an on-screen instructor or avatar?
- For the **expert first user**: no avatar. Learning benefits are small or null, cognitive load rises, and avatar minutes cost credits.
- For **staff or customer** versions, two options:
  - a brief human-like presenter (or a real physician recording) in the intro and outro only, never overlapping the diagram, for motivation and social presence;
  - or picture-in-picture during the "why it matters" segments, echoing Guo's interleaving finding.
- Never use a static portrait (image principle). If an agent is used, keep it 2D, with gestures and pointing, and pair it with a human-like voice.

#### Storyboard template for a 3–6-minute lesson (default about 4.5 minutes)
Scaling: the 3-minute version keeps sections 0, 2, two mechanism chunks, 6 and 7. The 6-minute version uses four chunks and two interpolated checks. Do not exceed 6 minutes; split the lesson into two parts instead.

| # | Section | Time | Narration (pt-BR) | Visual rules | Grounding |
|---|---|---|---|---|---|
| 0 | Hook + objective | 0:00–0:15 | One concrete question or scenario, plus a one-sentence learning objective | A still of the process's end state; no music, no logo sting | Signaling via outline; coherence |
| 1 | Pre-training: key parts | 0:15–0:45 | Name 3–5 components, one line each, defining each term once | Each component gets an icon and color "token" that stays the same through the lesson; print the English technical term as a label with a pt-BR gloss | Pre-training (d = 0.78); modality boundary for technical terms. **Skip automatically if the learner already knows the topic** |
| 2 | Big-picture map | 0:45–1:05 | "Primeiro… depois… por fim…" | 2D schematic of the whole process; it shrinks into a **persistent mini-map** in one corner | Signaling; remedy for transience |
| 3–5 | Mechanism, 3 chunks | 1:05–3:35 (40–60 s each) | One causal step per chunk; narration synchronized to on-screen events (word timestamps drive keyframes) | One moving focus at a time; highlight the active element and dim the rest; labels adjacent with leader lines; 3D only where spatial; 2–3 s freeze at the end of each chunk while the mini-map updates (natural pause point) | Segmenting (d = 0.67); spatial and temporal contiguity (d = 0.82 / 1.31); apprehension |
| opt | Interpolated check | After chunk 2, about 10 s | "Pause: what happens next?" | Freeze frame plus a question card | Interpolated testing; generative activity |
| 6 | Limits, failure modes, relevance | 3:35–4:00 | What breaks, the evidence level, and why it matters clinically or for the product | 2D; small on-screen source references | Accuracy and trust |
| 7 | Recap | 4:00–4:20 | Three takeaways in the same words as the objective | Replay the mini-map with the same tokens | Signaling; coherence |
| 8 | Retrieval quiz (outside the runtime) | 2–4 min | 3–5 items: 2 multiple-choice questions with plausible distractors, 1 ordering or labeling item, 1–2 "explain why" or transfer items | Immediate feedback with an explanation and a timestamp link back into the video; spaced re-quiz after 1–3 days and again after 1–2 weeks | Generative activity (d = 0.71); retrieval practice; benefits larger with more than a 1-day delay |

**Narration style**
- Conversational second person ("você"), active voice, short sentences, and explicit signal words.
- A human-like neural voice: the voice principle, and the risk that a machine voice undermines embodiment.
- A brisk, enthusiastic pace. Guo found a mean of 156 wpm and that faster delivery did not hurt. For pt-BR, a target of about 150–170 wpm (roughly 650–750 words for 4.5 minutes) is an **inference** that should be validated with the user.
- State uncertainty explicitly.
- Do not read on-screen text aloud, except labels.

**Visual rules**
1. One idea per shot.
2. Schematic, flat-shaded, with a limited palette and consistent color semantics across 2D and 3D.
3. No paragraph text; keywords and labels only, so redundancy is avoided. Optional subtitles for accessibility, as a toggle.
4. Labels sit next to the parts they name.
5. Keep a persistent mini-map of the process.
6. No background music, decorative B-roll, stock footage, or photoreal generative clips for mechanisms (coherence, plus the accuracy risk covered in Q3).
7. Slow, predictable camera moves that always return to a canonical view.
8. Orientation cues (anatomical axes and left/right) and scale bars or units wherever relevant.
9. Show the end state first and the mechanism after it.
10. System-paced playback is fine: Berney found system-paced animation had the largest advantage. Add chapter markers and pause points rather than fine-grained playback controls.

### Gaps
- The evidence base is dominated by **novice** learners in STEM, biology and anatomy. I found **no studies on expert learners** (such as a physician learning ML internals), on animated explanations of **AI/CS processes**, or on narration in **Brazilian Portuguese**, including optimal pt-BR speech rate.
- No controlled study was found that tests the learning effect of **AI-generated 3D explainers** specifically. The AI-video studies (Netland, Leiker) used avatar or slide formats on short business or general topics.
- The Guo 2014 findings concern MOOC **engagement**, not learning, and date from 2014.
- Mayer's medians differ across editions (2014 / 2017 / 2021). I used the 2021-based 2023 table consistently.
- Adesope 2017's exact pooled g and study counts were not verified against the original article: secondary sources disagree (about 0.6–0.7; 188/217 articles).
- The Mayer, Hegarty, Mayer & Campbell 2005 and Scheiter 2009 full texts were not read; their findings above come from records and citing papers.

## Q2. What would buying (studio or SaaS) cost per lesson compared with an automated pipeline? Is there a cheap existing baseline good enough to compare against?

### Takeaway
Professional medical 3D animation costs roughly **US$5k–20k per finished minute**, and mechanism-of-action work is quoted at **≥$20k/min**. That means about **$25k–100k+** for a 5-minute lesson and **6–10 weeks per 1–2 minutes**. AI SaaS tools (Synthesia, HeyGen, Pictory) cost roughly **$0.15–1.60 per minute** at plan allowances, but they produce 2D presenter, slide or stock-footage videos, not 3D mechanisms, and some restrict medical content. The cheapest acceptable baseline is **Google's Gemini Notebook (NotebookLM) Video Overview in pt-BR**. It is free, or included in Google AI Pro at R$96.99/month, and AI-illustrated and narrated, but not 3D and with an explicit accuracy disclaimer. A self-built pipeline should beat it on process animation and 3D, on accuracy controls, and on built-in retrieval practice, at a marginal cost close to zero.

### Cited Findings

#### Professional studios (vendor price guides; they likely skew toward studio rates)
- **VOKA** (a 3D medical animation studio; published 2026-02-23, updated 2026-06-27). [VOKA](https://voka.io/medical-animation-cost/)
  - Per-minute bands: freelance **$1.5k–4k/min**, professional studio **$5k–20k/min**, high-end agency **$25k+/min**.
  - "From" prices by content type: simple procedures $7.5k/min; mechanism of disease or physiology $10k/min; surgical or device $12.5k/min; biotech $15k/min; **scientific concepts or mechanism of action $20k/min**.
  - Its FAQ gives a professional-studio average of $6k–18k/min.
  - A 1–2-minute 3D project takes **6–10 weeks**. Rendering takes 60–150 hours per minute. Rush jobs add 25–50%.
  - 3D costs more than 2D, and 2D suits patient education.
- **Prolific Studio** (2026-08-24, medical devices). [Prolific Studio](https://prolificstudio.co/blog/medical-device-animation-cost/)
  - Most work runs **$8k–20k per finished minute**; simple **2D explainers $2k–5k/min**.
  - A paid storyboard phase costs $3k–8k.
  - Instructions-for-use and regulatory review add 15–30%.
  - Molecular mechanism work costs more because it must be "built from published structures."
- **General 3D animation** in 2026 is quoted at $5k–50k+ per finished minute (third-party price guide). [Framesixty](https://framesixty.com/how-much-does-3d-animation-cost/)

#### Existing medical-education platforms and libraries (not custom content)
- **Osmosis (Elsevier)** prices plans by program. [Osmosis MD plan](https://osmosis.org/plans/md); [Elsevier support pricing page](https://www.elsevier.support/osmosis/answer/pricing); aggregator check around 2026-10-07: [Techbloat](https://www.techbloat.com/software/osmosis/)
  - MD plan snapshots: 1 year $249 (about $21/month), 2 years $399, 3 months $149, with a 7-day free trial. Sale snapshots: 12 months $199, 24 months $279.
  - Refunds only for subscriptions of a year or longer.
  - The direct page fetch returned HTTP 403 on 2026-11-09, so these prices come from page snippets and aggregators.
- **Ninja Nerd** (official page, 2026-11-09). [Ninja Nerd membership](https://www.ninjanerd.org/membership)
  - Premium is **$50 for 3 months** or **$168 per year**; a Free tier exists.
  - Premium adds notes, illustrations, per-lecture quizzes, slide decks and a QBank. No CME.
  - Lectures are whiteboard-style on the linked YouTube channel; the page is in English only.
- **Visible Body**:
  - Human Anatomy Atlas is a one-time purchase of **$24.99** on iOS and Google Play (tracker, 2026-05-09). [App Store listing](https://apps.apple.com/il/app/id1117998129); [App Pricing Lab](https://apppricinglab.com/iap/apple/1117998129)
  - Add-ons: Patient Education Animations $19.99, Advanced Animations $9.99, Dental $7.99 (tracker, 2026-03-21). [App Pricing Lab](https://apppricinglab.com/iap/apple/1117998129)
  - Visible Body Suite subscriptions: Student $34.99, Professional $199.99 (US App Store tracker, March 2026; billing period not confirmed). [App Pricing Lab](https://apppricinglab.com/app/apple/1594705297)
  - Suite languages listed on the Korean App Store: German, Spanish, English, Italian, Japanese, Simplified Chinese, French. **No Portuguese.** [App Store KR](https://apps.apple.com/KR/app/id1594705297)
  - Institutional seat and site licenses are sold through sales. [Visible Body](https://www.visiblebody.com/subscription-request-page)
- **BioDigital Human**: "As of May 1, 2026," the paid Personal Plus plan and equivalent individual premium plans were retired. School and Business plans are institutional only, and individuals are pointed to the free Personal plan. [BioDigital support](https://support.biodigital.com/hc/en-us/articles/39657133675927) (seen via a search snippet; the direct fetch returned HTTP 403)
- **Nucleus Medical Media**:
  - No public price list was found. A third-party ranking says library content is licensed on custom-quoted 1-, 3- or 5-year terms, from a library of 25,000+ illustrations and 1,000+ animations, and puts custom work at $5k–50k+ per minute. [Knowlify ranking](https://knowlify.com/articles/best-medical-healthcare-animation-agencies) (low reliability: knowlify.com now presents itself as an ad agency)
  - Nucleus info packet: [download page](https://healthcare.nucleusmedicalmedia.com/Nucleus-Info-Packet/pdf/info-packet/download)
  - For comparison, another vendor, Understand.com, lists **$995–1,995 for a complete animation library**. [Understand.com FAQ](https://understand.com/pages/faq)

#### AI "topic or paper to video" SaaS (official pages fetched 2026-11-09 unless noted)
- **Synthesia** produces AI avatar presenters plus slides or templates; there are no 3D mechanisms. [Synthesia pricing](https://www.synthesia.io/pricing)
  - **Basic $0**: 500 credits/month, about 10 minutes, watermarked.
  - **Starter $19/month** ($9 the first month), or **$14/month billed yearly ($168/year)**: 1,250 credits/month, up to about 12 minutes of studio video per month (about 150 minutes/year).
  - **Pro $89/month** ($49 the first month), or **$59/month billed yearly ($708/year)**: 6,000 credits/month, about 60 minutes/month (about 720 minutes/year).
  - **Enterprise**: custom price, unlimited minutes.
  - Studio video works out to about 100 credits per minute (derived). Lip-sync costs 2× credits. "Syren" videos cost 1,000–2,000 credits per 1-minute video.
  - Avatars: 9 (Basic), 125+ (Starter), 180+ (Pro), 240+ (Enterprise).
  - 70+ output languages on self-serve plans and 140+ on Enterprise. The page names "**Portuguese (Brazil)**" as an example regional variant.
- **Synthesia's medical-content policy**:
  - It prohibits promotional or guaranteed-outcome content about medical treatments, and misleading or unverified medical information, including "miraculous" or full-recovery claims and testimonials.
  - It treats content "about specific medical treatments, diagnoses, or conditions directed at enterprise or corporate audiences" as restricted and requiring an **Enterprise workspace**.

  [Synthesia help: medical advice](https://help.synthesia.io/en/articles/15396882-medical-advice-and-information); [Synthesia help: disagreeable content](https://help.synthesia.io/en/articles/8330530-disagreeable-content) (seen via search snippets)
- **HeyGen** produces AI avatar video, translation and dubbing; no 3D mechanisms. [HeyGen pricing](https://www.heygen.com/pricing)
  - **Free $0**: 3 videos/month, up to 1 minute, watermarked, 30+ languages.
  - **Creator $29/month** ($24/month annual per the FAQ): 600 credits, videos up to 30 minutes, 175+ languages and dialects.
  - **Pro $49/month**: 1,000 credits; higher tiers go up to 100,000 credits for $4,300.
  - **Business $149/month + $20 per seat per month**: 1,500 credits, videos up to 60 minutes.
  - **Enterprise**: custom.
  - The main page does **not** state credits per minute and does not name Portuguese.
  - Credits per minute conflict between sources:
    - HeyGen's Singapore pricing page lists Avatar III at 3 credits/min and Avatar IV/V at 20 credits/min. [HeyGen SG pricing](https://www.heygen.com/en-sg/pricing) (search snippet)
    - Third-party trackers list 4, 16, 31 and 48 credits/min (Avatar III video look, Avatar IV photo look, Avatar IV video look, Avatar V; dated 2026-10-09). [Flexprice](https://flexprice.io/pricing-index/heygen); [Dupple](https://dupple.com/learn/heygen-pricing)
- **Pictory** turns scripts, URLs or text into videos with stock footage, ElevenLabs voices and avatars; no 3D. [Pictory pricing](https://pictory.ai/pricing)
  - 14-day trial: up to 10 minutes, 720p, watermarked.
  - **Starter $29/month** (annual $25/month): 2,000 credits, up to **30 minutes/month**.
  - **Professional $59/month**: 6,000 credits, up to **90 minutes/month**.
  - **Teams $199/month** (annual $119/month): 18,000 credits, up to **300 minutes/month**.
  - Maximum video length 30 minutes; 1080p on paid plans; no refunds.
  - Languages: 7 on Starter and 29 on Professional/Teams. **Portuguese is not listed.** Third-party trackers disagree on prices.
- **Kodisc**: the site was unreachable on 2026-11-09 (connection reset).
  - Product Hunt describes an AI tool to "create stunning animations in minutes." [Product Hunt](https://www.producthunt.com/p/kodisc)
  - The developer posted updates in r/manim in February 2025, aimed at teachers and educational creators. [r/manim mirror](https://axebps-redlib.hf.space/r/manim/comments/1imnjz0/kodisc_updates)
  - Pricing, Portuguese support and output type could **not** be verified.
- **Google Gemini Notebook (formerly NotebookLM) Video Overviews**. Google's help center now titles the product "Gemini Notebook" at the old NotebookLM URL.
  - **Formats**: Explainer, **Short (about 60 s)** and **Cinematic**. [Help: Video Overviews](https://support.google.com/notebooklm/answer/16454555)
  - **Visual styles**: Classic, Whiteboard, Watercolor, Retro Print, Heritage, Paper-craft, Kawaii, Anime, or a custom description.
  - **Portuguese (Brazil) is supported for Explainer and Short. Cinematic is English-only and limited to users 18+.**
  - Other features: an optional steering prompt, a review of "producer notes" before rendering, downloads, and share links. Public sharing is disabled for Workspace Enterprise and Education accounts.
  - Generation can take more than 30 minutes.
  - The page warns: "Video overviews, including voices and visuals, are AI-generated and may contain inaccuracies or audio glitches."
- **Gemini Notebook plans**: Standard is free; Plus is AI Plus; Pro is AI Pro, with watermark removal; Ultra adds watermark removal too. A visible watermark is still applied for residents of India, South Korea and Vietnam. [Help: Upgrade](https://support.google.com/notebooklm/answer/16213268?hl=en)
- **Limits**: since **September 2, 2026**, usage limits are compute-based and "refresh every five hours rather than daily." Heavy outputs such as Video Overviews can be deferred and generated later. [Google blog, 2026-08-28](https://blog.google/innovation-and-ai/products/gemini-notebook/new-flexible-usage-limits/)
  - Reported multipliers: AI Plus 2× standard, Pro 4×, Ultra 5× or 20× Pro. [9to5Google, 2026-08-28](https://9to5google.com/2026/08/28/gemini-notebook-usage-limits/)
  - Earlier fixed caps reportedly were Free 3 (later 6) per day, Plus 6, Pro 20 and Ultra 200 (search summaries of earlier snapshots; versions conflict).
  - Video Overviews expanded to 80+ languages in August 2025. [Google blog](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebook-lm-audio-video-overviews-more-languages-longer-content/)
- **Google AI plan prices in Brazil** (source dates vary):
  - **AI Pro R$96.99/month**, with promotions such as R$48.49 for the first 6 months. [Tecnoblog](https://tecnoblog.net/noticias/google-surpreende-ao-aumentar-espaco-e-manter-preco-do-one-ai-pro/); [Canaltech](https://canaltech.com.br/apps/assinar-o-gemini-agora-esta-mais-barato-veja-quanto/)
  - AI Plus R$24.99/month (September 2026). [Claro](https://www.claro.com.br/blog/celular/google-ai-plus)
  - Ultra R$779.90 (20 TB) or R$999.90 (30 TB). [Tecnoblog](https://tecnoblog.net/noticias/google-reduz-preco-de-ia-no-brasil-mas-continua-carissimo/)

#### Research systems (open source; cost equals your own model/API usage)
- **Paper2Video / PaperTalker** (arXiv 2510.05096, October 2025; NeurIPS 2025). [arXiv](https://arxiv.org/abs/2510.05096); [code](https://github.com/showlab/Paper2Video)
  - Benchmark of **101 papers** paired with author-made presentation videos, slides and speaker metadata.
  - A multi-agent system generates slides (layout chosen by "tree search visual choice"), subtitles, synthesized speech, cursor grounding and a **talking head**, with parallel slide-by-slide generation.
  - The output is **2D slides plus a presenter, not 3D**.
  - Metrics: Meta Similarity, PresentArena, PresentQuiz, IP Memory.
  - Generation time and cost are not stated on the abstract page.
- **Code2Video** (arXiv 2510.01174; NeurIPS 2025; ICML 2026 poster). [arXiv](https://arxiv.org/abs/2510.01174); [ICML 2026](https://icml.cc/virtual/2026/poster/65050)
  - A Planner, Coder and Critic generate **Manim code**, producing 2D (or Manim-3D) math and science animations.
  - Reports about 40% improvement over direct code generation, and videos "comparable to human-crafted tutorials."
- **TheoremExplainAgent** (arXiv 2502.19400). [arXiv](https://arxiv.org/abs/2502.19400); [project page](https://tiger-ai-lab.github.io/TheoremExplainAgent)
  - A planner plus a coding agent produce Manim videos.
  - TheoremExplainBench has 240 theorems across STEM fields and 5 automated metrics.
  - The o3-mini agent achieved a 93.8% success rate and an overall score of 0.77; most videos had minor layout issues.

### Inferences

#### Approximate cost per 5-minute lesson (derived from the cited figures; SaaS costs assume the full plan allowance is used)

| Option | Output | Basis | About per 5-min lesson | pt-BR | 3D |
|---|---|---|---|---|---|
| 3D medical studio | Custom 3D with scientific review | $5k–20k/min; mechanism of action from $20k/min | **$25k–100k+**; months of work | Via localization | Yes |
| 2D studio explainer | Custom 2D | $2k–5k/min | $10k–25k | Via localization | No |
| Synthesia Pro, annual | Avatar + slides | $59/month for about 60 min | About **$5** (about $1/min). Monthly Starter: about $1.6/min | pt-BR named | No; medical-treatment content may need Enterprise |
| HeyGen Creator | Avatar video | $29 for 600 credits at 3–48 credits/min | About **$0.7–7** ($0.15–1.5/min) | 175+ languages (Portuguese not named on the page) | No |
| Pictory | Stock footage + TTS + avatars | $29 for 30 min, up to $119 for 300 min | About **$2–5** ($0.4–1/min) | Not confirmed | No |
| Gemini Notebook Explainer | AI-illustrated narrated overview | Free, or AI Pro R$96.99/month | About **R$0 marginal** | **Yes** | No (Cinematic is English-only) |
| Libraries (Osmosis, Ninja Nerd, Visible Body, BioDigital) | Existing lessons and 3D atlases | $0–$249/year | Not applicable (not custom) | Mostly English | VB and BioDigital are interactive 3D |

#### The cheapest acceptable baseline
- **The Gemini Notebook Video Overview (Explainer, pt-BR)**, generated from the *same source pack* the pipeline uses, is the cheapest acceptable baseline:
  - zero marginal cost and minutes of effort,
  - pt-BR narration,
  - steerable, and from Google,
  - but 2D illustration-style, not editable frame by frame, with no 3D or quiz integration, and disclaimed as possibly inaccurate.
- If the self-built pipeline cannot clearly beat it in blind pairwise comparison and on quiz-based transfer (see Q3), the pipeline is not worth its complexity.
- For **3D anatomical accuracy**, a useful reference baseline is BioDigital (free Personal plan) or Visible Body Atlas ($24.99). Both are curated, interactive 3D but English-centric and not lesson generators. Use them to sanity-check the pipeline's 3D anatomy, not to produce content (licensing terms for reuse were not verified).
- For the **technical baseline** of a code-rendered pipeline, compare against open-source Code2Video and TheoremExplainAgent (Manim-based). Paper2Video is relevant for "paper to narrated slides plus presenter."
- **Implication**: a self-built pipeline costs orders of magnitude less than a studio ($25k–100k per lesson) and is comparable to the SaaS tools (dollars per lesson). Its value is not price but **3D/process animation that SaaS doesn't make, accuracy gating, and retrieval-practice integration**. Since the expected marginal cost is a few dollars or less, it needs to beat Gemini Notebook on quality, not price.
- **Avatars are where SaaS money goes, and they are the feature with the weakest learning evidence** (Q1). For the expert user, that is the part to drop.

### Gaps
- **Kodisc**: product, price and Portuguese support are unverified; the site was unreachable.
- **HeyGen**: credits-per-minute figures conflict, and Portuguese is not confirmed on the pricing page (it lists only language counts).
- **Pictory**: Portuguese support was not confirmed.
- **Gemini Notebook**: there is no per-day Video Overview number under the compute-based limits introduced in September 2026. Explainer length and whether the visuals are mostly static illustrations or animated were not documented on the help page.
- **Osmosis**: the official page returned 403, so prices come from snippets and aggregators.
- **Visible Body Suite**: billing period not confirmed.
- **BioDigital**: the support page was seen via search snippet only; the languages offered were not verified.
- **Nucleus**: no public pricing.
- **Portuguese libraries**: whether Osmosis, Visible Body or Nucleus offer Brazilian Portuguese content was not established; none was found.
- **Licensing for reuse**: reuse or screen-recording terms for Visible Body and BioDigital content in third-party videos were not checked.
- **Generative video APIs**: per-second prices for Veo or Sora (as 3D-looking B-roll) and TTS costs were not researched here; they are relevant to the build side.
- **Exchange rate**: no USD/BRL conversion is applied.

## Q3. Which risks require human review, and what checklist or evaluation should gate a lesson before it is delivered?

### Takeaway
Every medical or biological visual and every factual claim needs domain-expert review before anyone other than the expert owner sees the lesson:
- Generative image and video models still produce convincing but anatomically or procedurally wrong content: 80.8% of DALL·E 3 congenital-heart images were rated incorrect, and Veo-3 surgical clips looked plausible but failed on surgical logic.
- LLM text still hallucinates and omits: 1.47% and 3.45% of sentences in clinical-note generation.

For staff, patient or marketing use, Brazilian rules add hard constraints:
- **CFM Res. 2.336/2023**: identification requirements, and bans on unrecognized methods, guaranteed results, unregistered drugs or devices, and visual "seduction".
- **CFM Res. 2.454/2026**: AI transparency.
- **ANVISA RDC 96/2008, Art. 30**: mechanism-of-action illustrations must be "truthful, accurate, complete, and unbiased".
- **LGPD**: no patient data.
- **Copyright**: AI outputs are unlikely to be protectable, and third-party 3D assets carry licenses such as CC BY-SA.

Cheap automated gates can filter lessons before a human sees them, but cannot replace expert sign-off: pairwise VLM judging on frames, rubric scoring in the style of TheoremExplainBench, PresentQuiz/TeachQuiz-style probes, and synchronization and compliance lint.

### Cited Findings

#### Errors documented in AI-generated medical images, video and text
- **DALL·E 3, congenital heart disease** ("Art or Artifact…", *Journal of Medical Systems* 2024): 33 healthcare professionals rated the images. 80.8% were rated anatomically incorrect or fabricated, 85.2% had incorrect labels, and 78.1% were judged unusable for education. Complex anomalies were fabricated more often. [Record](https://nchr.elsevierpure.com/en/publications/art-or-artifact-evaluating-the-accuracy-appeal-and-educational-va/)
- **Noel** (*Anatomical Sciences Education*; skulls, heart, brain): no generator produced comprehensive anatomical detail. Errors included missing foramina and wrong coronary artery origins, although the tools were faster and cheaper than human illustrators. [BVS record](https://pesquisa.bvsalud.org/saudepublica/resource/pt/mdl-37694692)
- A comparative analysis of three text-to-image generators (ribs, brain, lungs) reported that none produced anatomically correct structures. [Eur J Anat](https://eurjanat.com/articles/a-comparative-analysis-to-assess-anatomical-illustrations-via-three-ai-driven-text-to-image-generators/)
- A craniofacial validity analysis of four models (*J Clin Med* 2025) found outputs more "artistic" than anatomically accurate. [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11989924/)
- **SurgVeo** (arXiv 2511.01775, November 2025): Veo-3 generated 8-second continuations of 50 real abdominal and brain surgery videos, rated by 4 board-certified surgeons on a 4-tier "Surgical Plausibility Pyramid". Veo-3 showed "exceptional visual perceptual plausibility" but failed the higher tiers (instrument operation, tissue feedback, surgical intent). [arXiv](https://arxiv.org/abs/2511.01775)
  - Press coverage reports abdominal scores of 1.78 for instrument handling, 1.64 for tissue response and 1.61 for surgical logic, with brain-surgery logic as low as 1.13 at 8 s. The scale was not verified. [The Decoder](https://the-decoder.com/googles-veo-3-can-fake-surgical-videos-but-misses-every-hint-of-medical-sense/)
- **MedGen** (arXiv 2507.05675): general video models (Sora, Pika, Hailuo) "frequently generate content with severe medical hallucinations": wrong anatomy, misused instruments, implausible clinical scenes. [arXiv](https://arxiv.org/html/2507.05675v1)
- A Canadian Medical Education Journal commentary argues Sora "cannot guarantee precise medical visuals" without professional validation. [CMEJ](https://journalhosting.ucalgary.ca/index.php/cmej/article/download/79065/57851/258885)
- **Text**: Asgari et al. 2025 (*npj Digital Medicine*) measured a **1.47% hallucination** and **3.45% omission** rate across 12,999 clinician-annotated sentences from 18 LLM configurations for clinical note generation. Refining prompts and workflows reduced major errors. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12075489/)
- Google's own help page states that Video Overviews "may contain inaccuracies." [Help](https://support.google.com/notebooklm/answer/16454555)

#### Copyright and licensing
- **Brazil**:
  - Lei 9.610/1998, art. 11: "autor é a pessoa física criadora de obra literária, artística ou científica." [Planalto](https://www.planalto.gov.br/ccivil_03/leis/l9610.htm)
  - The majority doctrinal reading is that purely AI-generated works have no copyright protection; the human-contribution threshold is unresolved. [Projuris](https://www.projuris.com.br/blog/direitos-autorais-inteligencia-artificial/); [Conjur, 2026-04-03](https://www.conjur.com.br/2026-abr-03/inteligencia-artificial-nao-pode-ser-titular-de-direitos-autorais//?print=1)
  - Copyright is one of the main bottlenecks for PL 2338/2023 in the Câmara. [Teletime, 2026-05-04](https://teletime.com.br/04/05/2026/parlamentares-tentam-retomar-cronograma-para-pl-de-ia/)
- **US**: the Supreme Court denied certiorari in *Thaler v. Perlmutter* (March 2, 2026), leaving the human-authorship requirement in place. The D.C. Circuit noted that AI-*assisted* works can be protected when a human is the author; how much human contribution is enough remains open (*Allen v. Perlmutter* is pending). [Mayer Brown](https://www.mayerbrown.com/en/insights/publications/2026/03/supreme-court-denies-review-in-ai-authorship-case)
- **Third-party 3D and molecular assets**:
  - **Z-Anatomy** is CC BY-SA 4.0 (share-alike), but its attributions include CC BY-NC-SA and CC BY-NC components. [GitHub](https://github.com/Z-Anatomy/Models-of-human-anatomy)
  - **BodyParts3D** licensing conflicts: CC BY-SA 2.1 Japan per Z-Anatomy credits, but the database README says CC BY 4.0. [README](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/README_e.html)
  - **PDB archive data are CC0 1.0**; attribution to structure authors is requested. [wwPDB](https://www.wwpdb.org/about/usage-policies)
  - RCSB molecular images are available under the same conditions as the data, and figures should cite the PDB ID, the structure paper and the graphics program. [RCSB policies](https://rcsb.org/pages/policies)

#### Brazilian rules if lessons go to patients, customers or marketing
- **CFM Res. 2.336/2023** (medical publicity): published 13/09/2023 and in force from 11/03/2024, replacing Res. 1.974/2011. [Legismap](https://legismap.com.br/conteudos/artigos-e-noticias/conselho-federal-de-medicina-atualiza-regras-para-a-publicidade-medica) Provisions from the official text ([CFM PDF](https://sistemas.cfm.org.br/normas/arquivos/resolucoes/BR/2023/2336_2023.pdf)):
  - **Art. 4**: publicity must carry the physician's name, CRM number with the word "MÉDICO", and the specialty with its **RQE**.
  - **Art. 10 §2**: in any exposition to lay audiences, the physician must **declare conflicts of interest**.
  - **Art. 11** prohibits:
    - III: publicizing equipment or drugs **without ANVISA registration**;
    - VII: publicizing a "método ou técnica não reconhecido pelo CFM";
    - XII: "garantir, prometer ou insinuar bons resultados";
    - XVI: sensationalist or self-promotional conduct, or "conteúdo inverídico".
  - **Art. 11 §2** defines sensationalism to include (b) publicizing a clinical or therapeutic approach not yet recognized by the CFM, and (f) "usar de forma abusiva, enganosa ou sedutora representações visuais… que induzam à percepção de garantia de resultados."
  - **Art. 13 I and III**: physicians have the right to publish educational and scientific content.
  - **Art. 14**: patient images may be used for educational purposes, but (e) not if they identify the patient, and (f) "é vedada qualquer edição, manipulação ou melhoramento das imagens."
- **Código de Ética Médica**:
  - Art. 113 forbids "Divulgar, fora do meio científico, processo de tratamento ou descoberta cujo valor ainda não esteja expressamente reconhecido cientificamente por órgão competente." This wording is from the 2009 code's chapter page; numbering in the current Res. 2.217/2018 was not verified. [CFM portal](https://portal.cfm.org.br/etica-medica/codigo-2010/codigo-de-etica-medica-res-1931-2009-capitulo-xiii-publicidade-medica/)
  - Art. 75 bars identifiable clinical cases or images in publicity even with the patient's authorization. [Migalhas](https://www.migalhas.com.br/coluna/migalhas-de-responsabilidade-civil/366566/publicidade-medica-em-redes-sociais-como-responsabilidade-civil)
- **CFM Res. 2.454/2026** (AI in medicine): approved 11 February 2026, published in the DOU 27 February 2026, in force 180 days later. [CFM news](https://portal.cfm.org.br/noticias/cfm-normatiza-uso-da-ia-na-medicina); [AMB guide](https://amb.org.br/wp-content/uploads/2026/04/cartilha-saude-digital_v1.pdf); [Mayer Brown](https://www.mayerbrown.com/pt/insights/publications/2026/03/brazilian-cfm-issues-resolution-on-the-use-of-artificial-intelligence-in-medicine)
  - Patients have the right to be informed "de forma clara e acessível" when AI is used.
  - Communication of diagnoses, prognoses or therapeutic decisions may not be delegated to AI.
  - The physician has the final word.
  - Data used must observe the LGPD.
  - AI systems are classified by risk (low, medium, high, unacceptable).
  - CRMs oversee compliance.
  - A collective lawsuit in the 21ª Vara Federal Cível do DF seeks suspension, and critics urge revision; current status unknown. [Futuro da Saúde](https://futurodasaude.com.br/acao-judicial-suspender-regras-cfm-inteligencia-artificial/); [Legismap, Aith](https://legismap.com.br/conteudos/artigos-e-noticias/resolucao-do-cfm-sobre-uso-da-ia-por-medicos-deve-ser-revogada-e-revisada)
- **ANVISA RDC 96/2008** (medicine advertising; official English translation). [ANVISA](https://www.gov.br/anvisa/en/rules-and-regulations/arquivos/rdc-96-2008-e.pdf)
  - Art. 3: advertising is allowed only for products regularized with ANVISA.
  - Art. 7: information must be scientifically proven.
  - Art. 8 forbids, among other things, suggesting diagnoses to the general public and showing images of people using the product.
  - **Art. 27 and 29**: prescription-drug advertising is restricted to channels for professionals authorized to prescribe or dispense; online, it must sit behind registration with a disclaimer.
  - **Art. 30 §2–3**: graphs and **illustrations of mechanisms of action** must accurately reflect the truth with a complete bibliographic reference, must be "truthful, accurate, complete, and unbiased," and must not mislead "through visual impact."
  - **Status**: ANVISA opened a review of RDC 96/2008 on 5 August 2026. [Agência Gov](https://agenciagov.ebc.com.br/noticias/202608/anvisa-aprova-abertura-de-processo-para-revisar-normas-da-propaganda-de-alimentos-e-de-medicamentos) ADI 7.788 challenging it is pending at the STF. [Souto Correa](https://www.soutocorrea.com.br/en/artigos/anvisa-decides-to-initiate-administrative-proceedings-to-review-rules-on-food-and-medicine-advertising/) In 2024 the STJ held provisions contrary to Lei 9.294/1996 to be illegal, limiting how the rule can be applied. [Conjur](https://www.conjur.com.br/2024-ago-14/nao-cabe-a-anvisa-restringir-propaganda-de-medicamentos-decide-stj//?print=1)
- **LGPD (Lei 13.709/2018)**: [Planalto](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
  - Health data are *dado pessoal sensível* (art. 5, II).
  - Processing sensitive data requires the specific legal bases of art. 11.
  - Anonymized data are not personal data unless the anonymization can be reversed (art. 12).
- **PL 2338/2023** (AI bill): passed by the Senate and sent to the Câmara on 17/03/2025. [Senado](https://www25.senado.leg.br/web/atividade/materias/-/materia/157233) A special committee was installed in May 2025, with Aguinaldo Ribeiro as rapporteur. By March to May 2026 a vote was considered unlikely before the elections. [Teletime, 2026-03-25](https://teletime.com.br/25/03/2026/votacao-do-pl-de-ia-antes-das-eleicoes-e-improvavel/) No report or vote was found as of November 2026.

#### Platform terms
- **YouTube, altered or synthetic content**: [YouTube Help](https://support.google.com/youtube/answer/14328491)
  - Disclosure is required for *realistic* AI content, such as real people appearing to say or do things they didn't, or realistic scenes that never happened.
  - It is **not required** for animation or clearly unrealistic content, minor aesthetic edits, or production help such as AI-drafted scripts.
  - Persistent non-disclosure can lead to labels being applied manually, content removal, or suspension from the YouTube Partner Program.
- **YouTube Medical Misinformation Policy**: prohibits prevention or treatment content that contradicts local health-authority guidance. Educational, documentary, scientific or artistic exceptions require added context and are "not a pass to promote misinformation." [YouTube Help](https://support.google.com/youtube/answer/13813322)
- **Google Generative AI Prohibited Use Policy** (last modified 17 December 2024; it applies to Gemini Notebook outputs) prohibits: [Google policy](https://policies.google.com/terms/generative-ai/use-policy)
  - 1.6: violating intellectual-property or privacy rights;
  - 1.8: automated decisions in high-risk domains, including healthcare, without human supervision;
  - 4.3: misleading claims of expertise in sensitive areas such as health, made to deceive;
  - 4.5: misrepresenting provenance, i.e. claiming AI content is human-made, to deceive.
- **Synthesia** medical-content rules are covered under Q2.

#### Automatic and cheap evaluation methods (from AI-video research)
- **TheoremExplainBench**:
  - Five automated dimensions: accuracy and depth, visual relevance, logical flow, element layout, visual consistency. The overall score is typically a geometric mean.
  - The paper notes that most generated videos have **minor layout issues**.
  - Manimator scored 0.845 on it, against 0.79 and 0.77 for the baselines.

  [Project page](https://tiger-ai-lab.github.io/TheoremExplainAgent); [arXiv](https://arxiv.org/abs/2502.19400); [Manimator](https://arxiv.org/pdf/2507.14306)
- **Code2Video**:
  - The Critic uses a vision-language model with "visual anchor prompts" to fix layout.
  - Evaluation combines VLM-as-judge aesthetics, code efficiency and **TeachQuiz**: a model is made to "unlearn" the target knowledge, then watches the video and retakes the quiz; the score is the knowledge recovered. [arXiv](https://arxiv.org/abs/2510.01174)
  - Secondary summaries report that with Claude Opus 4.1, aesthetics improved about 50% and TeachQuiz about 46% over direct code generation. Pixel-based video generators scored near zero on logic and layout and failed TeachQuiz. MMMC has 456 Manim tutorials across 13 subjects. [Emergent Mind](https://www.emergentmind.com/papers/2510.01174)
- **Paper2Video**: four metrics.
  - *Meta Similarity*: VLM comparison of generated vs human slides and subtitles, plus speaker-embedding similarity.
  - *PresentArena*: pairwise preference.
  - *PresentQuiz*: video LLMs answer multiple-choice questions derived from the paper after watching.
  - *IP Memory*.

  [arXiv](https://arxiv.org/abs/2510.05096) A secondary summary reports PaperTalker beat the human-made videos by about 10% on PresentQuiz. [Emergent Mind](https://www.emergentmind.com/papers/2510.05096)
- **How reliable VLM judges are** (MLLM-as-a-Judge, ICML 2024): multimodal LLMs align well with humans in **pairwise comparison** but diverge significantly in **absolute scoring and batch ranking**. They also show egocentric, position and verbosity biases and instability across runs. Chain-of-thought and vision-expert components mitigate some of this. [arXiv](https://arxiv.org/abs/2402.04788)
- **Patient-facing rubric: PEMAT-A/V** (AHRQ): 13 understandability and 4 actionability items, scored agree/disagree and reported as percentages. It was designed for professionals to apply, and it **does not assess accuracy**. [AHRQ PEMAT](https://www.ahrq.gov/health-literacy/patient-education/pemat.html); [PEMAT guide](https://ogg.osu.edu/media/documents/fd4me/pemat_guide.pdf)

### Inferences

#### Review intensity by audience tier

| Tier | Audience | Human review | Extra gates |
|---|---|---|---|
| A | The user only (expert, personal learning) | Owner watches each lesson (1.5× speed acceptable) with a flag button, plus a deeper audit of about 1 in 5 lessons, or of all lessons with medical-mechanism content | Automated gates 1–4 below |
| B | Hospital staff (internal training) | **100% sign-off by a subject-matter expert** before release; versioned, with reviewer, date and sources logged | AI-use disclosure; no patient data; dated source list; re-review whenever sources change |
| C | Patients, startup customers, public, marketing | **100% expert sign-off plus regulatory/legal review** | CFM 2.336 checks (identification, conflict-of-interest disclosure, no unrecognized methods, no guaranteed results, no unregistered drugs or devices, no "seductive" visuals); RDC 96 Art. 27–30 if a drug is mentioned (no prescription-drug promotion to lay audiences; mechanism-of-action visuals referenced and unbiased); CFM 2.454 transparency; PEMAT-A/V scoring; platform disclosure; licensing audit |

#### Automated gates (cheap; run before any human sees the lesson)
1. **Script fact gate**:
   - Extract the claims and link each factual sentence to a source passage; reject unsupported sentences.
   - Check numbers, units and dosing; prefer no doses at all.
   - Flag phrases forbidden for Tier C, such as "cura", "garantido" or "100%", and any brand names of prescription drugs.
   - Scan for personal or health data; use synthetic EHR examples only.
2. **Storyboard lint**: duration ≤6 minutes; chunks ≤60 s; one moving focus per shot; a word cap for on-screen text; a "3D justified" flag (Q1 rules); no music or B-roll; pre-training, recap and quiz present; consistent color tokens.
3. **Render QA with a VLM judge on keyframes** (scene boundaries plus every few seconds):
   - Score a TheoremExplainBench-style rubric plus domain checks: labels match narration, orientation and left/right, overlapping or occluded labels, legibility.
   - Use **pairwise** judging (new version vs previous, and vs the Gemini Notebook baseline), not absolute scores.
   - Check synchronization automatically from TTS word timestamps against animation event times (temporal contiguity).
4. **Knowledge-transfer probe**, in the style of PresentQuiz or TeachQuiz:
   - Generate 8–10 multiple-choice items from the **sources**, not from the script, and tag the critical facts.
   - Have a VLM answer from the frames plus transcript, and again without the video.
   - Require a gain over the no-video condition and 100% on critical-fact items.
   - This measures whether information is present, not human learning, so the thresholds need calibration against human quiz results.

#### Human subject-matter-expert checklist (about 10 minutes per lesson)
1. Every claim is traceable and no stronger than its source; uncertainty is stated.
2. Anatomy and structures are correct: orientation, left/right, proportions, counts, connections, and labels.
3. Molecular content: correct target and binding site. Simplifications are declared as schematic, and PDB IDs are shown.
4. The order and causality of steps are correct, with no impossible intermediate states.
5. Numbers, units and scale bars are correct, with no invented statistics.
6. Drug or device regulatory status and off-label use are flagged; nothing is promotional for lay audiences.
7. AI and technical content matches the cited papers; metaphors are labeled as metaphors.
8. No identifiable patient data.
9. Asset licenses are respected: attribution rendered, and share-alike or non-commercial obligations reviewed.
10. Disclosure: AI-generated narration and visuals are disclosed; CRM/RQE and conflicts of interest appear where the lesson counts as publicity.
11. The pedagogy checklist (Q1 template) is met.
12. Accessibility: subtitles available, colorblind-safe palette.

#### Further inferences
- **Highest-risk visual modality**: photoreal generative video (Veo or Sora style) for mechanisms or procedures. It should be **excluded** from mechanism segments. Code-rendered or curated-asset 3D (Manim, Blender or three.js driven by structured specifications, or PDB structures) is auditable and repeatable, which suits review.
- **Copyright posture**: treat AI-generated visuals and narration as probably not protectable. Protectable value comes from human-authored scripts, storyboards, and the selection and arrangement of material. Keep provenance logs (sources, prompts, model versions, reviewers). Share-alike 3D sources (Z-Anatomy, possibly BodyParts3D) may force share-alike terms on derived assets, so get legal review before any commercial (Tier C) use.
- **Third-party AI tools** (Gemini Notebook, Synthesia and others): never upload real patient documents to them. Doing so would require an LGPD legal basis and contracts, and the Google policy prohibits unsupervised automated healthcare decisions.

### Gaps
- **Gate thresholds**: no validated thresholds link VLM-judge scores or TeachQuiz/PresentQuiz gains to human learning or to expert-rated accuracy in medical content. These would need local calibration with a small human-rated set.
- **Accuracy of code-rendered 3D**: no study was found on the accuracy of procedurally generated (code-rendered) scientific 3D animations compared with generative video.
- **Cost of the automated gates**: the per-lesson cost of running them was not estimated, because it depends on model choice and pricing.
- **Vendor output ownership**: the ownership terms in Google's, HeyGen's and Synthesia's terms of service were not reviewed.
- **CFM Res. 2.454/2026**: the full text was not read (only the CFM news item and secondary sources), and the status of the lawsuit is unknown.
- **CEM numbering**: articles 75 and 113 come from secondary or 2009-code pages; the numbering in Res. 2.217/2018 was not verified.
- **Publicity status of internal training**: whether staff-training videos count as "publicidade médica" under CFM 2.336 is unclear.
- **ANVISA medical-device rules**: whether a patient-facing personalized lesson module could fall under ANVISA's software-as-a-medical-device rules was not researched.
- **YouTube avatars**: whether a photoreal AI avatar presenter counts as "realistic" content needing disclosure is not explicit in YouTube's page.
- **PL 2338/2023**: the final status as of November 2026 was not confirmed.
