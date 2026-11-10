# sotawhat/lessons/eleven.py
"""ElevenLabs narration for the HyperFrames lessons: one request per scene, with the time of every character.

Why per scene and not per sentence: the voice keeps its intonation across the sentences of a scene and makes its
own pauses, which is what made the Piper narration sound read. The character timestamps give the start and end of
every sentence (the beats that time the animation) and of every word (the captions and the cue words that make
an element appear when its name is spoken). `previous_text`/`next_text` keep the tone continuous across scenes.

Credits are spent once: every scene is cached by a hash of its text, voice, model and settings, so a rerun of the
same lesson costs nothing. The key travels only in the `xi-api-key` header and is never logged."""
import base64
import hashlib
import json
import re
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path

import httpx

API = "https://api.elevenlabs.io"
DEFAULT_VOICE = "UQ3s9h7N3CVJBL2USizn"      # Klaus, Brazilian professional narrator (in the user's library)
DEFAULT_MODEL = "eleven_v4"
SETTINGS = {"stability": 0.45, "similarity_boost": 0.8, "style": 0.15, "use_speaker_boost": True, "speed": 1.0}
RATE = 44100
SCENE_GAP_S = 0.7          # silence between scenes: the visual transition happens here
LEAD_IN_S = 0.35           # silence before the first word of a scene's audio


class ElevenError(Exception):
    pass


@dataclass
class SceneAudio:
    wav: Path
    duration: float
    beats: list            # [(start, end)] seconds local to the scene audio, one per sentence
    words: list            # [{"text", "start", "end", "beat"}] local seconds
    chars: int
    cached: bool = False


@dataclass
class Narration:
    wav: Path
    duration: float
    scenes: list = field(default_factory=list)   # [{"start", "end", "beats": [(s, e)], "words": [...]}] global seconds
    chars: int = 0
    billed_chars: int = 0


class ElevenLabs:
    def __init__(self, api_key, client=None):
        if not api_key:
            raise ElevenError("ELEVENLABS_API_KEY vazia: ponha a chave no .env")
        self.client = client or httpx.Client(base_url=API, timeout=180, headers={"xi-api-key": api_key})

    def speak(self, text, voice=DEFAULT_VOICE, model=DEFAULT_MODEL, previous_text=None, next_text=None,
              settings=None) -> tuple:
        """-> (mp3 bytes, alignment {"characters", "character_start_times_seconds", "character_end_times_seconds"})."""
        body = {"text": text, "model_id": model, "language_code": "pt", "voice_settings": settings or SETTINGS}
        if previous_text:
            body["previous_text"] = previous_text
        if next_text:
            body["next_text"] = next_text
        r = self.client.post(f"/v1/text-to-speech/{voice}/with-timestamps",
                             params={"output_format": "mp3_44100_128"}, json=body)
        if r.status_code != 200:
            raise ElevenError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
        data = r.json()
        alignment = data.get("alignment") or data.get("normalized_alignment")
        if not alignment or not data.get("audio_base64"):
            raise ElevenError("ElevenLabs não devolveu áudio com tempos")
        return base64.b64decode(data["audio_base64"]), alignment


def spans(sentences) -> list:
    """Character ranges of each sentence in `" ".join(sentences)`."""
    out, pos = [], 0
    for s in sentences:
        out.append((pos, pos + len(s)))
        pos += len(s) + 1
    return out


def beat_times(alignment, sentences) -> list:
    """[(start, end)] of each sentence from the character times (spaces and punctuation are skipped)."""
    chars = alignment["characters"]
    starts, ends = alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]
    text = " ".join(sentences)
    if "".join(chars) != text:
        raise ElevenError("o alinhamento não corresponde ao texto enviado")
    out = []
    for a, b in spans(sentences):
        idx = [i for i in range(a, b) if chars[i].strip() and chars[i] not in ".,;:!?"]
        if not idx:
            raise ElevenError(f"frase sem caracteres alinhados: {text[a:b]!r}")
        out.append((float(starts[idx[0]]), float(ends[idx[-1]])))
    return out


_WORD = re.compile(r"\S+")


def word_times(alignment, sentences) -> list:
    """[{"text", "start", "end", "beat"}] for every word of the text, with its punctuation."""
    starts, ends = alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]
    out = []
    for n, (a, _) in enumerate(spans(sentences)):
        for m in _WORD.finditer(sentences[n]):
            i, j = a + m.start(), a + m.end() - 1
            core = [k for k in range(i, j + 1) if sentences[n][k - a].isalnum()] or [i, j]
            out.append({"text": m.group(), "start": float(starts[core[0]]), "end": float(ends[core[-1]]), "beat": n})
    return out


