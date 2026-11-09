# sotawhat/lessons/assemble.py
"""Assembly: the audio of each scene (its sentences, each padded to the length of its animation), the opening and
closing cards (silent), and the final MP4: H.264 + AAC under the Telegram cloud limit (50 MB; target 48 MB), in
1080p when the bitrate allows it, otherwise 720p."""
import json
import subprocess
import wave
from pathlib import Path

from sotawhat.lessons.render import render_manim
from sotawhat.lessons.tools import media_seconds

AUDIO_KBPS = 96


def _read(path):
    with wave.open(str(path)) as w:
        return w.getparams(), w.readframes(w.getnframes())


def concat_wav(parts, out, rate=None, channels=1, width=2) -> float:
    """parts: [(wav path or None, seconds)]; each part is cut or padded with silence to its seconds. -> total s."""
    rate = rate or next((wav_rate(p) for p, _ in parts if p is not None), 24000)
    frames = []
    for path, seconds in parts:
        data = b""
        if path is not None:
            params, data = _read(path)
            if (params.framerate, params.nchannels, params.sampwidth) != (rate, channels, width):
                raise ValueError(f"{path}: formato {params.framerate} Hz/{params.nchannels} canais diferente do resto")
        size = int(round(seconds * rate)) * channels * width
        frames.append(data[:size].ljust(size, b"\0"))
    with wave.open(str(out), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(b"".join(frames))
    return sum(seconds for _, seconds in parts)


def wav_rate(path) -> int:
    with wave.open(str(path)) as w:
        return w.getframerate()


def scene_audio(beat_wavs, durations, out, video_seconds=None, rate=None) -> float:
    """The scene's track: each sentence at its slot; the last slot stretches to the video's real length."""
    parts = [(p, d) for p, d in zip(beat_wavs, durations)]
    if video_seconds is not None and parts:
        drift = video_seconds - sum(durations)
        path, last = parts[-1]
        parts[-1] = (path, max(0.05, last + drift))
    return concat_wav(parts, out, rate=rate)


def render_card(tools, card_dir, kit_dir, cache_dir, kind, title, lines, seconds) -> Path:
    card_dir = Path(card_dir)
    card_dir.mkdir(parents=True, exist_ok=True)
    spec = card_dir / "card.json"
    spec.write_text(json.dumps({"kind": kind, "title": title, "lines": lines, "seconds": seconds}, ensure_ascii=False),
                    encoding="utf-8")
    return render_manim(tools, card_dir, kit_dir, cache_dir, script=Path(kit_dir).resolve() / "cards.py", cls="Card",
                        out_name=f"{kind}.mp4", spec_env={"LESSON_CARD": spec.resolve()})


def target_kbps(seconds, max_mb) -> int:
    """Video bitrate that fits `max_mb` with the audio, with 4% for the container."""
    return int((max_mb * 8 * 1024 * 0.96) / max(1.0, seconds) - AUDIO_KBPS)


def encode(tools, videos, audio, out, max_mb=48, workdir=None) -> dict:
    """Concatenates the clips (all 30 fps), puts the narration under them and encodes under `max_mb`."""
    out = Path(out)
    workdir = Path(workdir or out.parent)
    listing = workdir / "clips.txt"
    listing.write_text("".join(f"file '{Path(v).resolve().as_posix()}'\n" for v in videos), encoding="utf-8")
    seconds = sum(media_seconds(tools, v) for v in videos)
    kbps = min(4000, target_kbps(seconds, max_mb))
    for attempt in range(3):
        scale = [] if kbps >= 900 else ["-vf", "scale=1280:720"]
        cmd = [tools.ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listing,
               "-i", audio, "-map", "0:v", "-map", "1:a", *scale, "-c:v", "libx264", "-preset", "medium", "-crf", "23",
               "-maxrate", f"{kbps}k", "-bufsize", f"{2 * kbps}k", "-pix_fmt", "yuv420p", "-r", "30",
               "-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k", "-ac", "1", "-ar", "48000", "-movflags", "+faststart",
               "-shortest", out]
        done = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace",
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if done.returncode != 0:
            raise RuntimeError(f"FFmpeg falhou: {done.stderr[-600:]}")
        size = out.stat().st_size
        if size <= max_mb * 1024 * 1024:
            return {"seconds": round(seconds, 2), "bytes": size, "kbps": kbps, "height": 1080 if not scale else 720}
        kbps = int(kbps * 0.8)
    raise RuntimeError(f"o vídeo não coube em {max_mb} MB")
