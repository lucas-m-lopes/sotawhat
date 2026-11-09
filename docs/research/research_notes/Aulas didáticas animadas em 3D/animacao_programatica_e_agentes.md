# Programmatic animation written by LLM agents (Manim, Blender/bpy, Three.js/R3F + Remotion and others), agentic educational-video systems, ZDR models on OpenRouter, and interactive 3D lessons: state as of 2026-11-09

These notes cover the "LLM writes code → deterministic renderer → MP4 or web page" route for sotawhat's auto-generated pt-BR lessons. Target hardware: RTX 4060 8 GB, Ryzen 5 5500, 32 GB RAM, Windows 11, Python 3.12. Sibling notes in this folder cover other parts of the problem: 3D assets and the PDB/CT pipelines (`ativos_e_geracao_3d.md`), narration, TTS, subtitles and Telegram delivery (`narracao_avatar_audio.md`), and generative video (`video_generativo.md`). These notes do not repeat that material.

Conventions:
- **Access date:** every URL was accessed on 2026-11-09 unless another date is given.
- **OpenRouter prices** come from direct API reads on 2026-11-09 at about 18:44 UTC: `GET https://openrouter.ai/api/v1/models` (462 models) and `GET https://openrouter.ai/api/v1/endpoints/zdr` (1,107 ZDR endpoints). Prices are USD per 1M tokens, input/output. They extend, and do not replace, the project's earlier notes: [llm_openrouter.md (2026-11-07)](../../2026-11-07-insight-engine/llm_openrouter.md). That file was not edited; section 3 lists what changed since then.
- **"Eligible" ZDR endpoint** follows the project policy from the 11-07 notes: the endpoint appears in `/endpoints/zdr`, its quantization is not fp4/mxfp4/nvfp4/int4, and (unless noted) it supports `structured_outputs`.
- **[local measurement]** marks a benchmark I ran on this machine on 2026-11-09. The scripts were in the session scratchpad and are described inline so they can be reproduced.
- **(secondary)** marks a blog, aggregator or vendor-comparison source rather than a primary one.
- **GitHub metadata** (license, stars, last push, latest release) was read from `api.github.com/repos/{owner}/{repo}` on 2026-11-09 and is cited by repository URL.

---

## Key Question 1: Which framework gives the best accuracy, aesthetics and cost when the code is LLM-generated, for AI and medical topics? (Manim 3D, Blender, Three.js/R3F + Remotion, or a combination; covers objective a)

### Takeaway
No single renderer wins. The evidence points to a hybrid:
- **Manim CE** for formula- and diagram-heavy explanations. It renders 2D faster than real time on this CPU, and its OpenGL renderer makes simple 3D practical.
- **Three.js/R3F** for spatial 3D: anatomy, CT gantry and volume, molecules, a "walk through the transformer". The same scene serves as the interactive web lesson and, via headless-Chromium frame capture (Remotion or a custom Puppeteer stepper), as the MP4.
- **Blender** only offline, to build or clean hero assets exported to glTF. Per-lesson EEVEE rendering costs hours of GPU time, and LLM agents are least reliable at bpy.

### Cited Findings

