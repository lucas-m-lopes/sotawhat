# sotawhat/rag/answer.py
"""The small language model that answers from the retrieved context (SDD §6.15).

The model sits behind an OpenAI-compatible endpoint (`SLM_BASE_URL`): Ollama here and on the VPS, or llama.cpp,
LM Studio, vLLM. It gets the context pack of retrieve.py and one instruction: answer only from it, citing [n].
A small model drifts, so what it writes is checked without another model:
- a citation of a source that is not in the context is flagged;
- an answer with no citation at all is flagged;
- every number of the answer has to be written in the context (the question's own numbers aside).
The flags go to the reader with the answer; the sources are always shown, so the answer can be checked.
When no model answers, the sources and the facts of the graph are the answer."""
import re
import time
from dataclasses import dataclass, field

import httpx

PROMPT_VERSION = "rag_answer_v1"
SYSTEM = """Você responde perguntas sobre o grafo de conhecimento pessoal do leitor: itens sobre IA na medicina e IA de fronteira que ele coletou, com as entidades e relações extraídas deles. O leitor é médico e empreendedor.

Regras:
- Use somente o CONTEXTO abaixo. Não use conhecimento próprio para fatos, números, nomes ou datas.
- Depois de cada afirmação tirada de uma fonte, cite o número dela entre colchetes, como [1] ou [2][5]. Os "Fatos do grafo" não têm número: use-os dizendo "segundo o grafo".
- Se o CONTEXTO não responde à pergunta, diga "Não encontrei isso no grafo." e, em uma frase, o que ele traz de mais próximo.
- Português do Brasil, com os termos técnicos em inglês. Direto ao ponto: no máximo 180 palavras; use lista quando forem vários itens.
- Nunca invente números, nomes, links ou fontes. Se as fontes divergem, diga."""
_CITE = re.compile(r"\[(\d{1,2})\]")
_NUMBER = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)*%?")
_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)


class SLMError(Exception):
    pass


@dataclass
class Reply:
    text: str
    model: str
    seconds: float
    tokens_in: int = 0
    tokens_out: int = 0


class SLM:
    """Chat completions on an OpenAI-compatible endpoint. `reasoning` goes as `reasoning_effort` ("none" turns
    the thinking of Qwen and Gemma off: on a small model it costs seconds and adds nothing to a grounded answer);
    a server that refuses the field is asked again without it."""

    def __init__(self, base_url, model, api_key="", reasoning="none", timeout=300, post=httpx.post, get=httpx.get):
        self.base_url, self.model, self.api_key = (base_url or "").rstrip("/"), model, api_key
        self.reasoning, self.timeout = reasoning, timeout
        self._post, self._get = post, get

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def ping(self) -> tuple:
        """-> (ok, detail): the endpoint answers and has the model."""
        if not self.configured:
            return False, "SLM_BASE_URL ou SLM_MODEL vazio"
        try:
            r = self._get(f"{self.base_url}/models", headers=self._headers(), timeout=5)
        except httpx.HTTPError as exc:
            return False, f"{self.base_url} não responde ({type(exc).__name__})"
        if r.status_code != 200:
            return False, f"{self.base_url} respondeu {r.status_code}"
        models = [m.get("id") for m in (r.json().get("data") or [])]
        if self.model not in models:
            return False, f"o modelo {self.model} não está no servidor (tem: {', '.join(models[:6]) or 'nenhum'})"
        return True, f"{self.model} em {self.base_url}"

    def chat(self, messages, max_tokens=600, temperature=0.2) -> Reply:
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        if self.reasoning:
            payload["reasoning_effort"] = self.reasoning
        started = time.perf_counter()
        try:
            r = self._post(f"{self.base_url}/chat/completions", json=payload, headers=self._headers(), timeout=self.timeout)
            if r.status_code == 400 and "reasoning_effort" in payload:
                plain = {key: value for key, value in payload.items() if key != "reasoning_effort"}
                r = self._post(f"{self.base_url}/chat/completions", json=plain, headers=self._headers(),
                               timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise SLMError(f"o SLM não respondeu em {self.base_url} ({type(exc).__name__}): rode `sotawhat rag up`") from None
        if r.status_code != 200:
            raise SLMError(f"o SLM respondeu {r.status_code}: {r.text[:200]}")
        body = r.json()
        text = _THINK.sub("", ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not text:
            raise SLMError("o SLM devolveu uma resposta vazia (o raciocínio pode ter gasto todos os tokens: "
                           "deixe SLM_REASONING=none)")
        usage = body.get("usage") or {}
        return Reply(text=text, model=body.get("model") or self.model, seconds=round(time.perf_counter() - started, 2),
                     tokens_in=usage.get("prompt_tokens") or 0, tokens_out=usage.get("completion_tokens") or 0)


def from_settings(settings) -> SLM:
    return SLM(settings.slm_base_url, settings.slm_model, api_key=settings.slm_api_key, reasoning=settings.slm_reasoning,
               timeout=settings.slm_timeout)


def messages_for(pack, budget=9000) -> list:
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"CONTEXTO\n{pack.context(budget)}\n\nPERGUNTA: {pack.question}"}]


def _numbers(text) -> set:
    """The numbers of a text as written, with the decimal comma and point taken as the same ("9,4" = "9.4")."""
    return {n.replace(",", ".").rstrip(".") for n in _NUMBER.findall(text or "")}


def check(text, pack, context) -> dict:
    """What can be verified in an answer without another model."""
    cited = sorted({int(n) for n in _CITE.findall(text)})
    known = {s.n for s in pack.sources}
    asked = _numbers(pack.question)
    in_context = _numbers(context)
    loose = sorted(n for n in _numbers(_CITE.sub("", text)) - in_context - asked
                   if len(n.rstrip("%")) > 1 or n.endswith("%"))
    warnings = []
    if [n for n in cited if n not in known]:
        warnings.append("cita fonte que não existe: " + ", ".join(f"[{n}]" for n in cited if n not in known))
    refused = "não encontrei" in text.lower()
    if not cited and not refused and pack.sources:
        warnings.append("resposta sem citação: confira nas fontes")
    if loose:
        warnings.append("números que não estão nas fontes: " + ", ".join(loose[:6]))
    return {"cited": [n for n in cited if n in known], "warnings": warnings, "refused": refused}


@dataclass
class Answer:
    question: str
    text: str | None                # None: no model answered, the sources stand alone
    pack: object
    model: str | None = None
    seconds: float = 0.0
    cited: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict:
        return {"question": self.question, "answer": self.text, "model": self.model, "seconds": self.seconds,
                "cited": self.cited, "warnings": self.warnings, "error": self.error, **self.pack.as_dict()}


def ask(retriever, slm, question, days=None, k=8, budget=9000, max_tokens=600) -> Answer:
    pack = retriever.retrieve(question, days=days, k=k)
    answer = Answer(question=pack.question, text=None, pack=pack)
    if not pack.sources and not pack.facts:
        answer.text = "Não encontrei isso no grafo."
        return answer
    if slm is None or not slm.configured:
        answer.error = "nenhum SLM configurado (SLM_BASE_URL e SLM_MODEL): seguem as fontes"
        return answer
    context = pack.context(budget)
    try:
        reply = slm.chat(messages_for(pack, budget), max_tokens=max_tokens)
    except SLMError as exc:
        answer.error = str(exc)
        return answer
    verdict = check(reply.text, pack, context)
    answer.text, answer.model, answer.seconds = reply.text, reply.model, reply.seconds
    answer.cited, answer.warnings = verdict["cited"], verdict["warnings"]
    pack.timings["responder"] = reply.seconds
    return answer
