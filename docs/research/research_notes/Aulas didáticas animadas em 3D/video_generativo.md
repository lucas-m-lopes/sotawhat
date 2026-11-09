# Generative video (text-to-video / image-to-video) for auto-generated 3D-style didactic lessons: models, prices, accuracy, local and rented compute, data terms (state as of 2026-11-09)

Conventions used in these notes:
- Pages were fetched on 2026-11-09 unless another date is given.
- "[STALE?]" marks a price or claim from before about 2026-08-09, or an undated secondary source.
- "$/s" means USD per second of output video.
- "AA" is the Artificial Analysis Video Arena. Its price column is "the cost to generate one minute of video on the creator's API at the benchmarked settings (1080p where offered)" ([AA I2V](https://artificialanalysis.ai/video/leaderboard/image-to-video)). I converted $/min to $/s by dividing by 60.
- AA's Elo comes from blind human preference votes, and Kling 3.0 1080p (Pro) is the anchor at 1000 ([AA T2V](https://artificialanalysis.ai/video/leaderboard/text-to-video)).

## 1. Which models are current on 2026-11-09, which is cheapest at acceptable quality, and which gives the best quality per dollar?

### Takeaway
The market changed a lot during 2026:
- Sora is gone. The OpenAI Videos API shut down on 2026-09-24.
- Veo 3.1 now ranks below the Kling 3.0 anchor.
- The arena is led by Chinese models: Wan 3.0 for text-to-video (T2V), Seedance 2.5 for image-to-video (I2V), and the MiniMax H3 family. H3 also ships open weights, and its licence excludes the US, EU, UK and South Korea but not Brazil.

The best quality per dollar comes from three options:
- **MiniMax H3:** Elo 1161 T2V and 1133 I2V at $0.08/s for 768p on the official API, or $0.04/s at 768p through fal's "H3 Max Turbo" (standard price from 2026-11-16; $0.028/s on promo until then).
- **HeyGen Video 1:** about $0.04/s, Elo 1153 / 1124.
- **Pika H3 Flex:** about $0.035/s, Elo 1124 / 1115. It is built on H3.

The cheapest options at lower but acceptable quality are:
- PixVerse V6 at $0.045/s (720p, silent).
- Seedance 1.x and Kling 2.5/2.6 legacy endpoints at about $0.02–0.07/s.
- Hosted Wan 2.2 (open, Apache-2.0) at about $0.003–0.01/s for 480p.

### Cited Findings

#### 1a. Artificial Analysis leaderboard snapshot (overall boards, fetched 2026-11-09)
Sources: [AA text-to-video](https://artificialanalysis.ai/video/leaderboard/text-to-video) and [AA image-to-video](https://artificialanalysis.ai/video/leaderboard/image-to-video). The page shows no snapshot date, only "Updated" badges.

| Model | Creator | T2V Elo | I2V Elo | Released | AA price $/min → $/s |
|---|---|---|---|---|---|
| Wan 3.0 | Alibaba | 1175 (rank 1–2) | 1108 | Aug 2026 | $12.00 → $0.20 |
| Utopai X | Utopai Studios | 1168 | 1151 | Sep 2026 | no API |
| MiniMax H3 (768p) | MiniMax | 1161 | 1133 | Jul 2026 | $4.80 → $0.08 |
| Dreamina Seedance 2.5 | ByteDance Seed | 1155 | 1161 (I2V #1) | Jul 2026 | $34.12 → $0.569 |
| FLUX 3 Max | fal / Black Forest Labs | 1154 | 1068 | Oct 2026 | $4.35 → $0.0725 |
| HeyGen Video 1 | HeyGen | 1153 | 1124 | Oct 2026 | $2.40 → $0.04 |
| MiniMax H3 Max | fal / MiniMax | 1147 | 1115 | Aug 2026 | $9.60 → $0.16 |
| SkyReels V4 | Skywork AI | 1138 | 1125 | Mar 2026 | $21.00 → $0.35 |
| FLUX 3 | Black Forest Labs | 1137 | 1071 | Jul 2026 | $17.40 → $0.29 |
| Dreamina Seedance 2.0 | ByteDance Seed | 1137 | 1140 | Mar 2026 | $22.45 → $0.374 |
| P-Video-2-Pro | Pruna AI | 1128 | 1116 | Sep 2026 | $5.70 → $0.095 |
| Gemini Omni Flash 1.1 | Google | 1128 | 1044 | Aug 2026 | $9.12 → $0.152 |
| Pika H3 Flex | Pika Art | 1124 | 1115 | Oct 2026 | $2.10 → $0.035 |
| Hyperflow H3 | Video Rebirth | n/a | 1120 | Sep 2026 | $9.00 → $0.15 |
| HiDream-O1-Video-1.0 | HiDream | n/a | 1101 | Aug 2026 | $5.80 → $0.097 |
| Agnes-Video-2.5 | Sapiens AI | 1063 | 1105 | Aug 2026 | $2.40 → $0.04 |
| Grok Imagine Video 1.5 | "SpaceXAI" (xAI) | 1056 | 1049 | May 2026 | $15.00 → $0.25 |
| HappyHorse-1.1 | Alibaba-ATH | 1049 | 1035 | Jun 2026 | $10.80 → $0.18 |
| MAGI-2 Preview | Sand.ai | 1040 | 965 | Sep 2026 | "Coming soon" |
| Wan2.7-260612 | Alibaba | 1037 | n/a | Jun 2026 | $9.00 → $0.15 |
| HappyHorse-1.0 | Alibaba-ATH | 1031 | 1023 | Apr 2026 | $14.40 → $0.24 |
| Vidu Q4 Preview | Vidu (Shengshu) | n/a | 1031 | Oct 2026 | $5.04 → $0.084 |
| Kling 3.0 Omni 1080p (Pro) | KlingAI | 1020 | 1002 | Feb 2026 | $8.40 → $0.14 |
| Kling 3.0 1080p (Pro), anchor | KlingAI | 1000 | 1000 | Feb 2026 | $10.08 → $0.168 |
| Grok Imagine Video 1.5 Lite | "SpaceXAI" | 989 | 1000 | Aug 2026 | $8.40 → $0.14 |
| PixVerse V6 | PixVerse | 981 | 959 | Mar 2026 | $6.90 → $0.115 |
| Veo 3.1 | Google | 965 | 956 | Jan 2026 | $24.00 → $0.40 |
| Veo 3.1 Fast | Google | 956 | 937 | Jan 2026 | $7.20 → $0.12 |
| Veo 3.1 Lite | Google | 949 | 931 | Mar 2026 | $4.80 → $0.08 |
| LTX-2.5 Fast / Pro | Lightricks | 942 / 939 | 911 / 914 | Aug 2026 | $7.80 / $10.20 → $0.13 / $0.17 |
| Vidu Q3 Pro / Turbo | Vidu | 939 / 910 | 926 / 902 | Jan / Feb 2026 | $7.20 / $3.90 → $0.12 / $0.065 |
| LTX-2.3 Pro / Fast | Lightricks | 884 / 840 | 838 / 832 | Mar 2026 | $4.80 / $3.60 → $0.08 / $0.06 |
| Boreal | Creatify | 828 | n/a | Sep 2026 | $2.69 → $0.045 |

- **Silent leaderboards.** The narration will be dubbed separately, so the silent boards are the relevant ones.
  - T2V "No Audio" top 5: HeyGen Video 1 (1146), MiniMax H3 Max (1139), FLUX 3 Max (1138), Wan 3.0 (1137), Utopai X (1135) ([AA T2V FAQ](https://artificialanalysis.ai/video/leaderboard/text-to-video)).
  - I2V silent top: Utopai X (1155), Seedance 2.5 (1127), Bach 1.0 Pro (1125), Hyperflow H3 (1123), MiniMax H3 Max (1123) ([AA I2V FAQ](https://artificialanalysis.ai/video/leaderboard/image-to-video)).
- **Open weights according to AA.**
  - T2V: MiniMax H3 (768p) 1161, Pika H3 Flex 1124, LTX-2.5 Fast 942 ([AA T2V](https://artificialanalysis.ai/video/leaderboard/text-to-video)).
  - I2V: MiniMax H3 1133, Hyperflow H3 1120, Pika H3 Flex 1115. Hyperflow H3 leads the silent I2V open-weights board at 1123 ([AA I2V](https://artificialanalysis.ai/video/leaderboard/image-to-video)).
  - AA does not list MAGI-2 Preview or HappyHorse among its open-weights leaders, even though other sources describe both as open (see 1c).

#### 1b. Chinese models: specs and prices (16:9; per-second prices exactly as published)

| Model (vendor) and latest version | Weights / licence | Access routes found | 720p $/s | 1080p $/s | Max clip | Native audio | I2V and first/last frame | Multi-shot / refs / camera |
|---|---|---|---|---|---|---|---|---|
| **Kling 3.0** and **3.0 Omni ("O3")**, Kuaishou, Feb 2026 | API only | Official Kling developer API (prepaid packs, smallest $9.80, units expire) ([costbench](https://costbench.com/software/ai-media-apis/kling-api/)); fal v3 Std/Pro T2V/I2V and O3 ref-to-video/edit ([fal pricing](https://fal.ai/pricing)); also Krea, Novita, EvoLink, WaveSpeed via 302.ai ([search summary](https://www.krea.ai/blog/kling-3-0-api-access-guide-pricing-code-examples-for-multi-shot-ai-video)) | Official, per secondary sources: about $0.084 silent, $0.112 with audio ([aireiter](https://aireiter.com/blog/kling-3-api-pricing-guide-2026)) [STALE?]. fal v3 Pro: $0.112 audio off, $0.168 audio on, $0.196 with voice control ([fal llms](https://fal.ai/models/fal-ai/kling-video/v3/pro/text-to-video/llms.txt)) | Official, per secondary sources: about $0.112 silent, $0.14 with audio ([aireiter](https://aireiter.com/blog/kling-3-api-pricing-guide-2026)). AA: $0.168 for Pro 1080p | 15 s (3–15 s) ([fal](https://fal.ai/models/fal-ai/kling-video/v3/pro/text-to-video/llms.txt)) | Yes, on by default. Voices only in Chinese and English; other languages are translated to English ([fal](https://fal.ai/models/fal-ai/kling-video/v3/pro/text-to-video/llms.txt)) | I2V endpoints exist ([fal pricing](https://fal.ai/pricing)). First/last frame not verified | `multi_prompt` sets per-shot prompts and durations; `shot_type` "intelligent" lets the model pick shots; O3 has reference-to-video. No camera parameter on fal ([fal](https://fal.ai/models/fal-ai/kling-video/v3/pro/text-to-video/llms.txt)) |
| Kling 2.5 Turbo Pro / 2.6 Pro (legacy, cheaper) | API only | fal | $0.07 for both ([fal pricing](https://fal.ai/pricing)); resolution not stated | n/f | n/f | n/f | I2V yes | n/f |
| **MiniMax H3** (base), **H3 Max**, **H3 Max Turbo**. H3 is "the omni-modal video model behind the Hailuo line" ([ComfyUI wiki](https://comfyui-wiki.com/en/news/2026-08-03-minimax-h3-open-weights-comfyui)). API from 2026-07-31; weights 2026-08-03 | H3 base: open weights under the MiniMax H3 Community License (see Q5). Max and Turbo are fal post-trained variants ([fal llms](https://fal.ai/models/minimax/h3-max/text-to-video/llms.txt)) | Official MiniMax API; fal (T2V, I2V, ref-to-video) ([fal pricing](https://fal.ai/pricing)); Atlas Cloud, Segmind, muapi | Official H3: $0.08 at 768p, 2K at $0.13, 2K regeneration $0.05 ([Atlas guide citing platform.minimax.io](https://www.atlascloud.ai/blog/guides/minimax-h3-api-pricing); [developersdigest](https://www.developersdigest.tech/models/video-generation/minimax)). fal H3 Max Turbo: 480p $0.025, 768p $0.04 (standard from 2026-11-16; promo $0.0175 / $0.028 until 2026-11-15) ([fal llms](https://fal.ai/models/minimax/h3-max-turbo/text-to-video/llms.txt)). fal H3 Max: 768p $0.08 standard ($0.056 promo) ([fal llms](https://fal.ai/models/minimax/h3-max/text-to-video/llms.txt)) | fal Turbo $0.08; fal Max $0.16. On fal, 1080p is a "latent refinement from a native 768P source" ([fal](https://fal.ai/models/minimax/h3-max-turbo/text-to-video/llms.txt)) | 15 s (fal: 0.92–15 s). Open weights: 4–15 s at 24 fps ([HF](https://huggingface.co/MiniMaxAI/MiniMax-H3)) | Yes, 32 kHz stereo generated jointly with video ([HF](https://huggingface.co/MiniMaxAI/MiniMax-H3)) | Open "FL2VA" checkpoint takes text only, a first frame, a last frame, or both ([HF](https://huggingface.co/MiniMaxAI/MiniMax-H3)). fal's T2V schema has no frame inputs | "Ref2VA" takes up to 9 images, 3 video clips and 3 audio clips ([HF](https://huggingface.co/MiniMaxAI/MiniMax-H3)). Camera only through the prompt (no parameter on fal) |
| **Seedance 2.0** (Fast, Mini), Mar 2026; **Seedance 2.5**, Jul 2026; ByteDance Seed | API only | BytePlus ModelArk: official, token or resource-pack billing, "100+ countries", US excluded ([The Decoder](https://the-decoder.com/bytedance-rolls-out-seedance-2-0-to-100-countries-but-keeps-the-us-off-the-list/)); fal 2.0 Fast/Mini T2V/I2V/ref-to-video ([fal pricing](https://fal.ai/pricing)); Atlas Cloud and others | fal 2.0 Fast: $0.2419. Tokens = h×w×duration×24/1024 at $0.0112 per 1k tokens; audio costs nothing extra ([fal llms](https://fal.ai/models/bytedance/seedance-2.0/fast/text-to-video/llms.txt)). fal 2.0 Mini lists $0.007 per 1k tokens ([fal pricing](https://fal.ai/pricing)), which I estimate at about $0.151 at 720p. Seedance 2.5: about $0.10 at 480p (BytePlus list per a third party) ([yottalabs](https://www.yottalabs.ai/post/seedance-2-5-vs-seedance-2-0-differences-which-to-use-2026)) | Seedance 2.0: AA $0.374. Seedance 2.5: AA $0.569, consistent with about $0.57 "BytePlus list" ([yottalabs](https://www.yottalabs.ai/post/seedance-2-5-vs-seedance-2-0-differences-which-to-use-2026)). fal 2.0 Fast has no 1080p | 2.0: 4–15 s ([fal](https://fal.ai/models/bytedance/seedance-2.0/fast/text-to-video/llms.txt)). 2.5: 30 s per most third-party sources; not officially confirmed ([search summary](https://docs.apiyi.com/en/live/2026-08/seedance-2-5-launch)) | Yes: SFX, ambient and lip-synced speech ([fal](https://fal.ai/models/bytedance/seedance-2.0/fast/text-to-video/llms.txt)) | I2V and reference-to-video endpoints ([fal pricing](https://fal.ai/pricing)) | Multi-shot "cut scene" works by prompt only. "Director-level" camera is claimed but has no parameter ([fal](https://fal.ai/models/bytedance/seedance-2.0/fast/text-to-video/llms.txt)) |
| Seedance 1.5 Pro / 1.0 Pro Fast (legacy, cheaper) | API only | fal | 1.5 Pro lists $1.2 per 1M tokens and 1.0 Pro Fast $1 per 1M tokens ([fal pricing](https://fal.ai/pricing)). With the same token formula I estimate about $0.026 and $0.022 at 720p, but I have not checked this on the model pages | about $0.058 and $0.049 (my estimate, same caveat) | n/f | n/f | I2V yes | n/f |
| **Wan 3.0** (public beta 2026-08-06, launched 2026-08-24) and Wan 2.7 (Jun 2026); Alibaba | Closed / API only. "Wan2.2 (July 2025) … the last open-weight video flagship" ([TNW](https://thenextweb.com/news/alibaba-wan3-video-model-after-share-sale)). No Wan 3.0 weights as of 2026-10-27 ([nemovideo](https://www.nemovideo.com/blog/ai-video-models/wan-3-0-open-source)) | Alibaba Cloud Model Studio (international) and Qwen Cloud; access is application-based ([TNW](https://thenextweb.com/news/alibaba-wan3-video-model-after-share-sale)). fal "Prime" tier, CometAPI, EmpirioLabs ([search summary](https://www.alibabacloud.com/help/en/model-studio/wan3-0-video)) | $0.10 per press and Qwen Cloud ([TNW](https://thenextweb.com/news/alibaba-wan3-video-model-after-share-sale)). The Model Studio Singapore help table shows about $0.0825; I could not fetch the page (HTTP 588), so this is from a search snippet ([help page](https://www.alibabacloud.com/help/en/model-studio/wan3-0-video)). fal Prime: $0.14 | $0.20 per press and AA; about $0.165 per the Singapore table; fal Prime $0.28 | 30 s (Wan 2.7: 15 s) ([TNW](https://thenextweb.com/news/alibaba-wan3-video-model-after-share-sale)) | Synchronized facial micro-expressions and multilingual voice; native audio generation not stated explicitly ([TNW](https://thenextweb.com/news/alibaba-wan3-video-model-after-share-sale)) | Inputs: text, images, audio, video, web pages, PDFs and PPT ([TNW](https://thenextweb.com/news/alibaba-wan3-video-model-after-share-sale)) | Company claim: keeps "character detail, props, spatial layout, and motion graphics" consistent across the clip. No independent benchmark ([TNW](https://thenextweb.com/news/alibaba-wan3-video-model-after-share-sale)) |
| **HappyHorse 1.0 / 1.1** (Apr / Jun 2026), Alibaba-ATH | Claimed open on GitHub with commercial licensing; the Hugging Face release was incomplete ([Atlas Cloud, Apr 2026](https://www.atlascloud.ai/blog/ai-updates/happyHorse-hits-1-api-coming-soon)) [STALE?]. AA does not list it as open weights | AA: creator API | n/f | AA: $0.18 (1.1) / $0.24 (1.0) | n/f | n/f | n/f | about 15B parameters; "about 38 s for a 5-s 1080p video on a single H100" (secondary) ([Atlas Cloud](https://www.atlascloud.ai/blog/ai-updates/happyHorse-hits-1-api-coming-soon)) |
| **Vidu Q3 Pro / Turbo** (Jan–Feb 2026), **Q4 Preview** (Oct 2026); Shengshu | API only | Vidu API (official page not retrieved); Krea, GMI Cloud, 302.AI, Atlas Cloud | Krea: $0.1617 at both 720p and 1080p, $0.0735 at 540p ([Krea](https://www.krea.ai/docs/api-reference/video/vidu-q3.md)). Atlas: $0.07 flat, 12 s cap, resolution unclear ([Atlas](https://www.atlascloud.ai/blog/guides/vidu-q3-api-guide)) [STALE?] | AA: Q3 Pro $0.12, Q3 Turbo $0.065, Q4 Preview $0.084. GMI: Q3 Pro $0.16 ([GMI](https://docs.gmicloud.ai/model-quickstarts/video/vidu-q3-pro-t2v.md)) | 12 s per Atlas (unverified) | Yes, "native audio and smart cuts" ([Atlas](https://www.atlascloud.ai/blog/guides/vidu-q3-api-guide)) | n/f | n/f |
| **PixVerse V6** (Mar 2026) | API only | fal (T2V, I2V, extend) | $0.045 silent, $0.060 with audio ([fal llms](https://fal.ai/models/fal-ai/pixverse/v6/text-to-video/llms.txt)) | $0.090 silent, $0.115 with audio (same source) | 1–15 s | Optional (`generate_audio_switch`: BGM, SFX, dialogue) | I2V endpoint; first/last frame not documented | `generate_multi_clip_switch` gives multi-clip "dynamic camera changes". Has a **`3d_animation` style** preset (also clay, anime, comic, cyberpunk) ([fal llms](https://fal.ai/models/fal-ai/pixverse/v6/text-to-video/llms.txt)) |
| **SkyReels V4** (Mar 2026), Skywork (Kunlun) | API only. V1–V3 were open; V4 weights not released ([WaveSpeed review](https://wavespeed.ai/blog/posts/skyreels-v4-review)) | AA: creator API | n/f | AA: $0.35 | n/f | n/f | n/f | n/f |
| **MAGI-2 Preview** (2026-08-05), Sand.ai | **Open.** Apache-2.0 per the HF card; 114B MoE with about 6B active parameters ([ComfyUI wiki](https://comfyui-wiki.com/en/news/2026-08-05-magi-2-preview); [HF](https://huggingface.co/sand-ai/MAGI-2-preview)) | Self-host. Hosted API "coming soon" (AA) | n/a | n/a | 10 s with synchronized audio ([ComfyUI wiki](https://comfyui-wiki.com/en/news/2026-08-05-magi-2-preview)) | Yes | n/f | n/f |
| **HunyuanVideo 1.5** (Nov 2025; no "2.0" found), Tencent | Open, Tencent Hunyuan Community License. One source says it excludes the EU, UK and South Korea ([search summary](https://huggingface.co/tencent/HunyuanVideo-1.5)) [STALE?] | Self-host; Wan2GP | n/a | n/a | n/f | n/f | 480p step-distilled I2V (8 or 12 steps) ([HF](https://huggingface.co/tencent/HunyuanVideo-1.5)) | n/f |
| **Wan 2.2** (2025-07-28), Alibaba | **Open, Apache-2.0**. Variants: T2V-A14B and I2V-A14B (480p/720p), TI2V-5B (720p at 24 fps) ([GitHub](https://github.com/Wan-Video/Wan2.2)) | Replicate, WaveSpeedAI, SiliconFlow, fal, 8Scale and many others | Hosted 480p examples: about $0.015 per 5 s at 8Scale; $0.05 per 5 s at WaveSpeed ([aiidelist, Oct 2026](https://aiidelist.com/blog/cheapest-wan-2-2-api-pricing-2026)); Replicate fast 480p I2V $0.05 per video and fast 720p T2V $0.10 per video ([Replicate launch post](https://replicate.com/blog/wan-22)) [STALE?]; SiliconFlow $0.29 per video for A14B ([SiliconFlow](https://www.siliconflow.com/articles/cheapest-video-multimodal-models)) | n/a (720p max) | about 5 s ("5-second 720P") ([GitHub](https://github.com/Wan-Video/Wan2.2)) | No (S2V variant is speech-to-video) | I2V yes | Camera only through the prompt |
| Step-Video (StepFun), CogVideoX (Zhipu) | Open (2025 releases) | n/f | n/f | n/f | n/f | n/f | n/f | No 2026 releases found; absent from both AA boards |

#### 1c. Western and other models

| Model (vendor), latest | Weights | Access routes | 720p $/s | 1080p $/s | Max clip | Audio | Notes |
|---|---|---|---|---|---|---|---|
| **Veo 3.1 / Fast / Lite**, Google. Lite preview since 2026-03-31 | API only | Gemini API (Brazil is on the list of available countries ([AI Studio regions](https://aistudio.google.com/docs/available-regions.md.txt))), Vertex AI | Lite $0.05; Fast $0.10 since 2026-04-07 (was $0.15); Standard $0.40 ([The Decoder](https://the-decoder.com/googles-veo-3-1-lite-cuts-video-generation-costs-by-more-than-half/); [benchlm](https://benchlm.ai/media-pricing/veo)) [STALE?] | Lite $0.08 ([benchlm](https://benchlm.ai/media-pricing/veo)). AA: Lite $0.08, Fast $0.12, Std $0.40 | Lite: 4, 6 or 8 s ([The Decoder](https://the-decoder.com/googles-veo-3-1-lite-cuts-video-generation-costs-by-more-than-half/)) | n/f | I could not find Veo rows on the current Gemini pricing page (2026-11-09 fetch; the page is about 100k characters and was read in two parts) ([AI Studio pricing](https://aistudio.google.com/docs/pricing)). Veo prices here are therefore secondary or from AA |
| **Gemini Omni 1.2 Flash** (`gemini-omni-1.2-flash`), Google | API only | Gemini API | about $0.07 (5,792 tokens/s); 360p $0.023 | $0.104 (upsampled); 4K $0.209 (upsampled) ([AI Studio pricing](https://aistudio.google.com/docs/pricing)) | n/f | "Native audio", not priced separately | No free tier. Omni 1.1 is deprecated and requests route to 1.2 from 2026-12-03. Paid-tier data "Used to improve our products: No" ([AI Studio pricing](https://aistudio.google.com/docs/pricing)) |
| **Sora 2 / 2 Pro**, OpenAI | n/a | **Discontinued.** Sora app and web closed 2026-04-26; Videos API and sora-2 / sora-2-pro shut down 2026-09-24 ([OpenAI model doc](https://developers.openai.com/api/docs/models/sora-2.md); [dev.to](https://dev.to/mr_manushukla/sora-2-and-the-videos-api-shut-down-on-24-september-2026-the-migration-and-the-real-cost-per-second-bek)). The current OpenAI pricing page has no video section ([OpenAI pricing](https://developers.openai.com/api/docs/pricing)) | n/a | n/a | n/a | n/a | |
| **Runway Gen-4.5** | API only | Runway API (separate credit wallet) | About $0.12 (12 credits/s at $0.01), after a cut from 25 credits/s in mid-June 2026 ([magichour](https://magichour.ai/blog/runway-gen-45-pricing); [flexprice](https://flexprice.io/pricing-index/runway)) [STALE?] | same | n/f | n/f | Not on AA's current boards |
| **Luma Ray3.2** (Luma Agents API, Jun 2026); Ray3.14 | API only | Luma API | About $0.06 ($0.30 per 5-s clip) | About $0.24 ($1.20 per 5-s clip) ([WaveSpeed blog](https://wavespeed.ai/blog/cost-and-billing/luma-ai-pricing/)) [STALE?] | n/f | n/f | Not on AA's current boards. No "Ray 4" found |
| **LTX-2.5** (2026-08-11) and LTX-2.3 (Mar 2026), Lightricks | **Open.** LTX-2.x Community License: free under $10M annual revenue; gated HF repo ([DataNorth](https://datanorth.ai/news/ltx-releases-ltx-2-5-open-weights-video-world-model); [RunPod](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod)) | LTX API, fal, self-host | n/f | AA (LTX API): 2.5 Fast $0.13, 2.5 Pro $0.17, 2.3 Fast $0.06, 2.3 Pro $0.08 | "Auto duration"; no maximum stated ([RunPod](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod)) | Yes, one pass | 22B parameters; native multi-shot in one prompt; first/last-frame-to-video (FLF2V); up to 4K HDR, 50 fps ([RunPod](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod)) |
| **FLUX 3 / FLUX 3 Max**, Black Forest Labs (Jul / Oct 2026) | Not determined | fal (T2V and I2V) | fal FLUX 3 Max: $0.085, resolution not stated ([fal pricing](https://fal.ai/pricing)) | AA: Max $0.0725; FLUX 3 $0.29 | n/f | n/f | FLUX 3 Max is #3 on the silent T2V board (1138) |
| **Grok Imagine Video 1.5 / 1.5 Lite**, xAI ("SpaceXAI" on AA) | API only | fal | $0.14 (480p $0.08) ([fal llms](https://fal.ai/models/xai/grok-imagine-video/v1.5/image-to-video/llms.txt)) | $0.25 | 1–15 s | "with audio" | 1–7 reference images at $0.01 each. Authorized callers may relax the safety checker ([fal llms](https://fal.ai/models/xai/grok-imagine-video/v1.5/image-to-video/llms.txt)) |
| **HeyGen Video 1** (Oct 2026) | n/f | n/f (AA lists a creator API) | n/f | AA: $0.04 | n/f | n/f | #1 on the silent T2V board (1146) |
| **Pika H3 Flex** (2026-10-29), Pika | **Open:** two LoRA adapters on unchanged MiniMax H3 base weights ([aiwiki](https://aiwiki.ai/wiki/pika_h3_flex); [HF](https://huggingface.co/Pika-Labs/Pika-H3-Flex)) | Pika API; self-host | n/f | AA: $0.035 | n/f | Yes | Six sampling steps instead of 50. Pika claims a 15-s 768p clip in about 7 s of transformer compute (vendor claim) ([aiwiki](https://aiwiki.ai/wiki/pika_h3_flex/raw); [digg](https://digg.com/ai/aa83tsqk)) |
| P-Video-2-Pro (Pruna, Sep 2026); Utopai X (no API) | n/f | n/f | n/f | AA: $0.095; Utopai has no API | n/f | n/f | Elo 1128 / 1116 and 1168 / 1151 ([AA](https://artificialanalysis.ai/video/leaderboard/text-to-video)) |

#### 1d. Other cited points
- fal's summary pricing page lists PixVerse V6 at "$0.005 per seconds" and Grok Imagine 1.5 at "$0.01 per seconds" ([fal pricing](https://fal.ai/pricing)). The per-model pages give $0.025–0.115/s and $0.08–0.25/s ([PixVerse llms](https://fal.ai/models/fal-ai/pixverse/v6/text-to-video/llms.txt); [Grok llms](https://fal.ai/models/xai/grok-imagine-video/v1.5/image-to-video/llms.txt)). fal says the authoritative current price is at `https://fal.ai/models/<endpoint-id>/llms.txt`, and it does not charge for server errors or queue time ([fal pricing](https://fal.ai/pricing)).
- Kling 3.0's official per-second rates come only from secondary sources, and they disagree:
  - EvoLink: $0.075/s versus "$0.084 on the official Kling API" ([EvoLink](https://evolink.ai/blog/kling-3-api-pricing-integration-guide)).
  - CostBench (Oct 2026): $0.056–0.42/s ([costbench](https://costbench.com/software/ai-media-apis/kling-api/)).
  - Another guide: $0.10–0.48/s ([search summary](https://magichour.ai/blog/kling-ai-pricing)).
- Reseller prices for Wan 3.0 vary: EmpirioLabs Standard $0.07 / $0.14 / $0.28 for 480p / 720p / 1080p, and fal "Prime" $0.068 / $0.14 / $0.28 ([search summary](https://www.alibabacloud.com/help/en/model-studio/wan3-0-video)). A 30% launch discount ended on 2026-09-23 (same source).
- Atlas Cloud advertises "MiniMax H3 Developer … From $0.02 per Second" ([Atlas](https://www.atlascloud.ai/blog/tips/wan-3.0-vram-requirements)). This is vendor marketing and I did not verify it.
- On DesignArena, Pika H3 Flex was reported at 1293 Elo, 7th overall and the top open entry, ahead of MiniMax H3 at 1277 ([AlphaSignal](https://alphasignal.ai/news/pika-drops-h3-flex-an-open-video-model-generating-audio-1-8x-faster)).

### Inferences
- **"Acceptable quality."** I use Kling 3.0 Pro (Elo 1000) as the bar. On that basis, the cheapest acceptable options in $/s are:

  | Option | $/s | Elo T2V / I2V |
  |---|---|---|
  | Pika H3 Flex | 0.035 | 1124 / 1115 |
  | HeyGen Video 1 | 0.04 | 1153 / 1124 |
  | Agnes 2.5 | 0.04 | 1063 / 1105 |
  | fal H3 Max Turbo, 768p, standard | 0.04 | no own Elo; it is a variant of H3 Max (1147 / 1115) |
  | FLUX 3 Max | 0.0725–0.085 | 1154 / 1068 |
  | MiniMax H3, official 768p | 0.08 | 1161 / 1133 |

  - The cheapest Chinese option at or above that bar is the MiniMax H3 family: $0.028–0.04/s on fal Turbo, $0.08/s official, or self-hosted from the open weights.
  - Kling 3.0 ($0.084–0.168/s) and Wan 3.0 ($0.08–0.20/s) cost 2–5 times the fal H3 Turbo price per second, and up to about 2.5 times the official H3 price.
  - Seedance 2.5 costs 7–14 times more for the best I2V. It is only worth it for a rare "hero" shot.
- **Quality-per-dollar outliers.** A 161-point Elo gap (MiniMax H3 at 1161 vs Kling at 1000) is about a 72% head-to-head preference (standard Elo formula). H3 delivers it at about half of Kling's AA price.
  - Veo 3.1 Standard (965, $0.40/s) is poor value for this use case.
  - Veo 3.1 Lite ($0.05/s, 949) is cheap but below the anchor.
- **Disable native audio.** Narration will be Brazilian Portuguese TTS added separately. Kling's voices only cover Chinese and English. Silent tiers are cheaper: Kling on fal $0.112 vs $0.168; PixVerse $0.045 vs $0.06.
- **PixVerse V6's `3d_animation` style** is the only explicit "3D-animation look" control I found. At $0.045/s for 720p it suits stylised B-roll, even though it ranks below the anchor.
- **Image-to-video with a programmatic first frame** is the most controllable route for consistency. Open H3 FL2VA and LTX-2.5 FLF2V accept both first and last frames, so the start and end states can be pinned to frames rendered in code.

### Gaps
- I could not retrieve these official price pages:
  - Kling developer platform.
  - MiniMax platform (I relied on third parties quoting it, plus AA).
  - BytePlus ModelArk (docs page did not load).
  - Alibaba Model Studio (HTTP 588/502).
  - Vidu.

  The figures attributed to them are therefore secondary or come from AA. AA's price is for 1080p and the "creator API" at benchmark settings.
- I found no 2026 information on Step-Video (StepFun) or CogVideoX (Zhipu); neither appears on the AA boards.
- I did not verify Together AI's video catalogue or prices. The SiliconFlow figures come from its own marketing article.
- Not verified:
  - Veo 3.1 first/last-frame support and maximum length for Standard and Fast.
  - Camera-control parameters for most models (fal schemas expose none for Kling 3, H3 or Seedance 2.0; camera is prompt-only).
  - Access routes for HeyGen Video 1, P-Video-2-Pro and Agnes.
  - FLUX 3 weights status.
- I found no per-model measurement of on-screen text legibility (see Q3).

## 2. What does 30–60 s of usable footage per lesson really cost once discarded takes are counted?

### Takeaway
Practitioners report roughly one usable shot per 3 generations at best, and 1 in 4 to 1 in 10 is common. With that:
- **30–60 s of usable B-roll costs about $3–30** with the cheap tier (MiniMax H3 Turbo, Pika H3 Flex, HeyGen, PixVerse, Veo Lite at $0.03–0.05/s).
- It costs about **$6–67** with mid-tier models (Gemini Omni Flash, H3 official, Wan 3.0, Kling 3.0 at $0.07–0.11/s).
- It costs **$20–340** with premium models (Seedance 2.x, Veo 3.1 Standard).
- **It costs under $1–6** when hosting open models such as Wan 2.2 or HunyuanVideo 1.5 at 480p, or self-hosting on a rented RTX 4090.

Accuracy-critical shots will need more retries than decorative ones.

### Cited Findings
- **Generations per usable shot.**
  - The most-cited figure is about 3 generations per usable shot ([invideo FAQ](https://invideo.io/faq/how-many-ai-video-generations-do-you-need-per-usable/)).
  - A documented 3-minute animated episode generated 164 clips and kept 41, a 25% keep rate ([invideo FAQ](https://invideo.io/faq/how-many-ai-video-generations-do-you-need-per-usable/)).
  - A horror short used "~400 video generations for 90 seconds of finished film" ([invideo](https://invideo.io/faq/how-many-ai-video-generations-do-you-need-per-usable/)).
  - Another source puts the keep rate at "roughly one keeper in ten" ([search summary of invideo/ClipSpeed pages](https://www.clipspeed.ai/blog/ai-video-generation-cost.html)).
- **Usable seconds per generation.** Editors kept about 5 usable seconds from each 15-second generation, and each 15-s clip held 4–7 usable shot candidates ([invideo](https://invideo.io/faq/what-percentage-of-ai-generated-video-clips-are-actually-2/)).
- **All-in cost per minute.** The episode cost about $950, or about $315 per finished minute. invideo gives a range of $315–750 per finished minute, depending on team and complexity, and about $23 per final-cut clip versus under $6 per raw generation ([invideo](https://invideo.io/faq/what-is-the-true-cost-per-usable-ai-video-clip-when-you/)). These figures are vendor-published and include labour.
- **No universal keep rate.** ClipSpeedAI says there is no reliable typical keep rate. It depends on the model, the shot and the prompt. Its formula is cost per attempt × attempts per keeper ([ClipSpeed](https://www.clipspeed.ai/blog/ai-video-generation-cost.html)).
- **List prices.** HeyGen's 2026 comparison found list prices of 3–40 cents per second. Its cost-per-usable-second scores did not include any retry multiplier ([HeyGen](https://www.heygen.com/blog/ai-video-cost-per-second)).
- **Billing granularity.** These details reduce waste from over-length takes:
  - H3 accepts 0.92–15 s durations ([fal](https://fal.ai/models/minimax/h3-max-turbo/text-to-video/llms.txt)).
  - PixVerse accepts 1–15 s ([fal](https://fal.ai/models/fal-ai/pixverse/v6/text-to-video/llms.txt)).
  - Veo 3.1 Lite only offers 4, 6 or 8 s ([The Decoder](https://the-decoder.com/googles-veo-3-1-lite-cuts-video-generation-costs-by-more-than-half/)).
  - WaveSpeed's Wan 2.2 has a 5-s minimum ([aiidelist](https://aiidelist.com/blog/cheapest-wan-2-2-api-pricing-2026)).

### Inferences
- **Cost formula and table.** Cost = usable seconds (U) × generated-to-usable ratio (R) × $/s. R=3 is the optimistic B-roll case and R=10 the pessimistic or accuracy-constrained case. Per-second prices come from Q1 (720p-class, silent where possible).

  | Option | $/s | 30 s, R=3 | 30 s, R=10 | 60 s, R=3 | 60 s, R=10 |
  |---|---|---|---|---|---|
  | Wan 2.2 hosted 480p, 8Scale | 0.003 | $0.27 | $0.90 | $0.54 | $1.80 |
  | Wan 2.2 hosted 480p, WaveSpeed or Replicate | 0.01 | $0.90 | $3.00 | $1.80 | $6.00 |
  | MiniMax H3 Max Turbo 768p, fal promo until 2026-11-15 | 0.028 | $2.52 | $8.40 | $5.04 | $16.80 |
  | Pika H3 Flex (AA price) | 0.035 | $3.15 | $10.50 | $6.30 | $21.00 |
  | H3 Max Turbo 768p, fal standard / HeyGen Video 1 | 0.04 | $3.60 | $12.00 | $7.20 | $24.00 |
  | PixVerse V6 720p silent | 0.045 | $4.05 | $13.50 | $8.10 | $27.00 |
  | Veo 3.1 Lite 720p | 0.05 | $4.50 | $15.00 | $9.00 | $30.00 |
  | Gemini Omni 1.2 Flash 720p | 0.07 | $6.30 | $21.00 | $12.60 | $42.00 |
  | MiniMax H3 official 768p | 0.08 | $7.20 | $24.00 | $14.40 | $48.00 |
  | Kling 3.0 official 720p silent (secondary price) | 0.084 | $7.56 | $25.20 | $15.12 | $50.40 |
  | Wan 3.0 720p (press price) | 0.10 | $9.00 | $30.00 | $18.00 | $60.00 |
  | Kling 3.0 Pro silent (fal) | 0.112 | $10.08 | $33.60 | $20.16 | $67.20 |
  | Seedance 2.0 Fast 720p (fal) | 0.2419 | $21.77 | $72.57 | $43.54 | $145.14 |
  | Veo 3.1 Standard | 0.40 | $36.00 | $120.00 | $72.00 | $240.00 |
  | Seedance 2.5 1080p (AA) | 0.569 | $51.21 | $170.70 | $102.42 | $341.40 |
  | Self-host HunyuanVideo 1.5 480p distilled on a RunPod RTX 4090 community pod (Q4; assumes about 240 s of video per GPU-hour) | about 0.0014 | $0.13 | $0.43 | $0.26 | $0.85 |

- **Daily-lesson budget.** With one lesson a day at 60 s of generative B-roll and R=3–4 on a $0.04/s model, the cost is about $7–10 per lesson, or about $220–290 a month. Restricting generative video to 15–20 s of hero shots per lesson cuts that by 3–4 times. Programmatic animation has near-zero marginal cost (local CPU/GPU rendering).
- **Keep rates for explanatory shots.** These will likely be worse than the B-roll figures above. Any visible anatomical, physical or labelling error disqualifies a take (see Q3), so for "explanatory" use R≈10 is the realistic planning number. That is a further argument for keeping generative shots decorative.
- **Cutting waste.**
  - Generate at 480p or 768p for selection, then re-render or upscale only the keepers. fal H3 1080p is a latent refinement of 768p anyway.
  - Request exact durations.
  - Use image-to-video from a programmatic still so composition is not left to chance.

### Gaps
- I found no practitioner retry data specific to scientific or educational content. All ratio data comes from entertainment workflows and mostly from one vendor (invideo), so it should be measured in-house.
- I found no published retry statistics per model, for example whether H3 needs fewer retries than Kling.

## 3. How well do these models depict scientific and technical processes (accuracy, labels, physics)? Do moderation filters block medical imagery? And where does generative video fit: explanatory visuals or decorative B-roll?

### Takeaway
Every benchmark I found points the same way. Current video generators produce visually convincing footage but are poor at:
- causal or physical correctness (Physics-IQ),
- surgical and medical semantics (SurgVeo, MedGen),
- legible on-screen text (T2VTextBench),
- the logic and layout needed to teach (Code2Video). There, pixel-based models scored near zero on logic flow and layout, while code-generated Manim videos taught measurably better.

The arena leaderboards rank human aesthetic preference, not correctness.

So generative video belongs in the decorative or "hero" layer: establishing shots, atmosphere, and metaphorical 3D B-roll, optionally animated from a programmatic still with first/last-frame locks. Mechanisms such as attention, denoising, RL post-training, CT reconstruction, segmentation, the EHR-to-discharge-summary flow, and molecular or cellular processes should be programmatic animations, with text overlaid in code. Moderation evidence is anecdotal: surgical imagery is a known false-positive category, and clinical framing without gore tends to pass.

### Cited Findings
- **Code2Video** (Show Lab; arXiv 2510.01174, Oct 2025) [STALE? but still the key study].
  - Setup: a benchmark of 456 professionally produced Manim tutorial videos across 13 subjects, from the 3Blue1Brown corpus. Baselines were Veo3, Wan2.2 and OpenSora-v2.
  - Result: "Pixel-based models are inadequate for educational video synthesis, scoring near zero on logic flow and element layout, and failing to transfer knowledge in TeachQuiz." Code generation gave about 30% higher TeachQuiz scores ([Emergent Mind](https://www.emergentmind.com/papers/2510.01174); [Moonlight review](https://www.themoonlight.io/review/code2video-a-code-centric-paradigm-for-educational-video-generation)).
  - These are the authors' own results without independent replication. An "88.1% vs 6.0% for Veo3" figure appears only in a blog post.
- **Physics-IQ** (Google DeepMind; WACV 2026). Physical understanding in generative video models is "severely limited, and unrelated to visual realism" ([CVF](https://openaccess.thecvf.com/content/WACV2026/html/Motamed_Do_Generative_Video_Models_Understand_Physical_Principles_WACV_2026_paper.html)).
  - Physics-IQ Verified (arXiv 2606.18943, June 2026) refined 57.6% of samples and changed rankings (Kendall τ = 0.46) ([papers.cool](https://papers.cool/arxiv/2606.18943)).
  - The top Verified score is 58.2 ± 1.8 (Magi-1 24B + GeoPhys with best-of-N, added 2026-06-19). On the original board, Magi-1 + GeoPhys scores 64.5% and Cosmos3-Super + WMReward 63.4% ([GitHub](https://github.com/google-deepmind/physics-IQ-benchmark)). Both are well below 100, and the leaders rely on best-of-N selection.
- **VBench-2.0** (Mar 2025) [STALE?]. It adds "intrinsic faithfulness" dimensions, including Physics (mechanics, material, state change) and Commonsense. It evaluated HunyuanVideo, CogVideoX-1.5, Sora-480p and Kling 1.6, and found struggles in controllability, physics and commonsense ([arXiv](https://arxiv.org/abs/2503.21755)). I found no live 2026 leaderboard.
- **SurgVeo** (arXiv 2511.01775, Nov 2025).
  - Method: four board-certified surgeons scored Veo-3 continuations of 8 s from a laparoscopic or neurosurgical frame.
  - Visual plausibility was "exceptional", but the model "fails critically at higher levels" of the Surgical Plausibility Pyramid (instrument operation, tissue response, surgical intent). The authors call this a "plausibility gap". Neurosurgery was harder ([arXiv](https://arxiv.org/abs/2511.01775); [The Decoder](https://the-decoder.com/googles-veo-3-can-fake-surgical-videos-but-misses-every-hint-of-medical-sense/)).
- **MedGen** (arXiv 2507.05675, Jul 2025). Commercial models (Sora, Pika, Hailuo) "often produce anatomical and instrument-handling errors on medical prompts". The authors built MedVideoCap-55K, a set of over 55k captioned medical clips, to fine-tune a medical video generator ([arXiv](https://arxiv.org/abs/2507.05675)).
- **On-screen text.**
  - T2VTextBench (arXiv 2505.04946, May 2025): "most models struggle to generate legible, consistent text" across 10 T2V systems ([Emergent Mind](https://www.emergentmind.com/papers/2505.04946)) [STALE?].
  - VTR-Bench (arXiv 2610.01499, Oct 2026) is a newer visual-text-rendering benchmark with an agentic "Director" refinement framework. I did not verify its results ([OpenTrain](https://www.opentrain.ai/papers/vtr-bench-a-systematic-benchmark-for-evaluating-visual-text-rendering-in-video-g--arxiv-2610.01499/)).
- **What the arena measures.** AA ranks by "Elo from blind human preference votes" ([AA](https://artificialanalysis.ai/video/leaderboard/text-to-video)). That is a preference measure, not a measure of scientific accuracy.
- **Wan 3.0 document inputs.** Wan 3.0 accepts PDFs and PowerPoint as inputs and claims stable "motion graphics" and spatial layout. These are company claims with no independent benchmark yet ([TNW](https://thenextweb.com/news/alibaba-wan3-video-model-after-share-sale)).
- **Moderation and medical imagery.**
  - fal endpoints default to `enable_safety_checker: true`. For Kling 3, disabling it "requires account authorization" ([fal Kling](https://fal.ai/models/fal-ai/kling-video/v3/pro/text-to-video/llms.txt)); for Grok, "authorized callers" may relax it ([fal Grok](https://fal.ai/models/xai/grok-imagine-video/v1.5/image-to-video/llms.txt)).
  - Segmind notes that "surgical imagery is a common false-positive category". Its clinically framed surgical-team prompt (gloved hands, no gore) passed on Gemini Omni Flash ([Segmind](https://blog.segmind.com/gemini-omni-flash-keeps-rejecting-your-prompts-9-fixes-that-actually-work/)).
  - Atlas Cloud (a reseller) reports that an anatomy prompt blocked on Hailuo passed with museum-style framing ([Atlas](https://www.atlascloud.ai/blog/guides/hailuo-ai-nsfw-content-restrictions-guide)). This is anecdotal.
  - BytePlus keeps filter-triggered inputs and outputs for 180 days in Malaysia ([BytePlus ModelArk Data Processing](https://docs.byteplus.com/ja/docs/ModelArk/BytePlus_ModelArk_Data_Processing)).
  - I found no official medical-content policy from any vendor.
- **MiniMax H3 acceptable-use policy.** It prohibits "high-risk automated decisions" in critical domains, including "healthcare or medical services" (item 14), and "unauthorized or unlicensed professional activity" including medical practice (item 20) ([LICENSE](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE)).

### Inferences
- **Where generative video fits: decorative and hero shots, not explanations.**
  - Good uses: cinematic establishing shots (hospital ward, CT gantry spinning, GPU data-centre fly-through), abstract "neural" or "latent space" atmospherics, and stylised 3D metaphors.
  - These should be labelled in the lesson as an "ilustração artística" (artistic illustration).
  - Tokens, attention weights, noise schedules, sinograms and back-projection, masks, EHR fields, and molecular structures should be rendered programmatically (Manim, Blender or three.js) so they are exact and their labels are crisp.
- **Hybrid pattern worth testing.** Render the first and last frames programmatically, then use first/last-frame image-to-video (open H3 FL2VA or LTX-2.5 FLF2V) to add camera motion or texture between them. Keep all text out of the generated frames and overlay it afterwards.
  - Even then, models may distort structure mid-clip (the Wan 2.2 5B tests in Q4 showed shape distortion), so each clip needs automated or human QA.
- **Text and narration.** Never rely on generated on-screen text, especially in Portuguese with accents. Composite text and labels in post. Narration is also separate, since native audio voices are Chinese or English only on Kling.
- **Medical topics.** Use clinical, non-gory framing ("schematic", "educational illustration", gloved hands, no blood). Expect occasional false-positive blocks and design fallbacks across two providers.
  - Do not use generative video to depict specific anatomy or surgical steps as if accurate. SurgVeo and MedGen show plausible-looking but wrong content, which is dangerous in a health startup's material.
- **Wan 3.0's PDF/PPT inputs** could be tested for "slide-to-motion-graphics" B-roll. Its motion-graphics consistency claim is unverified.

### Gaps
- I found no 2026 benchmark of scientific or medical process accuracy covering the current top models (Wan 3.0, H3, Seedance 2.5, Kling 3.0).
- I found no study of molecular or cellular animation accuracy.
- I found no per-model text-legibility scores for 2026 models; VTR-Bench results were not verified.
- Vendors publish no explicit medical, anatomical or surgical moderation policies. All moderation evidence is anecdotal or from resellers.
- AA's prompt mix is unknown and likely not scientific.

## 4. Which open-weight models actually run on 8 GB VRAM (RTX 4060, 32 GB RAM, Windows), at what resolution and minutes per clip, and what does the same work cost on a rented GPU?

### Takeaway
On an RTX 4060 8 GB with 32 GB RAM, only heavily quantized or distilled models run, and only with offloading to system RAM:
- **Wan 2.2 14B "Rapid" (4-step):** about 2 min for a 480×480, 33-frame (about 2 s) clip.
- **LTX-2.3 distilled GGUF Q4:** about 21 min for 20 s at 900×1600 on a comparable 8 GB card.
- **HunyuanVideo 1.5:** runs via Wan2GP from 6 GB.
- **MiniMax H3 (33B):** reported at 6–30 min per short clip, from weak sources.
- Wan 2.2 5B at fp8 runs, but its 480p quality was reported as poor.

Rented GPUs are cheap per hour (RTX 4090 $0.34/h community on RunPod, H100 $1.99–3.99/h) and could give about 30–470 s of video per GPU-hour depending on model and resolution. That works out to roughly $0.001–0.04 per output second, 1–2 orders of magnitude below APIs, before setup and idle overhead.

### Cited Findings
- **Wan 2.2 on an RTX 4060 8 GB with 32 GB RAM on Windows 11** ([lilting.ch, published 2026-03-07, updated 2026-05-20](https://lilting.ch/en/articles/wan22-comfyui-rtx4060-i2v)) [STALE?, but the hardware results still apply].
  - Setup: ComfyUI portable with `--lowvram`, running Phr00t's WAN2.2-14B-Rapid-AllInOne (about 22 GB, includes the text encoder and VAE).
  - Settings: 480×480, 33 frames, 4 steps, CFG 1.
  - Result: **111 s in total** (45 s sampling), with about 4.6 GB of the model in VRAM and about 11 GB offloaded to RAM.
  - Wan 2.2 TI2V-5B fp8 at 480×480 ran in 95–114 s but gave distorted shapes and almost no motion. At 768×480 the VAE decode ran out of memory and partly offloaded (179 s). The author concluded that "5B fp8 at 480x480 is simply the quality ceiling."
- **Wan 2.2 official requirements.**
  - TI2V-5B needs at least 24 GB VRAM (RTX 4090) with `--offload_model True --convert_model_dtype --t5_cpu`, and "can generate a 5-second 720P video in under 9 minutes on a single consumer-grade GPU" without specific optimization.
  - The A14B models need at least 80 GB on a single GPU with the official code ([GitHub](https://github.com/Wan-Video/Wan2.2)).
  - LightX2V released 4-step 720p I2V distills (Apr 2026), with a separate config for 24 GB+ cards (RTX 4090) ([HF](https://huggingface.co/lightx2v/Wan2.2-Distill-Models)).
- **LTX-2.3 distilled Q4_K_M GGUF** (Unsloth) on an RTX 3070 8 GB laptop with 32 GB RAM: 20 s of text-to-video at 900×1600 in **21 min**, using about 98% of VRAM, "the limit for an 8GB card" ([Reddit snapshot, captured 2026-03-20](https://reddit.sentinel-team.org/posts/1rxtay2/snapshots/2026-03-20T17%3A36%3A49.07391Z)).
  - A DEV guide recommends LTX-2 at Q3/Q4 for the RTX 4060. Q3_K_M is about 9 GB, with 10–11 GB VRAM suggested, so offloading is needed. It estimates 1–3 min for 1–2 s clips (unverified) ([DEV](https://dev.to/gary_yan_86eb77d35e0070f5/how-to-install-and-configure-ltx-2-gguf-models-in-comfyui-complete-2026-guide-1d3m)).
  - An 8 GB guide warns that VRAM spikes to about 14 GB during upscaling. It does not fail, but it is very slow ([aistudynow](https://aistudynow.com/how-to-run-ltx-2-3-on-an-8gb-gpu-without-oom-errors/)).
- **LTX-2.5 (22B)** has a "16GB VRAM floor" for its quantized variants:
  - 16–24 GB: int8 only, with offloading.
  - 32–48 GB: int8 runs well.
  - 80–96 GB: full bf16 distilled.

  It does not fit an 8 GB card without unofficial GGUFs. Its timing claim of a 10-s 24 fps I2V clip in 6.8 s is measured on 2× NVIDIA GB200; the LTX API takes 23.7 s end-to-end at 1080p ([RunPod](https://www.runpod.io/blog/ltx-2-5-the-open-weights-world-model-built-for-speed-and-how-to-run-it-on-runpod)).
- **HunyuanVideo 1.5** (8.3B). The official card says Wan2GP runs it on "as low 6 GB of VRAM" using an 8-step LoRA accelerator, and that the 480p step-distilled I2V "can generate videos within 75 seconds" on a single RTX 4090 ([HF card via search](https://huggingface.co/tencent/HunyuanVideo-1.5)). Other sources say about 14 GB minimum with offloading and FP8, and 24 GB to be comfortable ([search summary](https://studio.aifilms.ai/blog/tencent-hunyuanvideo-1-5-lightweight-video-generation)).
- **MiniMax H3 (33B dense, BF16).**
  - The repository is about 288 GB ([search summary](https://rits.shanghai.nyu.edu/ai/minimax-ships-h3-weights-with-the-us-and-eu-excluded/)). The official SGLang example uses 4 GPUs ([HF](https://huggingface.co/MiniMaxAI/MiniMax-H3)).
  - It had native ComfyUI support from day one, with multiple quantizations ([ComfyUI wiki](https://comfyui-wiki.com/en/news/2026-08-03-minimax-h3-open-weights-comfyui)), and Hugging Face lists 87 community quantizations ([HF](https://huggingface.co/MiniMaxAI/MiniMax-H3)).
  - Low-VRAM reports: 6–12 min for short low-resolution clips ([MindStudio](https://www.mindstudio.ai/blog/minimax-h3-run-locally-guide)); about 12 min on an RTX 2060 6 GB (user report, per search summary); "10–30 min per clip" for 10-s clips on 8 GB from a low-quality source ([besthub](https://www.besthub.dev/articles/freevideo-runs-33b-minimax-h3-on-8gb-vram-benchmarks-show-10-30-min-per-clip-a5168cf6034a)).
  - RunPod suggests a pod with about 600 GB of disk and gives no VRAM figures ([RunPod](https://www.runpod.io/blog/minimax-h3-the-open-weight-omni-modal-video-model-and-what-it-takes-to-run-it)).
- **Wan2GP** supports Wan, Hunyuan Video, LTXV, LTX-2 and others, with claims of running from 6 GB for some models ([search summary](https://github.com/sriadm/Wan2GP)). One Reddit comment says 8 GB works for distilled LTX 2.3 "if there is plenty of system RAM" (same source).
- **ComfyUI flags.** From ComfyUI v0.18.0, Dynamic VRAM is on by default and `--lowvram` is ignored while it is active ([eastondev, 2026-07-21](https://eastondev.com/blog/en/posts/ai/20260721-comfyui-low-vram-acceleration/)).
- **RunPod pricing** (page "Updated November 4, 2026") ([RunPod pricing](https://www.runpod.io/pricing)):

  | GPU | Community $/h | Secure $/h | Serverless $/h |
  |---|---|---|---|
  | RTX 4090 | 0.34 | 0.89 | 1.34 |
  | RTX 5090 | 0.69 | 1.19 | 1.79 |
  | L40S | 0.79 | 1.09 | 1.75 |
  | A100 80 GB PCIe | 1.19 | 1.79 | 2.72 (A100) |
  | A100 80 GB SXM | 1.39 | 1.79 | 2.72 (A100) |
  | H100 PCIe | 1.99 | 2.89 | 5.39 (H100) |
  | H100 SXM | 2.69 | 3.99 | 5.39 (H100) |
  | H200 | 3.59 | 5.29 | 6.99 |
  | RTX Pro 6000 | 1.69 | 2.49 | 3.49 |
  | B200 | 5.98 | 7.99 | 10.79 |

- **Modal pricing** (per-second billing; hourly figures are the per-second rate × 3600) ([Modal pricing](https://modal.com/pricing)):
  - GPUs: H100 $3.95/h, A100 80 GB $2.50/h, L40S $1.95/h, RTX PRO 6000 $3.03/h, L4 $0.80/h, B200 $6.25/h.
  - Region selection multiplies prices by 1.15–1.75×. Functions are preemptible by default.
  - Free credits: Starter $30/month, Team $100/month.
- **Vast.ai.** The pricing page did not render live per-GPU prices. It only says interruptible instances are "50%+ cheaper" than on-demand ([Vast.ai](https://vast.ai/pricing)).
- **Throughput data points.**
  - HappyHorse: about 38 s per 5-s 1080p clip on one H100 (secondary) ([Atlas](https://www.atlascloud.ai/blog/ai-updates/happyHorse-hits-1-api-coming-soon)).
  - Wan 2.1 720p, not distilled: about 284 s on an H100 [STALE?] ([InstaSD](https://instasd.com/post/wan2-1-performance-testing-across-gpus)).
  - LightWan2.2 720p I2V at 4 steps: 26.7 s on a Blackwell GPU, frame count not stated ([HF](https://huggingface.co/sisniha/LightWan2.2-A14B)).
  - LTX-2: about 1.5 min for a 5-s clip on a 4090 ([evezone](https://evezone.evetech.co.za/build-lab/how-to-set-up-local-ai-video-generation-with-wan-and-ltx-2)).
  - Wan 2.2 4-step: an RTX 4070 Super user reported 61 frames at 1280×720 in about 5 min (anecdotal; from a search summary of the [Wan2.2-Lightning HF discussions](https://huggingface.co/lightx2v/Wan2.2-Lightning/discussions/26); I did not open the post).

### Inferences
- **Practical local menu for the RTX 4060.**
  1. Wan 2.2 14B Rapid or LightX2V 4-step GGUF at 480p for 2–3 s shots, about 2–4 min each. Expect roughly 1 min of compute per second of 480p video.
  2. LTX-2.3 distilled Q4 GGUF for longer 720p-class shots with audio. This is roughly 1 min of compute per second of video, extrapolating the 3070 result.
  3. HunyuanVideo 1.5 via Wan2GP for 480p I2V.

  MiniMax H3 is technically possible but slow (10+ minutes per clip, weak evidence) and needs over 200 GB of disk for the repository. LTX-2.5 and MAGI-2 (114B) are not practical on 8 GB. Overnight batch runs of a few dozen short 480p clips are realistic. 720p/1080p "hero" quality is not.
- **Steady-state cost per output second on rented GPUs.** These assume no retries and exclude cold-start, model download and idle time:

  | Model on GPU | Price used | Throughput assumption | ≈ $/s |
  |---|---|---|---|
  | HunyuanVideo 1.5 480p distilled on RunPod 4090 community | $0.34/h | 75 s per clip, about 5-s clips (clip length is my assumption), about 240 s of video per hour | 0.0014 |
  | LTX-2 on a 4090 | $0.34/h | about 200 s of video per hour | 0.0017 |
  | HappyHorse 1080p on H100 PCIe community | $1.99/h | about 470 s of video per hour | 0.004 |
  | Wan 2.2 TI2V-5B 720p, unoptimized, on a 4090 | $0.34/h | at least 33 s of video per hour | 0.01 |
  | Wan 2.1 720p, not distilled, on H100 SXM | $2.69/h | about 63 s of video per hour | 0.04 |

  - Self-hosting is 10–50× cheaper per raw second than the $0.04–0.08/s APIs. However, the cheap self-hostable models (Wan 2.2, HunyuanVideo 1.5, LTX-2.x) rank well below H3, Seedance and Wan 3.0 in quality.
  - Self-hosting H3 or Pika H3 Flex on an H100 or RTX Pro 6000 is the interesting middle ground, but I found no H100 timing for it.
- **Modal's free credits.** The $30/month Starter credit is about 15 L40S-hours or 7.6 H100-hours before region multipliers. That is enough for monthly experiments at no cash cost.
- **Workflow.** Spot or community pods suit batch rendering. Serverless costs about 2–4× more per hour but avoids idle time for sporadic jobs (RunPod 4090: $1.34/h serverless vs $0.34/h community).

### Gaps
- I found no RTX 4060 benchmark for LTX-2.3 or 2.5, HunyuanVideo 1.5, or MiniMax H3 with stated resolution, frames and time.
- I found no reliable H100, L40S or 4090 timings for MiniMax H3, Pika H3 Flex or LTX-2.5 at 720p.
- Vast.ai live prices were not retrievable.
- Seconds-per-GPU-hour figures are derived from heterogeneous single reports and should be benchmarked.

## 5. Which API providers state no training on inputs or zero retention, are any unavailable from Brazil, and what are the licensing limits for later commercial use by a Brazilian health startup?

### Takeaway
**Terms by provider:**
- **Google (Gemini API, paid tier), BytePlus ModelArk and Alibaba Model Studio** all state that customer API data is not used for training. BytePlus adds "without prior authorization", and Alibaba advertises a zero-data-retention control for enterprise customers.
- **Replicate** deletes API inputs and outputs after 1 hour.
- **fal** keeps request payloads for 30 or 90 days by default (its docs conflict) unless storage is disabled per request. Its docs do not state a training policy.
- **Kling's** consumer terms reportedly grant Kling a licence to use inputs and outputs for training.

**Availability from Brazil:**
- Nothing found is blocked. The Gemini API lists Brazil, and Seedance excludes the US, not Brazil.
- The MiniMax H3 and Hunyuan licences exclude the US, EU and UK (and Korea), not Brazil.
- Sora no longer exists anywhere.

**Commercial-reuse licences:** the cleanest are Apache-2.0 (Wan 2.2; MAGI-2 per its card) and the LTX licence (free under $10M revenue).

### Cited Findings
- **Google.** The Gemini API pricing page marks paid-tier data "Used to improve our products: No" and free-tier data "Yes". The Gemini Omni video models have no free tier ([AI Studio pricing](https://aistudio.google.com/docs/pricing)). Brazil is on the Gemini API and AI Studio list of available countries ([AI Studio regions](https://aistudio.google.com/docs/available-regions.md.txt)). Vertex AI has a São Paulo region (southamerica-east1) for Gemini models, but Veo was not confirmed there ([Google Cloud locations](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations)).
- **OpenAI.** The Sora API was removed on 2026-09-24 ([OpenAI model doc](https://developers.openai.com/api/docs/models/sora-2.md)).
- **fal.**
  - Retention period: the data-retention doc says "Request inputs and outputs are stored in the platform for **90 days** by default" ([fal data retention](https://fal.ai/docs/model-apis/data-retention)). Another fal doc snippet said 30 days ([fal media expiration via search](https://docs.fal.ai/documentation/model-apis/media-expiration)), so the two conflict.
  - Controls: the `X-Fal-Store-IO: 0` header disables payload storage. CDN expiry is set with `X-Fal-Object-Lifecycle-Preference`.
  - Zero data retention is "not enabled by default", so contact sales.
  - The doc does not address training ([fal data retention](https://fal.ai/docs/model-apis/data-retention)). A reseller (Opper) claims fal does not train on customer data, which I could not verify ([Opper](https://opper.ai/provider/fal)).
- **Replicate.** "All input parameters, output values, and logs are automatically removed after an hour, by default" for API predictions ([Replicate docs](https://replicate.com/docs/topics/predictions/data-retention); [changelog 2023-01-04](https://replicate.com/changelog/2023-01-04-api-prediction-data-no-longer-stored)). I found no statement on training.
- **BytePlus ModelArk** (Seedance).
  - "Without the customer's prior authorization, BytePlus ModelArk will neither interfere with the data processing nor use Customer Data for its own model training."
  - It acts as a data processor.
  - Filter-triggered inputs and outputs are kept for 180 days in Malaysia, and processing may happen in Malaysia, Indonesia or the EU/EEA ([ModelArk Data Processing](https://docs.byteplus.com/ja/docs/ModelArk/BytePlus_ModelArk_Data_Processing)).
  - Seedance 2.0 is offered to businesses in "over 100 countries", excluding the US ([The Decoder](https://the-decoder.com/bytedance-rolls-out-seedance-2-0-to-100-countries-but-keeps-the-us-off-the-list/); [CnTechPost, 2026-04-14](https://cntechpost.com/2026/04/14/bytedance-opens-seedance-2-0-api-globally-openai-retreats/)). Brazil is not named. Some guides say self-serve API access is limited or B2B-only ([search summary](https://www.glbgpt.com/hub/seedance-2-0-public-availability-which-countries-have-access-api-status/)).
- **Alibaba Model Studio** (Wan).
  - The platform "does not train models on customer data" ([privacy notice](https://help.aliyun.com/en/model-studio/privacy-notice)), and "input and output data from API calls are not used for model training or optimization" ([agreements](https://docs.agent.bailian.aliyun.com/en/resources/agreements)).
  - A zero-data-retention control exists for enterprise international inference customers ([data retention policy](https://www.alibabacloud.com/help/en/model-studio/data-retention-policy)). A third-party aggregator says ZDR is not offered, so this conflicts ([standardcompute](https://standardcompute.com/providers/alibaba)).
  - International deployment modes involve cross-border computation ([search summary](https://alibabacloud.com/help/en/model-studio/what-is-model-studio)).
  - Wan 3.0 API access is application-based ([TNW](https://thenextweb.com/news/alibaba-wan3-video-model-after-share-sale)).
- **Kling.** A third-party analysis of Kling's Terms of Service says users grant Kling "a broad, royalty-free license to use both the content users submit and the AI-generated outputs" for purposes including AI model training. It cites Section 4.7.3(f) reserving the right to train on inputs ([ConductAtlas](https://conductatlas.com/platform/kling-ai/kling-ai-terms-of-service/user-content-license/)).
  - Another rating site describes a "revocable opt-out" and a vague retention period ("as long as necessary") ([VerifyWise](https://verifywise.ai/ai-trust-index/kling-ai)).
  - I could not read the official API privacy policy text ([Kling API privacy policy](https://kling.ai/document-api/guides/protocols/privacy-policy.md)).
- **MiniMax H3 Community License** (dated 2026-08-02) ([LICENSE](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE)):
  - "Excluded Territories" means the EU, UK, Republic of Korea and USA.
  - The grant is non-exclusive and royalty-free.
  - Above 20 million US dollars of yearly revenue, prior written authorization is needed (api@minimax.io).
  - Commercial products must "prominently display" the MiniMax H3 name in the UI, and a NOTICE file is required for distribution.
  - Outputs may not be used to improve other AI models.
  - MiniMax "claims no rights over the Outputs".
  - The acceptable-use policy contains the healthcare restrictions quoted in Q3.
  - RunPod reads the licence as not authorizing use, including use of outputs, in those territories ([RunPod](https://www.runpod.io/blog/minimax-h3-the-open-weight-omni-modal-video-model-and-what-it-takes-to-run-it)).
- **Other open-weight licences.**
  - Wan 2.2: "licensed under the Apache 2.0 License" ([GitHub](https://github.com/Wan-Video/Wan2.2)).
  - MAGI-2 Preview: Apache-2.0 on the HF card ([HF](https://huggingface.co/sand-ai/MAGI-2-preview)). One wiki says no licence breakdown was published.
  - LTX-2.5: LTX-2.x Community License, free for organisations under $10M annual revenue, with custom agreements above that. Transferring fine-tunes may need a paid licence ([DataNorth](https://datanorth.ai/news/ltx-releases-ltx-2-5-open-weights-video-world-model)).
  - HunyuanVideo: Tencent Hunyuan Community License. The original version excluded the EU, UK and South Korea and applied a 100M monthly-active-user threshold ([search summary](https://www.maginative.com/article/tencent-launches-hunyuanvideo-an-open-source-ai-video-model/)) [STALE?]. LightX2V's distilled HunyuanVideo 1.5 models claim Apache-2.0, which contradicts the official licence ([HF](https://huggingface.co/lightx2v/hy1.5-distill-models)).
  - Pika H3 Flex ships as LoRA adapters on H3 base weights ([aiwiki](https://aiwiki.ai/wiki/pika_h3_flex)). It probably depends on the H3 licence, but I have not verified that.

### Inferences
- **For personal study now:**
  - Gemini API (paid; Veo 3.1 Lite or Omni Flash), BytePlus and Alibaba have the clearest no-training language among the APIs.
  - fal is the most convenient aggregator. Send `X-Fal-Store-IO: 0` and set a short CDN lifecycle, and do not send private material until there is a contractual no-training commitment (DPA).
  - Replicate's 1-hour deletion is the best default retention found.
  - Avoid Kling's first-party consumer terms for anything proprietary, since inputs and outputs may be licensed back to Kling.
- **Patient data.** Never put identifiable patient data (LGPD "sensitive data") in prompts or reference images for any of these services. Several process data cross-border (BytePlus in Malaysia, Indonesia or the EU; Alibaba international). Lessons should use synthetic EHR examples.
- **If a Brazilian health startup reuses the lessons later:**
  - Outputs from self-hosted H3 used in Brazil are allowed (Brazil is not an excluded territory, and the revenue threshold is $20M).
  - However, any US or EU distribution or hosting is outside the licence, and the "display MiniMax H3 name in UI" duty applies to commercial products.
  - Apache-2.0 Wan 2.2 (and MAGI-2, if its licence is confirmed) carry the fewest strings.
  - LTX is free while revenue stays under $10M.
  - For API-generated footage, re-check each vendor's output-ownership clause before commercial reuse. Of the models covered here, I verified this only for H3, where MiniMax claims no rights over outputs.

### Gaps
- I did not find MiniMax's API (hosted) data-use and retention terms, Kling's official API privacy text, or the WaveSpeedAI, Together AI and SiliconFlow retention and training policies.
- I did not find explicit Brazil availability lists for BytePlus ModelArk, Alibaba Model Studio international, Kling or MiniMax developer platforms. Whether Veo is served from Vertex AI's São Paulo region is also unconfirmed.
- I could not check the output-ownership and commercial-use clauses of the API ToS for Kling, Seedance/BytePlus, Wan/Alibaba, PixVerse, Vidu, Google and HeyGen.
- I did not research LGPD or ANVISA implications of using AI-generated medical imagery in startup marketing or educational content.
- The fal retention period (30 vs 90 days) and its training policy are unresolved.
