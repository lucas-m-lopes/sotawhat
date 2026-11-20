# sotawhat/rag/jev.py
"""Jev (TypeSafe System One, through OpenRouter) as the fast engine of `sotawhat ask` (SDD §6.15, 2026-11-20).

Jev does not write: it takes a state and typed questions and gives back probabilities. So in this mode nothing
is generated. For each of the best candidates of the retrieval, one request asks two things:
- a yes/no (Noul): does this passage contain the answer to the question? Its probability reorders the
  sources, in the place of the cross-encoder that takes seconds on the CPU;
- a choice among the sentences of the passage (plus "none"): which one answers it? That sentence is quoted.
The answer shown is those sentences, each with its source number: extracted, never invented.

The requests go in parallel (about a second for ten), with the privacy the other OpenRouter calls have (ZDR
and data_collection=deny from the settings; Jev has a ZDR endpoint) and their cost in the `llm_calls` ledger
(task `rag_jev`, about US$ 0.0002 a question). Only the question and passages of approved items are sent:
no graph facts, no ideas. The instructions are in English, as the vendor asks; the passages are the pt-BR
cards, which Jev read correctly in the measurements of 2026-11-20."""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

DEFAULT_MODEL = "typesafe/jev-1.13"      # pinned: typesafe/jev-latest changes without notice
# "The answer or a part of it": a question such as "which models address sepsis and who made them" is answered by
# several sources, each with one piece. Asked for the whole answer, Jev gave those sources 0.32 and 0.38 and the
# question got "not found"; asked this way it gave them 0.73, with an off-topic question still at 0.01.
ANSWERS = {"type": "noul", "instructions": "The passage helps to answer the question: it contains the answer or a part of it.",
           "criteria": {"true": "The passage states the answer, or one of the things the question asks for (one example, "
                                "one item of a list, one of several facts).",
                        "false": "The passage is about something else, or has nothing of what the question asks for."}}
RELEVANT = 0.6        # from this probability on, a source counts as answering (0.5 let in sources that only share the theme)
BEST = "Which sentence of the passage answers the question best?"
NONE = "No sentence of the passage answers the question."
MAX_SENTENCES = 8
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\"“'(\[]?[A-ZÀ-Ý0-9])")


class JevError(Exception):
    pass


@dataclass
class Judgment:
    probability: float          # that the passage answers the question
    quote: str = ""             # the sentence of the passage that answers it, when one does


def sentences(text) -> list:
    return [s.strip() for s in _SENTENCE.split(" ".join((text or "").split())) if len(s.strip()) >= 25][:MAX_SENTENCES]


