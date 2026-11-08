# sotawhat/pipeline/media.py
"""What an Instagram post shows (P5, SDD §7.2): its images go to the vision model and, if the optional
`faster-whisper` is installed, a reel's audio is transcribed on the CPU.

- Images are downloaded in the same run (CDN URLs expire), cut to ≤ 800 px on the long side and sent as
  JPEG in base64; at most `max_images` per carousel. Downloads have a size cap and never follow a URL
  outside the Instagram/Facebook CDNs.
- A failure (download, vision or transcript) only costs that part: the post still gets its caption. A budget
  stop turns the vision off for the rest of the run (the posts were already paid for on Apify)."""
import base64
import importlib.util
import io
import logging
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import PostVision

log = logging.getLogger("sotawhat.media")
CDN = ("cdninstagram.com", "fbcdn.net")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_VIDEO_BYTES = 60 * 1024 * 1024


def _cdn(url) -> bool:
    host = (urlsplit(url or "").hostname or "").lower()
    return urlsplit(url or "").scheme == "https" and any(host == d or host.endswith("." + d) for d in CDN)


def download(client, url, limit) -> bytes:
    if not _cdn(url):
        raise ValueError(f"fora da CDN do Instagram: {urlsplit(url or '').hostname}")
    with client.stream("GET", url, timeout=30) as r:
        r.raise_for_status()
        chunks, size = [], 0
        for chunk in r.iter_bytes():
            size += len(chunk)
            if size > limit:
                raise ValueError(f"arquivo maior que {limit // 1024 // 1024} MB")
            chunks.append(chunk)
    return b"".join(chunks)


def shrink(data, side=800) -> str:
    """-> data URL of a JPEG with the long side ≤ `side`."""
    from PIL import Image

    with Image.open(io.BytesIO(data)) as img:
        img = img.convert("RGB")
        img.thumbnail((side, side))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode("ascii")


def whisper_available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


class Transcriber:
    """faster-whisper on the CPU (model `base`, int8), loaded on first use into data/models/whisper."""

    def __init__(self, models_dir, model="base"):
        self.models_dir, self.model_name, self._model = Path(models_dir) / "whisper", model, None

    def __call__(self, video: bytes) -> str:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8",
                                       download_root=str(self.models_dir))
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(video)
            path = f.name
        try:
            segments, _ = self._model.transcribe(path, vad_filter=True)
            return " ".join(s.text.strip() for s in segments)[:4000]
        finally:
            Path(path).unlink(missing_ok=True)


def make_describer(gateway, max_images=3, transcriber=None, client=None):
    """-> describer(post) -> text: what the images show and, for a reel, what is said."""
    system = load_prompt("vision_v1")
    budget = {"stopped": None}

    def describe(post) -> str:
        own = client or httpx.Client(follow_redirects=True, headers={"User-Agent": "sotawhat/3.0"})
        parts = []
        try:
            images = []
            for media in post["media"][:max_images]:
                try:
                    images.append(shrink(download(own, media["url"], MAX_IMAGE_BYTES)))
                except (httpx.HTTPError, ValueError, OSError) as exc:
                    log.warning("instagram %s: imagem ignorada (%s)", post["shortcode"], exc)
            if images and gateway is not None and not budget["stopped"]:
                content = [{"type": "text", "text": f"@{post['owner']} ({post['type']}). Legenda:\n{post['caption'][:2000]}"}]
                content += [{"type": "image_url", "image_url": {"url": url}} for url in images]
                try:
                    res = gateway.structured_call("vision", [{"role": "system", "content": system},
                                                             {"role": "user", "content": content}], PostVision)
                    parts.append(res.output.descricao.strip())
                    if res.output.texto_na_imagem.strip():
                        parts.append(f"Texto nas imagens: {res.output.texto_na_imagem.strip()}")
                except LLMFailure as exc:
                    log.warning("instagram %s: visão falhou (%s)", post["shortcode"], exc)
                except (BudgetExceeded, InsufficientCredits) as exc:
                    budget["stopped"] = str(exc)
                    log.warning("instagram: visão desligada pelo resto do run (%s)", exc)
            if transcriber is not None and post.get("video_url"):
                try:
                    said = transcriber(download(own, post["video_url"], MAX_VIDEO_BYTES))
                    if said:
                        parts.append(f"Transcrição: {said}")
                except Exception as exc:  # noqa: BLE001 - the transcript is a bonus
                    log.warning("instagram %s: transcrição falhou (%s)", post["shortcode"], exc)
        finally:
            if client is None:
                own.close()
        return "\n".join(parts)

    return describe