**Manim Community Edition (CE)**
- Latest release v0.22.1, published 2026-10-27. MIT license, ~42.4k stars, last push 2026-11-09 ([GitHub](https://github.com/ManimCommunity/manim); [changelog](https://docs.manim.community/en/stable/changelog/0.22.1-changelog.html)). The release list shows v0.20.0 → v0.20.1 → v0.21.0 → v0.22.0 → v0.22.1 ([changelog index](https://docs.manim.community/en/stable/changelog.html)).
- The v0.22.1 notes are bug-fix level: a fix for `OpenGLImageMobject` rendering, a fix for `ImageMobject` with Pillow 13, and a TinyTeX CI cache change. They say nothing about OpenGL-renderer status, ThreeDScene or Windows ([0.22.1 changelog](https://docs.manim.community/en/stable/changelog/0.22.1-changelog.html)).
- The 0.22.1 CLI still offers `--renderer [cairo|opengl]`. Output is set with `--format [auto|none|png|png-sequence|gif|mp4|webm|mov]`, and the old `--write_to_movie` flag is gone. [local measurement: `manim render --help`, 0.22.1]
- **Windows install:** `uv run --no-project --python 3.12 --with manim==0.22.1` resolved and installed 33 packages in **~15 s** on this machine (wheels including `av`, `manimpango`, `skia-pathops`, `pyglm`). Text-only and 3D scenes rendered to MP4 with **no system FFmpeg and no LaTeX installed**. `MathTex`/`Tex` still need a TeX distribution, and none is installed here, so that path was not tested. [local measurement]
- **3D:** `ThreeDScene` with `ThreeDAxes`, a 24×24 `Surface` and 6 `Cube`s, rotated with an ambient camera, rendered **~5× faster with `--renderer=opengl`** (12.3 s) than with the default Cairo renderer (60.9 s) at 1080p30. Both runs produced valid MP4s. Section 5 has the numbers. [local measurement]
- **LLM reliability problems specific to Manim:**
  - ManiBench (arXiv 2603.13251, Feb 2026) targets two failure modes. The first is "syntactic hallucinations": valid Python that calls nonexistent or deprecated Manim APIs. The second is "visual-logic drift". The benchmark notes that LLMs mix ManimGL and ManimCE APIs ([arXiv](https://arxiv.org/abs/2603.13251)).
  - Its prompt guide documents **145 ManimGL→ManimCE incompatibilities** across the pilot problems ([HF guide](https://huggingface.co/datasets/nabin2004/ManiBench/blob/main/ManiBench_Prompt_Engineering_Guide.md)).
  - TheoremExplainAgent's error analysis ranks the failures as: (1) Manim code hallucinations, (2) LaTeX rendering errors, (3) general coding errors ([arXiv 2502.19400v2](https://arxiv.org/html/2502.19400v2)).
  - Code2Video pins **Manim CE v0.19.0** ([GitHub](https://github.com/showlab/Code2Video)). Version pinning is standard practice in these systems.

**ManimGL (3b1b/manim)**
- MIT license, ~96.3k stars. The last tagged release is **v1.7.2 (2024-12-13)**, although the repo was pushed on 2026-09-09 ([GitHub](https://github.com/3b1b/manim)).
- ManiBench grounds its problems in 3Blue1Brown's ManimGL source (about 53,000 lines and 143 scene classes). It describes ManimCE as the actively maintained implementation with a modern API, and says ManimGL contains deprecated constructs ([arXiv](https://arxiv.org/abs/2603.13251)).

**Blender scripted via Python (bpy)**
- **Blender 5.2 LTS** was released 2026-07-14 and is supported until July 2028. It adds experimental cloth/hair physics in Geometry Nodes, online asset libraries, EEVEE cleanup (screen-space and Fast GI changes can alter existing scenes) and a Python API change to Geometry Nodes modifier properties ([Phoronix](https://www.phoronix.com/news/Blender-5.2-Released); [GameFromScratch](https://gamefromscratch.com/blender-5-2-lts-released/); [gamineai](https://gamineai.com/blog/blender-5-2-lts-what-indies-should-lock-before-upgrading-game-assets-2026) (secondary)).
- **Blender 5.1** (2026-03-17) changed EEVEE in three ways: materials compile faster through parallel precompilation of GPU pipelines, texture memory falls by 30–40%, and a new Raycast node is available for EEVEE and Cycles ([linuxiac](https://linuxiac.com/blender-5-1-3d-creation-software-released/); [BlenderNation](https://www.blendernation.com/2026/04/02/new-blender-5-1-eevee-feature-gi-intensity/)).
- **Official Blender Lab MCP server**, version 1.0.3:
  - It needs Blender 5.1 or newer, and it "will execute LLM generated code in Blender without any guards in place."
  - Its stated scope is "improving access to documentation" and "allowing users to explore and understand complex setups."
  - The page documents no headless mode ([blender.org/lab/mcp-server](https://www.blender.org/lab/mcp-server/)).
  - A vendor comparison dates it v0.1.0 on 2026-03-24 and v1.0.0 on 2026-04-27. The same source says it shipped as Anthropic's official Blender connector on 2026-04-28 ([StraySpark](https://www.strayspark.studio/blog/official-blender-mcp-server-comparison-2026) (secondary, vendor)).
- **Community "MCP for Blender"** (ahujasid, formerly `blender-mcp`, renamed in September 2026): MIT license, ~33.8k stars, pushed 2026-11-04. Its description reads "Not affiliated with the official Blender Foundation" ([GitHub](https://github.com/ahujasid/mcp-for-blender)).
- **Evidence on how well LLMs write bpy:**
  - LL3M (Univ. of Chicago, Aug 2025) uses six agents on Blender 4.4. Its BlenderRAG raised complex operations per script to 5.86 from 1.20 and cut errors by 26% (2.43 vs 3.29). Even so, "VLMs may still struggle to accurately identify spatial artifacts", and without RAG the coder "sometimes removes buggy lines rather than fixing them" ([arXiv 2508.08228v1](https://arxiv.org/html/2508.08228v1)).
  - In an earned-autonomy Blender scene task with output-only (visual) feedback, a coding agent reached **0% full-scene success**. Injecting minimal code-level knowledge restored convergence ([arXiv 2603.26942](https://arxiv.org/abs/2603.26942)).
  - BlenderGym (CVPR 2025): "even the state-of-the-art VLM system struggles with tasks relatively easy for human Blender users" ([arXiv 2504.01786](https://arxiv.org/abs/2504.01786)).
- **EEVEE vs Cycles on an RTX 4060:**
  - One 250-frame 1080p EEVEE animation took ~9 min 31 s, about **2.3 s/frame** ([DatabaseMart](https://www.databasemart.com/blog/blender-gpu-cpu-benchmark-rtx4060-e5-2667v3)).
  - A 250-frame 1080p Cycles job at 128 samples took ~68 min, about **16 s/frame**. This comes from an RTX 5060 review, so it is lower confidence ([Evetech](https://evezone.evetech.co.za/performance-pulse/rtx-5060-blender-performance-benchmark-real-world-test-2026) (secondary)).
  - A render-farm guide gives typical 1080p frame times of 5–60 s for EEVEE and 2–30 min for Cycles, without stating hardware ([SuperRenders](https://superrendersfarm.com/de/article/eevee-vs-cycles-cloud-render-farm-comparison-2026) (secondary)).

**Three.js / React Three Fiber**
- three.js latest release **r187 (2026-10-30)**, MIT, ~117.9k stars ([GitHub](https://github.com/mrdoob/three.js)). React Three Fiber latest release **v9.8.2 (2026-10-15)**, MIT, ~33.6k stars ([GitHub](https://github.com/pmndrs/react-three-fiber)).
- **AA-3D benchmark** (Artificial Analysis, launched 2026-10-12) tests LLM agents writing three.js:
  - Each model, running as an agent in an offline sandbox, turns a brief into an interactive three.js `index.html`. The sandbox includes **Blender, Rapier physics, Python, a headless browser and a CC0 asset library**. The agent writes code, renders, reviews its own screenshots and revises.
  - Runs are capped at 3 h or 250 turns. Ranking uses more than 10K blind pairwise human votes (Elo). Example briefs include "Inside the mitochondrion" and "Coral reef dive".
  - "Every model's median frame takes under 1.3 ms of GPU time" ([AA article](https://artificialanalysis.ai/articles/aa-3d)).
  - Model scores are in Key Question 3.
- **WorldCoder-Bench** (June 2026; 2,026 tasks, each a single self-contained HTML file): the best of nine frontier models reached only **27.8%** verification coverage on WorldCoder-Core and **19.9%** on WorldCoder-Robust ([Emergent Mind summary](https://www.emergentmind.com/papers/2606.01869) (secondary)).
- **WorldBench** (Three.js voxel worlds): code-based and visual evaluation "disagree on 32% of required items" ([GameDev.net](https://gamedev.net/news/6322-worldbench-evaluating-llms-on-threejs-voxel-world-generation/) (secondary)).

**Remotion (and @remotion/three)**
- Latest release **v4.0.542 (2026-11-09)**, ~72k stars. GitHub reports the license as NOASSERTION, meaning a custom, non-OSI license ([GitHub](https://github.com/remotion-dev/remotion)).
- **License text:** a Free License covers "an individual," "a for-profit organization with up to 3 employees," "a non-profit or not-for-profit organization," or anyone "evaluating whether Remotion is a good fit, and are not yet using it in a commercial way". Everyone else needs a Company License. The text adds: "In Remotion 5.0, the license will slightly change" ([LICENSE.md](https://cdn.jsdelivr.net/npm/remotion/LICENSE.md)).
- **Company pricing:**
  - "Remotion for Creators": **$25/mo per seat**.
  - "Remotion for Automators": **$0.01 per render, $100/mo minimum**, for building video-creation tools.
  - Enterprise: "Starting at $500 per month" ([remotion.pro/license](https://www.remotion.pro/license)).
  - Third-party pages quote other figures (for example "$100/month" or tiered annual prices), so they are not reliable ([wireflow](https://www.wireflow.ai/blog/remotion-pricing) (secondary)).
- **@remotion/three:**
  - `<ThreeCanvas/>` lets R3F scenes use `useCurrentFrame()`. "Animations are now not inside a `useFrame()` hook, but directly rendered into the markup."
  - There is also `<ThreeWebGPUCanvas/>`, which uses `WebGPURenderer` and TSL.
  - Rendering needs the ANGLE GL backend, because "Three.JS does not render with the default OpenGL renderer". Set it with `Config.setChromiumOpenGlRenderer('angle')` or `chromiumOptions: { gl: "angle" }` in `renderMedia()` ([docs](https://www.remotion.dev/docs/three)).
- **Remotion performance guidance:**
  - WebGL and GPU-accelerated CSS use the GPU, and "Compute instances in the cloud do not have a GPU."
  - Tune `--concurrency` with `npx remotion benchmark`.
  - PNG frames are slower than JPEG, and VP8/VP9 encoding is "very slow" ([docs](https://www.remotion.dev/docs/performance)).

**Motion Canvas / Revideo**
- **Motion Canvas:** MIT, ~19.7k stars. Latest release **v3.17.2 (2024-12-14)**, last push 2026-07-02 ([GitHub](https://github.com/motion-canvas/motion-canvas)). It is 2D, and per Revideo's README rendering requires a button press in the editor UI ([Revideo README](https://cdn.jsdelivr.net/gh/midrender/revideo@main/README.md)).
- **Revideo:** the repo moved to `midrender/revideo`. MIT, ~4.2k stars, last push 2026-07-15 ([GitHub](https://github.com/midrender/revideo)). It is a Motion Canvas fork with a headless render API. One comparison says it folded into the commercial Midrender editor ([wireflow](https://www.wireflow.ai/blog/best-remotion-alternatives-in-2026) (secondary, unconfirmed)).

**Theatre.js**
- The core is Apache-2.0 and the studio editor (`@theatre/studio`) is AGPL-3.0. The studio is used only during design ([GitHub](https://github.com/theatre-js/theatre)).
- The public repo's last push was **2024-08-14**. Its README says development "temporarily moved to a private repo" ([GitHub](https://github.com/theatre-js/theatre)). I found no 2026 release.

**Babylon.js**
- Apache-2.0, ~26.3k stars. Latest release **9.35.0 (2026-11-06)**, actively pushed ([GitHub](https://github.com/BabylonJS/Babylon.js)).

**Godot**
- MIT, ~119.9k stars. Latest stable **4.7.2 (2026-08-18)** ([GitHub](https://github.com/godotengine/godot)).
- **Movie Maker mode** records non-real-time video with "*always* … perfect frame pacing." On faster hardware "the visual output remains identical."
  - Command line: `godot --path … --write-movie output.avi --fixed-fps 30`.
  - Output formats: OGV (recommended, editor builds only), AVI with MJPEG (4 GB cap), or a PNG sequence plus WAV ([docs](https://docs.godotengine.org/en/stable/tutorials/animation/creating_movies.html)).

**What practitioners chose in a large open competition**
- Teaching Monster Challenge (NTU, Mar–Jun 2026; 77 teams in the Preliminary round; 30-min generation budget per video):
  - "Manim … was the most common animation engine (4 of the top 10 respondents)."
  - HTML/CSS was the most common slide format.
  - "Generated images are unreliable for factual diagrams", so some teams used matplotlib.
  - "One-shot Manim code often fails", and splitting storyboard from code generation raised rendering success ([arXiv 2608.08852v1](https://arxiv.org/html/2608.08852v1)).
- Code2Video (ICML 2026) on its MMMC benchmark (topics from 3Blue1Brown):
  - Pixel-based **Veo3: aesthetics 9.0, TeachQuiz 2.5**.
  - **Code2Video (Claude Opus 4.1): 87.9 and 86.0**.
  - Human-made 3B1B videos: 99.7 and 97.1 ([arXiv 2510.01174v1](https://arxiv.org/html/2510.01174v1)).

### Inferences
- **Comparison table** (my synthesis of the findings above; the "LLM reliability" column is a judgment):

| Framework | Status 2026-11-09 | License | 3D capability | LLM reliability when writing it | Render speed (this PC) | Exports |
|---|---|---|---|---|---|---|
| Manim CE 0.22.1 | Active, monthly-ish releases | MIT | `ThreeDScene` works. Cairo is slow for 3D; OpenGL is ~5× faster but less exercised | Medium–high **if** version-pinned, given a CE-only cheat-sheet and templates. Top failures are API hallucination and LaTeX | 2D ≈ 0.8× real time; 3D Cairo ≈ 10×; 3D OpenGL ≈ 2× (section 5) | MP4/WebM/MOV/GIF/PNG. No interactive web output |
| ManimGL 1.7.2 | Last release Dec 2024 | MIT | Better native OpenGL 3D | Low–medium. LLMs mix it with CE, and docs are thin | Fast (OpenGL) | MP4, plus a live preview window |
| Blender 5.2 LTS (bpy) | Very active; LTS until 2028 | Not verified here (GPL family; check blender.org) | Best: physics, Geometry Nodes, materials | Lowest of the options: large API with yearly changes, and output-only feedback fails (0% in 2603.26942). RAG helps | EEVEE ≈ 2.3 s/frame example ⇒ hours per 5 min; Cycles ≈ 10× slower | MP4/PNG sequence, glTF export for the web |
| Three.js r187 + R3F 9.8 | Very active | MIT | Full real-time PBR, WebGPU, physics via Rapier | High. Agents produce competent scenes (AA-3D); the main risks are empty or sparse scenes and broken pages | 338–409 fps live; **≈ 10.8 fps** frame-stepped headless capture at 1080p (≈ 14 min per 5-min lesson; section 5) | **Interactive web page** + MP4 via capture |
| Remotion 4.0 (+ @remotion/three) | Very active | Source-available; free for individuals and companies with ≤3 people | Via R3F (`ThreeCanvas`) | High (React/TS; deterministic `useCurrentFrame`) | Headless Chrome screenshots + FFmpeg; needs `gl=angle` for WebGL | MP4/WebM, plus an embeddable web player |
| Motion Canvas 3.17 / Revideo | Slow (no MC release since Dec 2024); Revideo stalled since Jul 2026 | MIT | 2D only | Medium, but less training data | n/a | MP4 (Revideo headless) |
| Theatre.js | Public repo dormant since Aug 2024 | Apache-2.0 core / AGPL studio | Animation sequencer for three.js | Low | n/a | Web |
| Babylon.js 9.35 | Active | Apache-2.0 | Full engine | Medium (less common than three.js in training data) | Real time | Web; capture needed for video |
| Godot 4.7 | Active | MIT | Full engine | Low–medium (GDScript, scene files) | Deterministic Movie Maker; scene-dependent speed | OGV/AVI/PNG; desktop or web export |

- **Recommended combination for sotawhat:**
  1. **Manim CE (pinned 0.22.1)** for math and diagram scenes: attention matrices, softmax, noise schedules, loss curves, sinogram/back-projection math, and an EHR→discharge-summary token flow as 2D diagrams. Use the OpenGL renderer for its few 3D shots.
  2. **Three.js/R3F** for 3D process scenes: CT gantry and reconstruction volume, organ segmentation, molecular mechanisms, a 3D "inside the transformer" walkthrough. These scenes are delivered both as the interactive lesson and as MP4 via capture.
  3. **Blender only for asset prep:** build or clean meshes and export to glTF. The asset pipelines are in `ativos_e_geracao_3d.md`.
  - This split matches what agents do best (JS/Python, not bpy). It keeps render times to minutes, and it reuses one 3D scene for two outputs.
- **Remotion vs a custom Puppeteer stepper:** for one person running a personal tool, Remotion is free. If the pipeline becomes part of a startup with 4 or more people, it needs a Company License ($25/seat-month as a creator, or the $100/month automator minimum). A ~100-line Puppeteer frame-stepper with FFmpeg (MIT/LGPL stack) avoids the license, at the cost of Remotion's audio and composition tooling.
- **Medical accuracy argument:** the strongest case for deterministic renderers is correctness. Labels, geometry and numeric content are exact in code. Pixel generators score near zero on teaching quizzes (Veo3 TeachQuiz 2.5 vs 86.0 for Code2Video), and competition teams avoided generated images for factual diagrams.

### Gaps
- No official statement of the Manim CE OpenGL renderer's support status ("experimental" or not) appears in the 0.22.x release notes. My test shows that it works for a simple 3D scene, not that it has feature parity with Cairo (for example `Text`/`MathTex` behavior or every mobject type).
- No measured EEVEE time on this exact PC: Blender is not installed. The 2.3 s/frame figure is for an unspecified scene.
- No head-to-head study compares LLM success rates across Manim, three.js and bpy on the same lesson briefs. The reliability ranking is inferred from separate benchmarks.
- Blender's license and the Remotion 5.0 license changes were not verified. The LICENSE file only links to a PR.

---

## Key Question 2: What success rates and costs do the agentic systems report, and which design choices matter most? (covers objective b)

### Takeaway
- Modern pipelines reach **85–99% final render success** per scene with a planner → coder → render → repair loop. The VLM critic mostly improves layout.
- Reported costs are low:
  - **$0.10–$4.67 per ~5-min video** with 2025 models (TheoremExplainAgent).
  - **20K–75K tokens per topic or scene** (Code2Video, OmniManim, ManimAgent).
- What matters most, in order:
  1. Separating planning/storyboard from coding.
  2. Explicit layout control: anchor grid, learned bounding boxes, or deterministic geometry checks.
  3. Scoped repair driven by renderer errors plus API docs.
  4. Memory of past successes and failures.
- A VLM critic used alone is the weakest link: it correlates poorly with humans and introduces regressions.

### Cited Findings

**TheoremExplainAgent** (TIGER-Lab / Waterloo, Feb 2025; ACL 2025 oral; MIT; ~1.5k stars; last push 2025-07-27)
- **Architecture** ([arXiv 2502.19400v2](https://arxiv.org/html/2502.19400v2); [GitHub](https://github.com/TIGER-AI-Lab/TheoremExplainAgent)):
  - A planner turns a scene plan into per-scene visual elements, animations and transitions.
  - A coding agent writes Manim code per scene, and TTS produces the voice-over.
  - Error-fix loop of **up to N = 5 attempts**.
  - Agentic RAG over the Manim docs (relevance threshold 0.5, k = 2).
  - **No VLM in the loop.** VLMs are used only for evaluation.
- **Benchmark (TheoremExplainBench):** 240 theorems (CS, chemistry, math, physics; 80 each at easy, medium and hard). Videos run about 5 min, versus about 20 s without the agentic approach.
- **Success rate** (videos rendered) / overall score:

| Agent | Success rate | Overall score |
|---|---|---|
| GPT-4o | 55.0% | 0.78 |
| GPT-4o + RAG | 45.8% | 0.76 |
| Claude 3.5 Sonnet | 2.1% | 0.79 |
| Claude 3.5 Sonnet + RAG | 14.6% | 0.71 |
| Gemini 2.0 Flash | 14.6% | 0.76 |
| Gemini 2.0 Flash + RAG | 20.4% | 0.76 |
| **o3-mini (medium)** | **93.8%** | 0.77 |
| o3-mini (medium) + RAG | 82.1% | 0.76 |

- **Cost and time per video:**

| Agent | Cost | Time | Notes |
|---|---|---|---|
| Gemini 2.0 Flash | **$0.10** | 1,120 s | |
| o3-mini | **$1.16** | 1,680 s | **434K input + 154K output tokens** |
| GPT-4o | $1.71 | | |
| Claude 3.5 Sonnet + RAG | $4.67 | | |

  Total API spend for the project was about $1,500.
- **Quality issues:** "most of the videos produced exhibit minor issues with visual element layout": misaligned text, overlapping shapes, inconsistent sizes.
- **Metric validity:** automatic metrics correlate weakly with humans. Spearman correlations: accuracy 0.14, layout 0.42, visual relevance 0.72.

**Code2Video** (Show Lab, NUS; Oct 2025; **ICML 2026**; MIT; ~2.35k stars)
- **Architecture** ([arXiv 2510.01174v1](https://arxiv.org/html/2510.01174v1); [GitHub](https://github.com/showlab/Code2Video)):
  - **Planner:** outline → storyboard, plus an external asset database (icons and reference images), cached.
  - **Coder:** generates sections in parallel and repairs them with **ScopeRefine**: line scope (±1 line) → block scope → global regeneration.
  - **Critic:** uses a **visual anchor prompt**, a "6×6 grid of predefined anchor points" mapped to Manim coordinates, with point- or region-level placement and an occupancy table. A VideoLLM compares the render with the code to fix overlap, occlusion and unused space.
  - Recommended models: **Claude-4-Opus** as planner/coder and **gemini-2.5-pro** as critic. Manim CE v0.19.0.
- **MMMC benchmark:** 117 long-form 3Blue1Brown videos, 339 clips, 13 categories.
- **Results** (aesthetics / TeachQuiz):

| System | Aesthetics | TeachQuiz |
|---|---|---|
| Direct code generation, Claude Opus 4.1 | 37.8 | 40.0 |
| Code2Video, Claude Opus 4.1 | **87.9** | **86.0** |
| Code2Video, GPT-4.1 | 79.0 | 82.0 |
| Code2Video, GPT-5 | 72.2 | 80.0 |
| Code2Video, Gemini 2.5 Pro | 57.4 | 72.0 |

  Code2Video reports no pass or render rates.
- **Cost per topic:**

| System | Time | Tokens | Video length |
|---|---|---|---|
| Code2Video, Claude Opus 4.1 | 13.8 min | 43.1K | ≈ 2.0 min |
| Code2Video, GPT-5 | 8.8 min | 19.3K | |
| Code2Video, GPT-4.1 | 15.4 min | 30.8K | |
| Direct generation, Claude | 2.8 min | 2.3K | |

- **Ablations (GPT-4.1):**
  - Removing the planner drops quiz 82.0 → 40.5 and aesthetics 79.0 → 38.1.
  - Without parallel execution, time grows 15.4 → 86.6 min.
  - Plain retry instead of ScopeRefine: 42.9 min and 49.8K tokens.
  - Without both: 149.8 min.
- **Human study:** Code2Video (Claude) aesthetics 81.8 and quiz 80.3, versus 96.5 and 78.8 for 3B1B. "Humans penalize brief occlusions in layout, which VideoLLMs often miss." Asset retrieval sometimes returns unusable images.

**OmniManim / "See Before You Code"** (Wuhan Univ., 2026-05-15; code "planned")
- **Agents** ([arXiv 2605.15585v1](https://arxiv.org/html/2605.15585v1)):
  - Scene Agent.
  - **Vision Agent** that predicts keyframe bounding boxes *before* code is written. It is a learned layout prior, a Transformer denoiser trained on ManimLayout-1K: 22,579 keyframes, ~43.5 h on 4×RTX 3090.
  - Code Agent that must keep those layouts.
  - Repair Agent that routes failures: overlap/boundary → Vision Agent, runtime → Code Agent, temporal → Scene Agent.
- **Results on EduRequire-500** (5 runs each, at most 1 repair round):

| System | R@1 | R@F | OV | LQ | Tokens/task | Time |
|---|---|---|---|---|---|---|
| OmniManim (GPT-5.4) | 0.907 | 0.986 | 0.763 | 0.931 | 73,279 | 72 s |
| Code2Video (GPT-5.4) | 0.841 | 0.923 | 0.598 | 0.742 | 69,532 | 148 s |
| GPT-5.4 alone | 0.812 | 0.934 | 0.628 | 0.778 | 56,328 | 108 s |

  R@1 and R@F are the paper's render-success metrics; reading them as first try and final is my interpretation.
- **Human evaluation** (60 tasks): overall OmniManim 81.0, GPT-5.4 76.0, Code2Video 68.4.
- **Ablation:** removing the Vision Agent drops OV 0.763 → 0.491 and LQ 0.931 → 0.614.
- Single-model baselines included **Kimi K2.5, MiniMax-M2.7 and Qwen3-14B**. Kimi K2.5 had the best AC (0.808 vs 0.802). Claude Opus 4.6 was the VLM evaluator.

**SGA, geometric verification without rendering** (KAUST, 2026-07-20; no code URL)
- **MVQS** is a deterministic score computed from Manim objects' bounding boxes. It covers overlap (severity above 0.10 and above 0.30 coverage), canvas boundary, minimum legible scale δ = 0.15, separation, density, distribution on a 4×3 grid, and labeling completeness ([arXiv 2607.18116v1](https://arxiv.org/html/2607.18116v1)).
- **On MMMC-Code** (117 topics; GPT-5.1, GPT-5 mini, Claude 4.6 Sonnet and Gemini 3.0 Flash backbones):
  - SGA improved MVQS in **7 of 8** configurations.
  - Code2Video + GPT-5.1: RAW 62.97 → VLM critic 64.54 → **SGA 73.11**.
  - Gemini 3.0 Flash: 67.82 → 69.09 → 71.86.
- **Speed:** partial execution takes **< 5 s**, against 30–90 s for a full render, a 6–18× per-iteration speedup. Per-sample time: RAW 6.4 min, VLM critic 8.8 min, SGA 6.8 min.
- **Robustness:** scene completion was 1.000 for RAW and SGA and 0.996 with the VLM critic.
- **VLM critic weaknesses:** it "introduces regressions, including out-of-canvas displacement and missing semantic elements", and VLM scores are "largely insensitive to geometric inconsistencies."
- **Limits:** MVQS is not validated against humans, and it covers 2D only.

**ManimAgent** (Alberta/Amii et al.; **EMNLP 2026**; code [jwj1342/Paper2Manim](https://github.com/jwj1342/Paper2Manim), no license, 13 stars)
- **Architecture** ([arXiv 2606.30296](https://arxiv.org/html/2606.30296)):
  - Six agents: Storyboarder, Coder, Renderer, text Reviewer, VLM Reviewer and Visual Reviser.
  - A **dual-channel Episodic Memory Bank**: success rationales serve as soft references, and VLM-screened failure patterns serve as hard "Known Pitfalls". There are no weight updates.
  - All agents use one "GPT-5.5 family endpoint". The weak-VLM ablation uses **Step-3.7-Flash**.
- **Blind human scoring** (Pass@1 / reflection rounds / quality):

| Condition | Pass@1 | Reflection rounds | Quality |
|---|---|---|---|
| VLM reflection only | 68.5 | 12.2 | 3.41 |
| Manim-code RAG | 83.3 | 11.4 | 3.65 |
| EMB@0 | 62.0 | 12.2 | 3.26 |
| **EMB@200** | **84.9** | **6.5** | **3.88** |

- **Cost per task:** about 36–38K LLM tokens plus 20–23K VLM tokens, and 19–31 min of render/wall time. Token counts are estimated.
- **Agreement:** VLM–human agreement is weak (Pearson r = −0.17, Cohen's κ = −0.07), and so is human–human agreement (Fleiss' κ = −0.01).

**Teaching Monster Challenge** (NTU, 2026; [arXiv 2608.08852v1](https://arxiv.org/html/2608.08852v1))
- **Pipeline:** a near-universal six-stage cascade: persona parsing → lesson planning → slides and script → visual rendering → TTS → assembly. faster-whisper word timestamps drive animation triggers.
- **Scale:** 1,696 + 1,612 videos were submitted, each with a 30-min budget.
- **Judging:** gemini-3-flash was the LLM judge, and its ranking correlated with the crowd at **Spearman ρ = −0.17**. Only the winner beat all three organizer baselines in crowd Elo.
- Organizer baselines used **Qwen3-VL-8B-Instruct**, gemini-3-flash-preview and Qwen3-TTS.

**Manimator** (2025; ICML 2025 listing; MIT; 75 stars; **stale since 2025-02-14**)
- Two steps: one LLM writes a Markdown scene description, then a code LLM writes Manim. Inputs can be a prompt, a PDF or an arXiv ID.
- The "manimator (DeepSeek V3)" configuration has an overall visual score of **0.738**.
- Documented limits: overlap between elements, and weak visualization of complex papers ([arXiv 2507.14306](https://arxiv.org/abs/2507.14306); [GitHub](https://github.com/HyperCluster-Tech/manimator)).

**Math-To-Manim v2.0.0** (2026-10-07; MIT; ~2.8k stars; active)
- **Chain:** GPT-6 Astra (via the Codex SDK) writes the learner/prerequisite brief, a math dossier checked with tools, a timed storyboard and the full scene.
- **Checks before render:** static checks (AST, banned imports, "camera discipline") and a real Manim execution probe.
- **Review:** "Jev" review gates send failures back to the earliest responsible stage.
- **Other providers:** commands exist for sol, grok, glm and mimo.
- **3D films:** e.g., "Every Orbit Is a Great Circle", 166 s at 1080p60. No success rates or costs are published ([GitHub](https://github.com/HarleyCoops/Math-To-Manim)).

**Generative Manim** (Apache-2.0; ~0.9k stars; v4.0.0 on 2026-07-13; product site animo.video)
- Described as "GPT for video generation". I found no published evaluation ([GitHub](https://github.com/marcelo-earth/generative-manim)).

**Paper2Video / PaperTalker** (Show Lab, Oct 2025; MIT; ~2.4k stars; last push 2026-03-05)
- **Pipeline:** slide generation with layout refinement by "tree search visual choice", cursor grounding, subtitles, speech synthesis and talking-head rendering, generated in parallel per slide.
- **Benchmark:** 101 papers with author-made talks. Metrics: Meta Similarity, PresentArena, PresentQuiz and IP Memory ([arXiv 2510.05096](https://arxiv.org/abs/2510.05096); [GitHub](https://github.com/showlab/Paper2Video)).
- I did not extract numeric results.

**PresentAgent** (Jul 2025; EMNLP 2025 Demo per repo)
- **Pipeline:** segment the document → render slide frames → LLM narration → TTS → audio-visual alignment.
- **PresentEval** is VLM-based. On 30 document–presentation pairs the system "approaches human-level quality" ([arXiv 2507.04036](https://arxiv.org/abs/2507.04036); [GitHub](https://github.com/AIGeeksGroup/PresentAgent), 146 stars).
- A successor, PresentAgent-2, exists (18 stars, 2026) ([GitHub search](https://github.com/AIGeeksGroup/PresentAgent-2)).

**LL3M** (Univ. of Chicago, Aug 2025; project page, code license NOASSERTION, ~556 stars)
- **Agents** ([arXiv 2508.08228v1](https://arxiv.org/html/2508.08228v1); [repo](https://github.com/threedle/ll3m)):

| Role | Model |
|---|---|
| Planner | GPT-4o |
| Retrieval (BlenderRAG) | GPT-4o |
| Coder | **Claude 3.7 Sonnet** |
| Critic (renders + VLM) | **Gemini 2.0 Flash** (one appendix says GPT-4o) |
| Verification | Gemini 2.0 Flash |
| User agent | (not specified) |

- **Times:** about 4 min for initial creation, about 6 min for auto-refinement, and about 38 s per user edit. About 41% of edits needed 3–4 follow-ups.

**SceneCraft** (Google et al., 2024)
- Builds a scene graph first, then writes Blender Python that turns the relations into numeric layout constraints. Scenes can hold up to 100 assets.
- GPT-V gives rendered-image feedback, and **library learning** of reusable functions improves the agent without fine-tuning. It "surpasses existing LLM-based agents" ([arXiv 2403.01248](https://arxiv.org/abs/2403.01248)).

**BlenderGym / BlenderAlchemy**
- **BlenderGym** (CVPR 2025): code-based 3D reconstruction tasks. State-of-the-art VLM systems still struggle where humans find the tasks easy, and verifier compute can itself be scaled ([arXiv 2504.01786](https://arxiv.org/abs/2504.01786)).
- **BlenderAlchemy** (ECCV 2024): VLM-guided editing of Blender visual programs ([GitHub](https://github.com/ianhuang0630/BlenderAlchemyOfficial), last push 2024-12).

**3D-GPT** (2023, revised 2024)
- Task-dispatch, conceptualization and modeling agents drive procedural 3D modeling in Blender ([arXiv 2310.12945](https://arxiv.org/abs/2310.12945)).

**2026 successors and adjacent work**
- **Video-Coder** (2026-11-06): the first *trained* code-driven video agent. It writes code that builds a dynamic 3D "draft video" to condition downstream video generators. It uses SFT on 6K examples plus agentic RL on 2K, with execution and video rewards, and improves Minimax-H3 by about 7 points on PhyGenBench and 24 on VBench-2.0. Code is open ([arXiv 2611.09894](https://arxiv.org/abs/2611.09894)).
- **Manim training study** (arXiv 2604.18364, v2 2026-08-31): 17 open sub-30B models were evaluated. **Qwen3-Coder-30B + GRPO + renderer-in-the-loop with API docs** reached a **94% render success rate** and 85.7% visual similarity, 3 points above a GPT-4.1 baseline ([arXiv](https://arxiv.org/abs/2604.18364)).
- **SceneAssistant** (2026-03): a VLM agent with atomic scene operations and rendered visual feedback for open-vocabulary 3D scenes ([arXiv 2603.12238](https://arxiv.org/abs/2603.12238)).
- **LiteReality-Agent** (2026-10): treats 3D reconstruction as editing one Python script, with an observe-edit-verify harness ([arXiv 2610.01863](https://arxiv.org/abs/2610.01863)).
- **AA-3D** (2026-10): an agentic three.js harness with self-screenshot review. GLM-5.3, which "cannot view images", hits the 250-turn limit in 64% of scenes and scores 197 Elo below its predicted trend. GLM-5.3-Flash, which can view images, "scores 149 higher despite a lower Intelligence Index" ([AA article](https://artificialanalysis.ai/articles/aa-3d)). The live leaderboard shows 937 vs 783, a 154-point gap ([AA-3D](https://artificialanalysis.ai/evaluations/aa-3d)).

### Inferences
- **Design choices ranked by evidence strength:**
  1. **Planner/storyboard separated from coding.**
     - Code2Video: removing the planner halves both quiz and aesthetics.
     - TheoremExplainAgent: about 20 s of video without agents versus about 5 min with them.
     - Teaching Monster teams confirm that splitting raises render success.
  2. **Explicit layout control before or instead of the VLM.**
     - OmniManim: removing the layout prior collapses overlap scores (0.763 → 0.491).
     - SGA: a geometry check beats the VLM critic in 7 of 8 configurations at 6–18× lower per-iteration cost.
     - Code2Video's 6×6 anchor grid is the cheap, training-free version. For sotawhat, use anchor slots in templates plus a bounding-box linter. Manim exposes `get_bounding_box`; in three.js, project `Box3` to screen space.
  3. **Scoped repair driven by renderer errors plus API docs.**
     - ScopeRefine cuts time by about 3× versus plain retry.
     - RITL-DOC is the best Manim inference strategy.
     - BlenderRAG makes code more ambitious and cuts errors.
     - Generic RAG can *hurt* strong models: GPT-4o went 55.0 → 45.8 and o3-mini 93.8 → 82.1.
  4. **Memory of what worked and what broke** (ManimAgent EMB: Pass@1 62 → 85, reflection rounds halved; SceneCraft library learning). For sotawhat this maps naturally onto a growing template library per topic family: transformer, diffusion, CT, molecule, EHR.
  5. **VLM critic as last line only.**
     - It misses brief occlusions (Code2Video) and introduces regressions (SGA).
     - Its judgments correlate negatively or near zero with humans (ManimAgent r = −0.17; Teaching Monster ρ = −0.17).
     - It still adds value for 3D, where coders without vision fail (AA-3D, GLM-5.3 vs GLM-5.3-Flash).
  6. **Asset libraries** help when curated. AA-3D gives agents a CC0 library; Code2Video's open icon retrieval returned unusable assets. Use a fixed local kit (`ativos_e_geracao_3d.md`) rather than web retrieval.
- **Model choice still dominates raw success.** In 2025, eventual render success ranged from 2% to 94% across models on the same harness. With 2026 models and a templated harness, 90–99% final render success per scene is a realistic target (OmniManim R@F 0.986; SGA completion 1.000).

### Gaps
- No system reports **cost per minute of video in USD** with 2026 open-weight models. The only USD figures are TheoremExplainAgent's 2025 models.
- No published agentic system targets **3D educational video specifically** (ThreeDScene, three.js or Blender lessons). All the measured systems are 2D Manim or slides. Math-To-Manim shows 3D films but no metrics.
- No numeric results were extracted for Paper2Video or PresentAgent, and none for ManimAgent's Step-3.7-Flash ablation (its Table 14 was not in the fetched text).
- ManiBench's per-model numbers were not on the abstract page. ManimBench (manimbench.pages.dev) V0.6 has **no official results yet** ([site](https://manimbench.pages.dev/)).

---

## Key Question 3: Which ZDR LLMs/VLMs on OpenRouter give the best cost-effectiveness for animation-code generation and for critiquing rendered frames? (covers objective c)

### Takeaway
- For code, the cost-effectiveness leader stays the pinned **DeepSeek V4.1 Flash 1017**:
  - ZDR fp8 from $0.078/$0.235.
  - Vendor-table DeepSWE score of 77.0, on par with Opus 5.5 there.
  - Its weaker vision and its absence from 3D-scene leaderboards argue for pairing it with a vision critic.
- For 3D/three.js, the evidence favours vision-capable coders:
  - **Kimi K3.1 Pro** is the best open-weight model on AA-3D (Elo 1110, above Haiku 5.5, GPT-6 Luna and Gemini 3.8 Flash), at $1.80/$8.20. Use it for storyboards and hard scenes.
  - **MiMo-V2.6-Pro** (Elo 983 at $0.44/task; $0.387/$0.783) is the cheap 3D workhorse.
- GLM-5.3 is text-only and does poorly as a 3D agent. GLM-5.3-Flash is the better GLM for this.
- **Critic:** MiMo-V2.6-Flash ($0.14/$0.28, takes video), GLM-5.3-Flash or Qwen3-VL-235B ($0.20/$0.88).
- Gemini Flash endpoints appear in the ZDR list only as **Safety Retention** endpoints, so a strict "ZDR only" account setting excludes them.

### Cited Findings

**Cheapest eligible ZDR endpoints, 2026-11-09** ([/endpoints/zdr](https://openrouter.ai/api/v1/endpoints/zdr); [/models](https://openrouter.ai/api/v1/models))

| Model (slug) | Input modalities | Cheapest eligible ZDR endpoints (provider · quant · in/out) | ZDR endpoints (total / non-fp4) |
|---|---|---|---|
| `deepseek/deepseek-v4.1-flash-1017` (pinned) | text, image | Particle AI · ? (flex) · 0.025/0.25 — Morph · fp8 · 0.022/0.40 — **DeepInfra · fp8 (flex) · 0.078/0.235** — Ionstream · ? (flex) · 0.083/0.248 | 43 / 36 |
| `deepseek/deepseek-v4.1-flash` | text, image | Morph · fp8 · 0.022/0.40 — DeepInfra fp8 flex 0.112/0.336 (68% uptime 1d) — DeepInfra fp8 0.14/0.42 | 33 / 29 |
| `deepseek/deepseek-v4-pro-0813` | text | Novita · fp8 · 0.99/2.97 — DeepInfra · fp8 · 1.30/2.60 (Phala 0.957/2.878 has no structured outputs) | 18 / 12 |
| `z-ai/glm-5.3` (pinned; **text-only**; reasoning mandatory, default `max`) | text | Reka · 0.14/2.10 — DekaLLM · 0.18/2.95 — PrimeIntellect · 0.40/2.464 — Novita · fp8 · 0.63/1.98 | 40 / 23 |
| `z-ai/glm-5.3-flash` (reasoning mandatory) | text, image, video | PrimeIntellect · 0.052/0.25 — Morph · fp8 · 0.085/0.173 — Tenstorrent · fp8 · 0.075/0.25 — Novita · fp8 · 0.084/0.28 | 36 / 16 |
| `moonshotai/kimi-k3.1-pro` (pinned; 2.8T/104B active) | text, image, video | **Phala (US) · 1.80/8.20** — DeepInfra · bf16 · 1.90/9.50 — Fireworks / DigitalOcean · 2.00/10.00; cache read 0.18–0.20 | 23 / 7 |
| `xiaomi/mimo-v2.6-pro` (pinned) | text, image, video, audio | **DeepInfra · fp8 · 0.387/0.783** (other endpoint: PrimaLabs 4/8) | 2 / 2 |
| `xiaomi/mimo-v2.6-flash` | text, image, video, audio | Cohere / Makora / DeepInfra · fp8 · 0.14/0.28 — Venice · fp8 · 0.175/0.35 | 4 / 4 |
| `minimax/minimax-m3.1-flash` (reasoning mandatory) | text, image, video | Fireworks / DigitalOcean / SambaNova · 0.15/0.60 (Novita fp16 lacks structured outputs) | 10 / 6 |
| `minimax/minimax-m3` | text, image, video | DeepInfra · fp8 flex · 0.224/0.88 (**no structured outputs on cheap endpoints**) | 8 / 7 |
| `moonshotai/kimi-k2.7-code` (reasoning mandatory) | text, image | Cloudflare / Moonshot · 0.95/4.00 (SiliconFlow fp8 0.859/3.80 lacks structured outputs) | 8 / 4 |
| `moonshotai/kimi-k2.6` | text, image | DigitalOcean · 0.57/2.40 | 12 / 7 |
| `qwen/qwen3-coder-next` (80B/3B active) | text | Parasail · bf16 · 0.12/0.80 (single endpoint) | 1 / 1 |
| `qwen/qwen3-coder` (480B) | text | Venice · fp8 · 0.35/1.50 (88% uptime 1d) | 2 / 1 |
| `qwen/qwen3.8-27b` (dense VLM) | text, image, video | PrimeIntellect · fp8 · 0.052/0.369 — Near AI · fp8 · 0.04/1.35 | 19 / 17 |
| `qwen/qwen3.8-2.4t-a95b` (open Qwen3.8 Max) | text | Novita / SiliconFlow · 2.00/6.00 | 3 / 3 |
| `qwen/qwen3.6-35b-a3b` | text, image, video | PrimeIntellect · fp8 · 0.012/0.107 | 9 / 9 |
| `tencent/hy3` | text | Tencent · fp8 · 0.083/0.33, rising to 0.132/0.528 during 00:00–16:00 UTC | 3 / 3 |
| `mistralai/devstral-2512` | text | Mistral (EU) · 0.40/2.00 | 1 / 1 |
| `x-ai/grok-build-0.1` | text, image | xAI ZDR · 1.00/2.00 | 2 / 2 |

- **No ZDR endpoint:** Qwen3.8 Max (0902), Qwen3.8-Flash, Qwen3.7-Plus/Flash and Qwen3-Coder-Flash. The catalog has **no Qwen3.8-Coder** model; the newest "coder" slugs are `qwen3-coder-next` (Feb 2026) and the 2025 `qwen3-coder` family ([/models](https://openrouter.ai/api/v1/models)).
- **Tencent Hy4** (2026-11-04): its only ZDR endpoint is fp4, so it is excluded ([/endpoints/zdr](https://openrouter.ai/api/v1/endpoints/zdr)).

**VLM candidates for frame critique (eligible ZDR endpoints, 2026-11-09)**

| Model | Cheapest eligible ZDR (in/out) | Notes |
|---|---|---|
| `xiaomi/mimo-v2.6-flash` | 0.14/0.28 | Takes **video** and audio input, so it can review a rendered clip, not just keyframes |
| `z-ai/glm-5.3-flash` | 0.052–0.085 / 0.173–0.25 | Native image and video input; reasoning cannot be turned off |
| `inclusionai/ling-3.0-flash-vl` | DeepInfra fp16 · 0.06/0.18 | 124B/5.5B-active MoE with vision |
| `nvidia/nemotron-3.5-super-vl` | Crusoe bf16 · 0.10/0.40; Together 0.15/0.50 | AA Intelligence Index 14 |
| `bytedance-seed/seed-2.0-mini` | Seed fp8 · 0.10/0.40 (0.20/0.80 above 128K prompt) | |
| `qwen/qwen3-vl-30b-a3b-instruct` | DeepInfra fp8 · 0.15/0.60 | |
| `qwen/qwen3-vl-235b-a22b-instruct` | DeepInfra fp8 · 0.20/0.88; Parasail 0.21/1.90 | Knowledge cutoff 2025-03 |
| `qwen/qwen3-vl-8b-instruct` | Parasail bf16 · 0.25/0.75 | Organizer baselines in Teaching Monster used Qwen3-VL-8B |
| `z-ai/glm-4.6v` | Novita bf16 / Z.AI fp8 · 0.30/0.90 | No structured outputs |
| `z-ai/glm-5v-turbo` | Z.AI fp8 · 1.20/4.00 | No structured outputs |
| `z-ai/glm-4.5v` | 0.60/1.80 | **Expires 2026-12-31** |
| `meta/muse-glimmer-30b` | DeepInfra bf16 · 0.30/1.20 | |
| `google/gemini-3.1-flash-lite` | Vertex flex 0.125/0.75; standard 0.25/1.50 | **`safety_retention: true`** |
| `google/gemini-3.5-flash-lite` | Vertex flex 0.15/1.25; standard 0.30/2.50 | **`safety_retention: true`**; reasoning mandatory |
| `google/gemini-3.8-flash` | Vertex flex 0.375/1.875; standard 0.75/3.75 | **`safety_retention: true`** |
| `google/gemini-4-argon` | 2.00/10.00 | `safety_retention: true` |
| Kimi-VL | **not in the OpenRouter catalog** | Kimi K3.1 Pro itself takes image and video |

- **Safety Retention:** every Google Vertex endpoint in the ZDR list carries `safety_retention: true` ([/endpoints/zdr](https://openrouter.ai/api/v1/endpoints/zdr)). Per the 11-07 notes, OpenRouter's account-level "ZDR only" option excludes Safety Retention endpoints ([llm_openrouter.md](../../2026-11-07-insight-engine/llm_openrouter.md)). None of the Chinese-model endpoints listed above carries the flag.
- **Reference models (ZDR):**
  - `anthropic/claude-haiku-5.5`: 0.10/0.50, rising to 0.50/2.50 above 100K prompt.
  - `claude-sonnet-5.5`: 2/10.
  - `claude-opus-5.5`: 4/20.
  - `openai/gpt-6-luna`: Azure 0.10/0.50, rising to 0.20/0.75 above 272K.
  - `openai/gpt-6.1-terra`: 1.00/5.00 ([/endpoints/zdr](https://openrouter.ai/api/v1/endpoints/zdr)).

**Changes since the 2026-11-07 notes** (same method; [llm_openrouter.md](../../2026-11-07-insight-engine/llm_openrouter.md))
- **Kimi K3.1 Pro** has a new, cheaper ZDR endpoint: Phala (US) at 1.80/8.20. On 11-07 the cheapest was DeepInfra at 1.90/9.50.
- **GLM-5.3-Flash** has new cheaper endpoints: PrimeIntellect 0.052/0.25 and Morph fp8 0.085/0.173. On 11-07 the cheapest was Tenstorrent at 0.075/0.25.
- **GLM-5.3** adds PrimeIntellect (0.40/2.464) and Novita fp8 (0.63/1.98). Reka (0.14/2.10) is still the cheapest.
- **DeepSeek V4.1 Flash 1017** gained Ionstream (flex) at 0.083/0.248. The Particle AI, Morph and DeepInfra prices are unchanged.
- **MiMo-V2.6-Flash** has 4 ZDR endpoints (5 eligible on 11-07); Venice was added at 0.175/0.35.
- **Catalog size:** 462 models (460 on 11-07) and 1,107 ZDR endpoints (1,120 on 11-07).
- **New since 11-07:** `meta/muse-ember` (2026-11-09; no ZDR), `google/gemini-omni-1.1/1.2-flash` (2026-11-04/05; no ZDR), `tencent/hy4` (fp4-only ZDR) and `z-ai/glm-5.3-flashx-legal`.
- The 11-07 notes' caveats still apply: the catalog price is the cheapest endpoint, often fp4; some endpoints use time-of-day pricing; and credit purchases carry a fee of roughly 5.5%, which still needs checking at checkout.

**General quality: Artificial Analysis Intelligence Index**, read 2026-11-09 ([AA leaderboard](https://artificialanalysis.ai/leaderboards/models)); same values as the 11-07 notes. "Cost/task" is AA's column.

| Model (setting) | Index | Cost/task |
|---|---|---|
| Kimi K3.1 Pro | 46 | $3.68 |
| DeepSeek V4.1 Flash 1017 (max) | 33 | $0.60 |
| DeepSeek V4.1 Flash 1017 (high) | 29 | $0.46 |
| GLM-5.3 (max) | 32 | $5.01 |
| MiMo-V2.6-Pro | 30 | **$0.26** |
| MiniMax-M3.1-Flash | 29 | $0.49 |
| GLM-5.3-Flash | 28 | $0.58 |
| MiMo-V2.6-Flash | 27 | **$0.13** |
| Gemini 3.8 Flash (high) | 31 | $7.77 |
| Gemini 3.5 Flash-Lite | 12 | $0.69 |
| Nemotron 3.5 Super VL | 14 | $0.52 |
| Gemini 4 Argon (high) | 50 | $9.95 |
| GPT-6.1 Terra (max) | 51 | $0.96 |
| GPT-6 Luna (max) | 28 | $0.15 |
| Claude Haiku 5.5 (max) | 36 | $0.41 |
| Claude Sonnet 5.5 (max) | 55 | $10.02 |
| Claude Opus 5.5 (max) | 59 | $10.04 |

**3D-specific evidence: AA-3D** (three.js scenes built by agents; human Elo, 95% CI; selected rows of 24; [AA-3D leaderboard](https://artificialanalysis.ai/evaluations/aa-3d); [article](https://artificialanalysis.ai/articles/aa-3d))

| Rank | Model | Elo | Cost/task |
|---|---|---|---|
| 1 | Claude Sonnet 5.5 (Max) | 1199 | ≈ $14.93 run cost |
| 2 | Claude Opus 5.5 (Max) | 1196 | |
| 3 | GPT-6 Astra (Max) | 1164 | |
| 4 | Gemini 4 Argon (High) | 1153 | |
| 6 | GPT-6 Sol (Max) | 1121 | $3.46 |
| **8** | **Kimi K3.1 Pro** | **1110** (1078–1143) | |
| 9 | Muse Spark 1.3 | 1033 | |
| 11 | **GPT-6 Luna (Max)** | **1000** (anchor) | **$0.20** |
| 12 | **Claude Haiku 5.5 (Max)** | **998** | **$0.49** |
| 14 | **MiMo-V2.6-Pro** | **983** | **$0.44** |
| 15 | Kimi K3 (Max) | 982 | ≈ 68× Luna's cost |
| 16 | Gemini 3.8 Flash (High) | 966 | |
| 17 | Qwen3.8 Max (0902) | 945 | |
| 18 | GLM-5.3-Flash | 937 | |
| 20 | Step 5 Preview | 854 | |
| 21 | **GLM-5.3 (Max)** | **783** | |
| 22 | **MiniMax-M3** | **740** | |

  DeepSeek V4.x did not appear in the visible part of the leaderboard.
- AA says the best open-weight models (Kimi K3 and MiMo-V2.6-Pro) were "more than 200 Elo behind the leaders" in the launch article. K3.1 Pro, at 1110, has since narrowed that gap.

**Coding benchmarks** (mostly vendor-reported; treat as indicative)
- **Kimi K3.1 Pro model card**, max effort ([Hugging Face](https://huggingface.co/moonshotai/Kimi-K3.1-Pro)):

| Benchmark | K3.1 Pro | DeepSeek V4.1 Flash 1017 | GLM-5.3 | Opus 5.5 |
|---|---|---|---|---|
| Terminal-Bench 4.0 | 65.7 | 42.3 | 41.8 | 66.4 |
| SWE Marathon v1.1 | 51.7 | 40.0 | 42.5 | 46.3 |
| DeepSWE v1.1 | 75.5 | **77.0** | 66.9 | 74.2 |
| BenchCAD w/ tools | 92.7 | 81.6 | — | 96.2 |
| Design Bench (internal Elo) | 957 | 863 | 718 | 927 |
| MMMU-Pro (no tools) | 84.1 | 80.6 | — (text-only) | 87.7 |
| CharXiv RQ (no tools) | 89.0 | 77.0 | — (text-only) | 92.1 |
| PerceptionBench | 68.3 | 47.7 | — (text-only) | 72.1 |

- **Third-party, partly conflicting:**
  - Vals.ai: LiveCodeBench **Kimi K3 87.19% vs GLM-5.3 80.53%**; Vals' SWE-bench run GLM-5.3 95.40% vs Kimi K3 93.40% ([Vals.ai](https://www.vals.ai/comparisons/kimi_kimi-k3-vs-zai_glm-5.3)).
  - Friendli reports SWE-bench Verified 94.2% (GLM-5.3) and 93.8% (Kimi K3) ([Friendli](https://friendli.ai/blog/kimi-k3-glm-5.3-coding-agent-benchmark) (secondary)).
  - Morph states that Z.ai published no SWE-bench Pro or Verified figure for GLM-5.3, and Moonshot none for Kimi K3 ([Morph](https://www.morphllm.com/swe-bench-pro) (secondary)).
  - Regolo (2026-11-06) repeats the DeepSWE and Terminal-Bench figures. It adds Qwen3.8-27B at 42.5% on DeepSWE and 6.3% on Terminal-Bench 4.0 ([Regolo](https://regolo.ai/kimi-k3-1-pro-vs-deepseek-1017-vs-glm-5-3-qwen3-8-27b-benchmarks/) (secondary)).
- **Manim-specific:** a fine-tuned **Qwen3-Coder-30B** reached a 94% render success rate on ManimBench ([arXiv 2604.18364](https://arxiv.org/abs/2604.18364)). OmniManim's single-model baselines included Kimi K2.5 (best AC 0.808), MiniMax-M2.7 and Qwen3-14B ([arXiv 2605.15585v1](https://arxiv.org/html/2605.15585v1)). There are no ManimBench V0.6 official results yet ([ManimBench](https://manimbench.pages.dev/)).
- **Visual critics used in research:** Gemini 2.5 Pro (Code2Video critic), Gemini 3.0 Flash (SGA judge), Claude Opus 4.6 (OmniManim evaluator), a GPT-5.5-family model (ManimAgent reviewer), Step-3.7-Flash (ManimAgent "weak VLM" ablation) and gemini-3-flash (Teaching Monster judge). Sources are the papers cited in Key Question 2.

### Inferences
- **Suggested role assignment** (all ZDR, eligible endpoints):
  - **Planner / storyboard / pt-BR script:** Kimi K3.1 Pro (`high`). It is the best open-weight model on 3D and design, and planning is a small share of tokens. Economy option: DeepSeek V4.1 Flash 1017 (`max`).
  - **Manim coder and repairer:** DeepSeek V4.1 Flash 1017 (`high`), with MiMo-V2.6-Pro as a different-family fallback. Escalate to Kimi K3.1 Pro after 2 failed repairs.
  - **three.js/R3F coder:** MiMo-V2.6-Pro, which is multimodal and has proven AA-3D results at $0.44/task. Escalate to Kimi K3.1 Pro for hero scenes. Avoid GLM-5.3 (text-only, Elo 783) and MiniMax-M3 (Elo 740, and no structured outputs on its cheap ZDR endpoints).
  - **Visual critic:** a deterministic bbox linter first. Then **MiMo-V2.6-Flash** on the rendered clip (video input), or GLM-5.3-Flash on keyframes. Qwen3-VL-235B is a third-family fallback.
  - **Not used:** Gemini Flash, if the account enforces "ZDR only". It is also 2–5× pricier than the Chinese VLMs at similar or lower index scores.
- **Reasoning settings:** keep fallback chains on levels every member accepts (`low`/`high`), as the 11-07 notes advise. GLM-5.3 and GLM-5.3-Flash *force* reasoning, defaulting to `max`. That inflates output tokens, and at $2.10/M output GLM-5.3 can cost more than MiMo-V2.6-Pro.
- **Why vision matters for the coder:** AA-3D's GLM-5.3 vs GLM-5.3-Flash gap (+154 Elo for the model that can see) is the clearest evidence that a coder able to look at its own renders beats a stronger text-only coder in 3D.

### Gaps
- **No Aider Polyglot or LiveCodeBench results** were found for DeepSeek V4.1 Flash, MiMo-V2.6 or MiniMax-M3.1-Flash. SWE-bench Verified figures for 2026 models are third-party and conflicting, so vendor tables use DeepSWE and SWE Marathon instead.
- No 3D or three.js score was found for DeepSeek V4.1 Flash 1017. It was absent from the visible AA-3D table, and the page may have been truncated.
- No Blender (bpy) code-generation evaluation of 2026 Chinese models was found.
- VLM quality on *layout* critique specifically (overlap/occlusion detection) has no public comparison across Qwen3-VL, GLM-5.3-Flash, MiMo-V2.6-Flash and Gemini Flash.
- pt-BR narration quality of these LLMs was not assessed here; see `narracao_avatar_audio.md` for TTS.

---

## Key Question 4: How many tokens and how many USD does a 5-minute, ~10-scene lesson cost with the cheapest competent ZDR models, including repair loops and visual critique?

### Takeaway
A templated pipeline needs roughly **0.45–0.5M input and ~0.17M output tokens** per lesson. TheoremExplainAgent measured 434K/154K per ~5-min video, so the order of magnitude is grounded. At 2026-11-09 ZDR prices:
- **≈ $0.08** with DeepSeek V4.1 Flash 1017 plus a MiMo-V2.6-Flash critic.
- **≈ $0.30** with MiMo-V2.6-Pro plus a Qwen3-VL critic.
- **≈ $0.23** with a Kimi K3.1 Pro storyboard plus a DeepSeek coder.
- **≈ $1.8–2.2** with Kimi K3.1 Pro end to end.

Even a 3× token overrun keeps the cheap tiers under $1. LLM spend is negligible next to render time and human review.

### Cited Findings
- **TheoremExplainAgent (o3-mini):** **434,000 input + 154,000 output tokens per video** (about 5 min, 7 scenes, 4 code fixes assumed), $1.16 at o3-mini prices and 1,680 s ([arXiv 2502.19400v2](https://arxiv.org/html/2502.19400v2)).
- **Code2Video:** 19.3K–43.1K tokens and 8.8–15.4 min per topic for videos of about 2 min ([arXiv 2510.01174v1](https://arxiv.org/html/2510.01174v1)).
- **OmniManim:** 73–75K tokens per task with at most 1 repair round ([arXiv 2605.15585v1](https://arxiv.org/html/2605.15585v1)).
- **ManimAgent:** about 36–38K LLM plus 20–23K VLM tokens per task ([arXiv 2606.30296](https://arxiv.org/html/2606.30296)).
- **AA-3D**, fully agentic, one three.js scene per task, up to 250 turns: $0.20 for GPT-6 Luna, $0.44 for MiMo-V2.6-Pro and $0.49 for Haiku 5.5 per task ([AA-3D leaderboard](https://artificialanalysis.ai/evaluations/aa-3d)).
- **Prices (2026-11-09, eligible ZDR):**

| Model | In / out | Cache read |
|---|---|---|
| DeepSeek V4.1 Flash 1017 (DeepInfra fp8 flex) | 0.078 / 0.235 | 0.0024 |
| MiMo-V2.6-Flash | 0.14 / 0.28 | |
| MiMo-V2.6-Pro | 0.387 / 0.783 | |
| GLM-5.3-Flash (Tenstorrent) | 0.075 / 0.25 | |
| GLM-5.3 (Reka) | 0.14 / 2.10 | |
| Qwen3-VL-235B | 0.20 / 0.88 | |
| Kimi K3.1 Pro (Phala) | 1.80 / 8.20 | 0.18 |
| Claude Haiku 5.5 | 0.10 / 0.50 | |
| Claude Sonnet 5.5 | 2 / 10 | |

  Source: [/endpoints/zdr](https://openrouter.ai/api/v1/endpoints/zdr).
- **OpenRouter credit-purchase fee:** about 5.5% historically, unverified ([llm_openrouter.md](../../2026-11-07-insight-engine/llm_openrouter.md)).

### Inferences
- **Token budget per lesson** (5 min, 10 scenes; my assumptions; reasoning tokens counted as output):

| Stage | Calls | Input/call | Output/call (incl. reasoning) | Input total | Output total |
|---|---|---|---|---|---|
| Planner: outline + storyboard JSON + pt-BR narration (~750 words) | 1 | 15K | 15K | 15K | 15K |
| Coder per scene (template-library cheat-sheet ~8K + scene spec + helpers) | 10 | 12K | 6K | 120K | 60K |
| Repair (renderer traceback + code + doc snippets), ~1 per scene | 10 | 16K | 5K | 160K | 50K |
| VLM critique (4 keyframes ≈ 5K + layout JSON/code ≈ 2K) | 10 | 7K | 1K | 70K | 10K |
| Visual fixes (~0.5 per scene) | 5 | 16K | 5K | 80K | 25K |
| Re-critique after fix | 5 | 7K | 1K | 35K | 5K |
| **Total** | **41** | | | **≈ 480K** (LLM 375K + VLM 105K) | **≈ 165K** (LLM 150K + VLM 15K) |

- **Cost per lesson at 2026-11-09 eligible ZDR prices** (before the ~5.5% fee, no caching):

| Configuration | LLM part | VLM part | **Total** |
|---|---|---|---|
| A. DeepSeek V4.1 Flash 1017 (planner + coder + repair) + MiMo-V2.6-Flash critic | 375K × 0.078 + 150K × 0.235 = $0.064 | 105K × 0.14 + 15K × 0.28 = $0.019 | **≈ $0.08** |
| B. GLM-5.3-Flash for everything (vision-native; Tenstorrent) | $0.066 | $0.012 | **≈ $0.08** ($0.12–0.15 if forced `max` reasoning doubles output) |
| C. MiMo-V2.6-Pro coder + Qwen3-VL-235B critic | $0.145 + $0.117 = $0.262 | $0.021 + $0.013 = $0.034 | **≈ $0.30** |
| D. Kimi K3.1 Pro planner only (15K/15K = $0.15) + A for everything else | $0.15 + $0.06 | $0.019 | **≈ $0.23** |
| E. GLM-5.3 coder (Reka; text-only) + MiMo-V2.6-Flash critic | $0.05 + $0.32 | $0.019 | **≈ $0.39** (≈ $0.70 with `max` reasoning) |
| F. Kimi K3.1 Pro end to end (multimodal) | 480K × 1.80 + 165K × 8.20 | (included) | **≈ $2.22**; ≈ $1.76 with ~280K tokens of cached prefix at 0.18 |
| Ref. Claude Haiku 5.5 end to end | | | **≈ $0.13** |
| Ref. Claude Sonnet 5.5 end to end | | | **≈ $2.6** |
| Ref. Claude Opus 5.5 end to end | | | **≈ $5.2** |

- **Sensitivity:** 3× the tokens (more repairs, longer reasoning) gives about $0.25 for A, $0.90 for C and $6.6 for F.
- **Cross-check:** TheoremExplainAgent's measured 434K input + 154K output per video would cost 434K × 0.078 + 154K × 0.235 ≈ **$0.07** at today's DeepSeek V4.1 Flash 1017 ZDR price, versus $1.16 with o3-mini in 2025.
- **Agentic three.js:** building each of 10 scenes as an AA-3D-style free agent (up to 250 turns) would cost about $2–5 per lesson even with cheap models ($0.20–0.49 per scene). That is another reason to constrain coders with templates.
- **Caching:** the static prefix (template-library docs, style guide, rubric) repeats in about 35 calls. Implicit caching on DeepSeek, Kimi and MiMo endpoints cuts input cost further, but input is already a small share for the cheap tiers.
- **Outside this estimate:** TTS (see `narracao_avatar_audio.md`) and any generative assets (see `ativos_e_geracao_3d.md` and `video_generativo.md`).

### Gaps
- Real token counts depend on scene complexity and model verbosity, especially mandatory reasoning in GLM and MiniMax. The table is an engineering estimate anchored on one 2025 measurement (TheoremExplainAgent) and three 2026 per-task figures. A pilot with `usage.cost` logging should replace it.
- No published 2026 system reports first-pass render rates for DeepSeek V4.1 Flash or MiMo on Manim or three.js, so the "~1 repair per scene" assumption is unvalidated.

---

## Key Question 5: How long does a 5-minute 1080p lesson take to render on the RTX 4060 with Manim, Blender EEVEE and headless Chromium (Remotion/Three.js)?

### Takeaway
A 5-minute lesson is 9,000 frames at 30 fps. Measured on this PC:
- **Manim 2D** renders slightly faster than real time: about 4–5 min of render for 5 min of video.
- **Manim 3D on Cairo** runs about **10× slower than real time** (≈ 50 min single-process). With `--renderer=opengl` it is about **2×** (≈ 10 min).
- **Headless-Chromium capture of a moderately heavy three.js scene** (4,096 instanced cubes, shadows, PBR) runs at **≈ 10.8 fps** with per-frame screenshots on the RTX 4060: **≈ 14 min** for 5 min of video. Software GL drops to 4.1 fps (≈ 36 min).
- **Blender EEVEE** at about 2.3 s/frame would take **≈ 5–6 h**, and Cycles about a day or more.

So Manim plus three.js keeps a full lesson within **minutes to well under an hour**. Blender does not.

### Cited Findings
- **[local measurement]**: Manim CE 0.22.1 via `uv`, Python 3.12.4, Windows 11, Ryzen 5 5500, RTX 4060 8 GB (driver 616.92), `--disable_caching`. Wall time includes process start and imports (≈ 2–3 s).
  - **2D scene "Attn2D"** (10 s of video): 6 token boxes with Pango `Text`, a 6×6 heatmap of `Square`s, 5 weighted `Arrow`s, `Write` of a formula and a grid move.
    - 1080p30, Cairo: **8.2 s**.
    - 720p30, Cairo: **5.0 s**.
  - **3D scene "Diff3D"** (6 s of video): `ThreeDScene` with `ThreeDAxes`, a 24×24 `Surface` coloured by height, 6 `Cube`s and ambient camera rotation for 3 s.
    - 1080p30, Cairo: **60.9 s** (≈ 10× real time).
    - 1080p30, `--renderer=opengl --format=mp4`: **12.3 s** (≈ 2× real time).
  - All runs exited with code 0 and wrote MP4 files: 2D 1080p 366 KB; 3D 1080p about 1.38 MB for both renderers.
- **[local measurement]**: headless Chrome 156 + puppeteer-core 24 + three.js 0.181, 1920×1080. The scene has 16 PBR token boxes, 4,096 instanced cubes (a 64×64 "attention heatmap"), 120 Bézier attention lines, a TorusKnot with a physical material, shadows (2048 map) and a floor. Each frame is set with `renderAt(t)`, then captured with `page.screenshot({type:'jpeg', quality:80})`, the same per-frame screenshot approach Remotion uses. Variants: default flags, `--use-angle=d3d11`, `--use-angle=d3d11` with 4 tabs in parallel, and SwiftShader. **Results** (150 frames each):

| Variant | WebGL renderer reported | Capture | Render-only loop | Avg JPEG |
|---|---|---|---|---|
| Default headless flags | `ANGLE (NVIDIA … RTX 4060 … Direct3D11)`, so the GPU was used **without any flags** | **13.96 s = 10.7 fps** | 409 fps | 159 KB |
| `--use-angle=d3d11 --enable-gpu --ignore-gpu-blocklist` | Same | **13.85 s = 10.8 fps** | 338 fps | 159 KB |
| 4 tabs in parallel (same flags) | — | **Failed:** `Page.captureScreenshot timed out` | — | — |
| `--use-angle=swiftshader` (software GL, like a GPU-less server) | `SwiftShader driver` | **36.29 s = 4.1 fps** | 5.4 fps | 157 KB |

  The render-only loop runs 30–40× faster than capture. The bottleneck is per-frame screenshot, JPEG encoding and CDP transfer (≈ 90 ms/frame), not WebGL.
- **Blender EEVEE on an RTX 4060:** about 2.3 s/frame for a 250-frame 1080p animation ([DatabaseMart](https://www.databasemart.com/blog/blender-gpu-cpu-benchmark-rtx4060-e5-2667v3)). Cycles at 128 samples about 16 s/frame ([Evetech](https://evezone.evetech.co.za/performance-pulse/rtx-5060-blender-performance-benchmark-real-world-test-2026) (secondary)). Typical ranges are 5–60 s/frame for EEVEE and 2–30 min/frame for Cycles ([SuperRenders](https://superrendersfarm.com/de/article/eevee-vs-cycles-cloud-render-farm-comparison-2026) (secondary)).
- **Blender 5.1 EEVEE improvements:** parallel GPU-pipeline precompilation and 30–40% less texture memory, which matters on 8 GB VRAM ([linuxiac](https://linuxiac.com/blender-5-1-3d-creation-software-released/)).
- **Remotion:** WebGL/three.js uses the GPU, cloud machines without a GPU render it slowly, and `--concurrency` plus `npx remotion benchmark` tune throughput ([Remotion performance](https://www.remotion.dev/docs/performance); [@remotion/three](https://www.remotion.dev/docs/three)).
- **SGA:** a full Manim render pass for one scene takes 30–90 s on their setup ([arXiv 2607.18116v1](https://arxiv.org/html/2607.18116v1)).
- **Godot Movie Maker:** frame-paced offline render whose speed depends only on hardware; output is identical regardless ([Godot docs](https://docs.godotengine.org/en/stable/tutorials/animation/creating_movies.html)).

### Inferences
- **Estimates for 5 min = 300 s = 9,000 frames at 1080p30** (assumes this PC; scene complexity similar to the test scenes):

| Renderer | Basis | Serial estimate | With parallel scenes |
|---|---|---|---|
| Manim CE 2D (Cairo) | 8.2 s per 10 s of video | **≈ 4–5 min** | ≈ 1–2 min with 4–6 scene processes on 6 cores / 12 threads |
| Manim CE 3D (Cairo) | 60.9 s per 6 s | **≈ 50 min** | ≈ 10–15 min with 4–6 processes (CPU-bound) |
| Manim CE 3D (OpenGL) | 12.3 s per 6 s | **≈ 10 min** | Limited by the GPU and a single context; maybe 5–7 min with 2 processes (untested) |
| Mixed lesson (≈ 70% 2D Manim, 30% 3D OpenGL) | | **≈ 6–7 min** | ≈ 3 min |
| three.js via headless Chrome (GPU via ANGLE/D3D11), JPEG screenshot per frame | 10.8 fps (150 frames in 13.85 s) | **≈ 14 min** | Multi-tab capture timed out in my test. Remotion's `--concurrency` or a faster capture path (canvas readback, in-page WebCodecs) could cut this; untested |
| three.js, software GL (SwiftShader, e.g. a GPU-less server) | 4.1 fps | ≈ 36 min | — |
| Mixed lesson (≈ 50% Manim 2D + 50% three.js capture) | | **≈ 9–10 min** | ≈ 7–8 min (Manim scenes in parallel with the capture) |
| Blender EEVEE | 2.3 s/frame | **≈ 5.75 h** | No meaningful parallelism on one 8 GB GPU |
| Blender Cycles | ≈ 16 s/frame (128 samples) | **≈ 40 h** | |

- **Encoding** with FFmpeg x264 or NVENC at 1080p30 adds a small fraction of these times. I did not measure it here because there is no FFmpeg CLI on PATH; Manim encodes internally via PyAV.
- **Practical rule:** keep 3D in OpenGL Manim or three.js, and render Blender only for still assets or short hero clips (≤ 10–20 s, about 10–15 min of EEVEE).

### Gaps
- EEVEE and Cycles were not measured on this PC, and the cited per-frame figures are for unspecified scenes.
- Manim OpenGL parallelism and its feature coverage (MathTex, `Text`, updaters) on Windows were not tested beyond one scene.
- Remotion itself was not benchmarked: there was no Remotion project and it needs an `npm` install. The Puppeteer screenshot loop approximates its per-frame cost, but not its concurrency scheduling or audio muxing.
- Parallel multi-tab capture timed out (`Page.captureScreenshot`) in headless Chrome 156, so whether concurrency helps on this PC is open. Faster capture paths (WebGL readback via CDP, in-page WebCodecs/MediaRecorder) were not measured. The render-only loop at 338–409 fps suggests large headroom.
- Scene-to-scene variance is unmeasured. Heavier three.js scenes (volume rendering, post-processing, high-poly anatomy) will be slower than the test scene.

---

## Key Question 6: Is an interactive 3D web lesson (three.js scrollytelling served by the local web UI) cheaper or better than an MP4, and how can it also be exported to video? Which references exist and under what licenses? (covers objective d)

### Takeaway
- The flagship interactive explainers (Transformer Explainer, LLM Visualization, Diffusion Explainer and CNN Explainer) are all **MIT-licensed**, so their code and ideas can be studied and adapted with attribution.
- An interactive three.js lesson is **cheaper to produce than an MP4**: no render pass is needed, real-time frames cost about 1 ms of GPU time, and the scene doubles as the source for the video. It is also **better for exploration**: the learner can scrub, rotate and change inputs.
- But it **cannot be delivered through Telegram as-is**, because the web UI listens on 127.0.0.1. The practical design is one scene codebase producing two outputs: the interactive page for the desktop UI, and an MP4 captured with deterministic frame stepping for Telegram.

### Cited Findings
- **Transformer Explainer** (Georgia Tech Polo Club): "runs a live GPT-2 model right in your browser". **MIT license**. The paper appeared at CHI 2026 (arXiv 2408.04619). Repo files suggest a Svelte, Tailwind and Vite stack. ~9.1k stars, last push 2026-06-06 ([GitHub](https://github.com/poloclub/transformer-explainer)).
- **LLM Visualization** (Brendan Bycroft, bbycroft.net/llm):
  - A 3D interactive visualization of a GPT-style LLM "running inference".
  - The working weights belong to a tiny minGPT letter-sorting model. GPT-2-size networks are supported, but their weights are not downloaded.
  - Stack: Next.js and TypeScript.
  - **MIT**, except the personal homepage and third-party assets ([GitHub](https://github.com/bbycroft/llm-viz)).
  - ~5.6k stars, last push 2026-08-10 ([GitHub API](https://github.com/bbycroft/llm-viz)).
- **Diffusion Explainer** (Polo Club): "Visual Explanation for Text-to-image Stable Diffusion". **MIT**. Last push 2024-08-31 ([GitHub](https://github.com/poloclub/diffusion-explainer)).
- **CNN Explainer** (Polo Club): "Learning Convolutional Neural Networks with Interactive Visualization". **MIT**. Last release 0.9.1 (2020), last push 2023-10-14 ([GitHub](https://github.com/poloclub/cnn-explainer)).
- **Runtime cost:** in AA-3D, "every model's median frame takes under 1.3 ms of GPU time, well within the 16.7 ms budget for 60 fps", for agent-built three.js scenes ([AA article](https://artificialanalysis.ai/articles/aa-3d)).
- **Deterministic capture building blocks:**
  - Remotion `<ThreeCanvas>` ties R3F to `useCurrentFrame()` and needs `gl: "angle"` ([docs](https://www.remotion.dev/docs/three)).
  - Remotion's free license covers an individual ([LICENSE.md](https://cdn.jsdelivr.net/npm/remotion/LICENSE.md)).
  - A custom Puppeteer loop that calls `renderAt(t)` and then screenshots worked on this PC: headless Chrome 156 with three.js 0.181 [local measurement; numbers in Key Question 5].
- **Teaching Monster:** teams used word-level timestamps from forced alignment (faster-whisper) to trigger animations ([arXiv 2608.08852v1](https://arxiv.org/html/2608.08852v1)). The same timestamps can drive scroll or timeline cues in a web lesson.

### Inferences
- **Cost:** an interactive lesson removes the render step: zero GPU minutes per lesson, versus about 6–60 min for MP4 depending on the 3D share. LLM cost is about the same, since the same three.js scenes are written. Added work is a scroll or timeline controller and audio sync, which is a one-time template.
- **Quality:** interactivity helps "what if" exploration (temperature in attention, number of diffusion steps, CT projection count) and lets the learner pause and rotate 3D anatomy. Video gives guaranteed pacing with narration and works on a phone through Telegram.
- **Reach constraint:** the sotawhat UI is bound to 127.0.0.1:8765, so Telegram links to the interactive lesson only work on the same machine unless a tunnel or LAN binding is added. That is a security decision outside this research. MP4 remains the Telegram format.
- **Recommended architecture:**
  1. Each scene is a pure function of time, `renderAt(t)` (R3F with `useCurrentFrame`, or vanilla three.js), with no `requestAnimationFrame`-driven state.
  2. In the web UI, a timeline/scroll controller maps narration timestamps to `t`.
  3. For video, Puppeteer (or Remotion, free for an individual) steps `t` frame by frame and pipes JPEG/PNG frames to FFmpeg, then muxes the TTS track.
  4. Manim scenes are embedded in the web lesson as pre-rendered MP4/WebM segments.
- **Reuse of references:** all four explainers are MIT, so adapting patterns or code (for example the GPT-2-in-browser approach from Transformer Explainer) into sotawhat is permitted with the copyright notice. Third-party assets inside llm-viz are excluded.

### Gaps
- I did not verify whether Transformer Explainer uses ONNX Runtime Web or WebGPU, nor whether llm-viz renders with WebGL or WebGPU; the README only shows Next.js/TypeScript files.
- No user study compares interactive 3D lessons with narrated MP4 for physicians or for AI learning outcomes. Code2Video's human study covers MP4 only.
- Browser-side encoding (WebCodecs, MediaRecorder) as an alternative to headless capture was not researched or measured.
