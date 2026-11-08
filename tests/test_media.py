# tests/test_media.py
"""Images and reels of Instagram posts (P5): CDN-only downloads, ≤ 800 px JPEG, vision call, transcript."""
import base64
import io

import httpx
import pytest
from PIL import Image

from sotawhat.llm.gateway import LLMFailure, StructuredResult
from sotawhat.llm.schemas import PostVision
from sotawhat.pipeline.media import download, make_describer, shrink


def _png(width=1600, height=900):
    out = io.BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(out, format="PNG")
    return out.getvalue()


class VisionGateway:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def structured_call(self, task, messages, model_cls, models=None):
        self.calls.append((task, messages))
        if self.fail:
            raise LLMFailure("sem JSON")
        return StructuredResult(output=PostVision(descricao="Um gráfico de barras com AUROC.", texto_na_imagem="AUROC 0,91"),
                                model="xiaomi/mimo-v2.6-flash", provider=None, cost_usd=0.0003, latency_ms=1,
                                attempts=1, first_try_valid=True)


POST = {"shortcode": "C1", "owner": "medai.br", "type": "carousel", "caption": "Resultado novo",
        "media": [{"url": "https://scontent.cdninstagram.com/a.jpg"}, {"url": "https://evil.example/b.jpg"},
                  {"url": "https://scontent.cdninstagram.com/c.jpg"}, {"url": "https://scontent.cdninstagram.com/d.jpg"}],
        "video_url": "https://scontent.cdninstagram.com/v.mp4"}


def _client(requested):
    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(200, content=b"video" if request.url.path.endswith(".mp4") else _png())
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_shrink_and_cdn_only_downloads():
    url = shrink(_png())
    assert url.startswith("data:image/jpeg;base64,")
    with Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))) as img:
        assert max(img.size) == 800 and img.format == "JPEG"
    requested = []
    with pytest.raises(ValueError, match="CDN"):
        download(_client(requested), "https://evil.example/x.jpg", 1000)
    with pytest.raises(ValueError, match="MB"):
        download(_client(requested), "https://scontent.cdninstagram.com/a.jpg", 10)
    assert requested == ["https://scontent.cdninstagram.com/a.jpg"]


def test_describer_sends_up_to_three_cdn_images_and_the_transcript():
    gateway, requested, heard = VisionGateway(), [], []
    describe = make_describer(gateway, max_images=3, transcriber=lambda video: heard.append(video) or "Falamos de triagem.",
                              client=_client(requested))
    text = describe(POST)
    task, messages = gateway.calls[0]
    images = [p for p in messages[1]["content"] if p["type"] == "image_url"]
    assert task == "vision" and len(images) == 2                     # the third media is outside the CDN
    assert "evil.example" not in " ".join(requested) and heard == [b"video"]
    assert text == "Um gráfico de barras com AUROC.\nTexto nas imagens: AUROC 0,91\nTranscrição: Falamos de triagem."


def test_describer_survives_a_failing_vision_call():
    describe = make_describer(VisionGateway(fail=True), client=_client([]))
    assert describe(POST | {"video_url": ""}) == ""


def test_a_budget_stop_turns_the_vision_off_for_the_rest_of_the_run():
    from sotawhat.llm.gateway import BudgetExceeded

    class Broke(VisionGateway):
        def structured_call(self, task, messages, model_cls, models=None):
            self.calls.append(task)
            raise BudgetExceeded("daily LLM budget of US$ 1.00 reached")

    gateway = Broke()
    describe = make_describer(gateway, client=_client([]))
    assert describe(POST | {"video_url": ""}) == "" and describe(POST | {"video_url": ""}) == ""
    assert gateway.calls == ["vision"]
