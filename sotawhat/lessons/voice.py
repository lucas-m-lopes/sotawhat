# sotawhat/lessons/voice.py
"""Narration: one WAV per sentence (beat), so the length of each sentence becomes the length of its animation.

Voices: `piper:<faber|cadu|jeff>` (local, CPU, free) or `google:<voice>` (Chirp 3 HD pt-BR, GOOGLE_TTS_API_KEY,
1 million characters a month free). A lesson made from an idea of the ledger (possible IP) must use a local voice.

Speech that sounds less read (measured in the pilot: commas came out as 0.12–0.16 s gaps and every sentence was
followed by the same 0.6–0.7 s of silence):
- `speech_text` rewrites the subtitle text for the ear: dashes, parentheses and colons become commas,
  semicolons become full stops, acronyms are spelled (AUC → á u cê), symbols become words (% → por cento,
  2,86x → 2,86 vezes) and the glossary gives English jargon its Brazilian reading. The subtitles keep the original.
- `shape_pauses` (Piper only) trims the edges of each clip and lengthens the short pauses inside it to a
  breathing pause, without touching the brief silences of stop consonants.
- `narrate` puts a short pause between sentences and a longer one at the end of a scene."""
import base64
import json
import re
import wave
from pathlib import Path

import httpx
import numpy as np

from sotawhat.configfiles import read_yaml

DEFAULT_VOICE = "piper:faber"
GOOGLE_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
GOOGLE_VOICES = ("pt-BR-Chirp3-HD-Charon", "pt-BR-Chirp3-HD-Kore", "pt-BR-Chirp3-HD-Puck")   # blind-test candidates
SAMPLE = ("No mecanismo de atenção, cada token gera três vetores: a query, a key e o value. O produto entre query e "
          "key passa pela softmax, e o modelo de linguagem usa esses pesos para misturar os embeddings. Na tomografia, "
          "o detector mede a atenuação dos raios X e o computador reconstrói um volume de voxels.")
GAP_S, SCENE_END_S = 0.32, 0.75          # after a sentence; after the last sentence of a scene
INNER_PAUSE_S = 0.24                     # a comma, as heard
LETTERS = {"A": "á", "B": "bê", "C": "cê", "D": "dê", "E": "é", "F": "éfe", "G": "gê", "H": "agá", "I": "i",
           "J": "jota", "K": "cá", "L": "éle", "M": "ême", "N": "êne", "O": "ó", "P": "pê", "Q": "quê", "R": "érre",
           "S": "ésse", "T": "tê", "U": "u", "V": "vê", "W": "dáblio", "X": "xis", "Y": "ípsilon", "Z": "zê"}
WORD_ACRONYMS = {"SUS", "INCA", "AIDS", "SARS", "MERS", "COVID", "ONU", "OTAN", "FIFA", "UNESCO", "ANVISA"}
_ACRONYM = re.compile(r"(?<![\w-])([A-Z]{2,4})(?![\w-])")
_SYMBOLS = [(re.compile(r"(\d)\s*%"), r"\1 por cento"), (re.compile(r"(\d)\s*[x×](?=[\s,.;:!?]|$)"), r"\1 vezes"),
            (re.compile(r"\s*≈\s*"), " cerca de "), (re.compile(r"\s*≠\s*"), " diferente de "),
            (re.compile(r"\s*(→|->|⇒)\s*"), ", "), (re.compile(r"\s*&\s*"), " e "), (re.compile(r"\s+\+\s+"), " mais "),
            (re.compile(r"\s+=\s+"), " igual a "), (re.compile(r"(?<=[a-zà-ú])/(?=[a-zà-ú])", re.I), " ou ")]
_PUNCT = [(re.compile(r"\s*[—–]\s*"), ", "), (re.compile(r"\s*\(\s*"), ", "), (re.compile(r"\s*\)\s*"), ", "),
          (re.compile(r"\s*:\s*"), ", "), (re.compile(r"\s*;\s*"), ". "), (re.compile(r"[\"“”«»]|(?<!\w)'|'(?!\w)"), ""),
          (re.compile(r"\.{3}|…"), "."), (re.compile(r"\s*,(\s*,)+"), ","), (re.compile(r",\s*([.!?])"), r"\1"),
          (re.compile(r"\s+([,.!?])"), r"\1"), (re.compile(r"\s{2,}"), " ")]