def cache_key(text, voice, model, settings) -> str:
    raw = json.dumps([text, voice, model, settings], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def to_wav(ffmpeg, mp3, wav, lead_in=LEAD_IN_S) -> float:
    """MP3 → 44.1 kHz mono WAV with `lead_in` seconds of silence in front; -> duration."""
    subprocess.run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3),
                    "-af", f"adelay={int(lead_in * 1000)}:all=1", "-ac", "1", "-ar", str(RATE), str(wav)],
                   check=True, capture_output=True)
    with wave.open(str(wav), "rb") as w:
        return w.getnframes() / w.getframerate()


def speak_scene(el, sentences, out_dir, ffmpeg, name, voice=DEFAULT_VOICE, model=DEFAULT_MODEL,
                previous_text=None, next_text=None, settings=None) -> SceneAudio:
    """One scene: cached MP3 + alignment, WAV with lead-in, beat and word times shifted by the lead-in."""
    settings = settings or SETTINGS
    text = " ".join(sentences)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    key = cache_key(text, voice, model, settings)
    mp3, meta = out_dir / f"{name}-{key}.mp3", out_dir / f"{name}-{key}.json"
    cached = mp3.exists() and meta.exists()
    if cached:
        alignment = json.loads(meta.read_text(encoding="utf-8"))
    else:
        audio, alignment = el.speak(text, voice, model, previous_text, next_text, settings)
        mp3.write_bytes(audio)
        meta.write_text(json.dumps(alignment, ensure_ascii=False), encoding="utf-8")
    wav = out_dir / f"{name}.wav"
    duration = to_wav(ffmpeg, mp3, wav)
    beats = [(s + LEAD_IN_S, e + LEAD_IN_S) for s, e in beat_times(alignment, sentences)]
    words = [{**w, "start": w["start"] + LEAD_IN_S, "end": w["end"] + LEAD_IN_S} for w in word_times(alignment, sentences)]
    return SceneAudio(wav, duration, beats, words, len(text), cached)


def silence(path, seconds) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"\x00\x00" * int(round(seconds * RATE)))
    return Path(path)


def join(parts, out) -> float:
    """Concatenates 44.1 kHz mono 16-bit WAVs; -> duration."""
    frames = b""
    for p in parts:
        with wave.open(str(p), "rb") as w:
            if w.getframerate() != RATE or w.getnchannels() != 1 or w.getsampwidth() != 2:
                raise ElevenError(f"formato inesperado em {p}")
            frames += w.readframes(w.getnframes())
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)
    return len(frames) / 2 / RATE


def narrate(el, scenes, out_dir, ffmpeg, intro=0.0, voice=DEFAULT_VOICE, model=DEFAULT_MODEL, settings=None,
            gap=SCENE_GAP_S, progress=print) -> Narration:
    """`scenes`: [[sentence, …], …]. Builds narration.wav = intro silence + scene, gap, scene, …, with global times."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    texts = [" ".join(s) for s in scenes]
    parts, t, timeline, billed = [], 0.0, [], 0
    if intro > 0:
        parts.append(silence(out_dir / "intro.wav", intro))
        t = intro
    for n, sentences in enumerate(scenes):
        audio = speak_scene(el, sentences, out_dir, ffmpeg, f"cena{n + 1:02d}", voice, model,
                            previous_text=texts[n - 1] if n else None,
                            next_text=texts[n + 1] if n + 1 < len(texts) else None, settings=settings)
        billed += 0 if audio.cached else audio.chars
        progress(f"[voz] cena {n + 1}: {audio.duration:.1f} s{' (cache)' if audio.cached else ''}")
        parts.append(audio.wav)
        timeline.append({"start": t, "end": t + audio.duration, "duration": audio.duration,
                         "beats": [(t + s, t + e) for s, e in audio.beats],
                         "words": [{**w, "start": t + w["start"], "end": t + w["end"]} for w in audio.words]})
        t += audio.duration
        if n + 1 < len(scenes):
            parts.append(silence(out_dir / f"gap{n + 1:02d}.wav", gap))
            t += gap
    tail = silence(out_dir / "tail.wav", 1.2)
    parts.append(tail)
    wav = out_dir / "narration.wav"
    duration = join(parts, wav)
    return Narration(wav, duration, timeline, sum(len(x) for x in texts), billed)
