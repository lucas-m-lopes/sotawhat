# Narration (pt-BR TTS), presenter avatars, background music, subtitles and delivery for automated 3D-animated lessons — state as of 2026-11-09

Scope and conventions used throughout these notes:
- Lesson = ~5 min, ~750 words, **4,500 characters** of pt-BR narration. Cost per lesson = price per 1M characters × 0.0045. "8 lessons/month" is used as a reference volume. All prices in USD, checked on 2026-11-09 unless another date is given.
- "Commercial?" flags matter because the content may later be reused by a health startup. **NC** = non-commercial license.
- Hardware target: RTX 4060 8 GB, Ryzen 5 5500, 32 GB RAM, Windows 11, Python 3.12.
- Some facts were gathered by parallel sub-researchers who fetched the cited pages on 2026-11-09. Items marked "(snippet)" were taken from search-result summaries rather than from a fully read page. Items marked "(secondary)" come from aggregators or blogs, not vendors.

## Q1. What is the cheapest natural-sounding pt-BR TTS, via API and locally? Which Chinese TTS actually support Brazilian Portuguese well?

### Takeaway
**Cheapest via API:**
- **Google Chirp 3 HD** has 30 dedicated pt-BR voices and 1M free characters a month, so 8 lessons cost $0; beyond that it is $30/1M, or $0.135 per lesson.
- **Azure Neural pt-BR** costs $15/1M ($0.068 per lesson) and is the strongest for code-switching control.
- **Among Chinese APIs**, Alibaba **qwen3-tts-flash** is the cheapest at $10/1M ($0.045 per lesson), but it ranks low on the English-centric arena.
- **ElevenLabs v4** is the most natural (arena #1) at $80/1M ($0.36 per lesson).

**Cheapest locally:** **Qwen3-TTS 1.7B** (Apache-2.0) is the best commercially usable model. On the shared multilingual test set it beats MiniMax on Portuguese WER and has the highest speaker similarity, though ElevenLabs Multilingual v2 still has lower WER. It runs at about 1.8× real time on a Windows RTX 4060 with CUDA graphs. A Brazilian developer judged its pt-BR "acceptable" but flat.

**Which Chinese TTS handle pt-BR:**
- Only ByteDance Seed Speech exposes an explicit `pt-br` locale with a Brazilian voice.
- Qwen3-TTS and MiniMax publish Portuguese numbers without saying whether they are Brazilian or European.
- CosyVoice (open), IndexTTS and Step-Audio-EditX have no Portuguese.

### Cited Findings

**A. Chinese TTS: Portuguese support, naturalness and license**

| Product (latest, Nov 2026) | pt-BR support | Naturalness evidence | Open weights / license |
|---|---|---|---|
| **MiniMax speech-2.8-hd/turbo** (2.6 and 02 are now "Legacy") — [pricing](https://platform.minimax.io/docs/guides/pricing-paygo) | `language_boost` includes "Portuguese"; Brazilian vs European not stated; pt-BR preset voice IDs not verified — [T2A API](https://platform.minimax.io/docs/api-reference/speech-t2a-http) | MiniMax-Speech paper, Portuguese: WER 1.877, SIM 0.805, vs ElevenLabs Multilingual v2 at 1.331 / 0.711 — [arXiv 2505.07916](https://arxiv.org/html/2505.07916). Artificial Analysis (AA): 2.8 HD #28 (Elo 1175), 2.8 Turbo #32 — [AA leaderboard](https://artificialanalysis.ai/text-to-speech/leaderboard) | API only |
| **Alibaba Qwen3-TTS** (open, released 2026-01-22) + **qwen3-tts-flash** (API) | 10 languages incl. Portuguese; the 9 preset voices are native zh/en/ja/ko, none Portuguese — [GitHub](https://github.com/QwenLM/Qwen3-TTS) | Same multilingual test set: 12Hz-1.7B-Base Portuguese WER **1.526**, SIM **0.817** (the MiniMax and ElevenLabs reference numbers match the MiniMax paper) — [GitHub](https://github.com/QwenLM/Qwen3-TTS). AA: Qwen3 TTS Flash #92 (Elo 940) — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) | **Apache-2.0** — [GitHub](https://github.com/QwenLM/Qwen3-TTS) |
| **Alibaba Qwen-Audio-3.0 / 3.1-TTS** (API; 3.0 released 2026-07-21) | 16 languages incl. Portuguese, with "full language support rolling out soon" — [Alibaba blog](https://www.alibabacloud.com/blog/qwen-audio-3-0-tts-more-multilingual-easier-to-direct_603379). A 3.1-Flash voice group lists Portuguese (snippet) — [evolink](https://evolink.ai/docs/en/api-manual/audio-series/qwen-audio-tts/qwen-audio-3.1-tts-flash-voices.md) | AA: **3.1-Plus #3 (Elo 1303)**, 3.0-Plus #9 — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard). Vendor: Plus average SIM 82.75, first in all 16 languages — [Alibaba blog](https://www.alibabacloud.com/blog/qwen-audio-3-0-tts-more-multilingual-easier-to-direct_603379) | API only |
| **Alibaba CosyVoice** v3/v3.5 (API) + Fun-CosyVoice3 (open) | API: `pt` accepted in `language_hints` (snippet) — [Alibaba doc](https://www.alibabacloud.com/help/doc-detail/3032843.html); **no Portuguese system voice found** (snippet) — [voice list](https://www.alibabacloud.com/help/en/model-studio/cosyvoice-voice-list). Open model: 9 languages, **no Portuguese** (snippet) — [CosyVoice 3 paper](https://arxiv.org/html/2505.17589v2). For CosyVoice2 the maintainers said "due to our lack of Portuguese voice data, we currently have no plans to support it" (snippet) — [HF discussion](https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B/discussions/4) | Not on AA — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) | Open model has no Portuguese |
| **ByteDance Seed Speech TTS 2.0** (BytePlus; tested via resellers) | **Explicit `pt-br` language code**, no pt-pt; voice `martins_pt` plus multilingual voices that include pt — [fal.ai](https://fal.ai/models/fal-ai/bytedance/seed-speech/tts/v2/llms.txt). Seed Audio 1.0 lists Brazilian Portuguese (snippet) — [Morphic](https://morphic.com/resources/models/seed-audio-1) | None found; not on AA | API only; official BytePlus price page lists no figures — [BytePlus docs](https://docs.byteplus.com/docs/byteplusvoice/texttospeechv2) |
| **Fish Audio** s2.1-pro / drama-3 (API) + S2 Pro (open) | 80+ languages (snippet) — [fish.audio/s2](https://fish.audio/s2/); open S2 Pro tags `pt`, but its top tier is ja/en/zh (snippet) — [HF](https://huggingface.co/fishaudio/s2-pro) | AA: Drama 3 #7 (1275), S2.1 Pro #24 (1188) — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) | **NC**: Fish Audio Research License; commercial use requires contacting Fish (snippet) — [HF](https://huggingface.co/fishaudio/s2-pro) |
| **IndexTTS-2.5** (Bilibili, 2026-08-10) | **No Portuguese** (zh, en, ja, es, ar) — [GitHub](https://github.com/index-tts/index-tts) | Spanish WER 3.75 on CV3-Eval — [GitHub](https://github.com/index-tts/index-tts) | bilibili Model Use License; commercial use requires contacting Bilibili — [GitHub](https://github.com/index-tts/index-tts) |
| **StepFun** Step-Audio-EditX (open) / StepAudio 2.5 TTS (API) | EditX: **no Portuguese** — [GitHub](https://github.com/stepfun-ai/Step-Audio-EditX). 2.5 TTS language list disputed (zh+en vs zh+ja) — [llmreference](https://www.llmreference.com/provider/stepfun/step-audio-2-5-tts), [skills.sh](https://skills.sh/daymade/claude-code-skills/stepfun-tts) | AA: StepAudio 2.5 TTS #19 (1216) — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) | EditX code Apache-2.0 — [GitHub](https://github.com/stepfun-ai/Step-Audio-EditX) |
| **VoxCPM2** (OpenBMB) | Portuguese among 30 languages; variant not stated — [HF](https://huggingface.co/openbmb/VoxCPM2) | No Portuguese numbers | **Apache-2.0, "free for commercial use"** — [HF](https://huggingface.co/openbmb/VoxCPM2) |
| Confucius4-TTS (NetEase Youdao) | 14 languages incl. Portuguese (snippet) — [HF](https://huggingface.co/netease-youdao/Confucius4-TTS) | — | License not checked |

**B. Commercial (non-Chinese) TTS: pt-BR voices and naturalness**

| Vendor / model | pt-BR voices | Naturalness evidence |
|---|---|---|
| **ElevenLabs Eleven v4** (also v4 Turbo, v3, Multilingual v2) | v4 lists "Portuguese (pt)"; only Multilingual v2 names "Portuguese (Brazil, Portugal)"; the accent follows the chosen voice — [models](https://elevenlabs.io/docs/overview/models) | AA **#1, Elo 1339**; v4 Turbo #2 (1335); v3 #23 (1189) — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) |
| **Google Chirp 3 HD** | **30 dedicated `pt-BR-Chirp3-HD-*` voices** — [voice list](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types) | Not in AA top 25 — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) |
| **Google Gemini 3.8 Flash TTS** (Preview) | "Portuguese (Brazil) pt-BR GA" — [Gemini-TTS doc](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts) | AA #6 (1283) — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) |
| **Azure Neural** | 16 pt-BR voices (e.g. Francisca, Antonio, Thalita), ThalitaMultilingual and MacerioMultilingual, DragonHD voices and `pt-BR-Caio:MAI-Voice-2` — [Azure language support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts) | Not in AA top 25 |
| **Amazon Polly** | Camila (generative/neural/standard), Vitória (neural), Thiago (neural), Carolina and Leo (generative) — [Polly voices](https://docs.aws.amazon.com/polly/latest/dg/available-voices.html) | Not in AA top 25 |
| **Cartesia Sonic 3.6** | "Portuguese (`pt`)" among 44 languages; no pt-BR locale confirmed — [Cartesia docs](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest) | AA #4 (1297) — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) |
| **OpenAI gpt-4o-mini-tts / tts-1 / tts-1-hd** | Language support "follows the Whisper model... despite voices being optimized for English" — [OpenAI TTS guide](https://developers.openai.com/api/docs/guides/text-to-speech) | Not in AA top 25. **Deprecated: shutdown 2027-01-06** — [OpenAI TTS guide](https://developers.openai.com/api/docs/guides/text-to-speech) |
| Inworld TTS-2 / TTS-2 Flash | "200+ languages and locales"; Portuguese not explicitly confirmed — [Inworld docs](https://docs.inworld.ai/llms.txt) | AA #10 (1268) / #17 — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) |

- AA ranks with "no language filter, only an accent filter (US/UK)", so its Elo scores are English-centric — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard).
- The Hugging Face TTS Arena V2 leaderboard could not be read (rendered in JavaScript); its V1 is deprecated — [TTS Arena V2 about](https://tts-agi-tts-arena-v2.hf.space/about).

**C. Open-weight (non-Chinese) TTS with pt-BR**

| Model | pt-BR support | Evidence | License / commercial |
|---|---|---|---|
| **Kokoro-82M v1.0** | 3 pt-BR voices (pf_dora, pm_alex, pm_santa), espeak-ng `pt-br` G2P — [VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) | No official grade for the pt-BR voices — [raw VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/raw/main/VOICES.md); an aggregator rates pm_alex "C" (snippet) — [offlinetts](https://offlinetts.com/voice/pm-alex/) | Apache-2.0. Training data includes synthetic audio "generated by closed TTS models from large providers" — [card](https://huggingface.co/hexgrad/Kokoro-82M) |
| **Piper** pt_BR (cadu, edresson, faber, jeff) | 4 voices — [HF tree](https://huggingface.co/rhasspy/piper-voices/tree/main/pt/pt_BR) | STIL-2026: "most stable and reproducible" for neutral speech — [STIL 2026](https://aclanthology.org/2026.stil-1.29.pdf) | Engine GPL-3.0 — [piper1-gpl](https://github.com/OHF-Voice/piper1-gpl). faber CC0, "Finetuned from U.S. English lessac voice" — [card](https://huggingface.co/rhasspy/piper-voices/raw/main/pt/pt_BR/faber/medium/MODEL_CARD); edresson CC BY 4.0 (snippet) — [card](https://huggingface.co/rhasspy/piper-voices/blob/main/pt/pt_BR/edresson/low/MODEL_CARD); jeff unknown |
| **Chatterbox Multilingual V3 + `Chatterbox-Multilingual-pt-br`** | Pack "optimized for Portuguese as spoken in Brazil" — [pt-br card](https://huggingface.co/ResembleAI/Chatterbox-Multilingual-pt-br) | No pt-BR metrics; vendor claims 63.75% preference over ElevenLabs across languages (snippet) — [Resemble](https://resemble.ai/introducing-chatterbox-multilingual-open-source-tts-for-23-languages) | MIT; Perth watermark on every output; "As of August 2026, Chatterbox is retired research and is no longer maintained" — [GitHub](https://github.com/resemble-ai/chatterbox) |
| **NVIDIA Magpie TTS Multilingual 357M v2607** (2026-07-21) | "Brazilian Portuguese" — [NVIDIA blog](https://huggingface.co/blog/nvidia/magpie-tts-multilingual-voice-agents) | **CER 2.91%, SSIM 0.753** on CML-TTS PT — [card](https://huggingface.co/nvidia/magpie_tts_multilingual_357m) | NVIDIA Open Model License, "ready for commercial use"; 5 fixed voices; cloning removed; Linux (NeMo/Riva) — [card](https://huggingface.co/nvidia/magpie_tts_multilingual_357m) |
| Kyutai Pocket TTS (Jan 2026) | "portuguese" listed; variant not stated — [GitHub](https://github.com/kyutai-labs/pocket-tts) | None for Portuguese | Code MIT; weights license not stated on the repo — [GitHub](https://github.com/kyutai-labs/pocket-tts) |
| XTTS-v2 | "Portuguese (pt)" — [card](https://huggingface.co/coqui/XTTS-v2) | STIL-2026: satisfactory neutral speech, flattened emotion — [STIL 2026](https://aclanthology.org/2026.stil-1.29.pdf) | **NC**: CPML "allows only non-commercial use of a machine learning model and its outputs" — [LICENSE](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt) |
| F5-TTS pt-BR (firstpixel) | pt-BR fine-tune — [card](https://huggingface.co/firstpixel/F5-TTS-pt-br) | Card calls it a "preliminary test" | **NC**: CC-BY-NC-4.0 inherited from the base — [card](https://huggingface.co/firstpixel/F5-TTS-pt-br), [SWivid](https://huggingface.co/SWivid/F5-TTS) |
| Mistral Voxtral-4B-TTS-2603 | "Portuguese" — [card](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603) | — | **NC** (CC BY-NC 4.0); needs ≥16 GB — [card](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603) |
| VibeVoice-Realtime-0.5B | "Experimental" PT voice added 2025-12-16 — [GitHub](https://github.com/microsoft/VibeVoice) | Multilingual "not extensively tested" — [doc](https://github.com/microsoft/VibeVoice/blob/main/docs/vibevoice-realtime-0.5b.md) | MIT, but "intended for research and development purposes only" — [GitHub](https://github.com/microsoft/VibeVoice) |
| Higgs Audio v2 | Portuguese not mentioned — [card](https://huggingface.co/bosonai/higgs-audio-v2-generation-3B-base) | — | Boson community license (Llama-3-based); expanded license needed above 100,000 annual active users — [LICENSE](https://huggingface.co/bosonai/higgs-audio-v2-generation-3B-base/blob/main/LICENSE) |
| Orpheus multilingual | Checkpoints zh, hi, es_it, fr, de, ko: **no Portuguese** (snippet) — [collection](https://huggingface.co/collections/canopylabs/orpheus-multilingual-research-release); a community pt-BR LoRA exists (Paraíba accent) — [fala_pb](https://huggingface.co/acidente/fala_pb_checkpoints) | — | Llama-3-based |

**D. pt-BR-specific quality evidence (sparse)**
- **STIL-2026 (UFMT)** is the only head-to-head pt-BR comparison found: ElevenLabs, XTTS-v2, Piper, StyleTTS 2, Kokoro and F5-TTS+RVC.
  - The evaluation was a consensus of 4 team members, with no formal MOS and no blind test.
  - Piper gave the most stable results for neutral speech; Kokoro had trouble with nasal vowels and /ão/.
  - Source: [STIL 2026](https://aclanthology.org/2026.stil-1.29.pdf).
- **Akita on Rails, a Brazilian developer (April 2026)**, ran a weekly podcast on Qwen3 TTS 1.7B for about two months — [Akita on Rails](https://akitaonrails.com/en/2026/04/09/how-elevenlabs-was-not-killed-by-qwen3-tts/).
  - He found its pt-BR "acceptable" but with "Flat intonation, uniform rhythm".
  - English tech terms came out with a Brazilian accent, so he rewrote many English words into Portuguese in the script.
  - He then moved to ElevenLabs `eleven_v3`, where inline emotion tags work in pt-BR.
  - Cost per episode: about $0.08 of GPU time with Qwen3 vs about $2.70 in ElevenLabs credits.
  - His conclusion: "ElevenLabs is still untouchable".
- In the same report, a Portuguese-trained ElevenLabs clone kept a strong Brazilian accent when speaking English, and an `[American accent]` tag was too weak — [Akita on Rails](https://akitaonrails.com/en/2026/04/09/how-elevenlabs-was-not-killed-by-qwen3-tts/).

### Inferences
- **Which Chinese vendors actually do pt-BR:**
  - Only **ByteDance Seed Speech** declares Brazilian Portuguese explicitly (`pt-br`, `martins_pt`), but there is no quality evidence and no official price.
  - **Qwen3-TTS** and **MiniMax** have the best Portuguese evidence among Chinese models, both on the same multilingual test set. On that set, Qwen3-TTS-1.7B-Base beats MiniMax on both WER and similarity, and beats ElevenLabs Multilingual v2 on similarity. Because the test set does not say whether it is Brazilian or European, a pt-BR listening test is still needed before committing.
  - **Qwen-Audio-3.1-Plus** is the Chinese option most likely to sound most natural, given its AA Elo of 1303 at $30/1M. That is an extrapolation from English-centric votes, and its Portuguese coverage was still "rolling out" at the 3.0 launch.
- **Best balance under the budget:** for API, Chirp 3 HD (free at this volume, dedicated pt-BR voices); for local, Qwen3-TTS (free, Apache-2.0, commercially safe). ElevenLabs v4 is the quality ceiling at about $2.88/month for 8 lessons, or a $6/month Starter plan.
- **Avoid for startup reuse:** XTTS-v2, F5-TTS pt-BR, Fish S2 Pro, Voxtral (all NC); VibeVoice (R&D only); and the OpenAI TTS models (shutting down 2027-01-06).

### Gaps
- No blind, pt-BR-specific MOS or arena comparison of the leading candidates was found: Chirp 3 HD, Azure Thalita/Francisca, ElevenLabs v4, Qwen3-TTS, Qwen-Audio-3.1, MiniMax 2.8 and Seed Speech.
- It is unknown whether the multilingual test set used by MiniMax and Qwen is Brazilian or European Portuguese.
- No official BytePlus or Volcengine price, timestamps or data terms were found for Seed Speech; it was seen only through resellers.
- No list of MiniMax pt-BR preset voice IDs was found, and no Qwen-Audio Brazilian voice was confirmed.
- No independent pt-BR evaluation was found for Fish S2, VoxCPM2 or Seed Speech.

## Q2. What does each option cost per 5-minute lesson (4,500 chars), and which give word timestamps? Also pronunciation control, cloning consent and data terms

### Takeaway
At this volume, every credible pt-BR option costs less than $0.50 per lesson:
- Chirp 3 HD costs **$0** inside its 1M-character free tier.
- Alibaba qwen3-tts-flash costs **$0.045**; Azure and Inworld Flash **$0.068**; Chirp 3 HD beyond the free tier, Seed Speech and Qwen-Audio-3.1-Plus **$0.135**.
- MiniMax costs **$0.27–0.45** and ElevenLabs v4 **$0.36**.

Of the cheap options, only some return **word timings**:
- Azure (WordBoundary), MiniMax (`subtitle_type: "word"`), CosyVoice (`word_timestamp_enabled`), Cartesia and Inworld give them natively.
- ElevenLabs gives character-level timings, from which word timings can be built.
- Chirp 3 HD, Gemini TTS, OpenAI and the Qwen TTS APIs give none. Pair them with a forced aligner (see Q6), which is free and accurate because the script is known.

### Cited Findings

**Cost per lesson (4,500 characters; prices checked 2026-11-09; per-lesson figures computed from the cited unit price)**

| Option | Price | Per lesson | 8 lessons/mo | Free tier / commercial terms |
|---|---|---|---|---|
| Alibaba **qwen3-tts-flash** | $0.10 / 10k chars (Singapore) = $10/1M — [Alibaba pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing) | $0.045 | $0.36 | 10,000 free chars (Singapore) — [pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing) |
| Alibaba Qwen-Audio-3.0-TTS-Flash | $0.15 / 10k = $15/1M — [pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing) | $0.068 | $0.54 | — |
| Alibaba **Qwen-Audio-3.1-TTS-Plus** | $0.30 / 10k (Singapore); $0.20 (Beijing) — [pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing) | $0.135 (SG) / $0.09 (BJ) | $1.08 / $0.72 | — |
| Alibaba CosyVoice v3-flash / v3-plus | $0.13 / $0.26 per 10k (SG) — [pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing) | $0.059 / $0.117 | $0.47 / $0.94 | Non-Chinese letters count 1, Chinese characters 2 — [pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing) |
| **MiniMax** speech-2.8-turbo / hd | $60 / $100 per 1M — [MiniMax pricing](https://platform.minimax.io/docs/guides/pricing-paygo) | $0.27 / $0.45 | $2.16 / $3.60 | No free TTS tier stated; resellers $80–130/1M — [fal.ai](https://fal.ai/models/fal-ai/minimax/speech-2.6-hd/llms.txt), [Segmind](https://www.segmind.com/models/minimax-speech/pricing) |
| **ByteDance Seed Speech TTS 2.0** (reseller) | "$0.03 per 1000 characters" — [fal.ai](https://fal.ai/models/fal-ai/bytedance/seed-speech/tts/v2/llms.txt) | $0.135 (WaveSpeed bills started 1k blocks: $0.15, snippet) — [WaveSpeed](https://wavespeed.ai/docs/docs-api/bytedance/bytedance-seed-speech-tts-2.0) | $1.08 | Official BytePlus price not found |
| Fish Audio s2.1-pro | $15 per 1M **UTF-8 bytes** — [Fish docs](https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits) | ≈$0.07 (accented letters take 2 bytes) | ≈$0.56 | s1 retiring 2026-12-31 — [Fish docs](https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits) |
| **ElevenLabs v4** / v3 / Multilingual v2 | $0.08 / 1K chars — [ElevenLabs API pricing](https://elevenlabs.io/pricing/api) | $0.36 | $2.88 (or the $6/mo Starter, which includes 75,000 v4 chars) — [API pricing](https://elevenlabs.io/pricing/api) | The free plan "does **not** include a commercial license" and requires attribution; "All paid plans include a commercial license" — [ElevenLabs help](https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform.md) |
| ElevenLabs v4 Turbo / Flash | $0.04 / 1K — [API pricing](https://elevenlabs.io/pricing/api) | $0.18 | $1.44 | Same |
| **Google Chirp 3 HD** | $30/1M after "0 to 1 million characters" free per month — [Google pricing](https://cloud.google.com/text-to-speech/pricing) | **$0** within the free tier, then $0.135 | **$0** | Spaces and newlines are billed — [pricing](https://cloud.google.com/text-to-speech/pricing) |
| Google Gemini 3.8 Flash TTS (Preview) | $0.50/1M text-in + $9/1M audio-out tokens until 2026-12-31, then $1/$18; 25 audio tokens per second — [pricing](https://cloud.google.com/text-to-speech/pricing) | ≈$0.07, ≈$0.14 from 2027 (300 s × 25 tokens) | ≈$0.54 | No free usage on Cloud — [pricing](https://cloud.google.com/text-to-speech/pricing) |
| Google Neural2 / WaveNet / Standard | $16 / $4 / $4 per 1M; free 1M / 4M / 4M per month — [pricing](https://cloud.google.com/text-to-speech/pricing) | $0.072 / $0.018 / $0.018 | $0 within the free tier | Older voice families (pt-BR Neural2 A–C, WaveNet A–E) — [voices](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types) |
| **Azure Neural (S0)** | $15/1M (Retail Prices API, eastus) — [Azure Retail Prices](https://prices.azure.com/api/retail/prices?$filter=armRegionName%20eq%20'eastus'%20and%20contains(productName,'Speech')) | $0.068 | $0.54 | F0: 0.5M chars/month free — [Azure pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/). **But** the Product Terms grant output use rights "For Customers of the paid tier TTS Service only", and moderators say F0 output is not for commercial use — [Microsoft Q&A, 2026-03-03](https://learn.microsoft.com/en-us/answers/questions/5805156/please-clarify-the-conflicting-information-regardi) |
| Azure Neural HD (DragonHD, MAI-Voice-2) | $22/1M — [Retail Prices](https://prices.azure.com/api/retail/prices?$filter=armRegionName%20eq%20'eastus'%20and%20contains(productName,'Speech')) | $0.099 | $0.79 | — |
| **Amazon Polly** Neural / Generative | $16 / $30 per 1M — [Polly pricing](https://aws.amazon.com/polly/pricing/) | $0.072 / $0.135 | $0.58 / $1.08 | Neural 1M/mo free for 12 months; new customers after 2025-07-15 get up to $200 in credits instead — [Polly pricing](https://aws.amazon.com/polly/pricing/) |
| **Cartesia Sonic 3.6** | Pro $5/mo = 100K credits at 1 credit per character; overage $65/1M — [Cartesia pricing](https://cartesia.ai/pricing) | ≈$0.225 at the Pro rate | $5 (plan covers ~22 lessons) | Free tier 20K credits; commercial license starts at Pro — [pricing](https://cartesia.ai/pricing) |
| Inworld TTS-2 / TTS-2 Flash | $25 / $15 per 1M on demand — [Inworld pricing](https://inworld.ai/pricing) | $0.113 / $0.068 | $0.90 / $0.54 | "Commercial license" on On-Demand — [pricing](https://inworld.ai/pricing) |
| OpenAI tts-1 / tts-1-hd / gpt-4o-mini-tts | $15 / $30 per 1M chars; mini-tts $0.60/1M text-in + $12/1M audio-out tokens — [OpenAI pricing](https://developers.openai.com/api/docs/pricing) | $0.068 / $0.135 / ≈$0.075 (derived from an unverified tokens-per-minute figure) | — | **All three shut down 2027-01-06** — [OpenAI TTS guide](https://developers.openai.com/api/docs/guides/text-to-speech) |
| StepAudio 2.5 TTS | $85/1M as listed by AA — [AA](https://artificialanalysis.ai/text-to-speech/leaderboard) | $0.38 | $3.06 | Portuguese not confirmed |
| Local open weights (Qwen3-TTS, Kokoro, Piper, Chatterbox, VoxCPM2) | $0 | $0 (electricity) | $0 | See Q4 |

**Word timestamps, pronunciation control, cloning and data terms**

| Option | Word timestamps | Pronunciation control for English jargon | Cloning + consent | Data / training |
|---|---|---|---|---|
| MiniMax 2.8 | **Yes**: `subtitle_enable` + `subtitle_type` "word" (default "sentence"); non-streaming `subtitle_file` described as "aligned to sentences (≤ 50 characters), timestamped in milliseconds" — [T2A API](https://platform.minimax.io/docs/api-reference/speech-t2a-http) | `pronunciation_dict.tone` rules like "omg/oh my god", with replacements in plain text or **IPA**; `<#x#>` pauses; `language_boost` — [T2A API](https://platform.minimax.io/docs/api-reference/speech-t2a-http) | Rapid clone $1.5 per voice, voice design $3 — [pricing](https://platform.minimax.io/docs/guides/pricing-paygo); API consent clause not verified | Not verified (separate Open Platform and Audio privacy policies exist, snippet) — [MiniMax privacy](https://www.minimax.io/privacy-policy-v2.html) |
| Alibaba CosyVoice API | **Yes**: `word_timestamp_enabled` for cloned v3-plus voices and flagged system voices, via WebSocket events (snippet) — [Alibaba doc](https://www.alibabacloud.com/help/doc-detail/3032843.html) | SSML ("word pronunciation"), `language_hints`, `hot_fix` — [Qwen-TTS doc](https://www.alibabacloud.com/help/en/model-studio/qwen-tts) | Available; fee not captured | "Input and output data from API calls are not used for model training" (snippet) — [Bailian agreements](https://docs.agent.bailian.aliyun.com/en/resources/agreements); zero-retention option (policy updated 2026-10-11, snippet) — [retention policy](https://www.alibabacloud.com/help/ja/model-studio/data-retention-policy) |
| Alibaba qwen3-tts-flash / Qwen-Audio | Not documented | Qwen-Audio: SSML, `language_hints`/`hot_fix`, inline tags — [Qwen-TTS doc](https://www.alibabacloud.com/help/en/model-studio/qwen-tts) | qwen-voice-enrollment $0.01 per clone, 1,000 free (SG) — [pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing) | Same as CosyVoice (no training) |
| Seed Speech TTS 2.0 | Not found (fal.ai returns audio only) — [fal.ai](https://fal.ai/models/fal-ai/bytedance/seed-speech/tts/v2/llms.txt) | `voice_instruction` (natural language); no SSML found | "Voice Replication 2.0" exists — [BytePlus docs](https://docs.byteplus.com/docs/byteplusvoice/texttospeechv2) | Not fetched |
| ElevenLabs | **Character-level**: `/with-timestamps` returns `character_start_times_seconds` / `character_end_times_seconds` — [docs](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps) | v4 "understands IPA symbols when they are wrapped in forward slashes"; pronunciation dictionaries with alias; v4/v3 have no SSML break — [best practices](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices) | Instant clone from Starter; Professional clone requires a verification captcha — [captcha API](https://elevenlabs.io/docs/api-reference/voices/pvc/verification/captcha.md) | Uses "Inputs & Outputs" to "research, build, train and improve our AI models"; opt-out in settings, not retroactive — [privacy](https://elevenlabs.io/privacy-policy); Zero Retention Mode is Enterprise-only — [ZRM](https://elevenlabs.io/docs/eleven-api/resources/zero-retention-mode.md) |
| Google Chirp 3 HD | Timepoints need `<mark>` — [SSML doc](https://docs.cloud.google.com/text-to-speech/docs/ssml) — which is **not in Chirp 3 HD's supported-tag list** ("Any tags that are not on this list will be ignored") — [Chirp 3 HD doc](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd) | `custom_pronunciations` in **IPA or X-SAMPA**; SSML phoneme/sub (Preview, not for streaming) — [Chirp 3 HD doc](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd) | Instant Custom Voice is "restricted to allow-listed users" and requires a recorded consent statement; pt-BR supported — [doc](https://docs.cloud.google.com/text-to-speech/docs/chirp3-instant-custom-voice) | "Google will not use Customer Data to train or fine-tune any AI/ML models without Customer's prior permission" — [Service Terms](https://cloud.google.com/terms/service-terms) |
| Google Neural2 / WaveNet | SSML `<mark>` timepoints — [SSML doc](https://docs.cloud.google.com/text-to-speech/docs/ssml) | Full SSML | — | Same |
| Gemini TTS | None found | Prompt-based only | None found | Same (Cloud) |
| **Azure Neural** | **Yes**: WordBoundary "raised at the beginning of each new spoken word", with audio and text offsets — [Azure doc](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis?pivots=programming-language-python); for HD, documented only for Dragon HD Omni — [HD voices](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/high-definition-voices) | SSML `<phoneme>` (IPA), custom lexicon (IPA, x-microsoft-sapi, alias) — [pronunciation doc](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-pronunciation); `<lang xml:lang>` works on DragonHD — [HD voices](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/high-definition-voices) | Personal voice: "A recorded statement from the user is required" — [personal voice](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/personal-voice-overview) | "Microsoft doesn't retain or store the text that you provide with the real-time synthesis" API — [Azure data privacy](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/speech-service/text-to-speech/data-privacy-security) |
| Amazon Polly | Neural: speech marks (billed as characters) — [pricing](https://aws.amazon.com/polly/pricing/); Generative: "not available" — [generative doc](https://docs.aws.amazon.com/polly/latest/dg/generative-voices.html) | SSML phoneme; Generative supports "Many (but not all)" tags — [generative doc](https://docs.aws.amazon.com/polly/latest/dg/generative-voices.html) | None found | "we may use and store AI Content… to develop and improve" Polly; an organization-level opt-out policy exists — [AWS Service Terms](https://aws.amazon.com/service-terms/), [opt-out](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_ai-opt-out.html) |
| Cartesia | **Word and phoneme** timestamps — [Cartesia docs](https://docs.cartesia.ai/llms.txt) | Pronunciation dictionaries with IPA or "sounds-like" spellings — [doc](https://docs.cartesia.ai/build-with-cartesia/capability-guides/custom-pronunciations.md) | Instant clone from Pro; professional clone needs 30+ min of audio — [pricing](https://cartesia.ai/pricing) | Zero retention is Enterprise-only — [ZDR](https://docs.cartesia.ai/enterprise/zero-data-retention.md); training policy not found |
| Inworld | Word and character level — [Inworld docs](https://docs.inworld.ai/llms.txt) | Inline IPA, dictionaries, inline language tags — [docs](https://docs.inworld.ai/llms.txt) | Instant cloning plus 2 professional clones — [pricing](https://inworld.ai/pricing) | Zero retention is an add-on at the top tier — [pricing](https://inworld.ai/pricing) |
| OpenAI | None documented | No SSML; `instructions` prompt only — [TTS guide](https://developers.openai.com/api/docs/guides/text-to-speech) | Custom voices from a speaker's "consent recording"; eligibility-gated — [TTS guide](https://developers.openai.com/api/docs/guides/text-to-speech) | API data not used for training; speech-endpoint logs kept 30 days; zero retention eligible — [your data](https://developers.openai.com/api/docs/guides/your-data) |
| Local open models | None native (a community Pocket TTS fork adds them) — [Pocket TTS](https://github.com/kyutai-labs/pocket-tts) | Kokoro/Piper use espeak-ng IPA G2P — [Kokoro VOICES](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md), [piper1-gpl](https://github.com/OHF-Voice/piper1-gpl); Magpie supports "IPA G2P custom dictionaries and code-switching" — [card](https://huggingface.co/nvidia/magpie_tts_multilingual_357m) | Pocket TTS prohibits cloning without explicit, lawful consent — [GitHub](https://github.com/kyutai-labs/pocket-tts); Magpie "removed zero-shot voice-cloning capability for security reasons" — [card](https://huggingface.co/nvidia/magpie_tts_multilingual_357m) | Local: no data leaves the PC |

### Inferences
- **Monthly TTS spend is negligible against the US$8–11 LLM budget** for every option except a MiniMax HD habit at high volume. At 8 lessons a month: Chirp 3 HD $0, qwen3-tts-flash $0.36, Azure S0 $0.54, ElevenLabs v4 $2.88, MiniMax HD $3.60. Even 30 lessons a month on ElevenLabs v4 would be about $10.80.
- **Easiest subtitle path:** Azure S0 (WordBoundary + SSML `<phoneme>`/lexicon + `<lang>`) is the most complete single-vendor package for "TTS + word timings + jargon control" at $0.068 per lesson. MiniMax is the Chinese equivalent at 4–7× the price.
- **Alternative path:** with Chirp 3 HD or Qwen, word timings come from a local forced aligner run on the known script (Q6). This adds about one local step but $0.
- **Handling English jargon**, from strongest to weakest control:
  1. IPA lexicons or phonemes: Azure, Chirp 3 HD `custom_pronunciations`, MiniMax `pronunciation_dict`, ElevenLabs v4 inline IPA, Cartesia, Magpie.
  2. Alias or respelling, e.g. "fine-tuning" → "fáin-tiúnin": works for every engine, including local ones without phoneme input.
  3. Prompt-only control (OpenAI, Gemini), which is the least reliable.

  A shared glossary file (term → IPA → respelling) that is applied per engine is the portable solution.
- **Free tiers have commercial-use traps:**
  - Azure F0 output has no commercial rights.
  - The ElevenLabs free plan has no commercial license.
  - Cartesia's commercial license starts at Pro.
  - For sotawhat's personal use the free tiers are fine, but output intended for later startup reuse should come from a paid tier (Azure S0 at $0.54/month for 8 lessons) or from commercially licensed local models.

### Gaps
- Word timestamps are not documented for qwen3-tts-flash, Qwen-Audio, Seed Speech, Fish or Gemini TTS.
- MiniMax "word" subtitles vs the "sentence-aligned" file description need a live test in Portuguese.
- No source found on whether Google's Chirp 3 HD free tier or the Polly free tier restricts commercial use of output (no restriction found either way).
- The data/training terms of MiniMax, BytePlus, Fish Audio and Cartesia were not verified.
- OpenAI's per-minute token rate for gpt-4o-mini-tts could not be re-verified, so that per-lesson figure is a derivation.
- AI-Studio Gemini TTS free tier: secondary sources say 2.5/3.1 Flash TTS are free there — [nemovideo (secondary)](https://www.nemovideo.com/blog/gemini-3-1-flash-tts-pricing) — and an unverified listing claims those previews retire 2026-11-17. The data-use terms of that free tier were not verified.

## Q3. Is a presenter avatar worth its cost (price/min, quality), or is voice-over better for lessons built on 3D animation?

### Takeaway
Voice-over over the 3D animation should be the default:
- **Learning gain is small or zero.** Adding a talking head shows little to no gain: Mayer's image principle has a median d of 0.20, and recent meta-analyses and RCTs find equal test scores for AI and human videos. A face can also pull gaze away from the relevant visuals.
- **Cloud avatars are expensive here.** They cost about $0.84–12 per minute, which is 10–100× the TTS cost of a lesson.
- **Local avatars barely fit.** Only lip-sync on a pre-recorded base clip fits in 8 GB (MuseTalk 1.5 at 4 GB; LatentSync 1.5 at 8 GB), and it is slow: about 3 h per 5 minutes at the README's 3050 Ti rate.

If a presenter is wanted, use a ~1-minute picture-in-picture intro/outro: Kling Lip Sync on a self-recorded 10-s clip at about $0.84/min, or local MuseTalk.

### Cited Findings

**Comparison table (avatars; prices checked 2026-11-09; per-lesson figures computed from the cited unit price)**

| Product | Type | Price per minute | 5-min full screen / 1-min PiP | pt-BR | License / commercial | 8 GB RTX 4060 feasibility |
|---|---|---|---|---|---|---|
| **Kling Lip Sync** (Kuaishou) | Closed API; needs a base video of the presenter | Official "0.5 Units ($0.07) /5s" = $0.84/min — [Kling API pricing](https://kling.ai/document-api/pricing/base/video.md); fal $0.014/s in 5-s increments; input video 2–10 s, audio 2–60 s — [fal](https://fal.ai/models/fal-ai/kling-video/lipsync/audio-to-video) | $4.20 / $0.84, plus the base clip | Not stated | Closed; fal "Commercial use via fal partnership" — [fal](https://fal.ai/models/fal-ai/kling-video/lipsync/audio-to-video) | Cloud only |
| **Kling AI Avatar** | Closed API (image + audio) | Official $0.056/s ($3.36/min), higher tier $0.112/s — [Kling](https://kling.ai/document-api/pricing/base/video.md); fal v2 Standard $0.0562/s, Pro $0.115/s — [fal](https://fal.ai/models/fal-ai/kling-video/ai-avatar/v2/standard) | $16.80 / $3.36 | Not stated | Closed | Cloud only |
| **OmniHuman 1.5** (ByteDance) | Closed API | fal "$0.16 per second" ($9.60/min) — [fal](https://fal.ai/models/fal-ai/bytedance/omnihuman/v1.5); BytePlus $0.12/s (snippet) — [BytePlus](https://www.byteplus.com/de/product/OmniHuman) | $48 / $9.60 (fal) | No Portuguese statement | Closed; fal tags it "Commercial use" | Cloud only |
| InfiniteTalk (MeiGen) via fal | Open model, hosted | "$0.2 per second" at 480p, 720p "doubled"; "This endpoint is deprecated" — [fal](https://fal.ai/models/fal-ai/infinitalk) | $60 / $12 | chinese-wav2vec2-base audio encoder — [GitHub](https://github.com/MeiGen-AI/InfiniteTalk) | Apache-2.0 | See local row |
| **HeyGen** | SaaS + API | Plans: Free (3 watermarked videos/mo), Creator $29/mo (600 credits), Pro $49/mo (1,000), Business $149/mo — [HeyGen pricing](https://www.heygen.com/pricing). API per minute from third parties only: Avatar III ~$1, Avatar IV photo $3, Digital Twin $4 (conflicting) — [anam.ai](https://anam.ai/blog/heygen-pricing), [diyai](https://diyai.io/ai-tools/video-generation/heygen-pricing/) | ~$5–20 / ~$1–4 | "175 languages and dialects" on paid plans — [HeyGen pricing](https://www.heygen.com/pricing) | Proprietary; custom avatar "with your own voice and likeness" from Creator — [HeyGen pricing](https://www.heygen.com/pricing) | Cloud only |
| **Synthesia** | SaaS (API minutes come from the plan) | Basic $0 with a "10 min/month free allowance"; Starter $19/mo (~12 min); Pro $89/mo (~60 min); annual plans ≈$0.98/min — [Synthesia pricing](https://www.synthesia.io/pricing) | ≈$4.92–7.92 / ≈$0.98–1.58 pro-rata | **"Portuguese (Brazil)" listed**; 140+ languages — [Synthesia pricing](https://www.synthesia.io/pricing) | Proprietary; voice cloning Enterprise only — [Synthesia pricing](https://www.synthesia.io/pricing) | Cloud only |
| **Hedra** (Character-3, Hedra Avatar) | Pay-as-you-go API | "Avatar & lip-sync: from 2.5¢ / second" ($1.50/min floor) — [Hedra pricing](https://www.hedra.com/pricing); Character-3 "~3 to ~6 credits per second" — [Hedra develop](https://www.hedra.com/develop) | ≥$7.50 / ≥$1.50 | Not stated | Proprietary | Cloud only |
| D-ID | SaaS + API | Official page unreadable; third parties give Studio from $5.90/mo and API Build from $18/mo (conflicting) — [aiproductivity (secondary)](https://aiproductivity.ai/pricing/d-id/) | Not computed | Not verified | Proprietary | Cloud only |
| Captions / Mirage | SaaS | Max $24.99/mo for 500 credits; no per-second avatar cost published — [Captions pricing](https://www.captions.ai/pricing) | Not computable | Not named | Proprietary | Cloud only |
| **MuseTalk 1.5** (Tencent Music) | Open lip-sync on a base video | $0 | $0 | Whisper features; "supports audio in various languages, such as Chinese, English, and Japanese" — [GitHub](https://github.com/TMElyralab/MuseTalk) | Code MIT; the model can be used "even commercially"; bundled whisper, ft-mse-vae, dwpose and S3FD keep their own licenses — [GitHub](https://github.com/TMElyralab/MuseTalk) | **Yes**: 4 GB tested; "8-second video takes approximately 5 minutes" on an RTX 3050 Ti Laptop 4 GB; real-time 30 fps+ on a V100 — [GitHub](https://github.com/TMElyralab/MuseTalk) |
| **LatentSync 1.5 / 1.6** (ByteDance) | Open lip-sync on a base video | $0 | $0 | 1.5 "improves performance on Chinese videos"; no Portuguese claim | Apache-2.0 — [GitHub](https://github.com/bytedance/LatentSync) | "8 GB with LatentSync 1.5; 18 GB with LatentSync 1.6", so 1.5 is tight and 1.6 won't fit — [GitHub](https://github.com/bytedance/LatentSync) |
| EchoMimic v3 Flash / v2 (Ant Group) | Open (image + audio) | $0 | $0 | v2 "trained on English and Mandarin Chinese" — [GitHub v2](https://github.com/antgroup/echomimic_v2) | Apache-2.0 — [GitHub v3](https://github.com/antgroup/echomimic_v3) | v3 Flash needs 12 GB (16 GB in ComfyUI): **no** — [GitHub v3](https://github.com/antgroup/echomimic_v3) |
| InfiniteTalk (local) | Open (Wan2.1-I2V-14B) | $0 | $0 | — | Apache-2.0 | Low-VRAM flags, int8 and Wan2GP routes exist; default max is 40 s; FusionX LoRA "exacerbates color shift over 1 minute" — [GitHub](https://github.com/MeiGen-AI/InfiniteTalk). Impractical for 5 min |
| Wan2.2-S2V-14B (Alibaba) | Open | $0 | $0 | — | Not re-verified | Single-GPU command needs ≥80 GB; offload/FP8 via DiffSynth — [GitHub](https://github.com/Wan-Video/Wan2.2). **No** |
| HunyuanVideo-Avatar (Tencent) | Open | $0 | $0 | — | Tencent Hunyuan Community License "DOES NOT APPLY IN THE EUROPEAN UNION, UNITED KINGDOM AND SOUTH KOREA"; >100M MAU needs a separate license — [GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-Avatar) | 24 GB minimum ("very slow"); 10 GB via Wan2GP: **no** — [GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-Avatar) |
| Hallo3 (Fudan) | Open | $0 | $0 | "Audio must be in English" — [GitHub](https://github.com/fudan-generative-vision/hallo3) | CogVideoX-5B license applies | Tested on H100: **no** |
| Sonic (Tencent) | Open | $0 | $0 | — | **NC**: CC BY-NC-SA 4.0 — [GitHub](https://github.com/jixiaozhong/Sonic) | 32 GB tested: **no** |
| StableAvatar / FantasyTalking / OmniAvatar / HuMo | Open | $0 | $0 | — | Not captured | StableAvatar: ~18 GB for 5 s, 3 min on a 4090 — [GitHub](https://github.com/Francis-Rings/StableAvatar). FantasyTalking 5 GB mode: 42.6 s/it on an A100 — [GitHub](https://github.com/Fantasy-AMAP/fantasy-talking). OmniAvatar 8 GB mode: 22.1 s/it on an A800 — [GitHub](https://github.com/Omni-Avatar/OmniAvatar). Fit only with offload, and very slow |
| LongCat-Video-Avatar 1.5 (Meituan, 2026-05-21) | Open | $0 | $0 | Whisper-large-v3 audio encoder — [GitHub](https://github.com/meituan-longcat/LongCat-Video) | MIT | VRAM not found |
| Duix.Avatar (ex-HeyGem) | Open Windows app (Docker) | $0 | $0 | Script languages exclude Portuguese — [GitHub](https://github.com/duixcom/Duix.Heygem) | License not reviewed | Unknown |

- No user reports of Portuguese lip-sync quality were found for any product; none of the open models claims Portuguese specifically. They are audio-driven: MuseTalk and LongCat use Whisper features; InfiniteTalk and EchoMimic v3 use chinese-wav2vec2-base — [MuseTalk](https://github.com/TMElyralab/MuseTalk), [LongCat](https://github.com/meituan-longcat/LongCat-Video), [InfiniteTalk](https://github.com/MeiGen-AI/InfiniteTalk).
- Wan2GP says "8 GB of VRAM is enough to get started" for its Wan-family video models — [Wan2GP](https://github.com/deepbeepmeep/Wan2GP).

**Evidence: presenter vs voice-over**
- **Mayer's image principle:** adding the speaker's image does not reliably help. The median effect size is d = 0.20, and in the 2014 tally half of 14 tests were negative or negligible — [Cambridge Handbook chapter](https://www.cambridge.org/core/books/abs/cambridge-handbook-of-multimedia-learning/principles-of-multimedia-learning-based-on-social-cues-personalization-voice-and-image-principles/19309D764FD015A556334531A463DE03), [Mayer 2020 summary](https://ugc.futurelearn.com/uploads/files/7d/d6/7dd6188d-c343-4311-b064-ac98d2c95abc/Multimedia_Principles._R._E._Mayer__2020.pdf).
- **Embodiment principle** (humanlike gesture, gaze and expression): median d = 0.36 (11/11 tests, 2014) and 0.58 (15/17, 2021). These figures come from a secondary summary — [blog summary (secondary)](https://clarakucher.opened.ca/?p=303).
- **Beege et al. 2023**, *Educational Research Review* 41:100564, meta-analysis of 35 studies (N = 6,339):
  - A small significant benefit for retention and none for transfer.
  - Social presence and motivation increased, but learners spent less time looking at the relevant visuals.
  - Source: [DDB record](https://www.deutsche-digitale-bibliothek.de/item/PBOMPA7MBJFP5UZOZIZ5TTKBWQG7UUP3).
- **Alemdag 2022**, *Education and Information Technologies*, 20 experiments: no learning effect; cognitive load and motivation increased — [Springer PDF](https://link.springer.com/content/pdf/10.1007/s10639-022-11532-4.pdf).
- **Netland et al. 2025**, *Computers & Education* 224:105164 (n = 447):
  - Same exam scores for AI-generated and human-made videos.
  - Humans had a small (~4%) edge in learning experience.
  - The AI videos took hours to produce instead of days.
  - Sources: [x-mol](https://x-mol.com/paper/1857628113137397760), [Media & Learning](https://media-and-learning.eu/subject/artificial-intelligence/when-ai-took-over-my-teaching-videos-students-enjoyed-them-less-but-learned-the-same/).
- **Arkün-Kocadere & Çağlar Özhan 2024**, IRRODL: same performance but lower engagement; students found the AI instructor distracting — [IRRODL](https://www.irrodl.org/index.php/irrodl/article/view/7815).
- **JMIR Formative Research 2026**, randomized crossover: no significant difference in learning gain; the avatar was perceived as neutral — [JMIR](https://formative.jmir.org/2026/1/e90037).
- **Uncanny valley:** among ~500 learners, most did not dislike the avatar but some noticed something "off" — [Media & Learning](https://media-and-learning.eu/subject/artificial-intelligence/do-ai-avatars-teach-as-well-as-humans-the-results-might-surprise-you/).

### Inferences
- **Cost check at 8 lessons per month:**

| Option | Monthly cost |
|---|---|
| Full-screen presenter, Kling AI Avatar (official) | ≈$134 |
| Full-screen presenter, OmniHuman via fal | ≈$384 |
| 1-min PiP, Kling AI Avatar | ≈$27 |
| 1-min PiP, Kling Lip Sync on a self-recorded clip | ≈$6.72 |
| Synthesia Basic free allowance (10 min/month) | Might cover 8 one-minute PiPs, but watermark and commercial terms were not verified |

  Only the last two come near the US$8–11 total budget. Narration alone costs $0–3.60 a month.
- **Local path:** record a short idle clip of the presenter once (the user, consenting), then lip-sync each lesson's intro/outro narration with MuseTalk 1.5. At the README's 3050 Ti rate (~37× slower than real time), a 1-minute PiP takes ~40 minutes and a full 5-minute lesson ~3 hours. The desktop 4060 should be faster, but that is unmeasured.
- Image-to-video talking-head models (InfiniteTalk, OmniAvatar, HunyuanVideo-Avatar, Wan S2V, EchoMimic v3) are not practical for 5-minute output on 8 GB.
- **Better use of effort for 3D lessons:** the embodiment evidence suggests a stylized 3D guide character inside the scene, with gestures and gaze pointing at the structures being explained. It could pay off more than a photoreal talking head, which competes with the 3D visuals for attention per Beege et al. This is a design inference, not a tested claim.
- If any presenter is used in a health-startup context, disclose it as AI up front, because perceived trust is fragile. That is supported only by secondhand reports.

### Gaps
- Official per-minute API prices were not verified for HeyGen (third-party figures conflict), D-ID, Dreamina or BytePlus OmniHuman.
- Synthesia Basic's watermark and commercial-use terms were not verified.
- No pt-BR lip-sync quality reports were found, and no RTX 4060 timing benchmarks for any avatar model.
- Licenses not captured: Wan2.2-S2V, StableAvatar, FantasyTalking, OmniAvatar, HuMo and Duix.
- Vendor consent and verification rules for custom or "digital twin" avatars were not collected.
- Unverified hardware note: the Ryzen 5 5500 platform's PCIe generation and the 4060's x8 link may slow CPU-offload routes relative to published figures. This came from a sub-researcher's general knowledge and was not sourced.

## Q4. What zero-cost local stack options exist on an RTX 4060 8 GB, and what are their quality trade-offs?

### Takeaway
A fully local, commercially safe stack is feasible:
- **Qwen3-TTS 1.7B** (Apache-2.0) via `faster-qwen3-tts`, at about 1.8× real time on a Windows RTX 4060, i.e. ~3 min of compute per lesson. Kokoro or Piper serve as instant CPU fallbacks.
- **Qwen3-ForcedAligner** or WhisperX for subtitles.
- **ACE-Step 1.5** for music.
- **FFmpeg** for mixing and burn-in.
- A **local Bot API server** to lift Telegram's 50 MB cap.

The trade-off is voice quality: open pt-BR voices are intelligible but flatter than ElevenLabs or Chirp 3 HD, and English jargon needs respelling. Avatars are the one part that does not fit well in 8 GB (see Q3).

### Cited Findings

**Local TTS on 8 GB / CPU**

| Model | VRAM / speed | Windows | Commercial? | Quality trade-off |
|---|---|---|---|---|
| **Qwen3-TTS 1.7B / 0.6B** via `faster-qwen3-tts` | Measured on an **RTX 4060 (Windows)**. 1.7B: baseline RTF 0.23, **1.83 with CUDA graphs**, first audio in 460 ms. 0.6B: 0.23 baseline, **2.26 with CUDA graphs**. Here "RTF > 1.0 = faster than real-time" — [PyPI](https://pypi.org/project/faster-qwen3-tts/) | `setup_windows.bat` / `benchmark_windows.bat`; MIT wrapper — [PyPI](https://pypi.org/project/faster-qwen3-tts/) | Apache-2.0 — [GitHub](https://github.com/QwenLM/Qwen3-TTS) | Portuguese WER 1.526 / SIM 0.817 on the shared test set, beating MiniMax 2.x on both; ElevenLabs Multilingual v2 has a lower WER of 1.331 (Q1); "flat intonation" and Brazilian-accented English terms — [Akita](https://akitaonrails.com/en/2026/04/09/how-elevenlabs-was-not-killed-by-qwen3-tts/) |
| **VoxCPM2** (2B) | "~8 GB" VRAM; RTF ~0.30 (standard) / ~0.13 (Nano-vLLM) on an RTX 4090 — [HF](https://huggingface.co/openbmb/VoxCPM2) | `pip install voxcpm` — [HF](https://huggingface.co/openbmb/VoxCPM2) | Apache-2.0 — [HF](https://huggingface.co/openbmb/VoxCPM2) | No Portuguese metrics; borderline fit on 8 GB |
| **Kokoro-82M** | 82M parameters, so tiny — [card](https://huggingface.co/hexgrad/Kokoro-82M); no primary speed figure for pt-BR found | — | Apache-2.0 | 3 fixed pt-BR voices, no official grade, nasal-vowel issues reported in STIL-2026 — [STIL 2026](https://aclanthology.org/2026.stil-1.29.pdf) |
| **Piper** pt_BR | CPU model; no speed figure found | `pip install piper-tts`; the project is "looking for maintainers" — [piper1-gpl](https://github.com/OHF-Voice/piper1-gpl) | Engine GPL-3.0 (used as a separate program, not linked); voices CC0 / CC BY 4.0 | Most stable for neutral speech in STIL-2026, but an older architecture — [STIL 2026](https://aclanthology.org/2026.stil-1.29.pdf) |
| **Chatterbox pt-br** | 0.5B; pt-br checkpoint fp32 2.14 GB — [pt-br card](https://huggingface.co/ResembleAI/Chatterbox-Multilingual-pt-br) | Authors tested only Python 3.11 / Debian 11 — [GitHub](https://github.com/resemble-ai/chatterbox) | MIT with mandatory Perth watermark; unmaintained since Aug 2026 | Zero-shot cloning; the reference clip's accent can leak (use `cfg_weight=0`) — [GitHub](https://github.com/resemble-ai/chatterbox) |
| **Kyutai Pocket TTS** (100M) | CPU about 2.3–2.5× real time on 4 vCPUs — [GitHub](https://github.com/kyutai-labs/pocket-tts) | Windows CPU binary — [GitHub](https://github.com/kyutai-labs/pocket-tts) | Code MIT; weights license unstated | Portuguese variant unknown |
| **NVIDIA Magpie 357M** | GGUF Q8 332 MB — [card](https://huggingface.co/nvidia/magpie_tts_multilingual_357m) | **Linux only** (NeMo/Riva) — [card](https://huggingface.co/nvidia/magpie_tts_multilingual_357m) | Yes (NVIDIA Open Model License) | Only open model with a published pt-BR metric (CER 2.91%); 5 fixed voices |
| Step-Audio-EditX / Higgs Audio v2 / Voxtral | ~12 GB (EditX) — [GitHub](https://github.com/stepfun-ai/Step-Audio-EditX); ~11.6 GB of BF16 weights (Higgs) — [card](https://huggingface.co/bosonai/higgs-audio-v2-generation-3B-base); ≥16 GB (Voxtral) — [card](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603) | — | Mixed / NC | Too large for 8 GB, and none has confirmed pt-BR |

- Without CUDA graphs, even an RTX 4090 runs Qwen3-TTS below real time: 1.7B baseline RTF 0.82, rising to 4.22 with CUDA graphs — [PyPI faster-qwen3-tts](https://pypi.org/project/faster-qwen3-tts/). So without CUDA graphs a 4060 (baseline RTF 0.23) would take ~22 min per 5-min lesson; the benchmark's "baseline" is the community streaming / dynamic-cache path, not necessarily the official inference code. A Brazilian developer reported ~1× real time (serialized) on a rented GPU: a 28-minute episode took about 25–30 minutes — [Akita on Rails](https://akitaonrails.com/en/2026/04/09/how-elevenlabs-was-not-killed-by-qwen3-tts/).
- **Free cloud with caveats: edge-tts.**
  - The `edge-tts` package uses "Microsoft Edge's online text-to-speech service", needs no API key in the README, and writes SRT via `--write-subtitles`. Custom SSML was removed: the service allows only a single voice tag with prosody — [edge-tts](https://github.com/rany2/edge-tts).
  - The Microsoft Edge terms (updated September 2026) say "You may not use tokens the Software uses to call into a Microsoft Azure service separate from the Software" — [Edge terms](https://explore.microsoft.com/en-us/edge/terms).
  - Azure's Product Terms grant TTS output rights to paid-tier customers only — [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5805156/please-clarify-the-conflicting-information-regardi).
  - A Microsoft Q&A question on edge-tts commercial use received no clear answer (snippet) — [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/2088770/are-opensource-edge-tts-free-for-commercial-use).

**Rest of the local stack (details in Q5 and Q6)**
- **Alignment:** Qwen3-ForcedAligner-0.6B (Apache-2.0, Portuguese, ≤5 min) — [HF](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B). Alternatively WhisperX (BSD-2 + Apache-2.0 pt model) — [GitHub](https://github.com/m-bain/whisperX), or faster-whisper large-v2 int8 at 2.9 GB VRAM — [GitHub](https://github.com/SYSTRAN/faster-whisper).
- **Music:** ACE-Step 1.5 (MIT; 6–8 GB tier supported) — [GitHub](https://github.com/ace-step/ACE-Step-1.5).
- **Mixing and burn-in:** FFmpeg `sidechaincompress`, `loudnorm` and `subtitles` (libass) — [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html).
- **Delivery:** the local Bot API server raises uploads to 2,000 MB — [tdlib/telegram-bot-api](https://github.com/tdlib/telegram-bot-api).

**Local avatars on 8 GB (details in Q3)**
- **MuseTalk 1.5** is the only clearly feasible option. It was tested at 4 GB, takes ~5 min per 8 s of video on a 3050 Ti Laptop, and its model can be used commercially — [GitHub](https://github.com/TMElyralab/MuseTalk).
- **LatentSync 1.5** needs 8 GB (tight) and is Apache-2.0 — [GitHub](https://github.com/bytedance/LatentSync).
- Image-to-video avatar models need 10–80 GB, or offload at tens of seconds per step — [HunyuanVideo-Avatar](https://github.com/Tencent-Hunyuan/HunyuanVideo-Avatar), [Wan2.2](https://github.com/Wan-Video/Wan2.2), [OmniAvatar](https://github.com/Omni-Avatar/OmniAvatar).
- Sonic is non-commercial (CC BY-NC-SA 4.0) — [GitHub](https://github.com/jixiaozhong/Sonic).

### Inferences
- **Recommended zero-cost default:**
  1. Generate narration per scene with Qwen3-TTS 1.7B on the 4060, about 3 minutes per 5-minute lesson with CUDA graphs. Use a cloned or designed voice from a consenting speaker (e.g. the user's own voice), because there is no Portuguese preset voice.
  2. Fall back to Kokoro pm_alex or pf_dora, or Piper faber, when the GPU is busy rendering 3D.
  3. Align with Qwen3-ForcedAligner; add ACE-Step beds; mix, burn in and encode with FFmpeg.
  4. Deliver through a local Bot API server.
- **VRAM:** each step fits in 8 GB on its own, so run them **sequentially** (TTS → aligner → music → render/encode) and unload models in between. A single process holding TTS, aligner and music at once could exceed 8 GB. Blender/3D rendering competes for the same GPU.
- **Quality ladder for pt-BR narration** (an inference from the evidence above, not a measured ranking):
  1. ElevenLabs v4 (paid)
  2. Chirp 3 HD / Azure HD / Qwen-Audio-3.1 (cheap API)
  3. Qwen3-TTS 1.7B (local)
  4. Chatterbox pt-br (local)
  5. Kokoro / Piper (local, robotic but stable)

  A 15-minute blind A/B test of 3–4 candidates on one real lesson script with heavy jargon would settle this cheaply.
- **The cheapest hybrid** is local Qwen3-TTS for daily drafts plus Chirp 3 HD free tier or Azure S0 for "publishable" lessons. Either stays within a few cents a month.

### Gaps
- No primary RTX 4060 speed figures were found for Kokoro, Piper, Chatterbox pt-br or VoxCPM2 synthesizing Portuguese.
- No VRAM figure was found for Qwen3-TTS 1.7B on the official card; faster-qwen3-tts lists speed only.
- Magpie on Windows (WSL2) was not tested by any source found.
- The base-voice dataset terms for Piper's faber/edresson (fine-tuned from English lessac/ryan) were not verified. The researcher recalled that lessac's data was research-restricted; this should be checked before commercial reuse.
- Kokoro's training data includes audio from closed TTS vendors. Whether those vendors' terms affect downstream commercial use is unresolved.

## Q5. Background music: which sources fit (ACE-Step, MiniMax Music, Suno/Udio, Pixabay, YouTube Audio Library), at what cost and license?

### Takeaway
The cheapest startup-safe route is to generate a small library of instrumental beds **locally with ACE-Step 1.5**. It is MIT-licensed, runs in under 4 GB of VRAM, and its model card states that outputs can be used commercially. Pixabay Music is the zero-effort fallback (free, no attribution), with a known Content ID claim risk. Several options should be avoided: Suno's free tier is non-commercial; Udio's licensed app does not allow downloads; MusicGen weights are CC-BY-NC; and the YouTube Audio Library terms do not cover use outside YouTube. MiniMax's own Music API has been closed to new users since 2026-08-20, so it is reachable only through resellers such as fal.ai, at $0.15 per track.

### Cited Findings

**Comparison table (music)**

| Option | Cost | License / commercial use | Runs on RTX 4060 8 GB? | Notes |
|---|---|---|---|---|
| **ACE-Step 1.5** (2B DiT + 0.6B LM; open) | $0 | Code MIT; HF card license MIT; card says "You can strictly use the generated music for commercial purposes" — [HF card](https://huggingface.co/ACE-Step/Ace-Step1.5) | Yes: "6–8GB: 2B turbo with the 0.6B LM on the PyTorch backend" — [GitHub](https://github.com/ace-step/ACE-Step-1.5) | Data: licensed + royalty-free/public-domain + synthetic MIDI-to-audio — [HF card](https://huggingface.co/ACE-Step/Ace-Step1.5) |
| ACE-Step 1.5 **XL** (4B DiT, 2026-04-02) | $0 | MIT (repo) | **No**: "≥12GB VRAM (with offload + quantization) or ≥20GB (without offload)" — [GitHub](https://github.com/ace-step/ACE-Step-1.5) | — |
| **Stable Audio 3** Small / Medium (open weights, 2026-05-20) | $0 | Stability AI Community License; outputs usable commercially; organizations with >$1M annual revenue need an enterprise license — [The Decoder](https://the-decoder.com/stability-ai-launches-stable-audio-3-0-with-up-to-six-minute-tracks-and-open-weights/) | Small 459M / Medium 1.4B params; VRAM not stated — [The Decoder](https://the-decoder.com/stability-ai-launches-stable-audio-3-0-with-up-to-six-minute-tracks-and-open-weights/) | "Trained entirely on licensed data"; Medium up to 6:20 per track — [The Decoder](https://the-decoder.com/stability-ai-launches-stable-audio-3-0-with-up-to-six-minute-tracks-and-open-weights/) |
| DiffRhythm (ASLP-Lab; open) | $0 | Code and DiT weights Apache-2.0; a secondary source says the VAE is under the Stability Community License and MuQ-MuLan is **CC BY-NC 4.0** — [GitHub](https://github.com/ASLP-Lab/DiffRhythm), [issoh.co.jp (secondary)](https://www.issoh.co.jp/md/tech/5685) | Base needs "minimum of 8G of VRAM" with `--chunked` — [GitHub](https://github.com/ASLP-Lab/DiffRhythm) (snippet) | Pure instrumental mode added in a March 2025 update (snippet) |
| MusicGen (Meta AudioCraft) | $0 | **NC**: "model weights... released under the CC-BY-NC 4.0 license" — [GitHub](https://github.com/facebookresearch/audiocraft) | — | Avoid for startup reuse |
| **MiniMax Music** (API) | Music-2.0 $0.03/track; Music-2.5, 2.5+, 2.6 and 3.0 $0.15/track (≤5 min); lyrics $0.01 — [MiniMax pricing](https://platform.minimax.io/docs/guides/pricing-paygo) | Output license not verified | Cloud | "As of August 20, 2026, the music generation and lyrics generation APIs are no longer available to new users" — [MiniMax pricing](https://platform.minimax.io/docs/guides/pricing-paygo) |
| MiniMax Music v2.5 via **fal.ai** | $0.15 per audio — [fal.ai](https://fal.ai/models/fal-ai/minimax-music/v2.5/llms.txt) | No license statement on the fal page | Cloud | `is_instrumental=true` "generates vocal-free instrumental music" — [fal.ai](https://fal.ai/models/fal-ai/minimax-music/v2.5/llms.txt) |
| **Suno** | Pro $10/mo ($8 billed annually); Premier $30/mo ($24 annually) (secondary) — [diyai.io](https://diyai.io/ai-tools/audio-generation/suno-pricing/), [usagepricing](https://usagepricing.com/blueprint/suno) | Free: "Trial downloads are not eligible for commercial use"; paid: "Songs downloaded from Suno on paid plans remain yours to use commercially or personally" — [Suno blog, 2026-08-10](https://suno.com/blog/suno-updates-tos) | Cloud | Downloads: Free 7 lifetime, Pro 20/month, Premier 60/month, from Sept 3 — [Suno blog](https://suno.com/blog/suno-updates-tos) |
| **Udio** | Tiered subscription, pricing unconfirmed (secondary) | Licensed app ("Starstruck") reportedly "disallows downloads of generated recordings" (secondhand report) — [MBW](https://www.musicbusinessworldwide.com/udios-licensed-ai-music-app-will-be-called-starstruck-with-four-creation-modes-for-fans-report/) | Cloud | Downloads were turned off after the UMG settlement — [VCPost](https://www.vcpost.com/articles/129929/20251103/udio-users-scramble-save-creations-universal-settlement-forces-policy-shift.htm) |
| **Pixabay Music** | $0 | Free use and modification; attribution not required; no selling or distribution "on a Standalone basis" — [Pixabay license summary](https://pixabay.com/service/license-summary/) | n/a | Content ID claims possible (see below) |
| **YouTube Audio Library** | $0 | Monetization OK within the YouTube Partner Program; CC tracks require credit in the video description; **off-YouTube use not addressed** — [YouTube Help](https://support.google.com/youtube/answer/3376882) | n/a | Risky for Telegram delivery or startup reuse |

**ACE-Step 1.5 details**
- The arXiv paper was submitted on 31 Jan 2026, and Japanese press reports the open model went public on 2026-02-03 — [arXiv 2602.00744](https://arxiv.org/abs/2602.00744), [Gigazine](https://gigazine.net/news/20260204-ace-step-music-generation/).
- The model card says it "Runs locally with less than 4GB of VRAM". The repo's tier table lists "Under 6GB: 2B turbo, LM disabled by default, INT8 quantization with full CPU offload" — [HF card](https://huggingface.co/ACE-Step/Ace-Step1.5), [GitHub](https://github.com/ace-step/ACE-Step-1.5).
- Speed: "Under 2s per full song on A100, under 10s on RTX 3090" — [GitHub](https://github.com/ace-step/ACE-Step-1.5). No official RTX 4060 figure exists. One third-party guide puts 8 GB-class cards such as the RTX 4060 at "~60–90s per song", without saying how it measured this — [Clore docs (secondary)](https://docs.clore.ai/guides/music-generation/ace-step).
- Windows: "A portable package with pre-installed dependencies is available", plus `start_gradio_ui.bat` and `start_api_server.bat` — [GitHub](https://github.com/ace-step/ACE-Step-1.5).
- It "Supports 50+ languages with lyrics prompt". The README does not explicitly document an instrumental-only mode; it lists Vocal2BGM and track separation — [GitHub](https://github.com/ace-step/ACE-Step-1.5).
- Quality claims and disputes:
  - The authors report SongEval 8.09 and say it beats Suno v5 on combined metrics.
  - An independent review reports AudioBox scores of Suno v5 7.87 vs ACE-Step 1.5 7.42, with human raters placing it between Suno v4.5 and v5 — [okmiku review (secondary)](https://okmiku.com/blog/ace-step-v1-5-review).

**Suno, Udio and the label deals**
- Warner settled with Suno in November 2025; the current models are to be deprecated when licensed models arrive in 2026 — [Music in Africa (secondary)](https://www.musicinafrica.net/magazine/suno-adjusts-ai-music-ownership-terms-after-warner-music-partnership).
- Suno's August 2026 post says new models are "developed in partnership with the music industry" and "When the new models launch, all prior models will be retired" — [Suno blog](https://suno.com/blog/suno-updates-tos).
- UMG and Udio settled in late October 2025 and planned a licensed subscription platform for 2026 — [Music Business Worldwide](https://www.musicbusinessworldwide.com/universal-music-settles-udio-lawsuit-strikes-deal-for-licensed-ai-music-platform). Warner signed a licensing agreement with Udio in November 2025 — [Music Week](https://www.musicweek.com/public_html/index.php/labels/read/warner-music-group-signs-ai-licensing-agreement-with-udio/093097).

**Pixabay Content ID risk (secondary sources only)**
- Some composers who share tracks on Pixabay register them with YouTube Content ID. The usual remedy is to dispute the claim using the Pixabay license certificate, which can be downloaded when logged in — [freetouse (secondary)](https://freetouse.com/blog/no-copyright-music-subject-to-copyright-claims), [smarthustlers101 (secondary)](https://smarthustlers101.blogspot.com/2022/09/how-to-clear-youtube-content-id-claim.html).
- A competitor's blog says Pixabay has no direct Content ID integration — [Thematic (secondary, competitor)](https://hellothematic.com/thematic-vs-pixabay/).

**YouTube Audio Library outside YouTube**
- YouTube says it "can't give legal guidance, including guidance on issues with music that can occur off the platform" — [YouTube Help](https://support.google.com/youtube/answer/3376882).
- One aggregator claims standard-license tracks are restricted to YouTube videos — [LicenseOrg (secondary)](https://licenseorg.com/guide/music-audio/youtube-audio-library). Others say the Help Center simply does not address it — [Creator Essentials (secondary)](https://www.creatoressentials.com/glossary/youtube-audio-library/).

**Mixing tools (zero cost)**
- FFmpeg has a `sidechaincompress` filter for ducking music under the voice, and `loudnorm` for "EBU R128 loudness normalization" — [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html).
- Apple recommends spoken-word loudness of about −16 LKFS ±1 dB, with true peak ≤ −1 dBFS — [Apple Podcasts audio requirements](https://podcasters.apple.com/support/audio-requirements).

### Inferences
- Background beds can be generated once and reused, because a lesson needs a loopable instrumental bed rather than a new song. A library of 10–20 ACE-Step 1.5 turbo beds of ~2–5 minutes costs $0, and even at the unverified 60–90 s per song on the 4060 it takes well under an hour in total.
- MiniMax Music no longer fits: it is closed to new users, and $0.15 per track via fal.ai buys nothing that ACE-Step does not already provide for an instrumental bed. Suno Pro ($10/mo) would roughly equal the user's entire LLM budget.
- For startup-grade provenance, ACE-Step 1.5 (licensed, royalty-free and synthetic training data, with a commercial-use statement) and Stable Audio 3 (licensed data, free under $1M revenue) are better documented than Pixabay, whose claims process puts the burden on the uploader.
- Suggested mix: duck the music with `sidechaincompress` keyed on the narration, then `loudnorm` the final mix to about −16 LUFS (Apple's spoken-word target). This is a craft recommendation, not a sourced standard for video lessons.

### Gaps
- No measured ACE-Step 1.5 generation time on an RTX 4060; whether 1.5 has an explicit instrumental-only switch needs a hands-on test.
- MiniMax Music output-rights terms and fal.ai output license: not found.
- Pixabay's own Content ID help page and full Content License were not fetched; only the summary and secondary sources were read.
- No official YouTube statement on Audio Library use outside YouTube was found.
- Suno pricing comes from secondary sources; suno.com/pricing was not fetched.
- VRAM needs of Stable Audio 3 Small/Medium were not found.

## Q6. Subtitles and delivery: alignment (WhisperX, faster-whisper, stable-ts), burned-in vs SRT, Telegram limits, and file size of a 5-minute 1080p H.264 lesson

### Takeaway
The narration text is known in advance, so subtitles should come from **aligning the known script to the TTS audio**, not from transcription. Use the TTS vendor's own word timestamps where they exist. Otherwise use **Qwen3-ForcedAligner-0.6B** (Apache-2.0, includes Portuguese, up to 5 min, ~43 ms average shift vs ~133 ms for WhisperX), or WhisperX with its Apache-2.0 Portuguese wav2vec2 model.

Burn the subtitles in with FFmpeg/libass, because Telegram's built-in player does not show subtitle tracks embedded in the file. Keep a WebVTT sidecar for the local web UI.

The cloud Bot API caps `sendVideo` at **50 MB**, which means a 5-minute lesson must average about **≤1.3 Mbps** in total. That is achievable for clean 3D animation only with a two-pass target-bitrate encode or 720p. A self-hosted Bot API server raises the cap to **2,000 MB**, and at YouTube-grade bitrates a 5-minute 1080p lesson is about 300 MB.

### Cited Findings

**Alignment tools (local, zero cost)**

| Tool | License | Portuguese | How it gets word times | Local cost / VRAM | Caveats |
|---|---|---|---|---|---|
| **Qwen3-ForcedAligner-0.6B** (Alibaba Qwen, Jan 2026) | Apache-2.0 — [HF card](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) | Yes (11 languages incl. Portuguese) — [HF card](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) | Aligns given text; "word or character level timestamps" — [HF card](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) | VRAM not stated; `pip install -U qwen-asr` — [HF card](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) | "within up to 5 minutes of speech", so align per scene or paragraph — [HF card](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) |
| **WhisperX** | BSD-2-Clause — [GitHub](https://github.com/m-bain/whisperX) | Default pt aligner `jonatasgrosman/wav2vec2-large-xlsr-53-portuguese` — [alignment.py](https://raw.githubusercontent.com/m-bain/whisperX/main/whisperx/alignment.py); Apache-2.0, Common Voice pt test WER 11.31 (9.01 with LM) — [HF card](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-portuguese) | wav2vec2 forced alignment — [GitHub](https://github.com/m-bain/whisperX) | "<8GB gpu memory for large-v2 with beam_size=5"; "70x realtime with large-v2" — [GitHub](https://github.com/m-bain/whisperX) | Numbers and currency "cannot be aligned and therefore are not given a timing"; Windows needs CUDA toolkit 12.8 — [GitHub](https://github.com/m-bain/whisperX) |
| **faster-whisper** | MIT — [GitHub](https://github.com/SYSTRAN/faster-whisper) | Whisper multilingual | `word_timestamps=True` (transcription, not known-text alignment) — [GitHub](https://github.com/SYSTRAN/faster-whisper) | On an RTX 3070 Ti 8 GB, 13 min of audio with large-v2 int8: 59 s, 2,926 MB; batched int8: 16 s, 4,500 MB — [GitHub](https://github.com/SYSTRAN/faster-whisper) | Windows CUDA libraries via Purfview's standalone archive — [GitHub](https://github.com/SYSTRAN/faster-whisper) |
| **stable-ts** | MIT — [GitHub](https://github.com/jianfch/stable-ts) | Whisper multilingual | `model.align(audio, text, language=...)` aligns plain text at word level — [GitHub](https://github.com/jianfch/stable-ts) | Works with openai-whisper, faster-whisper or HF backends — [GitHub](https://github.com/jianfch/stable-ts) | **Repository archived**: "Development on this repository is indefinitely paused" — [GitHub](https://github.com/jianfch/stable-ts) |
| torchaudio MMS_FA / ctc-forced-aligner default model | **NC**: CC-BY-NC 4.0 — [PyTorch docs](https://docs.pytorch.org/audio/2.8.0/generated/torchaudio.pipelines.MMS_FA.html), [deskpai](https://huggingface.co/deskpai/ctc_forced_aligner) | Yes (1,130 languages) | CTC forced alignment | — | Avoid for startup reuse |

- Qwen3-ForcedAligner accuracy, as Accumulated Average Shift (lower is better):
  - MFA-labeled raw: Qwen3-ForcedAligner 42.9 ms, NFA 129.8 ms, WhisperX 133.2 ms.
  - 300-second concatenated audio: Qwen3-ForcedAligner 52.9 ms vs WhisperX 2,708.4 ms.
  - Source: [HF card](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B), with the tech report at [arXiv 2601.21337](https://arxiv.org/abs/2601.21337).
- stable-ts output and grouping features:
  - Outputs: SRT/VTT (`to_srt_vtt(word_level=...)`), ASS with `karaoke=True` progressive highlighting, TSV and JSON.
  - Subtitle lines can be regrouped with `split_by_length(max_chars, max_words)`, `split_by_gap`, `split_by_punctuation` and `merge_by_gap`.
  - Source: [GitHub](https://github.com/jianfch/stable-ts).
- TTS-native word timestamps are covered in Q2 (MiniMax `subtitle_type: "word"`, CosyVoice `word_timestamp_enabled`, and the commercial vendors). The free `edge-tts` package writes SRT directly with `--write-subtitles` — [edge-tts](https://github.com/rany2/edge-tts). Its licensing caveats are in Q4.

**Burned-in vs soft subtitles**
- Telegram's player does not render embedded subtitle tracks:
  - A feature request open since 2021-08-13 asks for "ASS/SRT subtitle support" in the built-in player — [Telegram bugs card 8284](https://bugs.telegram.org/c/8284).
  - A 2024-12-29 comment on that card says subtitles inside .mkv/.m4v/.mp4 files can't currently be shown in Telegram, though MPV and VLC can show them — [card 8284](https://bugs.telegram.org/c/8284).
  - No official response appears on the card.
- A separate Android bug cut off the bottom of videos (hiding captions) in landscape full-screen. It is marked "Fixed" in 13.0.0; the page doesn't show the year — [Telegram bugs card 62682](https://bugs.telegram.org/c/62682).
- FFmpeg's `subtitles` filter can "Draw subtitles on top of input video using the libass library", with `force_style` to override fonts and colours — [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html).
- The HTML `<track>` element uses WebVTT (`.vtt`) files, with `kind="subtitles"` or `"captions"` — [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/track). The local web UI therefore needs VTT, not SRT.

**Telegram Bot API limits (Bot API 10.4, dated 2026-11-09)**
- `sendVideo`: "Telegram clients support MPEG4 videos (other formats may be sent as Document)... Bots can currently send video files of up to 50 MB in size, this limit may be changed in the future." It has a `supports_streaming` parameter ("Pass True if the uploaded video is suitable for streaming") — [Bot API](https://core.telegram.org/bots/api).
- Sending files by URL: "5 MB max size for photos and 20 MB max for other types of content". Multipart upload: "10 MB max size for photos, 50 MB for other files" — [Bot API](https://core.telegram.org/bots/api).
- `getFile`: "The maximum file size to download is 20 MB" — [Bot API](https://core.telegram.org/bots/api).
- The Bot FAQ also says: "Bots can currently send files of any type of up to 50 MB in size" — [Bots FAQ](https://core.telegram.org/bots/faq).
- A **local Bot API server** (`--local`) can "Upload files up to 2000 MB", "Download files without a size limit", and "Upload files using their local path and the file URI scheme" — [Bot API](https://core.telegram.org/bots/api), [tdlib/telegram-bot-api](https://github.com/tdlib/telegram-bot-api).
  - Setup requires your own `api_id`/`api_hash`, and the bot must call `logOut` on the cloud server before switching — [README](https://raw.githubusercontent.com/tdlib/telegram-bot-api/master/README.md).
  - It is licensed BSL-1.0 and builds with a C++17 compiler, MSVC 19.1+ included. The README gives no Windows-specific steps — [GitHub](https://github.com/tdlib/telegram-bot-api).

**File size of a 5-minute 1080p H.264 lesson**
- YouTube's recommended upload bitrates for 1080p SDR are 8 Mbps at 24/25/30 fps and 12 Mbps at 48/50/60 fps; for 720p, 5 and 7.5 Mbps. It also recommends AAC-LC audio at 384 kbps stereo, the MP4 container, and H.264 High Profile with progressive scan and a closed GOP of half the frame rate — [YouTube Help](https://support.google.com/youtube/answer/1722171).
- x264 CRF runs 0–51 with a default of 23 and "sane" values of 18–28. A change of ±6 CRF roughly halves or doubles the file size, and the bitrate a given CRF produces depends on content complexity — [slhck CRF guide](https://slhck.info/video/2017/02/24/crf-guide.html).
- Netflix's per-title encoding work found animated content could be streamed at 1080p with as little as ~1.5 Mbps, because animation is mostly flat regions with little noise — [The Register](https://www.theregister.com/2015/12/16/netflix_per_title_encode_optimization/), [Fortune](https://fortune.com/2015/12/15/netflix-less-data/).
- As a conversion rule, 1 Mbps ≈ 7.5 MB per minute — [streamersize calculator (secondary)](https://streamersize.pages.dev/size/1080p-30fps-h264).

### Inferences
- **Computed sizes for a 300-second lesson** (size MB ≈ total kbps × 0.0375; my arithmetic):

| Encode target | Video + audio | ≈ Size | Fits 50 MB cloud cap? |
|---|---|---|---|
| YouTube-grade 1080p30 | 8,000 + 384 kbps | ~314 MB | No (local Bot API server only) |
| Typical CRF 20–23 render of moderately complex 3D | ~3,000 + 128 kbps | ~117 MB | No |
| Netflix-style animation floor | 1,500 + 128 kbps | ~61 MB | No |
| Two-pass 1080p target | 1,100 + 96 kbps | ~45 MB | Yes, with ~10% margin |
| 720p two-pass | 900 + 96 kbps | ~37 MB | Yes |

- A practical rule follows: with the cloud Bot API, compute `video_kbps = (48 MB × 8,000 / duration_s) − audio_kbps` and run a two-pass x264 encode with `-movflags +faststart` and `supports_streaming=True`. Otherwise run the local Bot API server (Docker or a native MSVC build) and send 1080p at CRF 20–23.
- A further option is to send a 720p version under 50 MB through Telegram and keep the 1080p master and VTT on the local web UI.
- Normalize numbers, units and acronyms to words in the script before TTS. This helps both pronunciation and alignment, since WhisperX cannot time numbers or currency.
- Because Qwen3-ForcedAligner tops out at 5 minutes, align per scene. Per-scene TTS calls are needed anyway to sync with 3D shot boundaries.
- Burned-in subtitles should be generated as ASS (styled, optionally karaoke word highlighting via stable-ts `to_ass`, or a small custom writer if stable-ts's archived status is a concern). Keep subtitles above the bottom ~10% of the frame as a hedge against client cropping.

### Gaps
- No measured file size for this user's actual 3D renders: the bitrate CRF needs depends on motion, particles and render noise. A 30-second test encode is needed.
- Telegram does not document whether bot-sent videos are re-encoded server-side; no source found.
- Qwen3-ForcedAligner VRAM and Windows install friction were not documented; the accuracy figures are vendor-reported.
- No Windows-specific build guide for the local Bot API server in the official README (third-party Docker images exist but were not evaluated).