class VoiceError(Exception):
    pass


def parse_voice(spec) -> tuple:
    engine, _, name = (spec or DEFAULT_VOICE).partition(":")
    if engine not in ("piper", "google") or not name:
        raise VoiceError(f"voz inválida: {spec!r} (use piper:faber ou google:pt-BR-Chirp3-HD-Charon)")
    return engine, name


def load_glossary(path) -> list:
    terms = (read_yaml(Path(path)) or {}).get("terms") or [] if Path(path).exists() else []
    return sorted([t for t in terms if t.get("term")], key=lambda t: -len(t["term"]))


def spoken(text, glossary) -> str:
    """Each glossary term (whole word, any case) becomes its `spoken` form."""
    for entry in glossary:
        if entry.get("spoken"):
            text = re.sub(rf"(?<!\w){re.escape(entry['term'])}(?!\w)", entry["spoken"], text, flags=re.I)
    return text


def speech_text(text, glossary=(), spell=True) -> str:
    """The subtitle text rewritten for the ear (see the module docstring)."""
    out = spoken(text, glossary)
    for pattern, repl in _SYMBOLS:
        out = pattern.sub(repl, out)
    if spell:
        out = _ACRONYM.sub(lambda m: m.group(1) if m.group(1) in WORD_ACRONYMS
                           else " ".join(LETTERS[c] for c in m.group(1)), out)
    for pattern, repl in _PUNCT:
        out = pattern.sub(repl, out)
    out = re.sub(r"([.!?]\s+)([a-zà-ú])", lambda m: m.group(1) + m.group(2).upper(), out.strip(" ,"))
    out = out[:1].upper() + out[1:]
    return out if out.endswith((".", "!", "?")) else out + "."