class Jev:
    def __init__(self, api_key, base_url="https://openrouter.ai/api/v1", model=DEFAULT_MODEL, zdr=True,
                 data_collection="deny", store=None, budget_month=None, workers=10, timeout=30, post=None):
        self.api_key, self.base_url, self.model = api_key, (base_url or "").rstrip("/"), model or DEFAULT_MODEL
        self.zdr, self.data_collection = zdr, data_collection
        self.store, self.budget_month = store, budget_month
        self.workers, self.timeout = workers, timeout
        if post is None:                 # one pooled client: ten requests a question, and the TLS handshake of each
            post = httpx.Client(limits=httpx.Limits(max_connections=workers, max_keepalive_connections=workers)).post
        self._post = post                # one was half of the latency
        self._quotes = {}

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url)

    def decide(self, state, questions) -> dict:
        """One System One request -> {"answers", "usage", "model"}."""
        provider = {"data_collection": self.data_collection}
        if self.zdr:
            provider["zdr"] = True
        try:
            r = self._post(f"{self.base_url}/systemone", headers={"Authorization": f"Bearer {self.api_key}"},
                           json={"model": self.model, "state": state, "questions": questions, "provider": provider},
                           timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise JevError(f"a Jev não respondeu ({type(exc).__name__})") from None
        try:
            body = r.json()
        except ValueError:
            body = {}
        if r.status_code != 200:
            error = body.get("error") if isinstance(body, dict) else None
            detail = (error.get("message") if isinstance(error, dict) else error) or r.text[:160]
            raise JevError(f"a Jev respondeu {r.status_code}: {str(detail)[:200]}")
        if not isinstance(body.get("answers"), dict):
            raise JevError("resposta da Jev sem `answers`")
        return body

    def _one(self, question, title, text) -> tuple:
        """-> (Judgment, usage) for one passage."""
        parts = sentences(text)
        questions = {"answers": ANSWERS}
        if len(parts) > 1:
            options = {f"s{n}": sentence for n, sentence in enumerate(parts, 1)}
            questions["best"] = {"type": "choice", "instructions": BEST, "criteria": {**options, "none": NONE}}
        body = self.decide({"question": question, "passage": f"{title}. {text}" if title else text}, questions)
        answers = body["answers"]
        probability = (answers.get("answers") or {}).get("noul")
        if not isinstance(probability, (int, float)):
            raise JevError("resposta da Jev sem a probabilidade pedida")
        if probability < RELEVANT or not parts:
            return Judgment(float(probability)), body.get("usage") or {}
        # The passage helps: quote its best sentence. A passage that holds one piece of a larger answer often gets
        # "none" from the choice (no sentence answers the whole question); then the most probable sentence is
        # quoted, and without probabilities the first one, which in these summaries says what the item is.
        best = answers.get("best") or {}
        choice, spread = best.get("choice"), best.get("probabilities") or {}
        valid = [f"s{n}" for n in range(1, len(parts) + 1)]
        if choice not in valid:
            ranked = sorted(valid, key=lambda key: -float(spread.get(key) or 0.0))
            choice = ranked[0] if float(spread.get(ranked[0]) or 0.0) > 0 else "s1"
        return Judgment(float(probability), parts[int(choice[1:]) - 1]), body.get("usage") or {}

    def _check_budget(self) -> None:
        if self.store is None or self.budget_month is None:
            return
        month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if self.store.llm_cost_since(month.isoformat(timespec="seconds")) >= self.budget_month:
            raise JevError(f"orçamento mensal de LLM (US$ {self.budget_month:.2f}) atingido")

    def judge(self, question, passages) -> list:
        """passages: [(title, text)] -> [Judgment], in the same order, the requests in parallel. A passage whose
        request failed gets probability 0; when every request fails the error is raised."""
        passages = list(passages)
        if not passages:
            return []
        if not self.configured:
            raise JevError("sem OPENROUTER_API_KEY: a Jev roda pelo OpenRouter")
        self._check_budget()
        started = time.perf_counter()
        results, errors = [None] * len(passages), []

        def work(i):
            try:
                results[i] = self._one(question, *passages[i])
            except JevError as exc:
                errors.append(str(exc))

        with ThreadPoolExecutor(max_workers=max(1, min(self.workers, len(passages)))) as pool:
            list(pool.map(work, range(len(passages))))
        done = [r for r in results if r is not None]
        latency = int((time.perf_counter() - started) * 1000)
        if self.store is not None:
            self.store.record_llm_call(
                task="rag_jev", requested_model=self.model, model=self.model, provider="TypeSafe",
                input_tokens=sum(int(u.get("input_tokens") or 0) for _, u in done),
                output_tokens=sum(int(u.get("output_tokens") or 0) for _, u in done),
                cost_usd=sum(float(u.get("cost") or 0.0) for _, u in done), latency_ms=latency,
                status="ok" if done else "error", error="; ".join(sorted(set(errors)))[:300] or None)
        if not done:
            raise JevError(errors[0] if errors else "a Jev não respondeu")
        return [r[0] if r is not None else Judgment(0.0) for r in results]

    # --- the reranker protocol of retrieve.py: score(), then evidence() for the sentence of each text -----------
    def score(self, question, texts) -> list:
        texts = list(texts)
        passages = [tuple(t.split("\n", 1)) if "\n" in t else ("", t) for t in texts]
        judgments = self.judge(question, passages)
        self._quotes = {text: j.quote for text, j in zip(texts, judgments)}
        return [j.probability for j in judgments]

    def evidence(self, text) -> str:
        return self._quotes.get(text, "")


def from_settings(settings, store=None):
    """None without an OpenRouter key."""
    if not settings.openrouter_api_key:
        return None
    return Jev(settings.openrouter_api_key, base_url=settings.openrouter_base_url, model=settings.rag_jev_model,
               zdr=settings.openrouter_zdr, data_collection=settings.openrouter_data_collection, store=store,
               budget_month=settings.sotawhat_llm_budget_usd_month)
