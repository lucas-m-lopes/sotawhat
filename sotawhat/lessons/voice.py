# sotawhat/lessons/voice.py
"""Narration: one WAV per sentence (beat), so the length of each sentence becomes the length of its animation.

Voices: `piper:<faber|cadu|jeff>` (local, CPU, free) or `google:<voice>` (Chirp 3 HD pt-BR, GOOGLE_TTS_API_KEY,
1 million characters a month free). The glossary rewrites English jargon for the local voices (the subtitles keep
the original); Google gets IPA pronunciations when the glossary has them. A lesson made from an idea of the
ledger (possible IP) must use a local voice."""
import base64
import json
import re
import wave
from pathlib import Path

import httpx

from sotawhat.configfiles import read_yaml

DEFAULT_VOICE = "piper:faber"
GOOGLE_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
GOOGLE_VOICES = ("pt-BR-Chirp3-HD-Charon", "pt-BR-Chirp3-HD-Kore", "pt-BR-Chirp3-HD-Puck")   # blind-test candidates
SAMPLE = ("No mecanismo de atenção, cada token gera três vetores: a query, a key e o value. O produto entre query e "
          "key passa pela softmax, e o modelo de linguagem usa esses pesos para misturar os embeddings. Na tomografia, "
          "o detector mede a atenuação dos raios X e o computador reconstrói um volume de voxels.")


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
    """The text the local voices read: each glossary term (whole word, any case) becomes its `spoken` form."""
    for entry in glossary:
        if entry.get("spoken"):
            text = re.sub(rf"(?<![\w-]){re.escape(entry['term'])}(?![\w-])", entry["spoken"], text, flags=re.I)
    return text


def wav_seconds(path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


class PiperEngine:
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
                                   "items": [{"text": spoken(t, glossary), "out": str(Path(p).resolve())} for t, p in jobs]},
                                  ensure_ascii=False), encoding="utf-8")
        import subprocess

        from sotawhat.lessons.tools import KIT
        try:
            done = self.tools.run([self.tools.python, KIT / "tts_piper.py", job], cwd=workdir, timeout=900)
        except subprocess.TimeoutExpired:
            raise VoiceError("o Piper passou de 15 min") from None
        if done.returncode != 0:
            raise VoiceError(f"Piper falhou: {done.stderr[-600:]}")


class GoogleEngine:
    def __init__(self, api_key, voice="pt-BR-Chirp3-HD-Charon", client=None):
        if not api_key:
            raise VoiceError("GOOGLE_TTS_API_KEY vazio: crie a chave (Cloud Text-to-Speech API) ou use piper:faber")
        self.api_key, self.voice = api_key, voice
        self._client = client

    def synthesize(self, jobs, glossary=(), workdir=None) -> None:
        client = self._client or httpx.Client(timeout=60)
        try:
            for text, out in jobs:
                body = {"input": {"text": text}, "voice": {"languageCode": "pt-BR", "name": self.voice},
                        "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}
                ipa = [{"phrase": e["term"], "phoneticEncoding": "PHONETIC_ENCODING_IPA", "pronunciation": e["ipa"]}
                       for e in glossary if e.get("ipa") and re.search(rf"(?<!\w){re.escape(e['term'])}(?!\w)", text, re.I)]
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


def narrate(engine, plan, audio_dir, glossary=(), pause=0.45) -> list:
    """One WAV per sentence in audio_dir (c01f01.wav…), keeping the ones already there.
    -> [[seconds of each beat, pause included] per scene]."""
    audio_dir = Path(audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)
    paths = [[audio_dir / f"c{n:02d}f{k:02d}.wav" for k, _ in enumerate(scene.beats, 1)]
             for n, scene in enumerate(plan.scenes, 1)]
    jobs = [(beat.narration, path) for scene, row in zip(plan.scenes, paths) for beat, path in zip(scene.beats, row)
            if not path.exists()]
    engine.synthesize(jobs, glossary, workdir=audio_dir)
    return [[round(wav_seconds(p) + pause, 3) for p in row] for row in paths]


def beat_paths(audio_dir, plan) -> list:
    return [[Path(audio_dir) / f"c{n:02d}f{k:02d}.wav" for k, _ in enumerate(scene.beats, 1)]
            for n, scene in enumerate(plan.scenes, 1)]