def wav_seconds(path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def shape_pauses(path, inner=INNER_PAUSE_S, threshold_db=-38.0, min_run=0.10, edge=0.04) -> float:
    """Trims the silence at both ends of a clip (keeping `edge`) and lengthens every inner pause of at least
    `min_run` s (a comma; shorter gaps are stop consonants) to `inner` s. -> the new length in seconds."""
    with wave.open(str(path)) as w:
        params, data = w.getparams(), w.readframes(w.getnframes())
    if params.sampwidth != 2 or params.nchannels != 1 or not data:
        return wav_seconds(path)
    x = np.frombuffer(data, dtype=np.int16)
    rate, win = params.framerate, max(1, params.framerate // 100)          # 10 ms windows
    n = len(x) // win
    if n < 3:
        return wav_seconds(path)
    frames = (x[:n * win].astype(np.float32) / 32768).reshape(n, win)
    level = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    loud = np.flatnonzero(level > threshold_db)
    if loud.size == 0:
        return wav_seconds(path)
    first, last = max(0, loud[0] - 2), min(n - 1, loud[-1] + 3)        # a margin for soft onsets and endings
    pieces, cursor, quiet_from = [], first * win, None
    pad = np.zeros(int(edge * rate), dtype=np.int16)
    for i in range(first, last + 1):
        if level[i] <= threshold_db:
            quiet_from = i if quiet_from is None else quiet_from
            continue
        if quiet_from is not None:
            run = (i - quiet_from) * win
            if run >= min_run * rate and run < inner * rate:          # a short pause: make it a breathing pause
                middle = (quiet_from * win + i * win) // 2
                pieces += [x[cursor:middle], np.zeros(int(inner * rate) - run, dtype=np.int16)]
                cursor = middle
            quiet_from = None
    pieces.append(x[cursor:(last + 1) * win])
    shaped = np.concatenate([pad] + pieces + [pad])
    with wave.open(str(path), "wb") as w:
        w.setparams(params)
        w.writeframes(shaped.tobytes())
    return len(shaped) / rate


class PiperEngine:
    shapes_pauses = True

    def __init__(self, tools, voice="faber", length_scale=1.0):
        self.tools, self.voice, self.length_scale = tools, voice, length_scale
        self.model = tools.voices / f"pt_BR-{voice}-medium.onnx"

    def synthesize(self, jobs, glossary=(), workdir=None) -> None:
        """jobs: [(text, out_path)], all in one subprocess (the model loads once)."""
        if not jobs:
            return
        if not self.model.exists():
            raise VoiceError(f"voz Piper ausente: {self.model.name} (rode `sotawhat lessons setup`)")
        workdir = Path(workdir or Path(jobs[0][1]).parent).resolve()
        job = workdir / "piper_job.json"
        job.write_text(json.dumps({"model": str(self.model.resolve()), "length_scale": self.length_scale,
                                   "items": [{"text": speech_text(t, glossary), "out": str(Path(p).resolve())}
                                             for t, p in jobs]}, ensure_ascii=False), encoding="utf-8")
        import subprocess

        from sotawhat.lessons.tools import KIT
        try:
            done = self.tools.run([self.tools.python, KIT / "tts_piper.py", job], cwd=workdir, timeout=900)
        except subprocess.TimeoutExpired:
            raise VoiceError("o Piper passou de 15 min") from None
        if done.returncode != 0:
            raise VoiceError(f"Piper falhou: {done.stderr[-600:]}")
        for _, path in jobs:
            shape_pauses(path)


class GoogleEngine:
    shapes_pauses = False          # Chirp 3 HD already pauses like a person

    def __init__(self, api_key, voice="pt-BR-Chirp3-HD-Charon", client=None):
        if not api_key:
            raise VoiceError("GOOGLE_TTS_API_KEY vazio: crie a chave (Cloud Text-to-Speech API) ou use piper:faber")
        self.api_key, self.voice = api_key, voice
        self._client = client

    def synthesize(self, jobs, glossary=(), workdir=None) -> None:
        client = self._client or httpx.Client(timeout=60)
        try:
            for text, out in jobs:
                said = speech_text(text, [e for e in glossary if not e.get("ipa")])
                body = {"input": {"text": said}, "voice": {"languageCode": "pt-BR", "name": self.voice},
                        "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}
                ipa = [{"phrase": e["term"], "phoneticEncoding": "PHONETIC_ENCODING_IPA", "pronunciation": e["ipa"]}
                       for e in glossary if e.get("ipa") and re.search(rf"(?<!\w){re.escape(e['term'])}(?!\w)", said, re.I)]
                if ipa:
                    body["input"]["customPronunciations"] = {"pronunciations": ipa}
                r = client.post(GOOGLE_URL, json=body, headers={"X-Goog-Api-Key": self.api_key})
                if r.status_code != 200:   # the key travels in a header and never appears in the message
                    raise VoiceError(f"Google TTS HTTP {r.status_code}: {r.text[:300]}")
                Path(out).write_bytes(base64.b64decode(r.json()["audioContent"]))
        finally:
            if self._client is None:
                client.close()


def engine_for(spec, tools, settings):
    engine, name = parse_voice(spec)
    if engine == "piper":
        return PiperEngine(tools, name)
    return GoogleEngine(settings.google_tts_api_key, name)


def narrate(engine, plan, audio_dir, glossary=(), gap=GAP_S, scene_end=SCENE_END_S) -> list:
    """One WAV per sentence in audio_dir (c01f01.wav…), keeping the ones already there.
    -> [[seconds of each beat, its pause included] per scene]."""
    audio_dir = Path(audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    paths = beat_paths(audio_dir, plan)
    jobs = [(beat.narration, path) for scene, row in zip(plan.scenes, paths) for beat, path in zip(scene.beats, row)
            if not path.exists()]
    engine.synthesize(jobs, glossary, workdir=audio_dir)
    return [[round(wav_seconds(p) + (scene_end if k == len(row) - 1 else gap), 3) for k, p in enumerate(row)]
            for row in paths]


def beat_paths(audio_dir, plan) -> list:
    return [[Path(audio_dir) / f"c{n:02d}f{k:02d}.wav" for k, _ in enumerate(scene.beats, 1)]
            for n, scene in enumerate(plan.scenes, 1)]
