# Insight Engine · P1 Triagem + digest — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA — use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para executar este plano tarefa a tarefa. Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** transformar a coleta do P0 num digest útil:
- estágio A, sem LLM: filtros de silêncio, deduplicação "mesma história" por título, embeddings locais e novidade (D);
- estágio B: rubrica por LLM com JSON estrito, dentro do orçamento diário, em paralelo;
- digest ranqueado (≤ 15 principais + radar) em Markdown/HTML e no Telegram, com botões 👍 👎 🧪;
- votos persistidos (`feedback pull|listen`) e classificador por perfil a partir de 100 votos;
- golden set rotulado por você e *bake-off* de modelos (`eval models`) que define `config/llm.yaml`.

**Arquitetura:**
- O `run daily` do P0 ganha uma etapa de triagem logo depois da coleta. `pipeline/triage.py` lê do SQLite os itens ainda sem decisão: os novos e os pendentes de até 3 dias.
- O estágio A aplica, nesta ordem: `configfiles.Mutes`, `pipeline/dedup.py`, `store/vectors.py` e, quando já houver, o `store/classifier.py`. Os sobreviventes vão em paralelo para `LLMGateway.structured_call`.
- `decide()` aplica a rubrica de `config/rubric.yaml` e devolve `main`, `radar` ou `reject`. Todo descarte registra o motivo na tabela `triage`.
- `pipeline/deliver.py` monta o digest, grava os arquivos e envia as mensagens; `pipeline/feedback.py` lê os votos.
- Os YAMLs de `config/` são versionados e editáveis, e o código tem um padrão para cada chave.

**Stack:** o do P0 mais `pyyaml` 6, `numpy` 2, `scikit-learn` 1.9 e `fastembed` 0.9 (`onnxruntime`, CPU). O modelo de embeddings é `google/embeddinggemma-300m` (768-d, multilíngue, ~1,2 GB baixados uma vez).

**Spec:** `docs/sdd/2026-11-07-insight-engine-sdd.md` v1.2:
- §6.3 armazenamento e embeddings; §6.4 SQLite; §6.6 camada LLM; §6.7 triagem; §6.11 entrega; §7.7 Telegram; §11 (P1); §12 avaliação.
- Evidência: `docs/research/2026-11-07-insight-engine/embeddings_dedup.md` e `llm_openrouter.md`.

**Validação prévia (2026-11-07/08):**
- O código foi desenvolvido numa cópia isolada: 162 testes, sendo 107 do P0 e 55 novos.
- O plano foi **reaplicado tarefa a tarefa** sobre uma exportação limpa do P0. Em cada tarefa, os testes novos falharam antes da implementação, com a mensagem indicada, e a suíte passou depois, com a contagem indicada. A árvore final ficou idêntica à cópia validada.
- Rodou de verdade, sem chave do OpenRouter:
  - `run daily --no-llm --no-notify --limit 2`: saiu com código 0 em 83 s; migrou o `insight.db` real do P0 para o schema 2; gravou 45 embeddings 768-d; escreveu o digest em arquivo;
  - `doctor`: YAMLs válidos; os 4 candidatos do bake-off com endpoints ZDR e raciocínio "low" aceito; modelo de embeddings em cache;
  - `eval golden draft --vault`: 60 itens de 11 fontes.
- Benchmark de 6 modelos de embeddings e deduplicação nos 2.893 títulos do vault: `embeddings_dedup.md`.
- **Ainda não validado, porque depende do `.env`:** chamadas reais de triagem, envio ao Telegram e o bake-off. Isso fica na Tarefa 14.

**Convenções:**
- As do P0: PowerShell a partir da raiz, `.venv` com Python 3.12.4, testes sem rede, `core.autocrlf=true`.
- Edições pontuais em arquivos existentes. Quando o plano manda substituir o arquivo inteiro, o git normaliza o final de linha no commit.
- Um commit por tarefa, na branch `feature/insight-engine-p1`, criada a partir de `feature/insight-engine-p0`.

**Fora do escopo da P1:**
- P2: novas fontes; juiz LLM para notícias parecidas de veículos diferentes; sinais sociais (estrelas, upvotes) no classificador.
- P3: extração de entidades, grafo e migração do vault.
- P4: ideação.
- P5: processar a captura manual. Na P1, as mensagens que você mandar ao bot ficam guardadas na tabela `inbox`.
- *Active learning* e um resumo do dia inteiro escrito por LLM.

---

## Pré-requisitos do usuário (para a Tarefa 14)

1. **`.env` do P0** preenchido: `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`. O opcional `TELEGRAM_ALLOWED_USER_ID`, quando vazio, vale o próprio chat do bot.
2. **~1,3 GB livres em disco** para o modelo de embeddings, baixado no primeiro run para `data/models/fastembed`.
3. **Rotular o golden set:** ~60 itens, uns 30–40 minutos editando um Markdown. Para cada item, escreva `incluir`, `radar` ou `excluir`.

---

## Estrutura de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `pyproject.toml` | Substituir | deps `pyyaml`, `numpy`, `scikit-learn`, `fastembed`; prompts como *package data* |
| `sotawhat/config.py` | Modificar | `SOTAWHAT_CONFIG_DIR`, `TELEGRAM_ALLOWED_USER_ID`, `EMBEDDINGS_*`, `models_dir` |
| `sotawhat/configfiles.py` + `config/{rubric,mute,llm}.yaml` | Criar | rubrica, filtros de silêncio e modelos por etapa, validados |
| `sotawhat/store/db.py` | Substituir | schema 2 com migração no lugar: `triage`, `embeddings`, `clusters`, `feedback`, `deliveries`, `classifier_models`, `inbox` |
| `sotawhat/items.py` | Modificar | `from_row()` |
| `sotawhat/taxonomy.py` | Criar | vocabulários A–G do SDD §6.5 |
| `sotawhat/llm/schemas.py`, `sotawhat/llm/prompts/{__init__.py,triage_v1.md}` | Criar | `TriageOutput` (só enums no schema) e prompt v1 |
| `sotawhat/llm/tasks.py`, `sotawhat/llm/gateway.py` | Modificar/Substituir | `config/llm.yaml` na resolução; `structured_call()` com custo, tentativas e validade |
| `sotawhat/store/vectors.py`, `sotawhat/pipeline/dedup.py` | Criar | embeddings locais e novidade; "mesma história" por título |
| `sotawhat/store/classifier.py` | Criar | regressão logística por perfil, retreino quando os votos mudam |
| `sotawhat/pipeline/triage.py` | Criar | estágios A e B, orçamento, concorrência, decisões |
| `sotawhat/notify/telegram.py` | Substituir | botões, `getUpdates`, resposta e edição de botões, *flood control* |
| `sotawhat/pipeline/deliver.py`, `sotawhat/pipeline/feedback.py` | Criar | digest (MD/HTML/Telegram) e votos |
| `sotawhat/pipeline/daily.py` | Substituir | etapa de triagem, log diário, digest novo |
| `sotawhat/evals/{__init__,golden,bakeoff,commands}.py` | Criar | golden set e bake-off |
| `sotawhat/doctor.py` | Substituir | verificações da P1 |
| `sotawhat/cli.py` | Modificar | `run daily --no-llm`, `feedback pull/listen`, `eval golden/models` |
| `scripts/schedule_daily.ps1` | Substituir | opção `-Listener` (votos em tempo real ao fazer logon) |
| `README.md`, `.env.example` | Modificar | seção P1 e variáveis novas |
| `tests/test_{configfiles,store_v2,schemas,dedup_vectors,classifier,triage,deliver,feedback,evals,doctor_p1}.py` | Criar | testes novos |
| `tests/test_{store,gateway,daily,cli}.py` | Modificar | casos novos |

---

## Tarefa 0: Branch, documentos e linha de base

- [ ] **Passo 1: Criar a branch a partir do P0**

```powershell
git checkout feature/insight-engine-p0
git checkout -b feature/insight-engine-p1
```

- [ ] **Passo 2: Commitar os documentos da P1** (SDD v1.2, nota de pesquisa e este plano)

```bash
git add docs/sdd/2026-11-07-insight-engine-sdd.md docs/research/2026-11-07-insight-engine/embeddings_dedup.md docs/superpowers/plans/2026-11-08-insight-engine-p1-triage-digest.md
git commit -m "docs: SDD v1.2 (embeddings and dedup measurements) and P1 plan"
```

Se `tests/evals/triage/golden_v1.md` e `.jsonl` já existirem (rascunho entregue antes da P1), não os commite agora: eles entram na Tarefa 14, com os seus rótulos.

- [ ] **Passo 3: Confirmar a suíte atual**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `107 passed`.

---

## Tarefa 1: Dependências, `Settings` e configuração editável

**Files:**
- Modify: `pyproject.toml` (substituir o conteúdo inteiro), `sotawhat/config.py`
- Create: `sotawhat/configfiles.py`, `config/rubric.yaml`, `config/mute.yaml`, `config/llm.yaml`, `tests/test_configfiles.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_configfiles.py`:

````python
# tests/test_configfiles.py
from pathlib import Path

import pytest

from sotawhat.config import Settings
from sotawhat.configfiles import ConfigError, Mutes, load_config, load_llm_config, load_mutes, load_rubric
from sotawhat.items import Item

REPO_CONFIG = Path(__file__).resolve().parents[1] / "config"


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_missing_files_mean_defaults(tmp_path):
    config = load_config(tmp_path)
    assert config.rubric.min_total == 3.2 and config.rubric.weights == {"A": 0.35, "B": 0.35, "C": 0.2, "D": 0.1}
    assert config.mutes == Mutes() and config.llm == {"tasks": {}, "bakeoff": {}}


def test_repository_config_files_are_valid():
    config = load_config(REPO_CONFIG)
    assert config.rubric.main_limit == 15 and config.rubric.novelty_thresholds == (0.70, 0.76, 0.82, 0.88, 0.94)
    assert config.llm["tasks"]["triage"]["reasoning"] == "low"
    assert len(config.llm["bakeoff"]["triage"]) == 4


def test_rubric_overrides_and_validation(tmp_path):
    rubric = load_rubric(_write(tmp_path, "r.yaml", "min_total: 3.0\nweights: {A: 0.4, B: 0.4, C: 0.1, D: 0.1}\n"
                                                    "weak_sources: [rss:marktechpost]\n"))
    assert rubric.min_total == 3.0 and rubric.weights["A"] == 0.4 and rubric.weak_sources == ("rss:marktechpost",)
    with pytest.raises(ConfigError, match="somando 1"):
        load_rubric(_write(tmp_path, "r.yaml", "weights: {A: 0.5, B: 0.5, C: 0.5, D: 0.5}\n"))
    with pytest.raises(ConfigError, match="desconhecidas"):
        load_rubric(_write(tmp_path, "r.yaml", "min_totl: 3\n"))
    with pytest.raises(ConfigError, match="crescentes"):
        load_rubric(_write(tmp_path, "r.yaml", "novelty_thresholds: [0.9, 0.8, 0.7, 0.6, 0.5]\n"))
    with pytest.raises(ConfigError, match="YAML inválido"):
        load_rubric(_write(tmp_path, "r.yaml", "weights: {A: [\n"))


def test_mutes_match_with_reasons(tmp_path):
    mutes = load_mutes(_write(tmp_path, "m.yaml", "terms: [webinar]\ntitle_terms: [Sponsored]\n"
                                                  "domains: [example.com]\nauthors: [Spam Bot]\nsources: ['rss:*']\n"))

    def it(**kw):
        base = dict(id="x", kind="article", source="pubmed", source_id="", title="AI triage", url="https://ok.org/a",
                    authors=["Ana"], text="")
        base.update(kw)
        return Item(**base)

    assert mutes.match(it()) is None
    assert "webinar" in mutes.match(it(text="Join our WEBINAR on AI"))
    assert "título" in mutes.match(it(title="Sponsored: AI scribe"))
    assert "example.com" in mutes.match(it(url="https://news.example.com/x"))
    assert "Spam Bot" in mutes.match(it(authors=["spam bot"]))
    assert "rss:*" in mutes.match(it(source="rss:labs"))
    assert mutes.match(it(text="webinars are not a whole-word match")) is None
    with pytest.raises(ConfigError, match="listas"):
        load_mutes(_write(tmp_path, "m.yaml", "terms: webinar\n"))


def test_llm_config_validation(tmp_path):
    ok = load_llm_config(_write(tmp_path, "l.yaml", "tasks:\n  triage: {models: [a/b], reasoning: high}\n"
                                                    "bakeoff:\n  triage: [a/b, c/d]\n"))
    assert ok["tasks"]["triage"]["models"] == ["a/b"] and ok["bakeoff"]["triage"] == ["a/b", "c/d"]
    for bad in ("tasks:\n  triage: {models: [nope]}\n", "tasks:\n  triage: {reasoning: turbo}\n",
                "tasks:\n  triage: {max_tokens: -1}\n", "tasks:\n  triage: {temperature: 1}\n", "other: 1\n"):
        with pytest.raises(ConfigError):
            load_llm_config(_write(tmp_path, "l.yaml", bad))


def test_settings_paths_and_allowed_user(tmp_path):
    s = Settings(_env_file=None, sotawhat_data_dir=tmp_path, telegram_chat_id="42")
    assert s.models_dir == tmp_path / "models" and s.allowed_user_id == "42"
    assert s.embeddings_backend == "fastembed" and s.embeddings_model == "google/embeddinggemma-300m"
    assert Settings(_env_file=None, telegram_chat_id="42", telegram_allowed_user_id="7").allowed_user_id == "7"
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_configfiles.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.configfiles'`.

- [ ] **Passo 3: Atualizar `pyproject.toml`**

````toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "sotawhat"
version = "3.0.0.dev0"
description = "Insight engine for AI/ML x medicine: multi-source collection, triage, knowledge graph and idea generation"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "feedparser>=6.0",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "truststore>=0.10",
    "pyyaml>=6.0",
    "numpy>=2.0",
    "scikit-learn>=1.5",
    "fastembed>=0.9",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
sotawhat = "sotawhat.cli:main"

[tool.setuptools.packages.find]
include = ["sotawhat*"]

[tool.setuptools.package-data]
"sotawhat.llm.prompts" = ["*.md"]
````

- [ ] **Passo 4: Instalar**

Run: `uv pip install --python .\.venv\Scripts\python.exe -e ".[dev]"`
Expected: instala `pyyaml` 6.0.3, `numpy` 2.5.x, `scikit-learn` 1.9.1, `fastembed` 0.9.1, `onnxruntime` 1.31.x e dependências. Nenhum modelo é baixado nesta etapa.

- [ ] **Passo 5: Novos campos em `sotawhat/config.py`**

5a. Logo depois de `sotawhat_data_dir: Path = Path("./data")`:

```python
    sotawhat_config_dir: Path = Path("./config")
```

5b. Logo depois de `telegram_chat_id: str = ""`:

```python
    telegram_allowed_user_id: str = ""

    embeddings_backend: str = "fastembed"
    embeddings_model: str = "google/embeddinggemma-300m"
```

5c. Logo antes da propriedade `quantizations`:

```python
    @property
    def models_dir(self) -> Path:
        return self.sotawhat_data_dir / "models"

    @property
    def allowed_user_id(self) -> str:
        """Only this Telegram user may vote or send links (defaults to the private chat id)."""
        return self.telegram_allowed_user_id or self.telegram_chat_id

```

- [ ] **Passo 6: Criar `sotawhat/configfiles.py`**

````python
# sotawhat/configfiles.py
"""Versioned, editable YAML in `config/` (SDD §6.2, §6.7): triage rubric, mute filters and per-task
LLM overrides. Every file and every key is optional; built-in defaults fill the gaps."""
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from sotawhat.textmatch import contains_term

REASONING_LEVELS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}


class ConfigError(Exception):
    pass


def read_yaml(path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path.name}: YAML inválido ({exc})") from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path.name}: o topo do arquivo precisa ser um mapeamento")
    return data


@dataclass(frozen=True)
class Rubric:
    """SDD §6.7. total = wA·A + wB·B + wC·C + wD·D − penalties; main if total ≥ min_total and B ≥ min_b."""
    version: int = 1
    weights: dict = field(default_factory=lambda: {"A": 0.35, "B": 0.35, "C": 0.20, "D": 0.10})
    min_total: float = 3.2
    min_b: int = 2
    radar_min_a: int = 4
    radar_max_b: int = 1
    main_limit: int = 15
    radar_limit: int = 10
    vendor_only_penalty: float = 0.5
    weak_source_penalty: float = 0.5
    weak_sources: tuple = ()
    # max cosine similarity to the last `novelty_window_days` -> D: below the 1st threshold D=5 ... above the 5th D=0
    novelty_thresholds: tuple = (0.70, 0.76, 0.82, 0.88, 0.94)
    novelty_window_days: int = 30
    max_text_chars: int = 8000
    max_items_per_run: int = 300
    backlog_days: int = 3
    concurrency: int = 6
    classifier_min_ratings: int = 100
    classifier_top_n: int = 40


def load_rubric(path) -> Rubric:
    data = read_yaml(path)
    unknown = sorted(set(data) - {f.name for f in fields(Rubric)})
    if unknown:
        raise ConfigError(f"rubric.yaml: chaves desconhecidas {unknown}")
    values = {k: tuple(v) if isinstance(v, list) else v for k, v in data.items()}
    weights = dict(Rubric().weights)
    weights.update(values.pop("weights", None) or {})
    if set(weights) != {"A", "B", "C", "D"} or abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ConfigError(f"rubric.yaml: weights precisa de A, B, C e D somando 1 (recebido {weights})")
    thresholds = values.get("novelty_thresholds", Rubric().novelty_thresholds)
    if len(thresholds) != 5 or list(thresholds) != sorted(thresholds):
        raise ConfigError("rubric.yaml: novelty_thresholds precisa de 5 limiares crescentes")
    return replace(Rubric(), weights=weights, **values)


@dataclass(frozen=True)
class Mutes:
    """config/mute.yaml: drop an item before the LLM; the reason is recorded in `triage`."""
    terms: tuple = ()          # whole word/phrase in title or text, case-insensitive
    title_terms: tuple = ()    # only in the title
    domains: tuple = ()        # URL host or any subdomain of it
    authors: tuple = ()        # exact name, case-insensitive
    sources: tuple = ()        # item source ("rss:marktechpost"); a trailing * matches a prefix ("rss:*")

    def match(self, item) -> str | None:
        title = item.title or ""
        for term in self.title_terms:
            if contains_term(title, term):
                return f"mute: '{term}' no título"
        body = f"{title} {item.text or ''}"
        for term in self.terms:
            if contains_term(body, term):
                return f"mute: termo '{term}'"
        host = urlsplit(item.url or "").netloc.lower()
        for domain in self.domains:
            domain = domain.lower().lstrip(".")
            if host == domain or host.endswith("." + domain):
                return f"mute: domínio {domain}"
        authors = {a.lower() for a in item.authors or []}
        for author in self.authors:
            if author.lower() in authors:
                return f"mute: autor {author}"
        for source in self.sources:
            if item.source == source or (source.endswith("*") and item.source.startswith(source[:-1])):
                return f"mute: fonte {source}"
        return None


def load_mutes(path) -> Mutes:
    data = read_yaml(path)
    unknown = sorted(set(data) - {f.name for f in fields(Mutes)})
    if unknown:
        raise ConfigError(f"mute.yaml: chaves desconhecidas {unknown}")
    not_lists = sorted(k for k, v in data.items() if v is not None and not isinstance(v, list))
    if not_lists:
        raise ConfigError(f"mute.yaml: {not_lists} precisam ser listas")
    return Mutes(**{k: tuple(str(x) for x in (v or [])) for k, v in data.items()})


def _check_models(where, models):
    if not isinstance(models, list) or not models or not all(isinstance(m, str) and "/" in m for m in models):
        raise ConfigError(f"llm.yaml: {where} precisa ser uma lista de ids do OpenRouter (autor/modelo)")


def load_llm_config(path) -> dict:
    """{'tasks': {task: {models?, reasoning?, max_tokens?}}, 'bakeoff': {task: [models]}}."""
    data = read_yaml(path)
    unknown = sorted(set(data) - {"tasks", "bakeoff"})
    if unknown:
        raise ConfigError(f"llm.yaml: chaves desconhecidas {unknown}")
    tasks = data.get("tasks") or {}
    for task, spec in tasks.items():
        if not isinstance(spec, dict) or set(spec) - {"models", "reasoning", "max_tokens"}:
            raise ConfigError(f"llm.yaml: tasks.{task} aceita só models, reasoning e max_tokens")
        if "models" in spec:
            _check_models(f"tasks.{task}.models", spec["models"])
        if spec.get("reasoning") is not None and spec["reasoning"] not in REASONING_LEVELS:
            raise ConfigError(f"llm.yaml: tasks.{task}.reasoning inválido: {spec['reasoning']}")
        if "max_tokens" in spec and (not isinstance(spec["max_tokens"], int) or spec["max_tokens"] <= 0):
            raise ConfigError(f"llm.yaml: tasks.{task}.max_tokens precisa ser inteiro positivo")
    bakeoff = data.get("bakeoff") or {}
    for task, models in bakeoff.items():
        _check_models(f"bakeoff.{task}", models)
    return {"tasks": tasks, "bakeoff": bakeoff}


@dataclass(frozen=True)
class AppConfig:
    rubric: Rubric
    mutes: Mutes
    llm: dict


def load_config(config_dir) -> AppConfig:
    config_dir = Path(config_dir)
    return AppConfig(rubric=load_rubric(config_dir / "rubric.yaml"),
                     mutes=load_mutes(config_dir / "mute.yaml"),
                     llm=load_llm_config(config_dir / "llm.yaml"))
````

- [ ] **Passo 7: Criar os três YAMLs** (UTF-8; você pode editá-los depois)

`config/rubric.yaml`:

````yaml
# config/rubric.yaml — rubrica da triagem (SDD §6.7). Toda chave é opcional; faltando, vale o padrão do código.
# total = 0,35·A + 0,35·B + 0,20·C + 0,10·D − penalidades. Vai para "principais" se total ≥ min_total e B ≥ min_b.
# A = fronteira de IA/ML, B = aplicabilidade médico-hospitalar, C = acionabilidade (notas do LLM, 0–5);
# D = novidade frente ao que chegou nos últimos novelty_window_days (calculada por embeddings, sem LLM).
version: 1
weights: {A: 0.35, B: 0.35, C: 0.20, D: 0.10}
min_total: 3.2
min_b: 2

# Radar de fronteira: IA forte sem ponte médica clara (A ≥ radar_min_a e B ≤ radar_max_b) → 1 linha no digest.
radar_min_a: 4
radar_max_b: 1

# Limites do digest diário.
main_limit: 15
radar_limit: 10

# Penalidades: só o fornecedor como fonte (sem terceiro) e fontes fracas/agregadoras.
vendor_only_penalty: 0.5
weak_source_penalty: 0.5
weak_sources: []            # ex.: ["rss:marktechpost"]

# Similaridade máxima (cosseno, EmbeddingGemma-300m) com os itens recentes → D.
# Abaixo de 0,70: D = 5; acima de 0,94: D = 0. Itens distintos ficam, em média, em 0,66 (medido em 2026-11-07).
novelty_thresholds: [0.70, 0.76, 0.82, 0.88, 0.94]
novelty_window_days: 30

# Operação da triagem por LLM.
max_text_chars: 8000        # ~2.000 tokens do texto de cada item
max_items_per_run: 300
backlog_days: 3             # itens não triados (orçamento, falha) ficam para os próximos runs por até N dias
concurrency: 6

# Classificador por perfil (regressão logística sobre embeddings, treinada com os seus votos).
classifier_min_ratings: 100 # abaixo disso o LLM vê todos os itens (arranque a frio)
classifier_top_n: 40        # depois, o LLM vê só os N melhores por perfil e por run
````

`config/mute.yaml`:

````yaml
# config/mute.yaml — filtros de silêncio (SDD §6.7, estágio A). Item que casar com qualquer regra é descartado
# antes do LLM, e o motivo fica registrado na tabela `triage`. Todas as listas começam vazias.
terms: []          # palavra ou frase inteira no título ou no texto, sem diferenciar maiúsculas. Ex.: ["webinar", "sponsored"]
title_terms: []    # só no título
domains: []        # host da URL ou qualquer subdomínio dele. Ex.: ["example.com"]
authors: []        # nome exato do autor
sources: []        # fonte do item; "*" no fim casa prefixo. Ex.: ["rss:marktechpost"]
````

`config/llm.yaml`:

````yaml
# config/llm.yaml — modelos por etapa (SDD §6.6). Sobrescreve sotawhat/llm/tasks.py; a variável
# SOTAWHAT_MODEL_<ETAPA> do .env ainda vence para o modelo primário. `sotawhat eval models --apply`
# reescreve tasks.<etapa>.models com o vencedor do bake-off na frente.
tasks:
  triage:
    models: [deepseek/deepseek-v4.1-flash-1017, xiaomi/mimo-v2.6-flash, z-ai/glm-5.3-flash]
    reasoning: low
    max_tokens: 1500

# Candidatos do bake-off (`sotawhat eval models --task triage`). Só níveis de raciocínio aceitos por todos:
# GLM-5.3-Flash e MiniMax-M3.1-Flash não aceitam desligar o raciocínio; DeepSeek V4.1 Flash não aceita "medium".
bakeoff:
  triage: [deepseek/deepseek-v4.1-flash-1017, xiaomi/mimo-v2.6-flash, z-ai/glm-5.3-flash, minimax/minimax-m3.1-flash]
````

- [ ] **Passo 8: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `113 passed`.

- [ ] **Passo 9: Commit**

```bash
git add pyproject.toml sotawhat/config.py sotawhat/configfiles.py config tests/test_configfiles.py
git commit -m "feat: editable YAML config (rubric, mutes, LLM overrides) and P1 settings"
```

---

## Tarefa 2: SQLite schema 2

Por quê: a triagem, os embeddings, as histórias, os votos e as entregas precisam de tabelas próprias (SDD §6.4). Bancos do P0 migram no lugar quando abertos: as tabelas novas são criadas, `items` ganha `cluster_id` e `schema_version` passa a 2. A conexão passa a ser compartilhada pelas threads da triagem; o SQLite roda em modo serializado (`threadsafety = 3`) e as gravações dessas threads passam por um lock.

**Files:**
- Modify: `sotawhat/store/db.py` (substituir o conteúdo inteiro), `sotawhat/items.py`, `tests/test_store.py`
- Create: `tests/test_store_v2.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_store_v2.py`:

````python
# tests/test_store_v2.py
import sqlite3
import threading

import numpy as np

from sotawhat.items import Item, from_row
from sotawhat.store.db import Store


def _item(n, title=None, profile="medico", source="pubmed", text="machine learning for sepsis"):
    return Item(id=f"pmid:{n}", kind="paper", source=source, source_id=str(n), title=title or f"Paper {n}",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", authors=["Ana"], published_at="2026-11-07",
                text=text, pmid=str(n), profile=profile)


def test_v1_database_is_migrated_in_place(tmp_path):
    path = tmp_path / "insight.db"
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO meta VALUES('schema_version', '1');
        CREATE TABLE items(id TEXT PRIMARY KEY, kind TEXT NOT NULL, source TEXT NOT NULL, source_id TEXT,
            canonical_url TEXT, doi TEXT, arxiv_id TEXT, pmid TEXT, title TEXT NOT NULL,
            authors_json TEXT NOT NULL DEFAULT '[]', published_at TEXT, fetched_at TEXT NOT NULL, text TEXT,
            content_hash TEXT, concepts_json TEXT NOT NULL DEFAULT '[]', profile TEXT,
            status TEXT NOT NULL DEFAULT 'new', first_run_id INTEGER);
        INSERT INTO items(id, kind, source, title, fetched_at) VALUES('pmid:1', 'paper', 'pubmed', 'Old', '2026-11-07');
    """)
    con.commit()
    con.close()
    with Store(path) as st:
        names = {r[0] for r in st.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"triage", "embeddings", "clusters", "feedback", "deliveries", "classifier_models", "inbox"} <= names
        assert st.meta_get("schema_version") == "2"
        row = st.conn.execute("SELECT title, cluster_id FROM items WHERE id = 'pmid:1'").fetchone()
        assert tuple(row) == ("Old", None)


def test_triage_candidates_and_error_retries(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([_item(1), _item(2), _item(3)], run)
        st.record_triage("pmid:1", run, "main", total=4.1, scores={"A": 4}, tags={"domains": ["A03"]})
        st.record_triage("pmid:2", run, "error", reason="timeout")
        since = "2000-01-01T00:00:00+00:00"
        assert {r["id"] for r in st.triage_candidates(since)} == {"pmid:2", "pmid:3"}
        st.record_triage("pmid:2", run, "error", reason="timeout")
        st.record_triage("pmid:2", run, "error", reason="timeout")
        assert {r["id"] for r in st.triage_candidates(since)} == {"pmid:3"}     # 3 attempts: gave up
        rows = st.triage_rows(run)
        assert [r["item_id"] for r in rows] == ["pmid:1"] and rows[0]["title"] == "Paper 1"
        assert st.triage_counts(run) == {"main": 1, "error": 1}


def test_embeddings_round_trip_with_filters(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([_item(1), _item(2)], run)
        st.save_embeddings("m", [("pmid:1", np.array([1, 0], dtype=np.float32)),
                                 ("pmid:2", np.array([0, 1], dtype=np.float32))])
        ids, matrix = st.load_embeddings("m", exclude={"pmid:2"})
        assert ids == ["pmid:1"] and matrix.tolist() == [[1.0, 0.0]]
        assert st.embedded_ids("m", ["pmid:1", "pmid:9"]) == {"pmid:1"}
        assert st.load_embeddings("other")[0] == []
        assert st.load_embeddings("m", since_iso="2999-01-01")[0] == []


def test_latest_vote_wins_and_profile_filter(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([_item(1), _item(2, profile="geral")], run)
        st.add_feedback("item", "pmid:1", "up", "telegram")
        st.add_feedback("item", "pmid:1", "down", "telegram")
        st.add_feedback("item", "pmid:2", "test", "telegram")
        assert st.item_votes() == {"pmid:1": "down", "pmid:2": "test"}
        assert st.item_votes(profile="geral") == {"pmid:2": "test"}
        assert st.item_votes(ids=["pmid:1"]) == {"pmid:1": "down"}


def test_deliveries_by_key_and_message(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        a = st.record_delivery(1, "2026-11-08", "pmid:1", "k1", "radar", 1)
        b = st.record_delivery(1, "2026-11-08", "pmid:2", "k2", "radar", 2)
        st.mark_delivered([a, b], 42, 1001)
        assert st.delivery_by_key("k2")["item_id"] == "pmid:2"
        assert [r["key"] for r in st.deliveries_for_message("42", 1001)] == ["k1", "k2"]


def test_clusters_sources_and_redaction(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        st.upsert_items([_item(1), _item(2, source="crossref")], run)
        st.join_cluster("pmid:2", "pmid:1")
        assert st.cluster_sources("pmid:1") == ["crossref", "pubmed"]
        st.save_embeddings("m", [("pmid:1", np.array([1, 0], dtype=np.float32))])
        st.redact_item("pmid:1")
        item = from_row(st.get_items(["pmid:1"])[0])
        assert item.text == "" and "removido" in item.title and st.load_embeddings("m")[0] == []


def test_ledger_writes_from_threads(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        def work():
            for _ in range(25):
                st.record_llm_call(task="triage", requested_model="m", status="ok", cost_usd=0.001)
                st.llm_cost_since("2000-01-01")
        threads = [threading.Thread(target=work) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert st.conn.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0] == 100
        assert abs(st.avg_llm_cost("triage") - 0.001) < 1e-9
````

Em `tests/test_store.py`, `test_schema_created`: trocar `assert version == "1"` por `assert version == "2"`.

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_store_v2.py -q`
Expected: FAIL com `ImportError: cannot import name 'from_row' from 'sotawhat.items'`.

- [ ] **Passo 3: Substituir `sotawhat/store/db.py`**

````python
# sotawhat/store/db.py
"""SQLite operational store (SDD §6.4): items, runs, source health, LLM cost ledger and, since
schema 2 (P1), triage, embeddings, clusters, feedback, deliveries, classifiers and the inbox."""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS items(
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT,
    canonical_url TEXT,
    doi TEXT,
    arxiv_id TEXT,
    pmid TEXT,
    title TEXT NOT NULL,
    authors_json TEXT NOT NULL DEFAULT '[]',
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    text TEXT,
    content_hash TEXT,
    concepts_json TEXT NOT NULL DEFAULT '[]',
    profile TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    first_run_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_items_fetched ON items(fetched_at);
CREATE TABLE IF NOT EXISTS runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    ok INTEGER,
    stats_json TEXT,
    cost_usd REAL NOT NULL DEFAULT 0,
    error TEXT
);
CREATE TABLE IF NOT EXISTS source_state(
    source TEXT PRIMARY KEY,
    last_ok_at TEXT,
    last_error TEXT,
    last_error_at TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS llm_calls(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    task TEXT NOT NULL,
    requested_model TEXT NOT NULL,
    model TEXT,
    provider TEXT,
    generation_id TEXT,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    cached_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0,
    latency_ms INTEGER,
    status TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_created ON llm_calls(created_at);
"""

_SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS triage(
    item_id TEXT PRIMARY KEY,
    run_id INTEGER,
    decision TEXT NOT NULL,          -- main | radar | reject | muted | duplicate | gated | error
    reason TEXT,
    total REAL,
    scores_json TEXT,                -- {"A":..,"B":..,"C":..,"D":..}
    summary_pt TEXT,
    why_it_matters_pt TEXT,
    tags_json TEXT,
    pre_score REAL,                  -- classifier probability, when a classifier exists
    classifier_version TEXT,
    model TEXT,
    prompt_version TEXT,
    cost_usd REAL NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 1,
    triaged_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_triage_run ON triage(run_id);
CREATE TABLE IF NOT EXISTS embeddings(
    item_id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector BLOB NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clusters(
    id TEXT PRIMARY KEY,             -- = id of the representative item
    representative_item_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL,       -- item | idea | entity
    target_id TEXT NOT NULL,
    value TEXT NOT NULL,             -- up | down | test | archive
    note TEXT,
    channel TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_target ON feedback(target_type, target_id);
CREATE TABLE IF NOT EXISTS deliveries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    day TEXT NOT NULL,
    item_id TEXT NOT NULL,
    key TEXT NOT NULL,               -- short id carried by the Telegram buttons
    section TEXT NOT NULL,           -- main | radar
    position INTEGER NOT NULL,
    chat_id TEXT,
    message_id INTEGER,
    sent_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_deliveries_key ON deliveries(key);
CREATE INDEX IF NOT EXISTS idx_deliveries_message ON deliveries(chat_id, message_id);
CREATE TABLE IF NOT EXISTS classifier_models(
    version TEXT PRIMARY KEY,
    profile TEXT NOT NULL,
    embed_model TEXT NOT NULL,
    trained_at TEXT NOT NULL,
    n_labels INTEGER NOT NULL,
    metrics_json TEXT,
    path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inbox(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    received_at TEXT NOT NULL,
    processed_at TEXT
);
"""

_LLM_FIELDS = ("run_id", "task", "requested_model", "model", "provider", "generation_id",
               "input_tokens", "output_tokens", "reasoning_tokens", "cached_tokens",
               "cost_usd", "latency_ms", "status", "error")

_TRIAGE_FIELDS = ("reason", "total", "scores", "summary_pt", "why_it_matters_pt", "tags", "pre_score",
                  "classifier_version", "model", "prompt_version", "cost_usd")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _in(ids) -> str:
    return ",".join("?" * len(ids))


class Store:
    """One connection, shared by the triage worker threads (SQLite runs in serialized mode);
    the writes those threads make go through `_lock`."""

    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.executescript(_SCHEMA_V2)
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(items)")}
        if "cluster_id" not in columns:
            self.conn.execute("ALTER TABLE items ADD COLUMN cluster_id TEXT")
        self.conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)",
                          (str(SCHEMA_VERSION),))
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # --- meta ---------------------------------------------------------------
    def meta_get(self, key, default=None):
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def meta_set(self, key, value) -> None:
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", (key, str(value)))
            self.conn.commit()

    # --- runs ---------------------------------------------------------------
    def start_run(self, kind: str) -> int:
        cur = self.conn.execute("INSERT INTO runs(kind, started_at) VALUES(?, ?)", (kind, utcnow()))
        self.conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, ok: bool, stats: dict, error: str | None = None) -> None:
        cost = self.conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE run_id = ?",
                                 (run_id,)).fetchone()[0]
        self.conn.execute(
            "UPDATE runs SET finished_at = ?, ok = ?, stats_json = ?, cost_usd = ?, error = ? WHERE id = ?",
            (utcnow(), int(ok), json.dumps(stats, ensure_ascii=False), cost, error, run_id))
        self.conn.commit()

    def last_run(self, kind: str | None = None):
        sql = "SELECT * FROM runs WHERE finished_at IS NOT NULL"
        args = ()
        if kind:
            sql += " AND kind = ?"
            args = (kind,)
        return self.conn.execute(sql + " ORDER BY id DESC LIMIT 1", args).fetchone()

    # --- items --------------------------------------------------------------
    def upsert_items(self, items, run_id: int) -> list[str]:
        """Insert unseen items; for known ids only merge concepts. Returns the ids that were new."""
        new_ids = []
        now = utcnow()
        for it in items:
            row = self.conn.execute("SELECT concepts_json FROM items WHERE id = ?", (it.id,)).fetchone()
            if row is not None:
                merged = json.loads(row["concepts_json"])
                merged += [c for c in it.concepts if c not in merged]
                self.conn.execute("UPDATE items SET concepts_json = ? WHERE id = ?",
                                  (json.dumps(merged, ensure_ascii=False), it.id))
                continue
            self.conn.execute(
                "INSERT INTO items(id, kind, source, source_id, canonical_url, doi, arxiv_id, pmid, title,"
                " authors_json, published_at, fetched_at, text, content_hash, concepts_json, profile,"
                " first_run_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (it.id, it.kind, it.source, it.source_id, it.url, it.doi, it.arxiv_id, it.pmid, it.title,
                 json.dumps(it.authors, ensure_ascii=False), it.published_at, now, it.text,
                 it.content_hash, json.dumps(it.concepts, ensure_ascii=False), it.profile, run_id))
            new_ids.append(it.id)
        self.conn.commit()
        return new_ids

    def count_items(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]

    def get_items(self, ids):
        ids = list(ids)
        if not ids:
            return []
        rows = self.conn.execute(f"SELECT * FROM items WHERE id IN ({_in(ids)})", ids).fetchall()
        order = {i: n for n, i in enumerate(ids)}
        return sorted(rows, key=lambda r: order[r["id"]])

    def titles_since(self, since_iso):
        return self.conn.execute("SELECT id, title, cluster_id FROM items WHERE fetched_at >= ? ORDER BY fetched_at",
                                 (since_iso,)).fetchall()

    def join_cluster(self, item_id, representative_id) -> None:
        with self._lock:
            row = self.conn.execute("SELECT cluster_id FROM items WHERE id = ?", (representative_id,)).fetchone()
            cluster = (row["cluster_id"] if row else None) or representative_id
            self.conn.execute("INSERT OR IGNORE INTO clusters(id, representative_item_id, created_at) VALUES(?,?,?)",
                              (cluster, representative_id, utcnow()))
            self.conn.execute("UPDATE items SET cluster_id = ? WHERE id IN (?, ?)", (cluster, item_id, representative_id))
            self.conn.commit()

    def cluster_sources(self, item_id) -> list:
        row = self.conn.execute("SELECT cluster_id, source FROM items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return []
        if not row["cluster_id"]:
            return [row["source"]]
        rows = self.conn.execute("SELECT DISTINCT source FROM items WHERE cluster_id = ? ORDER BY source",
                                 (row["cluster_id"],)).fetchall()
        return [r[0] for r in rows]

    def redact_item(self, item_id) -> None:
        """Identifiable patient data: keep the id (so it is never fetched again), drop the content."""
        with self._lock:
            self.conn.execute("UPDATE items SET text = NULL, title = '[removido: dado de paciente]' WHERE id = ?",
                              (item_id,))
            self.conn.execute("DELETE FROM embeddings WHERE item_id = ?", (item_id,))
            self.conn.commit()

    # --- source health ------------------------------------------------------
    def record_source_ok(self, source: str) -> None:
        self.conn.execute(
            "INSERT INTO source_state(source, last_ok_at, consecutive_failures) VALUES(?, ?, 0)"
            " ON CONFLICT(source) DO UPDATE SET last_ok_at = excluded.last_ok_at, consecutive_failures = 0",
            (source, utcnow()))
        self.conn.commit()

    def record_source_error(self, source: str, error: str) -> int:
        self.conn.execute(
            "INSERT INTO source_state(source, last_error, last_error_at, consecutive_failures) VALUES(?, ?, ?, 1)"
            " ON CONFLICT(source) DO UPDATE SET last_error = excluded.last_error,"
            " last_error_at = excluded.last_error_at, consecutive_failures = consecutive_failures + 1",
            (source, error[:500], utcnow()))
        self.conn.commit()
        return self.conn.execute("SELECT consecutive_failures FROM source_state WHERE source = ?",
                                 (source,)).fetchone()[0]

    def source_states(self):
        return self.conn.execute("SELECT * FROM source_state ORDER BY source").fetchall()

    # --- LLM ledger ---------------------------------------------------------
    def record_llm_call(self, **fields) -> int:
        unknown = set(fields) - set(_LLM_FIELDS)
        if unknown:
            raise ValueError(f"unknown llm_calls fields: {sorted(unknown)}")
        cols = list(fields) + ["created_at"]
        vals = [fields[c] for c in fields] + [utcnow()]
        with self._lock:
            cur = self.conn.execute(
                f"INSERT INTO llm_calls({', '.join(cols)}) VALUES({', '.join('?' * len(cols))})", vals)
            self.conn.commit()
        return cur.lastrowid

    def llm_cost_since(self, since_iso: str) -> float:
        with self._lock:
            return self.conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE created_at >= ?",
                                     (since_iso,)).fetchone()[0]

    def avg_llm_cost(self, task: str, last: int = 200) -> float | None:
        row = self.conn.execute(
            "SELECT AVG(cost_usd) FROM (SELECT cost_usd FROM llm_calls WHERE task = ? AND status = 'ok'"
            " ORDER BY id DESC LIMIT ?)", (task, last)).fetchone()
        return row[0]

    # --- triage -------------------------------------------------------------
    def triage_candidates(self, since_iso: str, max_attempts: int = 3):
        """Items fetched since `since_iso` with no decision yet, or whose triage errored < max_attempts."""
        return self.conn.execute(
            "SELECT i.* FROM items i LEFT JOIN triage t ON t.item_id = i.id WHERE i.fetched_at >= ?"
            " AND (t.item_id IS NULL OR (t.decision = 'error' AND t.attempts < ?)) ORDER BY i.fetched_at DESC",
            (since_iso, max_attempts)).fetchall()

    def record_triage(self, item_id, run_id, decision, **fields) -> None:
        unknown = set(fields) - set(_TRIAGE_FIELDS)
        if unknown:
            raise ValueError(f"unknown triage fields: {sorted(unknown)}")
        scores, tags = fields.pop("scores", None), fields.pop("tags", None)
        row = dict(fields, scores_json=json.dumps(scores) if scores is not None else None,
                   tags_json=json.dumps(tags, ensure_ascii=False) if tags is not None else None)
        cols = ["item_id", "run_id", "decision", "triaged_at"] + list(row)
        vals = [item_id, run_id, decision, utcnow()] + list(row.values())
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols[1:])
        with self._lock:
            self.conn.execute(
                f"INSERT INTO triage({', '.join(cols)}) VALUES({_in(cols)}) ON CONFLICT(item_id) DO UPDATE SET "
                f"{updates}, attempts = triage.attempts + 1", vals)
            self.conn.commit()

    def triage_rows(self, run_id, decisions=("main", "radar")):
        decisions = list(decisions)
        return self.conn.execute(
            "SELECT t.*, i.title, i.canonical_url, i.source, i.profile, i.published_at FROM triage t"
            f" JOIN items i ON i.id = t.item_id WHERE t.run_id = ? AND t.decision IN ({_in(decisions)})",
            [run_id] + decisions).fetchall()

    def triage_counts(self, run_id) -> dict:
        rows = self.conn.execute("SELECT decision, COUNT(*) FROM triage WHERE run_id = ? GROUP BY decision",
                                 (run_id,)).fetchall()
        return {r[0]: r[1] for r in rows}

    # --- embeddings ---------------------------------------------------------
    def save_embeddings(self, model: str, pairs) -> None:
        now = utcnow()
        rows = [(item_id, model, int(vec.shape[0]), np.asarray(vec, dtype=np.float32).tobytes(), now)
                for item_id, vec in pairs]
        with self._lock:
            self.conn.executemany("INSERT OR REPLACE INTO embeddings(item_id, model, dim, vector, created_at)"
                                  " VALUES(?,?,?,?,?)", rows)
            self.conn.commit()

    def embedded_ids(self, model: str, ids) -> set:
        ids = list(ids)
        if not ids:
            return set()
        rows = self.conn.execute(f"SELECT item_id FROM embeddings WHERE model = ? AND item_id IN ({_in(ids)})",
                                 [model] + ids).fetchall()
        return {r[0] for r in rows}

    def load_embeddings(self, model: str, ids=None, since_iso=None, exclude=()):
        """-> (ids, float32 matrix of unit vectors). Filter by explicit ids or by items fetched since."""
        sql = "SELECT e.item_id, e.dim, e.vector FROM embeddings e JOIN items i ON i.id = e.item_id WHERE e.model = ?"
        args = [model]
        if ids is not None:
            ids = list(ids)
            if not ids:
                return [], np.zeros((0, 0), dtype=np.float32)
            sql += f" AND e.item_id IN ({_in(ids)})"
            args += ids
        if since_iso:
            sql += " AND i.fetched_at >= ?"
            args.append(since_iso)
        excluded = set(exclude)
        rows = [r for r in self.conn.execute(sql, args).fetchall() if r["item_id"] not in excluded]
        if not rows:
            return [], np.zeros((0, 0), dtype=np.float32)
        matrix = np.stack([np.frombuffer(r["vector"], dtype=np.float32, count=r["dim"]) for r in rows])
        return [r["item_id"] for r in rows], matrix

    # --- feedback -----------------------------------------------------------
    def add_feedback(self, target_type, target_id, value, channel, note=None) -> int:
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO feedback(target_type, target_id, value, note, channel, created_at) VALUES(?,?,?,?,?,?)",
                (target_type, target_id, value, note, channel, utcnow()))
            self.conn.commit()
        return cur.lastrowid

    def item_votes(self, profile=None, ids=None) -> dict:
        """Latest vote per item (a later vote replaces an earlier one)."""
        sql = ("SELECT f.target_id, f.value FROM feedback f JOIN items i ON i.id = f.target_id"
               " WHERE f.target_type = 'item'")
        args = []
        if profile:
            sql += " AND i.profile = ?"
            args.append(profile)
        if ids is not None:
            ids = list(ids)
            if not ids:
                return {}
            sql += f" AND f.target_id IN ({_in(ids)})"
            args += ids
        votes = {}
        for row in self.conn.execute(sql + " ORDER BY f.id", args):
            votes[row[0]] = row[1]
        return votes

    # --- deliveries ---------------------------------------------------------
    def record_delivery(self, run_id, day, item_id, key, section, position) -> int:
        cur = self.conn.execute(
            "INSERT INTO deliveries(run_id, day, item_id, key, section, position) VALUES(?,?,?,?,?,?)",
            (run_id, day, item_id, key, section, position))
        self.conn.commit()
        return cur.lastrowid

    def mark_delivered(self, delivery_ids, chat_id, message_id) -> None:
        ids = list(delivery_ids)
        if not ids:
            return
        self.conn.execute(f"UPDATE deliveries SET chat_id = ?, message_id = ?, sent_at = ? WHERE id IN ({_in(ids)})",
                          [str(chat_id), message_id, utcnow()] + ids)
        self.conn.commit()

    def delivery_by_key(self, key):
        return self.conn.execute("SELECT * FROM deliveries WHERE key = ? ORDER BY id DESC LIMIT 1", (key,)).fetchone()

    def deliveries_for_message(self, chat_id, message_id):
        return self.conn.execute("SELECT * FROM deliveries WHERE chat_id = ? AND message_id = ? ORDER BY position",
                                 (str(chat_id), message_id)).fetchall()

    # --- classifiers --------------------------------------------------------
    def record_classifier(self, version, profile, embed_model, n_labels, metrics, path) -> None:
        self.conn.execute(
            "INSERT INTO classifier_models(version, profile, embed_model, trained_at, n_labels, metrics_json, path)"
            " VALUES(?,?,?,?,?,?,?)",
            (version, profile, embed_model, utcnow(), n_labels, json.dumps(metrics), str(path)))
        self.conn.commit()

    def latest_classifier(self, profile, embed_model):
        return self.conn.execute(
            "SELECT * FROM classifier_models WHERE profile = ? AND embed_model = ? ORDER BY trained_at DESC,"
            " rowid DESC LIMIT 1", (profile, embed_model)).fetchone()

    # --- inbox --------------------------------------------------------------
    def add_inbox(self, channel, payload) -> int:
        cur = self.conn.execute("INSERT INTO inbox(channel, payload_json, received_at) VALUES(?,?,?)",
                                (channel, json.dumps(payload, ensure_ascii=False), utcnow()))
        self.conn.commit()
        return cur.lastrowid
````

- [ ] **Passo 4: `from_row` em `sotawhat/items.py`**

4a. Acrescentar `import json` logo depois de `import hashlib`.

4b. Acrescentar ao final do arquivo:

````python
def from_row(row) -> Item:
    """An `items` row from the store back into an `Item`."""
    return Item(
        id=row["id"], kind=row["kind"], source=row["source"], source_id=row["source_id"] or "",
        title=row["title"], url=row["canonical_url"] or "", authors=json.loads(row["authors_json"] or "[]"),
        published_at=row["published_at"] or "", text=row["text"] or "", doi=row["doi"],
        arxiv_id=row["arxiv_id"], pmid=row["pmid"], concepts=json.loads(row["concepts_json"] or "[]"),
        profile=row["profile"])
````

- [ ] **Passo 5: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `120 passed`.

- [ ] **Passo 6: Commit**

```bash
git add sotawhat/store/db.py sotawhat/items.py tests/test_store.py tests/test_store_v2.py
git commit -m "feat: SQLite schema 2 (triage, embeddings, clusters, feedback, deliveries, classifiers, inbox)"
```

---

## Tarefa 3: Taxonomia, schema da triagem e prompt v1

Por quê: o schema estrito só usa `enum`, que todos os provedores aceitam no modo estrito. Notas 0–5, chaves da taxonomia e rótulos fechados viram enums; `minimum`, `maxLength` e `$ref` ficam de fora. Os limites de texto ficam no prompt. O prompt é versionado (`triage_v1`), e a versão fica gravada em cada decisão.

**Files:**
- Create: `sotawhat/taxonomy.py`, `sotawhat/llm/schemas.py`, `sotawhat/llm/prompts/__init__.py`, `sotawhat/llm/prompts/triage_v1.md`, `tests/test_schemas.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_schemas.py`:

````python
# tests/test_schemas.py
import json
import re

import pytest
from pydantic import ValidationError

from sotawhat import taxonomy as tx
from sotawhat.llm.gateway import strict_schema
from sotawhat.llm.prompts import load
from sotawhat.llm.schemas import TriageOutput

VALID = dict(summary_pt="Resumo.", hard_exclusion="none", inclusion_rules=[1, 4], frontier_ai=4,
             medical_applicability=5, actionability=3, domains=["A03"], problem_types=["B02"], techniques=["C05"],
             evidence_stage="D4", stakeholders=["radiologia_patologia"], br_applicability="F1", cfm_risk="alto",
             substance=3, audience=["clinico"], vendor_only=False, reason_pt="Motivo.", why_it_matters_pt="Importa.")


def test_strict_schema_uses_only_enums_and_requires_everything():
    schema = strict_schema(TriageOutput)
    text = json.dumps(schema)
    assert schema["required"] == list(schema["properties"]) and schema["additionalProperties"] is False
    for keyword in ("minimum", "maximum", "maxLength", "$ref", "anyOf", '"default"'):
        assert keyword not in text                    # portable strict mode across providers
    assert schema["properties"]["frontier_ai"]["enum"] == [0, 1, 2, 3, 4, 5]
    assert schema["properties"]["domains"]["items"]["enum"] == list(tx.DOMAINS)


def test_output_validation_and_tags():
    out = TriageOutput(**VALID)
    assert out.tags()["domains"] == ["A03"] and out.tags()["hard_exclusion"] == "none"
    for field, bad in (("frontier_ai", 6), ("domains", ["A99"]), ("cfm_risk", "altíssimo"), ("inclusion_rules", [11])):
        with pytest.raises(ValidationError):
            TriageOutput(**dict(VALID, **{field: bad}))


def test_taxonomy_matches_the_sdd_and_prompt_placeholders():
    assert (len(tx.DOMAINS), len(tx.PROBLEMS), len(tx.TECHNIQUES), len(tx.EVIDENCE)) == (23, 15, 21, 7)
    assert tx.label("A14") == "ciclo de receita/glosas/autorização" and tx.label("Z9") == "Z9"
    template = load("triage_v1")
    assert set(re.findall(r"\{\{(\w+)\}\}", template)) == {"DOMAINS", "PROBLEMS", "TECHNIQUES", "EVIDENCE",
                                                          "STAKEHOLDERS", "BR", "CFM", "AUDIENCE"}
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_schemas.py -q`
Expected: FAIL com `ImportError: cannot import name 'taxonomy' from 'sotawhat'`.

- [ ] **Passo 3: Criar `sotawhat/taxonomy.py`**

````python
# sotawhat/taxonomy.py
"""Controlled vocabularies A–G (SDD §6.5). Keys are stable: triage tags, digest labels and, from P3,
the graph use them. Labels are pt-BR (shown to the user)."""

DOMAINS = {
    "A01": "documentação clínica", "A02": "apoio à decisão", "A03": "radiologia/imagem",
    "A04": "patologia/laboratório", "A05": "terapia intensiva/deterioração", "A06": "emergência/triagem",
    "A07": "centro cirúrgico", "A08": "oncologia", "A09": "cardiologia/sinais", "A10": "farmácia clínica",
    "A11": "enfermagem", "A12": "fluxo/leitos/capacidade", "A13": "força de trabalho/escalas",
    "A14": "ciclo de receita/glosas/autorização", "A15": "suprimentos/OPME/logística",
    "A16": "experiência/acesso do paciente", "A17": "qualidade/segurança/infecção",
    "A18": "monitoramento remoto/wearables/hospital-em-casa", "A19": "telemedicina",
    "A20": "pesquisa clínica/dados/RWE", "A21": "educação médica", "A22": "governança de IA/regulação",
    "A23": "atenção primária/crônicos",
}
PROBLEMS = {
    "B01": "sobrecarga documental/burnout", "B02": "erro/atraso diagnóstico", "B03": "deterioração não detectada",
    "B04": "segurança do paciente", "B05": "variabilidade de conduta", "B06": "ineficiência de fluxo/espera",
    "B07": "escassez de força de trabalho", "B08": "perda de receita/glosas", "B09": "custo/desperdício",
    "B10": "acesso/experiência", "B11": "fragmentação de dados/interoperabilidade",
    "B12": "privacidade/conformidade", "B13": "confiabilidade/segurança da IA", "B14": "produtividade em pesquisa",
    "B15": "competência/confiança profissional",
}
TECHNIQUES = {
    "C01": "ASR/documentação ambiente", "C02": "LLMs/RAG/Q&A clínico", "C03": "agentes/orquestração",
    "C04": "modelos de fundação multimodais", "C05": "visão computacional diagnóstica",
    "C06": "patologia computacional", "C07": "visão ambiente/vídeo", "C08": "séries temporais/sinais",
    "C09": "preditivos tabulares em EHR", "C10": "generativos de eventos médicos",
    "C11": "otimização/pesquisa operacional", "C12": "PLN de extração/codificação", "C13": "automação de processos",
    "C14": "robótica/controle", "C15": "edge/wearables", "C16": "federado/privacidade",
    "C17": "dados sintéticos/pacientes simulados", "C18": "avaliação/benchmarks/monitoramento",
    "C19": "modelos pequenos/abertos/fine-tuning local", "C20": "interoperabilidade/engenharia de dados",
    "C21": "XR/BCI",
}
EVIDENCE = {
    "D0": "ideia/opinião", "D1": "pesquisa de fronteira", "D2": "estudo revisado por pares",
    "D3": "RCT/validação externa", "D4": "autorização regulatória", "D5": "implantação comercial em escala",
    "D6": "ROI/desfecho independente",
}
STAKEHOLDERS = {
    "medico": "médico", "enfermagem": "enfermagem", "farmacia": "farmácia",
    "radiologia_patologia": "radiologia/patologia", "uti": "UTI", "ps": "pronto-socorro",
    "cc": "centro cirúrgico", "oncologia": "oncologia", "rcm_admin": "ciclo de receita/admin",
    "suprimentos": "suprimentos", "paciente": "paciente", "qualidade": "qualidade",
    "pesquisa": "pesquisa/IDOR", "educacao": "educação", "ti_governanca": "TI/governança",
    "operadora": "operadora", "regulador": "regulador",
}
BR_APPLICABILITY = {
    "F0": "irrelevante para o Brasil", "F1": "global, adaptável", "F2": "depende de regulação brasileira",
    "F3": "específico do Brasil (TISS/TUSS/RNDS/SUS/Rede D'Or)",
}
CFM_RISK = {   # Resolução CFM 2.454/2026, Anexo II
    "baixo": "agendamento, logística, chatbot informativo, sumarização interna",
    "medio": "apoio à decisão sem execução autônoma",
    "alto": "influência direta em decisão crítica ou ação automatizada",
    "nao_se_aplica": "não é uso clínico de IA",
}
AUDIENCE = {"clinico": "clínico", "gestao": "gestão", "engenharia": "engenharia",
            "motor": "o próprio motor (agentes, MCP, busca, avaliação)"}


def label(key: str) -> str:
    for table in (DOMAINS, PROBLEMS, TECHNIQUES, EVIDENCE):
        if key in table:
            return table[key]
    return key


def render(table: dict) -> str:
    return " · ".join(f"{k} {v}" for k, v in table.items())
````

- [ ] **Passo 4: Criar `sotawhat/llm/schemas.py`**

````python
# sotawhat/llm/schemas.py
"""Structured outputs (SDD §6.6, §6.7). Every constraint is an enum, which strict JSON schema supports
on every provider; free text is limited by the prompt, not by the schema."""
from typing import Literal

from pydantic import BaseModel, Field

from sotawhat import taxonomy as tx

Score = Literal[0, 1, 2, 3, 4, 5]
Exclusion = Literal["none", "clinical_without_ai", "generic_ai_no_bridge", "marketing_no_substance",
                    "identifiable_patient_data"]


class TriageOutput(BaseModel):
    summary_pt: str = Field(description="até 60 palavras, pt-BR, só fatos presentes no texto")
    hard_exclusion: Exclusion
    inclusion_rules: list[Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
    frontier_ai: Score = Field(description="A: avanço de IA/ML")
    medical_applicability: Score = Field(description="B: aplicação médico-hospitalar direta ou plausível em 2 anos")
    actionability: Score = Field(description="C: dá para usar/testar agora")
    domains: list[Literal[tuple(tx.DOMAINS)]]
    problem_types: list[Literal[tuple(tx.PROBLEMS)]]
    techniques: list[Literal[tuple(tx.TECHNIQUES)]]
    evidence_stage: Literal[tuple(tx.EVIDENCE)]
    stakeholders: list[Literal[tuple(tx.STAKEHOLDERS)]]
    br_applicability: Literal[tuple(tx.BR_APPLICABILITY)]
    cfm_risk: Literal[tuple(tx.CFM_RISK)]
    substance: Literal[0, 1, 2, 3]
    audience: list[Literal[tuple(tx.AUDIENCE)]]
    vendor_only: bool
    reason_pt: str = Field(description="1 frase justificando as notas")
    why_it_matters_pt: str = Field(description="até 40 palavras para hospital/startup; vazio se excluído")

    def tags(self) -> dict:
        return {"domains": self.domains, "problem_types": self.problem_types, "techniques": self.techniques,
                "evidence_stage": self.evidence_stage, "stakeholders": self.stakeholders,
                "br_applicability": self.br_applicability, "cfm_risk": self.cfm_risk,
                "substance": self.substance, "audience": self.audience,
                "inclusion_rules": self.inclusion_rules, "hard_exclusion": self.hard_exclusion,
                "vendor_only": self.vendor_only}
````

- [ ] **Passo 5: Criar `sotawhat/llm/prompts/__init__.py`**

````python
# sotawhat/llm/prompts/__init__.py
"""Versioned prompts (SDD §6.6). The version string is stored with every result that used it."""
from importlib.resources import files


def load(name: str) -> str:
    return files(__package__).joinpath(f"{name}.md").read_text(encoding="utf-8")
````

- [ ] **Passo 6: Criar `sotawhat/llm/prompts/triage_v1.md`** (as marcações `{{…}}` são preenchidas com a taxonomia em tempo de execução)

````markdown
You are the relevance-triage stage of a personal insight engine. Its single reader is a physician-entrepreneur in Brazil who works with a large private hospital network (Rede D'Or) and runs a medical-AI startup. The engine follows frontier AI/ML and its intersection with medicine, hospitals, medical bioengineering and healthcare operations. Purely clinical research without AI and generic AI news without a path to health are noise.

You receive one item (paper, article, release or news) and fill a strict JSON form. Judge only what the text says.

## Scores (integers 0–5)
- frontier_ai (A): technical advance, strong result, relevant release or new tool in AI/ML. 0 = no AI content · 3 = solid applied AI work · 5 = clear advance with a result or artifact.
- medical_applicability (B): direct or plausible (within 2 years) application in medicine, hospitals, medical bioengineering or hospital management. 0 = none plausible · 2 = a plausible bridge you can name · 5 = direct application demonstrated or obvious.
- actionability (C): usable or testable now: code, model weights, dataset, API, available product, clear regulatory path. 0 = nothing available · 5 = open artifact ready to use.
Novelty against what the reader has already seen is computed elsewhere; do not judge it.

## Inclusion rules: list every rule that applies in inclusion_rules
1. AI product or platform in use by hospitals, health networks, labs, payers or public health systems, with substance (named customers, number of sites, results, regulatory clearance, price).
2. Evidence about AI in health: RCT, external validation, independent evaluation, reports of failure, incident or recall.
3. Regulation and governance: ANVISA, CFM, ANPD, ANS, MS/RNDS, PL 2338, FDA, EU AI Act, CHAI, FHIR/TISS.
4. Frontier AI capability with a plausible bridge to health even without medical context (new multimodal, 3D or long-context models; multilingual speech recognition; tool-using agents and MCP; small open or on-device models; evaluation, calibration, hallucination or drift detection; privacy; robotics; brain-computer interfaces; video understanding). Applies only if it maps to at least one problem type and one technique family below.
5. Moves by incumbents and capital (Epic, Oracle Health, Microsoft, Google, OpenAI, Anthropic, NVIDIA, Philips, GE, Siemens, MV/Tasy, Dasa, Einstein, Rede D'Or; funding rounds and M&A of AI healthtechs).
6. Hospital operations, revenue cycle and payers when there is a data or AI component.
7. Digital health or health AI in Brazil or Latin America.
8. Medical devices and bioengineering with validation or regulatory status.
9. Medical education or the health workforce with AI.
10. Evaluation methodology, safety, bias, de-identification or synthetic data in health.

## hard_exclusion: the first that applies, otherwise "none"
- clinical_without_ai: clinical research without AI or data methods (drugs, conventional surgical technique, epidemiology, guidelines), unless it is a digital tool or changes a protocol that an AI product implements.
- generic_ai_no_bridge: generic AI with no bridge to health (consumer apps, chips and datacenters, AI in finance, retail or games, corporate disputes, "AGI" talk, opinion).
- marketing_no_substance: press release without numbers, customers or evidence; listicles, webinars, awards, job posts.
- identifiable_patient_data: the text contains identifiable patient data.
Softer problems lower the scores instead: opinion without new facts, introductory explainers, drug discovery or bioinformatics far upstream of hospitals, consumer wellness without validation, reimbursement policy without a digital component, content older than 18 months that is not foundational, purely local rules of another country.

## Tags: use only these keys; several are allowed; use [] when nothing fits
- domains: {{DOMAINS}}
- problem_types: {{PROBLEMS}}
- techniques: {{TECHNIQUES}}
- evidence_stage (one): {{EVIDENCE}}
- stakeholders: {{STAKEHOLDERS}}
- br_applicability (one): {{BR}}
- cfm_risk (one; Brazilian CFM Resolution 2,454/2026, Annex II): {{CFM}}
- substance (one): 0 none · 1 weak · 2 concrete facts · 3 strong numbers or evidence
- audience: {{AUDIENCE}}
- vendor_only: true when the only source is the vendor itself, with no third party.

## Writing: Brazilian Portuguese, technical terms in English
- summary_pt: up to 60 words: what the item is and its main result. Only facts present in the text; never invent numbers, names, links or identifiers. If only the title is available, say so and score conservatively.
- why_it_matters_pt: up to 40 words, a concrete use for a hospital network or a medical-AI startup. Empty string when the item is excluded.
- reason_pt: one sentence that justifies the scores.

## Calibration examples
- "FDA clears Aidoc CARE foundation model with 14 CT indications" → include: inclusion_rules [1, 3, 8]; A 4, B 5, C 3; domains [A03]; problem_types [B02, B03]; techniques [C04, C05]; evidence_stage D4; br_applicability F1; cfm_risk alto.
- "Google releases an open 4B model that accepts 3D CT volumes" (no clinical study) → include through the bridge: inclusion_rules [4]; A 5, B 3, C 5; domains [A03, A04]; problem_types [B02]; techniques [C04, C19]; evidence_stage D1.
- "New datacenter chip doubles training throughput" → hard_exclusion generic_ai_no_bridge; A 3, B 0, C 1.
- "Phase III trial of an antibody for asthma" → hard_exclusion clinical_without_ai; A 0, B 1, C 0.
- "ANS changes the claim-denial (glosa) indicators that payers must report" → include for its data component: inclusion_rules [3, 6, 7]; A 2, B 4, C 3; domains [A14]; problem_types [B08, B11]; br_applicability F3; cfm_risk nao_se_aplica.
````

- [ ] **Passo 7: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `123 passed`.

- [ ] **Passo 8: Commit**

```bash
git add sotawhat/taxonomy.py sotawhat/llm/schemas.py sotawhat/llm/prompts tests/test_schemas.py
git commit -m "feat: controlled vocabularies, strict triage schema and prompt v1"
```

---

## Tarefa 4: `config/llm.yaml` no gateway e metadados da chamada

Por quê: a precedência fica `tasks.py` < `config/llm.yaml` < `SOTAWHAT_MODEL_<ETAPA>`. O bake-off e a triagem precisam saber o modelo efetivo, o custo de todas as tentativas e se o JSON veio válido de primeira; por isso existe `structured_call()`, e `structured()` continua devolvendo só a saída.

**Files:**
- Modify: `sotawhat/llm/tasks.py`, `sotawhat/llm/gateway.py` (substituir o conteúdo inteiro), `tests/test_gateway.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Acrescentar ao final de `tests/test_gateway.py`:

````python
def test_resolve_precedence_defaults_yaml_env():
    yaml_tasks = {"triage": {"models": ["a/x", "b/y"], "reasoning": "high", "max_tokens": 900}}
    spec = resolve("triage", None, yaml_tasks)
    assert (spec.models, spec.reasoning, spec.max_tokens) == (("a/x", "b/y"), "high", 900)
    spec = resolve("triage", _settings(sotawhat_model_triage="b/y"), yaml_tasks)
    assert spec.models == ("b/y", "a/x")                      # .env wins for the primary
    assert resolve("extract", None, yaml_tasks) == DEFAULT_TASKS["extract"]


def test_structured_call_reports_cost_attempts_and_validity(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        client = FakeClient(_completion('{"title": "x"}', cost=0.001),
                            _completion('{"title": "x", "score": 4, "note": null}', model="z-ai/glm-5.3-flash",
                                        cost=0.002))
        gw = LLMGateway(client, store=st, settings=_settings(), tasks={"triage": {"models": ["a/x"]}})
        res = gw.structured_call("triage", [{"role": "user", "content": "rate"}], Verdict)
        assert res.output.score == 4 and res.model == "z-ai/glm-5.3-flash" and res.provider == "DeepInfra"
        assert (res.attempts, res.first_try_valid) == (2, False) and abs(res.cost_usd - 0.003) < 1e-9
        assert client.payloads[0]["model"] == "a/x"           # config/llm.yaml chain was used
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_gateway.py -q`
Expected: FAIL (2 testes) com `TypeError: resolve() takes from 1 to 2 positional arguments but 3 were given`.

- [ ] **Passo 3: `resolve()` em `sotawhat/llm/tasks.py`**

Substituir:

```python
def resolve(task, settings=None) -> TaskSpec:
    spec = DEFAULT_TASKS[task]
    override = settings.model_override(task) if settings is not None else ""
```

por:

````python
def resolve(task, settings=None, overrides=None) -> TaskSpec:
    """Defaults < config/llm.yaml `tasks` (overrides) < SOTAWHAT_MODEL_<TASK> for the primary model."""
    spec = DEFAULT_TASKS[task]
    custom = (overrides or {}).get(task) or {}
    if custom:
        spec = replace(spec, models=tuple(custom.get("models") or spec.models),
                       reasoning=custom.get("reasoning", spec.reasoning),
                       max_tokens=custom.get("max_tokens", spec.max_tokens))
    override = settings.model_override(task) if settings is not None else ""
````

- [ ] **Passo 4: Substituir `sotawhat/llm/gateway.py`**

````python
# sotawhat/llm/gateway.py
"""Task-level LLM gateway (SDD §6.6): strict JSON output, repair + fallback, budget, cost ledger."""
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import ValidationError

from sotawhat.llm.openrouter import InsufficientCredits, OpenRouterError, Privacy, build_payload
from sotawhat.llm.tasks import resolve

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class BudgetExceeded(Exception):
    pass


class LLMFailure(Exception):
    pass


@dataclass
class StructuredResult:
    output: object
    model: str               # effective model reported by OpenRouter
    provider: str | None
    cost_usd: float          # every call made for this result, invalid attempts included
    latency_ms: int          # the successful call
    attempts: int            # calls made, including invalid JSON and errors
    first_try_valid: bool    # valid on the very first call


def _strictify(node):
    if isinstance(node, list):
        for sub in node:
            _strictify(sub)
        return
    if not isinstance(node, dict):
        return
    node.pop("default", None)
    node.pop("title", None)
    props = node.get("properties")
    if isinstance(props, dict):
        node["required"] = list(props)
        node["additionalProperties"] = False
        for sub in props.values():
            _strictify(sub)
    for key in ("items", "anyOf", "allOf", "oneOf", "prefixItems"):
        if key in node:
            _strictify(node[key])
    for sub in (node.get("$defs") or {}).values():
        _strictify(sub)


def strict_schema(model_cls) -> dict:
    """Pydantic JSON Schema -> strict structured-output schema (all keys required, no extras)."""
    schema = model_cls.model_json_schema()
    _strictify(schema)
    return schema


def extract_json(content: str) -> str:
    text = _FENCE.sub("", content.strip())
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


def _period_starts(now):
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return day.isoformat(timespec="seconds"), day.replace(day=1).isoformat(timespec="seconds")


class LLMGateway:
    def __init__(self, client, store=None, settings=None, run_id=None, budget_day=None,
                 budget_month=None, now=lambda: datetime.now(timezone.utc), tasks=None):
        self.client = client
        self.store = store
        self.settings = settings
        self.run_id = run_id
        self.tasks = tasks or {}   # config/llm.yaml `tasks`
        self._now = now
        if settings is not None:
            self.privacy = Privacy(zdr=settings.openrouter_zdr, data_collection=settings.openrouter_data_collection,
                                   quantizations=settings.quantizations)
            budget_day = settings.sotawhat_llm_budget_usd_day if budget_day is None else budget_day
            budget_month = settings.sotawhat_llm_budget_usd_month if budget_month is None else budget_month
        else:
            self.privacy = Privacy()
        self.budget_day = budget_day
        self.budget_month = budget_month

    def _check_budget(self):
        if self.store is None:
            return
        day_start, month_start = _period_starts(self._now())
        if self.budget_day is not None and self.store.llm_cost_since(day_start) >= self.budget_day:
            raise BudgetExceeded(f"daily LLM budget of US$ {self.budget_day:.2f} reached")
        if self.budget_month is not None and self.store.llm_cost_since(month_start) >= self.budget_month:
            raise BudgetExceeded(f"monthly LLM budget of US$ {self.budget_month:.2f} reached")

    def _record(self, task, requested, completion=None, status="ok", error=None):
        if self.store is None:
            return
        fields = dict(run_id=self.run_id, task=task, requested_model=requested, status=status,
                      error=(error or "")[:500] or None)
        if completion is not None:
            fields.update(model=completion.model, provider=completion.provider,
                          generation_id=completion.generation_id, input_tokens=completion.input_tokens,
                          output_tokens=completion.output_tokens, reasoning_tokens=completion.reasoning_tokens,
                          cached_tokens=completion.cached_tokens, cost_usd=completion.cost_usd,
                          latency_ms=completion.latency_ms)
        self.store.record_llm_call(**fields)

    def structured(self, task, messages, output_model, models=None):
        """Return a validated `output_model` (see `structured_call`)."""
        return self.structured_call(task, messages, output_model, models).output

    def structured_call(self, task, messages, output_model, models=None) -> StructuredResult:
        """Tries each model (with the remaining ones as server-side fallbacks); one repair round per
        model when the JSON does not validate. Returns the output plus what it took to get it."""
        spec = resolve(task, self.settings, self.tasks)
        chain = tuple(models) if models else spec.models
        schema = strict_schema(output_model)
        name = re.sub(r"[^a-z0-9_]+", "_", output_model.__name__.lower())
        last_error = None
        attempts, cost = 0, 0.0
        for i, model in enumerate(chain):
            convo = list(messages)
            for _attempt in range(2):
                self._check_budget()
                payload = build_payload(chain[i:], convo, schema=schema, schema_name=name,
                                        reasoning=spec.reasoning, max_tokens=spec.max_tokens,
                                        privacy=self.privacy)
                attempts += 1
                try:
                    completion = self.client.chat(payload)
                except InsufficientCredits as exc:
                    self._record(task, model, status="error", error=str(exc))
                    raise
                except OpenRouterError as exc:
                    self._record(task, model, status="error", error=str(exc))
                    last_error = exc
                    break
                cost += completion.cost_usd
                try:
                    result = output_model.model_validate_json(extract_json(completion.content))
                except ValidationError as exc:
                    self._record(task, model, completion, status="invalid", error=str(exc))
                    last_error = exc
                    problems = json.dumps(exc.errors(include_url=False)[:3], default=str)
                    convo = list(messages) + [
                        {"role": "assistant", "content": completion.content},
                        {"role": "user", "content": "The previous answer did not validate against the JSON "
                                                    f"schema: {problems}. Reply again with only valid JSON."}]
                    continue
                self._record(task, model, completion)
                return StructuredResult(output=result, model=completion.model or model,
                                        provider=completion.provider, cost_usd=cost,
                                        latency_ms=completion.latency_ms, attempts=attempts,
                                        first_try_valid=attempts == 1)
        raise LLMFailure(f"{task}: every model failed; last error: {last_error}")
````

- [ ] **Passo 5: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `125 passed`.

- [ ] **Passo 6: Commit**

```bash
git add sotawhat/llm/tasks.py sotawhat/llm/gateway.py tests/test_gateway.py
git commit -m "feat: config/llm.yaml task overrides and structured_call metadata"
```

---

## Tarefa 5: Embeddings locais e deduplicação "mesma história"

Por quê, com os números de `embeddings_dedup.md`:
- O EmbeddingGemma-300m roda a ~2,4 itens/s em CPU, cerca de 1 min por dia, e é multilíngue.
- Em 5 modelos, o cosseno não separa "mesma história" de "mesmo tema, outro trabalho". A fusão usa título quase idêntico, com números iguais. No vault, isso achou 11 duplicatas reais em 2.893 títulos, 9 delas entre fontes diferentes, sem nenhum falso positivo.
- O embedding alimenta a novidade D e o classificador.
- Os testes usam `HashEmbedder`; nenhum modelo é baixado.

**Files:**
- Create: `sotawhat/store/vectors.py`, `sotawhat/pipeline/dedup.py`, `tests/test_dedup_vectors.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_dedup_vectors.py`:

````python
# tests/test_dedup_vectors.py
import numpy as np

from sotawhat.config import Settings
from sotawhat.items import Item
from sotawhat.pipeline.dedup import find_duplicates, norm_title, same_title
from sotawhat.store.vectors import FastEmbedder, HashEmbedder, get_embedder, item_text, novelty_scores


def _it(iid, title):
    return Item(id=iid, kind="paper", source="pubmed", source_id="", title=title, url="")


def test_titles_from_two_sources_are_the_same_story():
    # real pair from the vault: JMIR RSS vs PubMed (en dash vs hyphen, trailing period)
    a = "Knowledge-Augmented Large Language Model for Multimodal Electronic Health Record–Based Risk Prediction"
    b = "Knowledge-Augmented Large Language Model for Multimodal Electronic Health Record-Based Risk Prediction."
    assert norm_title(a) == norm_title(b)
    assert same_title("AI Scribe Safety: Measuring What Happens After Signing",
                      "AI scribe safety - measuring what happens after signing.")
    assert same_title("Deep learning detects pneumothorax on chest radiographs in a multicenter cohort",
                      "Deep learning detects pneumothorax on chest radiographs: a multicenter cohort study")


def test_same_topic_different_work_is_not_merged():
    assert not same_title("Deep learning detects pneumothorax on chest radiographs",
                          "Deep learning detects pulmonary nodules on low-dose chest CT")
    assert not same_title("Editorial", "Editorial")       # uninformative titles never cluster
    assert not same_title("Qwen3.8 technical report: scaling open multimodal models",
                          "Qwen3.9 technical report: scaling open multimodal models")   # numbers must match


def test_find_duplicates_against_known_and_within_batch():
    known = [("pmid:1", "Real-World Implementation of Large Language Models for Writing Discharge Summaries", None)]
    items = [_it("url:a", "Real-world implementation of large language models for writing discharge summaries."),
             _it("doi:b", "A foundation model for retinal imaging"),
             _it("arxiv:c", "A Foundation Model for Retinal Imaging"),
             _it("pmid:d", "Editorial"), _it("pmid:e", "Editorial")]
    assert find_duplicates(items, known) == {"url:a": "pmid:1", "arxiv:c": "doi:b"}
    assert find_duplicates(items[:1], [("pmid:1", known[0][1], "cluster-x")]) == {"url:a": "cluster-x"}


def test_hash_embedder_is_deterministic_and_unit_norm():
    emb = HashEmbedder(dim=64)
    a, b, c = emb.embed(["sepsis early warning model", "sepsis early warning model", "datacenter chip"])
    assert np.allclose(a, b) and abs(float(np.linalg.norm(a)) - 1) < 1e-6
    assert float(a @ c) < float(a @ b)
    assert emb.embed([]).shape == (0, 64)


def test_novelty_scores_map_similarity_to_d():
    thresholds = (0.70, 0.76, 0.82, 0.88, 0.94)
    ref = np.array([[1.0, 0.0]], dtype=np.float32)
    vecs = np.array([[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]], dtype=np.float32)   # cos 1.0, 0.8, 0.0
    assert novelty_scores(vecs, ref, thresholds) == [0, 3, 5]
    assert novelty_scores(vecs, np.zeros((0, 0)), thresholds) == [5, 5, 5]
    assert novelty_scores(np.zeros((0, 2)), ref, thresholds) == []


def test_item_text_and_backend_factory(tmp_path):
    assert item_text("T", "x" * 5000).count("x") == 2000
    fast = get_embedder(Settings(_env_file=None, sotawhat_data_dir=tmp_path))
    assert isinstance(fast, FastEmbedder) and fast.name == "google/embeddinggemma-300m"
    assert str(fast.cache_dir).endswith("fastembed") and fast._model is None    # nothing downloaded yet
    assert isinstance(get_embedder(Settings(_env_file=None, embeddings_backend="hash")), HashEmbedder)
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_dedup_vectors.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.pipeline.dedup'`.

- [ ] **Passo 3: Criar `sotawhat/store/vectors.py`**

````python
# sotawhat/store/vectors.py
"""Local embeddings (SDD §6.3, D3): fastembed (ONNX on CPU, no per-call cost) and vector helpers.

Default model: google/embeddinggemma-300m (768-d, multilingual, 1.2 GB, downloaded once to
data/models/fastembed). On the reference machine (Ryzen 5 5500) it embeds ~2.4 items/s, about 1 min
for a day's items. BGE-M3, assumed in SDD v1.1, is not offered by fastembed 0.9.
"""
import hashlib
import re

import numpy as np

DEFAULT_MODEL = "google/embeddinggemma-300m"
# EmbeddingGemma expects a task prefix; "clustering" fits both novelty and the relevance classifier.
_PREFIXES = {"google/embeddinggemma-300m": "task: clustering | query: "}


def item_text(title, text, limit=2000) -> str:
    return f"{title}\n{(text or '')[:limit]}".strip()


def normalize(matrix) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.ndim == 1:
        matrix = matrix[None, :]
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class FastEmbedder:
    def __init__(self, model=DEFAULT_MODEL, cache_dir=None, batch_size=16):
        self.name = model
        self.cache_dir = cache_dir
        self.batch_size = batch_size
        self._model = None

    def _load(self):
        if self._model is None:
            from fastembed import TextEmbedding   # heavy import (onnxruntime); only when used
            self._model = TextEmbedding(self.name, cache_dir=str(self.cache_dir) if self.cache_dir else None)
        return self._model

    def embed(self, texts) -> np.ndarray:
        texts = list(texts)
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        prefix = _PREFIXES.get(self.name, "")
        vectors = self._load().embed([prefix + t for t in texts], batch_size=self.batch_size)
        return normalize(np.array(list(vectors), dtype=np.float32))


class HashEmbedder:
    """Deterministic bag-of-words hashing. Used by the tests and as an explicit offline backend
    (EMBEDDINGS_BACKEND=hash); far weaker than a real model."""

    def __init__(self, dim=256):
        self.dim = dim
        self.name = f"hash-{dim}"

    def embed(self, texts) -> np.ndarray:
        texts = list(texts)
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in re.findall(r"\w+", text.lower()):
                out[row, int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16) % self.dim] += 1.0
        return normalize(out) if texts else out


def get_embedder(settings):
    backend = (settings.embeddings_backend or "fastembed").lower()
    if backend == "hash":
        return HashEmbedder()
    if backend == "fastembed":
        return FastEmbedder(settings.embeddings_model, cache_dir=settings.models_dir / "fastembed")
    raise ValueError(f"EMBEDDINGS_BACKEND desconhecido: {settings.embeddings_backend}")


def novelty_scores(vectors, reference, thresholds) -> list:
    """D (0–5) per row of `vectors`: 5 minus how many thresholds the best cosine match reaches."""
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.size == 0:
        return []
    reference = np.asarray(reference, dtype=np.float32)
    if reference.size == 0:
        return [5] * len(vectors)
    best = (vectors @ reference.T).max(axis=1)
    return [5 - sum(1 for t in thresholds if score >= t) for score in best.tolist()]
````

- [ ] **Passo 4: Criar `sotawhat/pipeline/dedup.py`**

````python
# sotawhat/pipeline/dedup.py
"""Same-story dedup by near-identical titles (SDD §6.7, stage A).

Measured on 2026-11-07: for 5 local embedding models, cosine similarity does not separate "the same
story worded differently" from "same topic, different work" (gap from -0.05 to -0.12). So clusters are
formed only on near-identical titles, which covers the same paper arriving from PubMed, Crossref,
arXiv and HF. Embeddings feed the novelty score D instead. Cross-outlet news clustering (P2, newsletters)
will add an LLM judge for embedding-similar pairs.
"""
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

_STOP = {"the", "and", "for", "with", "from", "into", "via", "using", "based", "toward", "towards", "its",
         "are", "our", "new", "how", "what", "why", "uma", "para", "com", "por", "dos", "das", "nos", "nas",
         "que", "sobre", "entre"}


def norm_title(title) -> str:
    text = unicodedata.normalize("NFKD", (title or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def title_tokens(title) -> frozenset:
    return frozenset(w for w in norm_title(title).split() if len(w) > 2 and w not in _STOP)


def _numbers(norm) -> frozenset:
    return frozenset(w for w in norm.split() if any(ch.isdigit() for ch in w))


class _Seen:
    __slots__ = ("id", "rep", "norm", "tokens", "nums")

    def __init__(self, item_id, title, rep):
        self.id, self.rep = item_id, rep
        self.norm, self.tokens = norm_title(title), title_tokens(title)
        self.nums = _numbers(self.norm)


def _informative(norm, tokens) -> bool:
    return len(tokens) >= 4 or len(norm) >= 25   # "Editorial" twice is not the same story


def _same(norm, tokens, seen, ratio, jaccard) -> bool:
    if not _informative(norm, tokens) or not seen.norm:
        return False
    if norm == seen.norm:
        return True
    if _numbers(norm) != seen.nums:
        return False   # "Qwen3.8 technical report" vs "Qwen3.9 technical report", "Part 1" vs "Part 2"
    if len(tokens) >= 4 and len(seen.tokens) >= 4:
        overlap = len(tokens & seen.tokens) / len(tokens | seen.tokens)
        if overlap >= jaccard:
            return True
        if overlap < 0.5:
            return False
    return SequenceMatcher(None, norm, seen.norm).ratio() >= ratio


def same_title(a, b, ratio=0.92, jaccard=0.8) -> bool:
    return _same(norm_title(a), title_tokens(a), _Seen("b", b, "b"), ratio, jaccard)


class _Index:
    """Exact normalized titles + an inverted token index, so each title is compared only with
    titles that share at least half of its words."""

    def __init__(self):
        self.entries, self.exact, self.postings = [], {}, {}

    def add(self, entry):
        self.exact.setdefault(entry.norm, entry)
        position = len(self.entries)
        self.entries.append(entry)
        for token in entry.tokens:
            self.postings.setdefault(token, []).append(position)

    def candidates(self, tokens):
        counts = Counter()
        for token in tokens:
            counts.update(self.postings.get(token, ()))
        need = max(1, len(tokens) // 2)
        return [self.entries[i] for i, c in counts.items() if c >= need]


def find_duplicates(items, known, ratio=0.92, jaccard=0.8) -> dict:
    """items: new Items, in priority order. known: rows (id, title, cluster_id) already stored.
    Returns {item_id: representative_id} for every item that repeats a known item or an earlier one."""
    index = _Index()
    for row in known:
        index.add(_Seen(row[0], row[1], row[2] or row[0]))
    out = {}
    for it in items:
        norm, tokens = norm_title(it.title), title_tokens(it.title)
        informative = _informative(norm, tokens)
        match = index.exact.get(norm) if informative else None
        if match is None and informative:
            match = next((s for s in index.candidates(tokens) if _same(norm, tokens, s, ratio, jaccard)), None)
        if match is not None:
            out[it.id] = match.rep
            continue
        index.add(_Seen(it.id, it.title, it.id))
    return out
````

- [ ] **Passo 5: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `131 passed`.

- [ ] **Passo 6: Commit**

```bash
git add sotawhat/store/vectors.py sotawhat/pipeline/dedup.py tests/test_dedup_vectors.py
git commit -m "feat: local embeddings (EmbeddingGemma via fastembed) and same-story dedup by title"
```

---

## Tarefa 6: Classificador por perfil

Por quê (SDD §6.7, D9):
- Funciona como o Scholar Inbox: regressão logística sobre embeddings, treinada com os seus votos. 👍 e 🧪 contam como positivos; 👎, como negativo.
- Abaixo de 100 votos por perfil, nada é treinado e o LLM vê todos os itens.
- O retreino acontece quando o número de votos muda. As métricas de validação cruzada ficam em `classifier_models`.

**Files:**
- Create: `sotawhat/store/classifier.py`, `tests/test_classifier.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_classifier.py`:

````python
# tests/test_classifier.py
from datetime import datetime, timezone

from sotawhat.items import Item
from sotawhat.store.classifier import load_gate, refresh, train
from sotawhat.store.db import Store
from sotawhat.store.vectors import HashEmbedder

EMB = HashEmbedder(dim=64)
NOW = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)


def _seed(st, n_pos, n_neg, profile="medico", start=0):
    run = st.start_run("daily")
    items, votes = [], []
    for i in range(start, start + n_pos):
        items.append(Item(id=f"p{i}", kind="paper", source="pubmed", source_id="", url="", profile=profile,
                          title=f"deep learning radiology model {i}", text="hospital imaging ai validation"))
        votes.append((f"p{i}", "up" if i % 3 else "test"))
    for i in range(start, start + n_neg):
        items.append(Item(id=f"n{i}", kind="paper", source="pubmed", source_id="", url="", profile=profile,
                          title=f"asthma antibody phase trial {i}", text="randomized dosing placebo cohort"))
        votes.append((f"n{i}", "down"))
    st.upsert_items(items, run)
    st.save_embeddings(EMB.name, zip([it.id for it in items],
                                     EMB.embed([f"{it.title}\n{it.text}" for it in items])))
    for item_id, value in votes:
        st.add_feedback("item", item_id, value, "telegram")


def test_no_model_below_min_ratings_or_with_one_class(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        _seed(st, 30, 0)
        assert train(st, "medico", EMB.name, tmp_path / "models", min_ratings=20) is None   # one class only
        _seed(st, 0, 5)
        assert train(st, "medico", EMB.name, tmp_path / "models", min_ratings=100) is None  # 35 < 100


def test_trained_gate_ranks_positives_first(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        _seed(st, 60, 50)
        info = train(st, "medico", EMB.name, tmp_path / "models", min_ratings=100, now=NOW)
        assert info["version"] == "medico-20261108T100000"
        assert info["metrics"]["n"] == 110 and info["metrics"]["f1"] >= 0.9
        gate = load_gate(st, "medico", EMB.name)
        good, bad = gate.score(EMB.embed(["deep learning radiology model for hospital imaging",
                                          "asthma antibody dosing trial"]))
        assert good > 0.5 > bad


def test_refresh_retrains_only_when_votes_change(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        _seed(st, 60, 50)
        gates = refresh(st, ["medico", "geral"], EMB.name, tmp_path / "models", min_ratings=100, now=NOW)
        assert set(gates) == {"medico"}
        assert refresh(st, ["medico"], EMB.name, tmp_path / "models", min_ratings=100,
                       now=datetime(2026, 11, 9, tzinfo=timezone.utc))["medico"].version == "medico-20261108T100000"
        st.add_feedback("item", "n1", "up", "telegram")     # a changed vote is not a new vote: count stays 110
        st.add_feedback("item", "p0", "down", "telegram")
        _seed(st, 1, 0, start=500)                            # one more labeled item -> retrain
        later = datetime(2026, 11, 10, tzinfo=timezone.utc)
        assert refresh(st, ["medico"], EMB.name, tmp_path / "models", 100, now=later)["medico"].version \
            == "medico-20261110T000000"
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_classifier.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.store.classifier'`.

- [ ] **Passo 3: Criar `sotawhat/store/classifier.py`**

````python
# sotawhat/store/classifier.py
"""Per-profile relevance classifier (SDD §6.7, D9): logistic regression over the local embeddings,
trained on the user's votes (👍/🧪 positive, 👎 negative). Below `min_ratings` votes nothing is trained
and the LLM sees every item (cold start); afterwards the classifier decides which items reach it."""
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

POSITIVE = {"up", "test"}
NEGATIVE = {"down"}


@dataclass
class Gate:
    version: str
    model: object

    def score(self, vectors) -> np.ndarray:
        return self.model.predict_proba(np.asarray(vectors, dtype=np.float32))[:, 1]


def training_data(store, profile, embed_model):
    votes = {i: v for i, v in store.item_votes(profile=profile).items() if v in POSITIVE | NEGATIVE}
    ids, matrix = store.load_embeddings(embed_model, ids=list(votes))
    labels = np.array([1 if votes[i] in POSITIVE else 0 for i in ids], dtype=int)
    return ids, matrix, labels, len(votes)


def train(store, profile, embed_model, models_dir, min_ratings=100, now=None):
    """Train, cross-validate, save and register a classifier; None when there is not enough data."""
    ids, X, y, n_votes = training_data(store, profile, embed_model)
    if len(ids) < min_ratings or len(set(y.tolist())) < 2:
        return None
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    model = LogisticRegression(class_weight="balanced", max_iter=2000)
    metrics = {"n": int(len(y)), "positives": int(y.sum()), "votes": n_votes}
    folds = min(5, int(np.bincount(y).min()))
    if folds >= 2:
        proba = cross_val_predict(model, X, y, cv=StratifiedKFold(folds, shuffle=True, random_state=13),
                                  method="predict_proba")[:, 1]
        p, r, f1, _ = precision_recall_fscore_support(y, (proba >= 0.5).astype(int), average="binary",
                                                      zero_division=0)
        metrics.update(precision=round(float(p), 3), recall=round(float(r), 3), f1=round(float(f1), 3),
                       auc=round(float(roc_auc_score(y, proba)), 3))
    model.fit(X, y)
    version = f"{profile}-{(now or datetime.now(timezone.utc)).strftime('%Y%m%dT%H%M%S')}"
    path = Path(models_dir) / f"classifier-{version}.pkl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(model))
    store.record_classifier(version, profile, embed_model, int(len(y)), metrics, path)
    return {"version": version, "metrics": metrics}


def load_gate(store, profile, embed_model):
    row = store.latest_classifier(profile, embed_model)
    if row is None or not Path(row["path"]).exists():
        return None
    return Gate(row["version"], pickle.loads(Path(row["path"]).read_bytes()))   # our own file in data/models


def refresh(store, profiles, embed_model, models_dir, min_ratings=100, now=None) -> dict:
    """Retrain a profile whenever its vote count changed since the last model; return the gates."""
    import json

    gates = {}
    for profile in profiles:
        latest = store.latest_classifier(profile, embed_model)
        trained_votes = json.loads(latest["metrics_json"] or "{}").get("votes") if latest else None
        current = len([v for v in store.item_votes(profile=profile).values() if v in POSITIVE | NEGATIVE])
        if current >= min_ratings and current != trained_votes:
            train(store, profile, embed_model, models_dir, min_ratings, now)
        gate = load_gate(store, profile, embed_model)
        if gate is not None:
            gates[profile] = gate
    return gates
````

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `134 passed`. A primeira importação do `scikit-learn` leva ~2 s nesta máquina.

- [ ] **Passo 5: Commit**

```bash
git add sotawhat/store/classifier.py tests/test_classifier.py
git commit -m "feat: per-profile relevance classifier trained on votes"
```

---

## Tarefa 7: Triagem em dois estágios

Pontos de projeto:
- **Ordem do estágio A:** silêncio → mesma história (a cópia com mais texto representa a história) → embeddings e D → classificador, quando houver.
- **Orçamento:** antes do LLM, o run calcula quantos itens cabem em 80% do que resta do teto diário, usando o custo médio real das últimas triagens; sem histórico, US$ 0,001 por item. Os que não cabem ficam para os próximos runs, por até `backlog_days`.
- **Concorrência:** 6 chamadas por padrão. `BudgetExceeded` ou falta de créditos cancelam o que ainda não começou.
- **Falhas:** um item que falha em todos os modelos vira `error` e é retentado até 3 vezes.
- **Decisão:** `decide()` aplica a rubrica. Exclusões duras rejeitam. "IA genérica sem ponte" com A ≥ 4 vai para o radar; todo o resto segue a fórmula.
- **Dado de paciente identificável:** o texto é apagado do banco.
- **Embeddings indisponíveis** (download falhou): a triagem segue com D = 5 e sem classificador, e o digest avisa.

**Files:**
- Create: `sotawhat/pipeline/triage.py`, `tests/test_triage.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_triage.py`:

````python
# tests/test_triage.py
import re
import threading
from datetime import datetime, timezone

import numpy as np

from sotawhat.configfiles import Mutes, Rubric
from sotawhat.items import Item
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure, StructuredResult
from sotawhat.llm.schemas import TriageOutput
from sotawhat.pipeline.triage import decide, item_message, run_triage, system_prompt
from sotawhat.store.db import Store
from sotawhat.store.vectors import HashEmbedder

NOW = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)
RUBRIC = Rubric(concurrency=3)


def out(**kw):
    base = dict(summary_pt="Resumo.", hard_exclusion="none", inclusion_rules=[4], frontier_ai=3,
                medical_applicability=3, actionability=3, domains=["A03"], problem_types=["B02"],
                techniques=["C05"], evidence_stage="D1", stakeholders=["medico"], br_applicability="F1",
                cfm_risk="medio", substance=2, audience=["clinico"], vendor_only=False, reason_pt="Motivo.",
                why_it_matters_pt="Importa para o hospital.")
    base.update(kw)
    return TriageOutput(**base)


class FakeGateway:
    """Answers by the first word of the title; raises for 'fail' and 'budget' titles."""

    def __init__(self, answers, budget_day=None):
        self.answers = answers
        self.budget_day = budget_day
        self.calls = []
        self._lock = threading.Lock()

    def structured_call(self, task, messages, output_model, models=None):
        title = re.search(r"^title: (.*)$", messages[1]["content"], re.M).group(1)
        with self._lock:
            self.calls.append(title)
        key = title.split()[0].lower()
        if key == "fail":
            raise LLMFailure("triage: every model failed")
        if key == "budget":
            raise BudgetExceeded("daily LLM budget of US$ 1.00 reached")
        return StructuredResult(output=self.answers.get(key, out()), model="deepseek/deepseek-v4.1-flash-1017",
                                provider="DeepInfra", cost_usd=0.0005, latency_ms=10, attempts=1,
                                first_try_valid=True)


def _item(n, title, profile="medico", source="pubmed", text=None):
    return Item(id=f"pmid:{n}", kind="paper", source=source, source_id=str(n), title=title,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", authors=["Ana", "Bia", "Caio", "Davi"],
                published_at="2026-11-07", text=text if text is not None else f"{title} abstract text",
                profile=profile)


def _store(tmp_path, items):
    st = Store(tmp_path / "insight.db")
    run = st.start_run("daily")
    st.upsert_items(items, run)
    return st, run


def test_decide_follows_the_rubric():
    assert decide(out(frontier_ai=4, medical_applicability=5, actionability=3), 4, RUBRIC, "pubmed") == ("main", 4.15)
    assert decide(out(frontier_ai=5, medical_applicability=1, actionability=4), 5, RUBRIC, "arxiv")[0] == "radar"
    assert decide(out(frontier_ai=5, medical_applicability=0, hard_exclusion="generic_ai_no_bridge"), 5,
                  RUBRIC, "rss:x")[0] == "radar"
    assert decide(out(frontier_ai=3, medical_applicability=0, hard_exclusion="generic_ai_no_bridge"), 5,
                  RUBRIC, "rss:x")[0] == "reject"
    assert decide(out(frontier_ai=0, medical_applicability=5, hard_exclusion="clinical_without_ai"), 5,
                  RUBRIC, "pubmed")[0] == "reject"
    assert decide(out(frontier_ai=4, medical_applicability=1, actionability=5), 5, RUBRIC, "arxiv")[0] == "radar"
    # B below min_b never reaches "main", whatever the total
    assert decide(out(frontier_ai=5, medical_applicability=1, actionability=5), 5,
                  Rubric(radar_min_a=6), "x") == ("reject", 3.6)
    weak = Rubric(weak_sources=("rss:*",))
    assert decide(out(vendor_only=True), 5, weak, "rss:vendor")[1] == round(3 * 0.9 + 0.5 - 1.0, 2)


def test_prompt_is_fully_rendered_and_item_message_is_bounded():
    prompt = system_prompt()
    assert "{{" not in prompt and "A03 radiologia/imagem" in prompt and "C19 modelos pequenos" in prompt
    msg = item_message(_item(1, "T", text="x" * 9000), max_chars=100)
    assert msg.split("<<<")[1].count("x") == 100 and "Ana, Bia, Caio et al." in msg and "pubmed.ncbi.nlm.nih.gov" in msg
    assert "(sem texto: só o título)" in item_message(_item(2, "T", text=""))


def test_run_triage_end_to_end(tmp_path):
    items = [_item(1, "Radiology foundation model validated in 12 hospitals"),
             _item(2, "Radiology foundation model validated in 12 hospitals.", source="crossref", text="short"),
             _item(3, "Frontier video model with long context", profile="geral", source="arxiv"),
             _item(4, "Asthma antibody phase III trial"),
             _item(5, "Webinar: AI in healthcare", source="rss:vendor"),
             _item(6, "Patient case report with identifiable data")]
    answers = {"radiology": out(frontier_ai=4, medical_applicability=5, actionability=3),
               "frontier": out(frontier_ai=5, medical_applicability=1, actionability=4),
               "asthma": out(frontier_ai=0, medical_applicability=1, hard_exclusion="clinical_without_ai"),
               "patient": out(hard_exclusion="identifiable_patient_data")}
    st, run = _store(tmp_path, items)
    gw = FakeGateway(answers)
    stats = run_triage(st, run, gw, RUBRIC, Mutes(title_terms=("webinar",)), HashEmbedder(64), now=NOW)
    assert (stats.candidates, stats.muted, stats.duplicates, stats.triaged) == (6, 1, 1, 4)
    assert (stats.main, stats.radar, stats.rejected, stats.errors) == (1, 1, 2, 0)
    assert abs(stats.cost_usd - 0.002) < 1e-9
    rows = {r["item_id"]: r for r in st.conn.execute("SELECT * FROM triage")}
    assert rows["pmid:5"]["decision"] == "muted" and "webinar" in rows["pmid:5"]["reason"]
    assert rows["pmid:2"]["decision"] == "duplicate" and st.cluster_sources("pmid:1") == ["crossref", "pubmed"]
    main = rows["pmid:1"]
    assert main["decision"] == "main" and main["prompt_version"] == "triage_v1" and main["model"].startswith("deepseek")
    assert main["why_it_matters_pt"] == "Importa para o hospital." and '"A03"' in main["tags_json"]
    assert rows["pmid:4"]["why_it_matters_pt"] == ""            # excluded items carry no "why it matters"
    assert st.get_items(["pmid:6"])[0]["text"] is None            # patient data is not kept
    assert len(gw.calls) == 4 and st.embedded_ids("hash-64", ["pmid:1", "pmid:3"]) == {"pmid:1", "pmid:3"}
    assert run_triage(st, run, gw, RUBRIC, Mutes(), HashEmbedder(64), now=NOW).candidates == 0   # idempotent
    st.close()


def test_budget_cap_defers_items_to_the_next_run(tmp_path):
    st, run = _store(tmp_path, [_item(n, f"Paper number {n} on sepsis prediction") for n in range(1, 6)])
    for _ in range(3):
        st.record_llm_call(task="triage", requested_model="m", status="ok", cost_usd=0.10)   # avg US$ 0.10/item
    gw = FakeGateway({}, budget_day=1.0)       # 0.8 * 1.00 - 0.30 spent = 0.50 -> 5 items fit
    st.record_llm_call(task="other", requested_model="m", status="ok", cost_usd=0.30)   # now 0.20 -> 2 items
    stats = run_triage(st, run, gw, RUBRIC, Mutes(), None, now=datetime.now(timezone.utc))
    assert (stats.triaged, stats.deferred) == (2, 3) and "orçamento" in stats.stopped
    assert len(st.triage_candidates("2000-01-01")) == 3
    st.close()


def test_budget_stop_and_failures_do_not_break_the_run(tmp_path):
    items = [_item(1, "Budget breaker paper"), _item(2, "Fail paper"), _item(3, "Good paper on triage")]
    st, run = _store(tmp_path, items)
    stats = run_triage(st, run, FakeGateway({}), Rubric(concurrency=1), Mutes(), None, now=NOW)
    assert stats.stopped and "budget" in stats.stopped
    assert stats.errors + stats.triaged + stats.deferred == 3
    assert st.conn.execute("SELECT COUNT(*) FROM triage WHERE decision = 'error'").fetchone()[0] == stats.errors
    st.close()


def test_without_llm_everything_waits_and_gate_filters(tmp_path):
    items = [_item(n, f"Item {n} about sepsis models in intensive care", text=f"sepsis {'x' * n}") for n in range(1, 6)]
    st, run = _store(tmp_path, items)
    assert run_triage(st, run, None, RUBRIC, Mutes(), HashEmbedder(64), now=NOW).deferred == 5

    class Gate:
        version = "medico-test"

        def score(self, vectors):
            return np.linspace(0.9, 0.1, len(vectors))

    stats = run_triage(st, run, FakeGateway({}), Rubric(classifier_top_n=2), Mutes(), HashEmbedder(64),
                       gates={"medico": Gate()}, now=NOW)
    assert (stats.gated, stats.triaged) == (3, 2)
    gated = st.conn.execute("SELECT pre_score, classifier_version FROM triage WHERE decision='gated'").fetchall()
    assert len(gated) == 3 and all(r[1] == "medico-test" and r[0] < 0.9 for r in gated)
    st.close()
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_triage.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.pipeline.triage'`.

- [ ] **Passo 3: Criar `sotawhat/pipeline/triage.py`**

````python
# sotawhat/pipeline/triage.py
"""Two-stage triage (SDD §6.7).

Stage A, no LLM: mute filters, same-story dedup (near-identical titles), local embeddings, novelty (D)
and, once a profile has enough votes, the classifier gate. Stage B: the LLM rubric with strict JSON for
the survivors, concurrently, within 80% of what is left of the daily budget. Items that do not fit stay
undecided and are retried by the next runs for `backlog_days`.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import numpy as np

from sotawhat import taxonomy as tx
from sotawhat.items import from_row
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import TriageOutput
from sotawhat.pipeline.dedup import find_duplicates
from sotawhat.store.vectors import item_text, novelty_scores

PROMPT_VERSION = "triage_v1"
HARD_REJECT = {"clinical_without_ai", "marketing_no_substance", "identifiable_patient_data"}
DEFAULT_COST_PER_ITEM = 0.001   # US$, until the ledger has real triage calls (≈ 0.0005 expected)
log = logging.getLogger("sotawhat.triage")


@dataclass
class TriageStats:
    candidates: int = 0
    muted: int = 0
    duplicates: int = 0
    gated: int = 0
    deferred: int = 0      # left for the next run (budget cap, stop, no LLM)
    triaged: int = 0
    main: int = 0
    radar: int = 0
    rejected: int = 0
    errors: int = 0
    llm: bool = True
    stopped: str | None = None
    cost_usd: float = 0.0
    warnings: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def system_prompt() -> str:
    text = load_prompt(PROMPT_VERSION)
    for token, table in {"DOMAINS": tx.DOMAINS, "PROBLEMS": tx.PROBLEMS, "TECHNIQUES": tx.TECHNIQUES,
                         "EVIDENCE": tx.EVIDENCE, "STAKEHOLDERS": tx.STAKEHOLDERS, "BR": tx.BR_APPLICABILITY,
                         "CFM": tx.CFM_RISK, "AUDIENCE": tx.AUDIENCE}.items():
        text = text.replace("{{" + token + "}}", tx.render(table))
    return text


def item_message(item, max_chars=8000) -> str:
    text = (item.text or "").strip() or "(sem texto: só o título)"
    authors = ", ".join(item.authors[:3]) + (" et al." if len(item.authors) > 3 else "")
    return (f"Item to triage\ntitle: {item.title}\nsource: {item.source} (profile {item.profile or '?'})\n"
            f"published: {item.published_at or '?'}\nurl host: {urlsplit(item.url or '').netloc or '?'}\n"
            f"authors: {authors or '?'}\ntext:\n<<<\n{text[:max_chars]}\n>>>")


def messages_for(item, rubric, system=None) -> list:
    return [{"role": "system", "content": system or system_prompt()},
            {"role": "user", "content": item_message(item, rubric.max_text_chars)}]


def decide(out, novelty, rubric, source) -> tuple:
    """-> (decision, total). Score and thresholds from the rubric; hard exclusions first; frontier AI
    without a medical bridge (A ≥ radar_min_a, B ≤ radar_max_b) goes to the radar."""
    a, b, c = out.frontier_ai, out.medical_applicability, out.actionability
    w = rubric.weights
    total = w["A"] * a + w["B"] * b + w["C"] * c + w["D"] * novelty
    if out.vendor_only:
        total -= rubric.vendor_only_penalty
    if any(source == s or (s.endswith("*") and source.startswith(s[:-1])) for s in rubric.weak_sources):
        total -= rubric.weak_source_penalty
    total = round(max(total, 0.0), 2)
    radar = a >= rubric.radar_min_a and b <= rubric.radar_max_b
    if out.hard_exclusion in HARD_REJECT:
        return "reject", total
    if out.hard_exclusion == "generic_ai_no_bridge":
        return ("radar" if radar else "reject"), total
    if total >= rubric.min_total and b >= rubric.min_b:
        return "main", total
    return ("radar" if radar else "reject"), total


def _budget_cap(store, gateway, now):
    if store is None or gateway is None or gateway.budget_day is None:
        return None
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    room = 0.8 * gateway.budget_day - store.llm_cost_since(day_start)
    per_item = store.avg_llm_cost("triage") or DEFAULT_COST_PER_ITEM
    return max(0, int(room / per_item))


def _stage_a(store, run_id, items, rubric, mutes, embedder, gates, now, stats):
    survivors = []
    for it in items:
        reason = mutes.match(it)
        if reason:
            store.record_triage(it.id, run_id, "muted", reason=reason)
            stats.muted += 1
        else:
            survivors.append(it)

    window = (now - timedelta(days=rubric.novelty_window_days)).isoformat(timespec="seconds")
    pending = {it.id for it in survivors}
    known = [row for row in store.titles_since(window) if row["id"] not in pending]
    survivors.sort(key=lambda it: -len(it.text or ""))       # the richest copy represents the story
    dups = find_duplicates(survivors, known)
    for it in survivors:
        if it.id in dups:
            store.join_cluster(it.id, dups[it.id])
            store.record_triage(it.id, run_id, "duplicate", reason=f"mesma história que {dups[it.id]}")
            stats.duplicates += 1
    survivors = [it for it in survivors if it.id not in dups]

    novelty, vectors = {}, {}
    if embedder is not None and survivors:
        try:
            have = store.embedded_ids(embedder.name, [it.id for it in survivors])
            missing = [it for it in survivors if it.id not in have]
            if missing:
                texts = [item_text(it.title, it.text) for it in missing]
                store.save_embeddings(embedder.name, zip([it.id for it in missing], embedder.embed(texts)))
            ids, matrix = store.load_embeddings(embedder.name, ids=[it.id for it in survivors])
            _, reference = store.load_embeddings(embedder.name, since_iso=window, exclude=pending)
            novelty = dict(zip(ids, novelty_scores(matrix, reference, rubric.novelty_thresholds)))
            vectors = dict(zip(ids, matrix))
        except Exception as exc:  # noqa: BLE001 - e.g. the model download failed: triage still runs
            log.warning("embeddings: %s", exc)
            stats.warnings.append(f"embeddings indisponíveis ({type(exc).__name__}): D=5 e sem classificador hoje")

    pre, gated = {}, set()
    for profile, gate in (gates or {}).items():
        group = [it for it in survivors if it.profile == profile and it.id in vectors]
        if not group:
            continue
        probs = gate.score(np.stack([vectors[it.id] for it in group]))
        ranked = sorted(zip(group, probs.tolist()), key=lambda pair: -pair[1])
        for rank, (it, p) in enumerate(ranked):
            pre[it.id] = (p, gate.version)
            if rank >= rubric.classifier_top_n:
                store.record_triage(it.id, run_id, "gated", pre_score=p, classifier_version=gate.version,
                                    reason=f"classificador {gate.version}: p={p:.2f}, "
                                           f"fora do top {rubric.classifier_top_n}")
                gated.add(it.id)
                stats.gated += 1
    survivors = [it for it in survivors if it.id not in gated]
    return survivors, novelty, pre


def run_triage(store, run_id, gateway, rubric, mutes, embedder=None, gates=None, now=None) -> TriageStats:
    now = now or datetime.now(timezone.utc)
    stats = TriageStats(llm=gateway is not None)
    since = (now - timedelta(days=rubric.backlog_days)).isoformat(timespec="seconds")
    items = [from_row(row) for row in store.triage_candidates(since)][:rubric.max_items_per_run]
    stats.candidates = len(items)
    survivors, novelty, pre = _stage_a(store, run_id, items, rubric, mutes, embedder, gates, now, stats)
    if gateway is None:
        stats.deferred = len(survivors)
        return stats

    # medico first, then by classifier score, newest first
    survivors.sort(key=lambda it: (it.profile != "medico", -(pre.get(it.id, (0.5,))[0])))
    cap = _budget_cap(store, gateway, now)
    if cap is not None and cap < len(survivors):
        stats.deferred += len(survivors) - cap
        stats.stopped = f"orçamento: {cap} de {len(survivors)} itens triados neste run"
        survivors = survivors[:cap]

    system = system_prompt()
    with ThreadPoolExecutor(max_workers=max(1, rubric.concurrency)) as pool:
        futures = {pool.submit(gateway.structured_call, "triage", messages_for(it, rubric, system),
                               TriageOutput): it for it in survivors}
        for future in as_completed(futures):
            it = futures[future]
            if future.cancelled():
                stats.deferred += 1
                continue
            try:
                res = future.result()
            except (BudgetExceeded, InsufficientCredits) as exc:
                stats.stopped = str(exc)
                stats.deferred += 1
                for pending_future in futures:
                    pending_future.cancel()
                continue
            except LLMFailure as exc:
                store.record_triage(it.id, run_id, "error", reason=str(exc)[:300], prompt_version=PROMPT_VERSION)
                stats.errors += 1
                continue
            out = res.output
            decision, total = decide(out, novelty.get(it.id, 5), rubric, it.source)
            p, version = pre.get(it.id, (None, None))
            store.record_triage(
                it.id, run_id, decision, total=total, reason=out.reason_pt, summary_pt=out.summary_pt,
                why_it_matters_pt=out.why_it_matters_pt if decision != "reject" else "",
                scores={"A": out.frontier_ai, "B": out.medical_applicability, "C": out.actionability,
                        "D": novelty.get(it.id, 5)},
                tags=out.tags(), pre_score=p, classifier_version=version, model=res.model,
                prompt_version=PROMPT_VERSION, cost_usd=res.cost_usd)
            if out.hard_exclusion == "identifiable_patient_data":
                store.redact_item(it.id)
            stats.triaged += 1
            stats.cost_usd += res.cost_usd
            if decision == "main":
                stats.main += 1
            elif decision == "radar":
                stats.radar += 1
            else:
                stats.rejected += 1
    log.info("triage %s", stats.as_dict())
    return stats
````

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `140 passed`.

- [ ] **Passo 5: Commit**

```bash
git add sotawhat/pipeline/triage.py tests/test_triage.py
git commit -m "feat: two-stage triage (mutes, same-story, novelty, classifier gate, LLM rubric within budget)"
```

---

## Tarefa 8: Digest e Telegram com botões

Pontos de projeto (SDD §6.11):
- **Ordenação:** principais por total, com desempate por B; radar por A. Os aprovados além de `main_limit` aparecem só no arquivo do dia.
- **Mensagens no Telegram:**
  - um cabeçalho com notificação: contagens, custo, avisos e alertas, que são falhas a partir da 3ª seguida;
  - uma mensagem silenciosa por item principal, com 👍 👎 🧪;
  - uma mensagem de radar com botões numerados.
- **Quando não envia nada:** se nada foi aprovado e nada quebrou.
- **Botões:** cada um carrega `f:<sha1[:10] do id>:<u|d|t>` (≤ 64 bytes), e a tabela `deliveries` liga a chave ao item e à mensagem.
- **`TelegramNotifier`:** respeita o `retry_after` do 429 e nunca expõe o token.

**Files:**
- Modify: `sotawhat/notify/telegram.py` (substituir o conteúdo inteiro), `sotawhat/pipeline/daily.py`
- Create: `sotawhat/pipeline/deliver.py`, `tests/test_deliver.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_deliver.py`:

````python
# tests/test_deliver.py
import json

import httpx

from sotawhat.configfiles import Rubric
from sotawhat.items import Item
from sotawhat.notify.telegram import TelegramError, TelegramNotifier
from sotawhat.pipeline.daily import DailyReport
from sotawhat.pipeline.deliver import (build_digest, item_key, keyboard, render_html, render_markdown, send_digest,
                                       telegram_messages, write_files)
from sotawhat.pipeline.triage import TriageStats
from sotawhat.store.db import Store

TOKEN = "123456:SECRET-TOKEN"


class FakeBot:
    def __init__(self, updates=()):
        self.chat_id = "42"
        self.sent, self.answers, self.edits = [], [], []
        self.updates = list(updates)

    def send_message(self, text, reply_markup=None, disable_notification=False):
        self.sent.append((text, reply_markup, disable_notification))
        return {"message_id": 100 + len(self.sent)}

    def get_updates(self, offset=None, timeout=0):
        batch = [u for u in self.updates if offset is None or u["update_id"] >= offset]
        self.updates = []
        return batch

    def answer_callback(self, callback_id, text=""):
        self.answers.append(text)

    def edit_reply_markup(self, chat_id, message_id, markup):
        self.edits.append((chat_id, message_id, markup))


def _seed(st):
    run = st.start_run("daily")
    items = [Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"Título <{n}>",
                  url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", profile="medico") for n in range(1, 5)]
    st.upsert_items(items, run)
    rows = [("pmid:1", "main", 4.2, {"A": 4, "B": 5, "C": 3, "D": 5}),
            ("pmid:2", "main", 3.5, {"A": 3, "B": 4, "C": 3, "D": 5}),
            ("pmid:3", "radar", 2.9, {"A": 5, "B": 1, "C": 4, "D": 5}),
            ("pmid:4", "reject", 1.0, {"A": 0, "B": 1, "C": 0, "D": 5})]
    for item_id, decision, total, scores in rows:
        st.record_triage(item_id, run, decision, total=total, scores=scores, summary_pt=f"Resumo de {item_id}.",
                         why_it_matters_pt="Útil para o PS.", tags={"domains": ["A06"], "techniques": ["C02"],
                                                                    "evidence_stage": "D2"})
    report = DailyReport(run_id=run, day="2026-11-08", collected={"medico": 4}, new_items=items,
                         failing={"semantic_scholar": (3, "429 Too Many Requests"), "arxiv": (1, "timeout")},
                         cost_usd=0.0123, triage=TriageStats(triaged=4, main=2, radar=1, rejected=1, deferred=2))
    return run, report



def test_digest_ranks_limits_and_renders(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run, report = _seed(st)
        d = build_digest(st, report, Rubric(main_limit=1))
        assert [e.item_id for e in d.main] == ["pmid:1"] and [e.item_id for e in d.extra] == ["pmid:2"]
        assert [e.item_id for e in d.radar] == ["pmid:3"] and d.worth_sending
        assert "principais 1 · radar 1 · custo US$ 0,01" in d.stats_line
        assert any("2 itens ficaram" in n for n in d.notes) and any("+1 aprovados" in n for n in d.notes)
        md = render_markdown(d)
        assert "### 1. [Título <1>](https://pubmed.ncbi.nlm.nih.gov/1/)" in md and "**4,20** · A4 B5 C3 D5" in md
        assert "emergência/triagem" in md and "3ª falha seguida" in md and "## Também aprovados" in md
        page = render_html(d)
        assert "Título &lt;1&gt;" in page and "<script" not in page and 'lang="pt-BR"' in page
        md_path, html_path = write_files(d, tmp_path / "digests")
        assert md_path.name == "2026-11-08.md" and html_path.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_nothing_relevant_and_no_alerts_sends_nothing(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        report = DailyReport(run_id=run, day="2026-11-08", failing={"arxiv": (1, "timeout")},
                             triage=TriageStats())
        d = build_digest(st, report, Rubric())
        assert not d.worth_sending and "Nada relevante hoje." in render_markdown(d)


def test_telegram_messages_buttons_and_delivery_records(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run, report = _seed(st)
        d = build_digest(st, report, Rubric())
        messages = telegram_messages(d)
        assert len(messages) == 4 and messages[0]["silent"] is False and all(m["silent"] for m in messages[1:])
        assert "⚠️ <b>Alertas</b>: semantic_scholar (3ª falha seguida)" in messages[0]["text"]
        assert "falha hoje: arxiv" in messages[0]["text"] and "Título &lt;1&gt;" in messages[1]["text"]
        bot = FakeBot()
        assert send_digest(bot, st, d, run, pause=0) == 4
        main_markup = bot.sent[1][1]["inline_keyboard"]
        key = item_key("pmid:1")
        assert main_markup == [[{"text": "👍", "callback_data": f"f:{key}:u"},
                                {"text": "👎", "callback_data": f"f:{key}:d"},
                                {"text": "🧪", "callback_data": f"f:{key}:t"}]]
        assert bot.sent[3][1]["inline_keyboard"][0][0]["text"] == "👍"   # one radar item: plain buttons
        row = st.delivery_by_key(key)
        assert (row["item_id"], row["message_id"], row["chat_id"]) == ("pmid:1", 102, "42")


def test_keyboard_marks_the_chosen_vote():
    rows = [{"key": "a" * 10, "position": 1, "item_id": "x"}, {"key": "b" * 10, "position": 2, "item_id": "y"}]
    kb = keyboard(rows, {"y": "down"})["inline_keyboard"]
    assert [b["text"] for b in kb[0]] == ["1 👍", "1 👎", "2 👍", "✅2 👎"]


def test_notifier_buttons_updates_and_flood_control():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append((request.url.path.rsplit("/", 1)[-1], body))
        if len(calls) == 1:
            return httpx.Response(429, json={"ok": False, "parameters": {"retry_after": 3}})
        if calls[-1][0] == "getUpdates":
            return httpx.Response(200, json={"ok": True, "result": []})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 9}})

    waits = []
    bot = TelegramNotifier(TOKEN, "42", transport=httpx.MockTransport(handler), sleep=waits.append)
    assert bot.send_message("oi", reply_markup={"inline_keyboard": []}, disable_notification=True) == {"message_id": 9}
    assert waits == [3.0] and calls[1][1]["disable_notification"] is True
    assert bot.get_updates(offset=10, timeout=0) == [] and calls[2][1] == {
        "timeout": 0, "allowed_updates": ["callback_query", "message"], "offset": 10}
    bot.answer_callback("c1", "ok")
    bot.edit_reply_markup(42, 9, {"inline_keyboard": []})
    assert [c[0] for c in calls[3:]] == ["answerCallbackQuery", "editMessageReplyMarkup"]


def test_notifier_error_keeps_status_without_token():
    bot = TelegramNotifier(TOKEN, "42", transport=httpx.MockTransport(
        lambda r: httpx.Response(409, json={"ok": False, "description": "Conflict"})))
    try:
        bot.get_updates()
    except TelegramError as exc:
        assert exc.status == 409 and "SECRET" not in str(exc)
    else:
        raise AssertionError("expected TelegramError")
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_deliver.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.pipeline.deliver'`.

- [ ] **Passo 3: Substituir `sotawhat/notify/telegram.py`**

````python
# sotawhat/notify/telegram.py
"""Telegram Bot API client (SDD §7.7): messages with inline buttons, updates (votes and links) and
button refresh. The bot token never appears in raised errors."""
import html
import time

import httpx

API = "https://api.telegram.org"
LIMIT = 4096


class TelegramError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def esc(text) -> str:
    return html.escape(str(text), quote=False)


def esc_attr(text) -> str:
    return html.escape(str(text), quote=True)


def chunk(text, limit=LIMIT) -> list:
    """Split on line boundaries (HTML tags never span lines here); hard-split overlong lines."""
    parts, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            parts.append(current)
            current = line
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


class TelegramNotifier:
    def __init__(self, token, chat_id, transport=None, timeout=30.0, sleep=time.sleep):
        self.token = token
        self.chat_id = chat_id
        self._http = httpx.Client(base_url=f"{API}/bot{token}", timeout=timeout, transport=transport)
        self._sleep = sleep

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def _call(self, method, payload=None, timeout=None):
        for attempt in range(2):
            try:
                response = self._http.post(f"/{method}", json=payload or {},
                                           timeout=timeout or httpx.USE_CLIENT_DEFAULT)
            except httpx.TransportError as exc:
                raise TelegramError(f"{method}: transport error {type(exc).__name__}") from None
            try:
                data = response.json()
            except ValueError:
                data = {}
            if response.status_code == 429 and attempt == 0:   # flood control: wait as told, once
                self._sleep(min(float((data.get("parameters") or {}).get("retry_after", 1)), 30.0))
                continue
            if response.status_code != 200 or not data.get("ok"):
                raise TelegramError(f"{method}: HTTP {response.status_code} {data.get('description', '')}".strip(),
                                    status=response.status_code)
            return data.get("result")

    def send(self, text, parse_mode="HTML") -> int:
        parts = chunk(text)
        for part in parts:
            self._call("sendMessage", {"chat_id": self.chat_id, "text": part, "parse_mode": parse_mode,
                                       "disable_web_page_preview": True})
        return len(parts)

    def send_message(self, text, reply_markup=None, disable_notification=False, parse_mode="HTML") -> dict:
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode,
                   "disable_web_page_preview": True}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if disable_notification:
            payload["disable_notification"] = True
        return self._call("sendMessage", payload) or {}

    def get_updates(self, offset=None, timeout=0, allowed_updates=("callback_query", "message")) -> list:
        payload = {"timeout": timeout, "allowed_updates": list(allowed_updates)}
        if offset is not None:
            payload["offset"] = offset
        return self._call("getUpdates", payload, timeout=timeout + 15) or []

    def answer_callback(self, callback_id, text="") -> None:
        self._call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})

    def edit_reply_markup(self, chat_id, message_id, reply_markup) -> None:
        self._call("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": message_id,
                                              "reply_markup": reply_markup})

    def get_me(self) -> dict:
        return self._call("getMe") or {}
````

- [ ] **Passo 4: Criar `sotawhat/pipeline/deliver.py`**

````python
# sotawhat/pipeline/deliver.py
"""Daily digest (SDD §6.11): ranked selection, Markdown + HTML files (always) and Telegram messages
with 👍/👎/🧪 buttons. When nothing was approved and nothing broke, nothing is sent."""
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from sotawhat import taxonomy as tx
from sotawhat.notify.telegram import LIMIT, esc, esc_attr

VOTES = {"up": "👍", "down": "👎", "test": "🧪"}
CODES = {"up": "u", "down": "d", "test": "t"}
ALERT_AFTER = 3


def item_key(item_id) -> str:
    return hashlib.sha1(item_id.encode("utf-8")).hexdigest()[:10]


def num(value, digits=2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


@dataclass
class Entry:
    item_id: str
    title: str
    url: str
    source: str
    profile: str
    total: float
    scores: dict
    summary: str
    why: str
    tags: dict
    sources: list
    section: str = "main"
    position: int = 0

    @property
    def key(self) -> str:
        return item_key(self.item_id)

    def row(self) -> dict:
        return {"key": self.key, "position": self.position, "item_id": self.item_id, "section": self.section}


@dataclass
class Digest:
    day: str
    stats_line: str
    main: list
    radar: list
    extra: list                                  # approved beyond main_limit: only in the files
    failing: list                                # [(source key, consecutive failures, error)]
    error: str | None = None
    notes: list = field(default_factory=list)

    @property
    def alerts(self) -> list:
        return [f for f in self.failing if f[1] >= ALERT_AFTER]

    @property
    def worth_sending(self) -> bool:
        return bool(self.main or self.radar or self.alerts or self.error)


def _entry(store, row) -> Entry:
    return Entry(item_id=row["item_id"], title=row["title"], url=row["canonical_url"] or "", source=row["source"],
                 profile=row["profile"] or "", total=row["total"] or 0.0,
                 scores=json.loads(row["scores_json"] or "{}"), summary=row["summary_pt"] or "",
                 why=row["why_it_matters_pt"] or "", tags=json.loads(row["tags_json"] or "{}"),
                 sources=store.cluster_sources(row["item_id"]), section=row["decision"])


def build_digest(store, report, rubric) -> Digest:
    entries = [_entry(store, row) for row in store.triage_rows(report.run_id)]
    main = sorted((e for e in entries if e.section == "main"),
                  key=lambda e: (-e.total, -e.scores.get("B", 0), e.title))
    radar = sorted((e for e in entries if e.section == "radar"),
                   key=lambda e: (-e.scores.get("A", 0), -e.total, e.title))
    extra, main, radar = main[rubric.main_limit:], main[:rubric.main_limit], radar[:rubric.radar_limit]
    for position, e in enumerate(main, 1):
        e.position = position
    for position, e in enumerate(radar, 1):
        e.position = position
    t = report.triage
    triaged = t.triaged if t else 0
    stats_line = (f"coletados {sum(report.collected.values())} · novos {len(report.new_items)} · "
                  f"triados {triaged} · principais {len(main)} · radar {len(radar)} · "
                  f"custo US$ {num(report.cost_usd)}")
    notes = []
    if t is None or not t.llm:
        notes.append("triagem por LLM desligada (sem OPENROUTER_API_KEY ou --no-llm): itens aguardam o próximo run")
    if t and t.stopped:
        notes.append(f"triagem interrompida: {t.stopped}")
    if t and t.deferred and t.llm:
        notes.append(f"{t.deferred} itens ficaram para o próximo run")
    if t and t.errors:
        notes.append(f"{t.errors} itens com erro de LLM (nova tentativa no próximo run)")
    notes += list(t.warnings) if t else []
    if extra:
        notes.append(f"+{len(extra)} aprovados além do limite diário (só no arquivo do dia)")
    failing = [(key, count, err) for key, (count, err) in sorted(report.failing.items())]
    return Digest(day=report.day, stats_line=stats_line, main=main, radar=radar, extra=extra,
                  failing=failing, error=report.error, notes=notes)


def _tag_labels(e, limit=3) -> list:
    keys = (e.tags.get("domains") or [])[:2] + (e.tags.get("techniques") or [])[:2]
    labels = [tx.label(k) for k in keys][:limit]
    if e.tags.get("evidence_stage"):
        labels.append(f"{e.tags['evidence_stage']} {tx.label(e.tags['evidence_stage'])}")
    return labels


def _scores(e) -> str:
    return " ".join(f"{k}{e.scores[k]}" for k in "ABCD" if k in e.scores)


def _sources(e) -> str:
    return " + ".join(e.sources) if e.sources else e.source


# --- files --------------------------------------------------------------------
def render_markdown(d) -> str:
    out = [f"# sotawhat · {d.day}", "", d.stats_line, ""]
    out += [f"> {n}" for n in d.notes] + ([""] if d.notes else [])
    if d.error:
        out += [f"> ❌ erro no run: {d.error}", ""]
    if d.main:
        out += ["## Principais", ""]
        for e in d.main:
            out += [f"### {e.position}. [{e.title}]({e.url})",
                    f"**{num(e.total)}** · {_scores(e)} · {_sources(e)} · {' · '.join(_tag_labels(e))}", "",
                    e.summary, "", f"**Por que importa:** {e.why}", "", f"`{e.item_id}`", ""]
    if d.radar:
        out += ["## Radar de fronteira", ""]
        out += [f"{e.position}. [{e.title}]({e.url}) — {_sources(e)} · {_scores(e)}" for e in d.radar] + [""]
    if d.extra:
        out += ["## Também aprovados (além do limite diário)", ""]
        out += [f"- [{e.title}]({e.url}) — {num(e.total)} · {_sources(e)}" for e in d.extra] + [""]
    if d.failing:
        out += ["## Fontes com falha", ""]
        out += [f"- {key}: {err[:160]}" + (f" — **{count}ª falha seguida**" if count >= ALERT_AFTER else "")
                for key, count, err in d.failing] + [""]
    if not (d.main or d.radar):
        out += ["Nada relevante hoje.", ""]
    return "\n".join(out)


_CSS = """:root{--bg:#fbfaf7;--fg:#1f2328;--muted:#5d6670;--card:#fff;--line:#e3e0d8;--accent:#0b6e4f}
@media (prefers-color-scheme:dark){:root{--bg:#14171a;--fg:#e8e6e1;--muted:#a3abb3;--card:#1c2024;--line:#2c3237;--accent:#4cc39a}}
body{background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;max-width:46rem;margin:0 auto;padding:1rem}
h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem}.muted{color:var(--muted)}a{color:var(--accent)}
article{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.8rem 1rem;margin:.8rem 0}
article h3{font-size:1rem;margin:.2rem 0}.meta{color:var(--muted);font-size:.85rem}li{margin:.3rem 0}"""


def render_html(d) -> str:
    def a(e):
        return f'<a href="{esc_attr(e.url)}">{esc(e.title)}</a>'

    body = [f"<h1>sotawhat · {esc(d.day)}</h1>", f'<p class="muted">{esc(d.stats_line)}</p>']
    body += [f'<p class="muted">{esc(n)}</p>' for n in d.notes]
    if d.error:
        body.append(f"<p>❌ erro no run: {esc(d.error)}</p>")
    if d.main:
        body.append("<h2>Principais</h2>")
        for e in d.main:
            body.append(f'<article><h3>{e.position}. {a(e)}</h3><p class="meta"><b>{num(e.total)}</b> · '
                        f"{esc(_scores(e))} · {esc(_sources(e))} · {esc(' · '.join(_tag_labels(e)))}</p>"
                        f"<p>{esc(e.summary)}</p><p><b>Por que importa:</b> {esc(e.why)}</p></article>")
    if d.radar:
        body.append("<h2>Radar de fronteira</h2><ol>" + "".join(
            f"<li>{a(e)} <span class=\"meta\">— {esc(_sources(e))} · {esc(_scores(e))}</span></li>" for e in d.radar)
            + "</ol>")
    if d.extra:
        body.append("<h2>Também aprovados</h2><ul>" + "".join(
            f"<li>{a(e)} <span class=\"meta\">— {num(e.total)}</span></li>" for e in d.extra) + "</ul>")
    if d.failing:
        body.append("<h2>Fontes com falha</h2><ul>" + "".join(
            f"<li>{esc(k)}: {esc(err[:160])}" + (f" — <b>{c}ª falha seguida</b>" if c >= ALERT_AFTER else "") + "</li>"
            for k, c, err in d.failing) + "</ul>")
    if not (d.main or d.radar):
        body.append("<p>Nada relevante hoje.</p>")
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>sotawhat {esc(d.day)}</title>'
            f"<style>{_CSS}</style></head><body>{''.join(body)}</body></html>")


def write_files(d, out_dir) -> tuple:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md, page = out_dir / f"{d.day}.md", out_dir / f"{d.day}.html"
    md.write_text(render_markdown(d), encoding="utf-8")
    page.write_text(render_html(d), encoding="utf-8")
    return md, page


# --- Telegram -----------------------------------------------------------------
def keyboard(rows, votes=None) -> dict:
    """rows: mappings with key/position/item_id. One item: 👍 👎 🧪. Several (radar): '1 👍' '1 👎' pairs."""
    votes = votes or {}

    def button(row, value, label):
        chosen = votes.get(row["item_id"]) == value
        return {"text": f"✅{label}" if chosen else label, "callback_data": f"f:{row['key']}:{CODES[value]}"}

    if len(rows) == 1:
        return {"inline_keyboard": [[button(rows[0], v, e) for v, e in VOTES.items()]]}
    buttons = [button(r, v, f"{r['position']} {VOTES[v]}") for r in rows for v in ("up", "down")]
    return {"inline_keyboard": [buttons[i:i + 4] for i in range(0, len(buttons), 4)]}


def _clip(text, n) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n - 1] + "…"


def telegram_messages(d) -> list:
    day = "/".join(reversed(d.day.split("-")))
    header = [f"🗞️ <b>sotawhat · {esc(day)}</b>", esc(d.stats_line)]
    header += [f"ℹ️ {esc(n)}" for n in d.notes]
    if d.error:
        header.append(f"❌ <b>erro no run:</b> {esc(d.error[:300])}")
    if d.alerts:
        header.append("⚠️ <b>Alertas</b>: " + "; ".join(f"{esc(k)} ({c}ª falha seguida)" for k, c, _ in d.alerts))
    others = [k for k, c, _ in d.failing if c < ALERT_AFTER]
    if others:
        header.append(f"⚠️ falha hoje: {esc(', '.join(others))}")
    messages = [{"text": "\n".join(header), "rows": [], "silent": False}]
    for e in d.main:
        text = (f'<b>{e.position}.</b> <a href="{esc_attr(e.url)}">{esc(_clip(e.title, 300))}</a>\n'
                f"⭐ <b>{num(e.total)}</b> · {_scores(e)} · {esc(_sources(e))}\n"
                f"🏷️ {esc(' · '.join(_tag_labels(e)))}\n{esc(_clip(e.summary, 700))}\n"
                f"💡 <i>{esc(_clip(e.why, 450))}</i>")
        messages.append({"text": text[:LIMIT], "rows": [e.row()], "silent": True})
    if d.radar:
        lines = ["📡 <b>Radar de fronteira</b> (IA forte, sem ponte médica clara)"]
        lines += [f'{e.position}. <a href="{esc_attr(e.url)}">{esc(_clip(e.title, 200))}</a> — {esc(_sources(e))} '
                  f"· A{e.scores.get('A', '?')}" for e in d.radar]
        messages.append({"text": "\n".join(lines)[:LIMIT], "rows": [e.row() for e in d.radar], "silent": True})
    return messages


def send_digest(notifier, store, d, run_id, pause=0.4, sleep=time.sleep) -> int:
    """Send the header, one message per main item and the radar; record every delivery so the
    buttons can be traced back to their items."""
    sent = 0
    for message in telegram_messages(d):
        ids = [store.record_delivery(run_id, d.day, r["item_id"], r["key"], r["section"], r["position"])
               for r in message["rows"]]
        result = notifier.send_message(message["text"], reply_markup=keyboard(message["rows"]) if message["rows"] else None,
                                       disable_notification=message["silent"])
        store.mark_delivered(ids, notifier.chat_id, result.get("message_id"))
        sent += 1
        if pause:
            sleep(pause)
    return sent
````

- [ ] **Passo 5: `DailyReport` guarda as estatísticas da triagem**

Em `sotawhat/pipeline/daily.py`, logo depois de `cost_usd: float = 0.0` (dentro de `DailyReport`):

```python
    triage: object = None                           # TriageStats, when the triage stage ran
```

- [ ] **Passo 6: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `146 passed`.

- [ ] **Passo 7: Commit**

```bash
git add sotawhat/notify/telegram.py sotawhat/pipeline/deliver.py sotawhat/pipeline/daily.py tests/test_deliver.py
git commit -m "feat: ranked digest (Markdown, HTML, Telegram) with feedback buttons"
```

---

## Tarefa 9: Votos do Telegram

Pontos de projeto (SDD §7.7):
- **Validade dos updates:** o Telegram guarda os updates por 24 h.
  - `pull` esvazia a fila e grava o *offset* em `meta`;
  - `listen` faz *long polling* e marca um *heartbeat*;
  - o run diário só faz `pull` se não houver ouvinte ativo, o que evita o 409 de dois `getUpdates` simultâneos.
- **Quem pode votar:** só o usuário autorizado. Cliques de outras pessoas são ignorados.
- **Ao registrar um voto:** o bot confirma o clique e redesenha os botões, com ✅ no escolhido. O último voto vale.
- **Mensagens com link** que você mandar ao bot vão para `inbox` (P5).

**Files:**
- Create: `sotawhat/pipeline/feedback.py`, `tests/test_feedback.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_feedback.py`:

````python
# tests/test_feedback.py
import json
from datetime import datetime, timedelta, timezone

from sotawhat.configfiles import Rubric
from sotawhat.items import Item
from sotawhat.notify.telegram import TelegramError
from sotawhat.pipeline.daily import DailyReport
from sotawhat.pipeline.deliver import build_digest, item_key, send_digest
from sotawhat.pipeline.feedback import HEARTBEAT_KEY, handle_update, listen, listener_active, parse_callback, pull
from sotawhat.pipeline.triage import TriageStats
from sotawhat.store.db import Store

class FakeBot:
    def __init__(self, updates=()):
        self.chat_id = "42"
        self.sent, self.answers, self.edits = [], [], []
        self.updates = list(updates)

    def send_message(self, text, reply_markup=None, disable_notification=False):
        self.sent.append((text, reply_markup, disable_notification))
        return {"message_id": 100 + len(self.sent)}

    def get_updates(self, offset=None, timeout=0):
        batch = [u for u in self.updates if offset is None or u["update_id"] >= offset]
        self.updates = []
        return batch

    def answer_callback(self, callback_id, text=""):
        self.answers.append(text)

    def edit_reply_markup(self, chat_id, message_id, markup):
        self.edits.append((chat_id, message_id, markup))


def _seed(st):
    run = st.start_run("daily")
    items = [Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"Título <{n}>",
                  url=f"https://pubmed.ncbi.nlm.nih.gov/{n}/", profile="medico") for n in range(1, 5)]
    st.upsert_items(items, run)
    rows = [("pmid:1", "main", 4.2, {"A": 4, "B": 5, "C": 3, "D": 5}),
            ("pmid:2", "main", 3.5, {"A": 3, "B": 4, "C": 3, "D": 5}),
            ("pmid:3", "radar", 2.9, {"A": 5, "B": 1, "C": 4, "D": 5}),
            ("pmid:4", "reject", 1.0, {"A": 0, "B": 1, "C": 0, "D": 5})]
    for item_id, decision, total, scores in rows:
        st.record_triage(item_id, run, decision, total=total, scores=scores, summary_pt=f"Resumo de {item_id}.",
                         why_it_matters_pt="Útil para o PS.", tags={"domains": ["A06"], "techniques": ["C02"],
                                                                    "evidence_stage": "D2"})
    report = DailyReport(run_id=run, day="2026-11-08", collected={"medico": 4}, new_items=items,
                         failing={"semantic_scholar": (3, "429 Too Many Requests"), "arxiv": (1, "timeout")},
                         cost_usd=0.0123, triage=TriageStats(triaged=4, main=2, radar=1, rejected=1, deferred=2))
    return run, report



def test_votes_are_recorded_acknowledged_and_shown(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run, report = _seed(st)
        d = build_digest(st, report, Rubric())
        bot = FakeBot()
        send_digest(bot, st, d, run, pause=0)
        key = item_key("pmid:1")
        vote = {"update_id": 7, "callback_query": {"id": "cq1", "from": {"id": 42}, "data": f"f:{key}:t",
                                                   "message": {"message_id": 102, "chat": {"id": 42}}}}
        stranger = {"update_id": 8, "callback_query": {"id": "cq2", "from": {"id": 666}, "data": f"f:{key}:d"}}
        link = {"update_id": 9, "message": {"message_id": 5, "from": {"id": 42}, "date": 1,
                                            "text": "olha https://example.org/post?x=1"}}
        bot.updates = [vote, stranger, link]
        assert pull(st, bot, "42") == {"vote": 1, "inbox": 1, "ignored": 1}
        assert st.item_votes() == {"pmid:1": "test"} and bot.answers == ["🧪 registrado"]
        assert bot.edits[0][2]["inline_keyboard"][0][2]["text"] == "✅🧪"
        payload = json.loads(st.conn.execute("SELECT payload_json FROM inbox").fetchone()[0])
        assert payload["urls"] == ["https://example.org/post?x=1"]
        assert st.meta_get("telegram_offset") == "10" and st.meta_get("telegram_last_pull_at")
        assert parse_callback("f:zz:u") is None and parse_callback(f"f:{key}:x") is None
        assert handle_update(st, bot, {"update_id": 1, "callback_query": {"id": "c", "from": {"id": 42},
                                                                          "data": "f:0123456789:u"}}, "42") == "ignored"


def test_listener_heartbeat(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
        assert not listener_active(st, now)
        st.meta_set(HEARTBEAT_KEY, (now - timedelta(seconds=60)).isoformat())
        assert listener_active(st, now) and not listener_active(st, now + timedelta(minutes=5))


def test_listen_survives_conflicts_and_keeps_a_heartbeat(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        class Bot(FakeBot):
            calls = 0

            def get_updates(self, offset=None, timeout=0):
                Bot.calls += 1
                if Bot.calls == 1:
                    raise TelegramError("getUpdates: HTTP 409 Conflict", status=409)
                return []

        waits = []
        listen(st, Bot(), "42", should_stop=lambda: Bot.calls >= 2, timeout=1, sleep=waits.append)
        assert waits == [60] and listener_active(st)
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_feedback.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.pipeline.feedback'`.

- [ ] **Passo 3: Criar `sotawhat/pipeline/feedback.py`** (o comando de CLI entra na Tarefa 10)

````python
# sotawhat/pipeline/feedback.py
"""Telegram feedback (SDD §6.11, §7.7). Buttons -> `feedback`; messages from the user (links) ->
`inbox`, kept for manual capture (P5). Telegram keeps updates for 24 h only, so `run daily` pulls them
first, and `sotawhat feedback listen` can run all day as a logon task (instant ✅ on the buttons)."""
import logging
import re
import time
from datetime import datetime, timezone

from sotawhat.notify.telegram import TelegramError
from sotawhat.pipeline.deliver import CODES, VOTES, keyboard
from sotawhat.store.db import utcnow

VALUES = {code: value for value, code in CODES.items()}
OFFSET_KEY = "telegram_offset"
LAST_PULL_KEY = "telegram_last_pull_at"
HEARTBEAT_KEY = "telegram_listener_at"
_URL = re.compile(r"https?://\S+")
log = logging.getLogger("sotawhat.feedback")


def parse_callback(data):
    parts = (data or "").split(":")
    if len(parts) == 3 and parts[0] == "f" and parts[2] in VALUES and re.fullmatch(r"[0-9a-f]{10}", parts[1]):
        return parts[1], VALUES[parts[2]]
    return None


def _answer(notifier, query, text):
    try:
        notifier.answer_callback(query["id"], text)
    except TelegramError:
        pass   # queries older than a few minutes can no longer be answered; the vote still counts


def handle_update(store, notifier, update, allowed_user) -> str:
    query = update.get("callback_query")
    if query is not None:
        if str((query.get("from") or {}).get("id")) != str(allowed_user):
            return "ignored"
        parsed = parse_callback(query.get("data"))
        row = store.delivery_by_key(parsed[0]) if parsed else None
        if row is None:
            _answer(notifier, query, "item não encontrado")
            return "ignored"
        value = parsed[1]
        store.add_feedback("item", row["item_id"], value, "telegram")
        _answer(notifier, query, f"{VOTES[value]} registrado")
        message = query.get("message") or {}
        chat, message_id = (message.get("chat") or {}).get("id"), message.get("message_id")
        rows = store.deliveries_for_message(chat, message_id) if chat is not None and message_id else []
        if rows:
            try:
                notifier.edit_reply_markup(chat, message_id,
                                           keyboard(rows, store.item_votes(ids=[r["item_id"] for r in rows])))
            except TelegramError:
                pass   # "message is not modified" or too old to edit
        return "vote"
    message = update.get("message")
    if message and str((message.get("from") or {}).get("id")) == str(allowed_user):
        text = message.get("text") or message.get("caption") or ""
        store.add_inbox("telegram", {"message_id": message.get("message_id"), "date": message.get("date"),
                                     "text": text, "urls": _URL.findall(text)})
        return "inbox"
    return "ignored"


def pull(store, notifier, allowed_user, timeout=0) -> dict:
    """Process pending updates; with timeout=0 drain everything, otherwise long-poll one batch."""
    counts = {"vote": 0, "inbox": 0, "ignored": 0}
    offset = store.meta_get(OFFSET_KEY)
    while True:
        updates = notifier.get_updates(offset=int(offset) if offset else None, timeout=timeout)
        for update in updates:
            try:
                counts[handle_update(store, notifier, update, allowed_user)] += 1
            except Exception:  # noqa: BLE001 - one bad update must not block the queue
                log.exception("update %s", update.get("update_id"))
                counts["ignored"] += 1
            offset = update["update_id"] + 1
            store.meta_set(OFFSET_KEY, offset)
        if not updates or timeout:
            break
    store.meta_set(LAST_PULL_KEY, utcnow())
    return counts


def listener_active(store, now=None, max_age_s=180) -> bool:
    beat = store.meta_get(HEARTBEAT_KEY)
    if not beat:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - datetime.fromisoformat(beat)).total_seconds() < max_age_s


def listen(store, notifier, allowed_user, should_stop=lambda: False, timeout=50, sleep=time.sleep) -> None:
    while not should_stop():
        store.meta_set(HEARTBEAT_KEY, utcnow())
        try:
            counts = pull(store, notifier, allowed_user, timeout=timeout)
            if counts["vote"] or counts["inbox"]:
                log.info("feedback %s", counts)
        except TelegramError as exc:
            log.warning("telegram: %s", exc)
            sleep(60 if exc.status == 409 else 15)   # 409: another getUpdates is running

````

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `149 passed`.

- [ ] **Passo 5: Commit**

```bash
git add sotawhat/pipeline/feedback.py tests/test_feedback.py
git commit -m "feat: Telegram votes (pull, long-poll listener, button refresh) and inbox"
```

---

## Tarefa 10: `run daily` com triagem, log diário e CLI

Pontos de projeto:
- **Ordem do run:** votos → coleta → triagem → digest em `data/digests/` → Telegram.
- **Sem `OPENROUTER_API_KEY` ou com `--no-llm`:** roda só o estágio A, e os itens esperam o próximo run.
- **Se a triagem quebrar:** o run fica como falho, os itens coletados ficam salvos e o cabeçalho do Telegram mostra o erro.
- **Log:** `data/logs/AAAA-MM-DD.log`, sem tokens nem textos de prompt.

**Files:**
- Modify: `sotawhat/pipeline/daily.py` (substituir o conteúdo inteiro), `sotawhat/pipeline/feedback.py`, `sotawhat/cli.py`, `tests/test_daily.py`, `tests/test_cli.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Acrescentar ao final de `tests/test_daily.py`:

````python
def test_triage_stage_runs_after_collection_and_is_recorded(tmp_path):
    import json

    from sotawhat.pipeline.triage import TriageStats

    seen = []

    def triage(store, run_id):
        seen.append((run_id, store.count_items()))
        return TriageStats(triaged=2, main=1, rejected=1)

    sources = {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv"), _r("2511.00002", "arxiv")])]}
    with Store(tmp_path / "insight.db") as st:
        report = run_daily(st, sources, today=DAY, triage=triage)
        assert seen == [(report.run_id, 2)] and report.triage.main == 1
        stats = json.loads(st.last_run("daily")["stats_json"])
        assert stats["triage"]["triaged"] == 2


def test_triage_crash_fails_the_run_but_keeps_the_items(tmp_path):
    def triage(store, run_id):
        raise RuntimeError("embedder exploded")

    sources = {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv")])]}
    with Store(tmp_path / "insight.db") as st:
        report = run_daily(st, sources, today=DAY, triage=triage)
        assert not report.ok and "embedder exploded" in report.error and st.count_items() == 1
````

Acrescentar ao final de `tests/test_cli.py`:

````python
def test_parse_run_no_llm_and_feedback():
    assert parse_args(["run", "daily", "--no-llm"]).no_llm is True
    assert parse_args(["run", "daily"]).no_llm is False
    assert parse_args(["feedback", "listen"]).action == "listen"
    assert parse_args(["feedback", "pull"]).command == "feedback"
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_daily.py tests/test_cli.py -q`
Expected: FAIL (3 testes) com `TypeError: run_daily() got an unexpected keyword argument 'triage'`.

- [ ] **Passo 3: Substituir `sotawhat/pipeline/daily.py`**

````python
# sotawhat/pipeline/daily.py
"""`sotawhat run daily` (SDD §6.1): feedback -> collect -> normalize -> exact dedup -> SQLite ->
triage (stage A + LLM) -> digest files + Telegram. Extraction and the graph arrive in P3."""
import html
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import date

from sotawhat.digest import collect, filter_relevant
from sotawhat.items import to_item
from sotawhat.notify.telegram import esc, esc_attr
from sotawhat.profiles import PROFILES

ALERT_AFTER = 3   # consecutive failures before a source is flagged as an alert
log = logging.getLogger("sotawhat.daily")


@dataclass
class DailyReport:
    run_id: int
    day: str
    collected: dict = field(default_factory=dict)   # profile -> unique items collected
    new_items: list = field(default_factory=list)   # Items never seen before
    failing: dict = field(default_factory=dict)     # source key -> (consecutive failures, last error)
    ok: bool = True
    error: str | None = None
    cost_usd: float = 0.0
    triage: object = None                           # TriageStats, when the triage stage ran


def _dedupe(items):
    by_id = {}
    for it in items:
        kept = by_id.setdefault(it.id, it)
        if kept is not it:
            kept.concepts += [c for c in it.concepts if c not in kept.concepts]
    return list(by_id.values())


def _record_health(store, sources, errors, report):
    for src in sources:
        keyed = [(src.name, errors.get(src.name))]
        feed_errors = getattr(src, "feed_errors", {})
        keyed += [(f"{src.name}/{label}", feed_errors.get(label)) for label, _ in getattr(src, "feeds", [])]
        for key, err in keyed:
            if err:
                report.failing[key] = (store.record_source_error(key, err), err)
            else:
                store.record_source_ok(key)


def run_daily(store, sources_by_profile, limit=10, vault=None, today=None, triage=None) -> DailyReport:
    """triage: optional callable (store, run_id) -> TriageStats, run after collection."""
    day = (today or date.today()).isoformat()
    report = DailyReport(run_id=store.start_run("daily"), day=day)
    try:
        for name, sources in sources_by_profile.items():
            profile = PROFILES[name]
            errors = {}
            results = collect(sources, profile["keywords"], limit,
                              on_source_error=lambda src, msg: errors.setdefault(src.name, msg))
            if profile.get("require_any"):
                results = filter_relevant(results, profile["require_any"])
            items = _dedupe([to_item(r, profile=name) for r in results])
            new_ids = set(store.upsert_items(items, report.run_id))
            report.collected[name] = len(items)
            report.new_items += [it for it in items if it.id in new_ids]
            _record_health(store, sources, errors, report)
            log.info("%s: %d collected, %d new", name, len(items), len(new_ids))
            if vault:
                from sotawhat.obsidian import write_notes
                write_notes(results, vault=vault, profile_name=name, tags=profile["tags"],
                            keywords=profile["keywords"], added=day)
        if triage is not None:
            report.triage = triage(store, report.run_id)
    except Exception as exc:  # noqa: BLE001 - the run must always be closed and reported
        log.exception("daily run failed")
        report.ok = False
        report.error = f"{type(exc).__name__}: {exc}"
    stats = {"collected": report.collected, "new": len(report.new_items), "failing": sorted(report.failing)}
    if report.triage is not None:
        stats["triage"] = report.triage.as_dict()
    store.finish_run(report.run_id, ok=report.ok, stats=stats, error=report.error)
    row = store.conn.execute("SELECT cost_usd FROM runs WHERE id = ?", (report.run_id,)).fetchone()
    report.cost_usd = row[0]
    return report


def render_summary(report, max_items=10) -> str:
    """P0 summary: still used for the console when the LLM triage is off."""
    lines = [f"{'✅' if report.ok else '❌'} <b>sotawhat · run diário {report.day}</b>",
             f"coletados {sum(report.collected.values())} · novos {len(report.new_items)} · "
             f"custo LLM US$ {report.cost_usd:.2f}"]
    for name, count in report.collected.items():
        fresh = sum(1 for it in report.new_items if it.profile == name)
        lines.append(f"• {esc(name)}: {count} coletados, {fresh} novos")
    if report.error:
        lines.append(f"❌ erro: {esc(report.error)}")
    if report.failing:
        lines += ["", "⚠️ <b>Fontes com falha</b>"]
        for key, (count, err) in sorted(report.failing.items()):
            flag = f" — <b>alerta: {count}ª falha seguida</b>" if count >= ALERT_AFTER else ""
            lines.append(f"• {esc(key)}: {esc(err[:120])}{flag}")
    if report.new_items:
        lines += ["", f"<b>Novos</b> (até {max_items})"]
        for it in report.new_items[:max_items]:
            lines.append(f'• <a href="{esc_attr(it.url)}">{esc(it.title[:140])}</a> — {esc(it.source)}')
    return "\n".join(lines)


def to_plain(text) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


def setup_logging(data_dir, day, level="INFO"):
    """One log file per day under data/logs (RNF6); tokens never reach it (no request bodies are logged)."""
    folder = data_dir / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(folder / f"{day}.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger("sotawhat")
    root.handlers = [handler]
    root.setLevel(level)
    return folder / f"{day}.log"


def main_daily(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.configfiles import ConfigError, load_config
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient
    from sotawhat.notify.telegram import TelegramError, TelegramNotifier
    from sotawhat.pipeline import feedback
    from sotawhat.pipeline.deliver import build_digest, render_markdown, send_digest, write_files
    from sotawhat.pipeline.triage import run_triage
    from sotawhat.profiles import build_sources
    from sotawhat.store.classifier import refresh
    from sotawhat.store.db import Store
    from sotawhat.store.vectors import get_embedder

    settings = load_settings()
    day = date.today().isoformat()
    setup_logging(settings.sotawhat_data_dir, day, settings.sotawhat_log_level)
    try:
        config = load_config(settings.sotawhat_config_dir)
    except ConfigError as exc:
        print(f"[config] {exc}", file=sys.stderr)
        return 2
    sources = {name: build_sources(name, crossref_mailto=settings.crossref_mailto) for name in PROFILES}
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    use_llm = bool(settings.openrouter_api_key) and not getattr(ns, "no_llm", False)
    with Store(settings.db_path) as store:
        if notifier.configured and not feedback.listener_active(store):
            try:
                log.info("feedback %s", feedback.pull(store, notifier, settings.allowed_user_id))
            except TelegramError as exc:
                log.warning("feedback pull: %s", exc)
        embedder = get_embedder(settings)
        gateway = None
        if use_llm:
            client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                                      app_title=settings.openrouter_app_title)
            gateway = LLMGateway(client, store=store, settings=settings, tasks=config.llm["tasks"])

        def triage(st, run_id):
            if gateway is not None:
                gateway.run_id = run_id
            try:
                gates = refresh(st, list(PROFILES), embedder.name, settings.models_dir,
                                config.rubric.classifier_min_ratings)
            except Exception:  # noqa: BLE001 - without a classifier the LLM simply sees every item
                log.exception("classifier refresh")
                gates = {}
            return run_triage(st, run_id, gateway, config.rubric, config.mutes, embedder, gates)

        report = run_daily(store, sources, limit=ns.limit, vault=ns.vault, triage=triage)
        digest = build_digest(store, report, config.rubric)
        md_path, _ = write_files(digest, settings.sotawhat_data_dir / "digests")
        print(render_markdown(digest) if report.triage and report.triage.llm else to_plain(render_summary(report)))
        print(f"\n[digest] {md_path}")
        if not ns.no_notify and notifier.configured and digest.worth_sending:
            try:
                send_digest(notifier, store, digest, report.run_id)
            except TelegramError as exc:
                print(f"[telegram] {exc}", file=sys.stderr)
                log.error("telegram: %s", exc)
    return 0 if report.ok else 1
````

- [ ] **Passo 4: Comando `feedback`**

Acrescentar ao final de `sotawhat/pipeline/feedback.py`:

````python
def main_feedback(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.notify.telegram import TelegramNotifier
    from sotawhat.pipeline.daily import setup_logging
    from sotawhat.store.db import Store

    settings = load_settings()
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if not notifier.configured:
        print("Telegram não configurado: preencha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env")
        return 2
    with Store(settings.db_path) as store:
        if ns.action == "pull":
            counts = pull(store, notifier, settings.allowed_user_id)
            print(f"votos {counts['vote']} · mensagens {counts['inbox']} · ignorados {counts['ignored']}")
            return 0
        setup_logging(settings.sotawhat_data_dir, datetime.now().date().isoformat(), settings.sotawhat_log_level)
        print("ouvindo o Telegram (Ctrl+C para sair)")
        try:
            listen(store, notifier, settings.allowed_user_id)
        except KeyboardInterrupt:
            pass
    return 0
````

Em `sotawhat/cli.py`:

4a. `_SUBCOMMANDS`: acrescentar `"feedback"`.

4b. Logo depois de `p_run.add_argument("--no-notify", action="store_true")`:

```python
    p_run.add_argument("--no-llm", action="store_true", help="collect and run stage A only (no LLM calls)")
```

4c. Logo depois do parser `doctor`:

```python

    p_feedback = sub.add_parser("feedback")
    p_feedback.add_argument("action", choices=["pull", "listen"])
```

4d. No `main`, depois do ramo `doctor`:

```python
    elif ns.command == "feedback":
        from sotawhat.pipeline.feedback import main_feedback
        raise SystemExit(main_feedback(ns))
```

- [ ] **Passo 5: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `152 passed`.

- [ ] **Passo 6: Commit**

```bash
git add sotawhat/pipeline/daily.py sotawhat/pipeline/feedback.py sotawhat/cli.py tests/test_daily.py tests/test_cli.py
git commit -m "feat: run daily triages, writes the digest, logs to data/logs and pulls votes first"
```

---

## Tarefa 11: Golden set e *bake-off* de modelos

Pontos de projeto (SDD §6.6, §12, D15):
- **`eval golden draft`:** sorteia itens do banco e, com `--vault`, das notas do 2.0. A amostra tem metade por perfil, rodízio entre fontes e só itens com pelo menos 300 caracteres. O resultado é um Markdown para você rotular e um JSONL com o texto completo. O comando não sobrescreve um rascunho existente sem `--force`.
- **`eval golden import`:** lê os rótulos do Markdown.
- **`eval models`:**
  - roda cada candidato de `config/llm.yaml` (`bakeoff`) sozinho, sem fallback, com o prompt e a rubrica atuais;
  - mede F1 de "incluir", acurácia nos 3 rótulos, JSON válido de primeira, falhas, p50/p95 e custo real, lido do ledger;
  - escreve o relatório em `data/evals/`, com uma amostra dos resumos em português para você julgar;
  - com `--apply`, põe o vencedor na frente em `config/llm.yaml`.
- **Critério do vencedor:** maior F1 entre os modelos com ≥ 90% de JSON válido e ≤ 5% de falhas; desempate por acurácia e depois por custo.

**Files:**
- Create: `sotawhat/evals/__init__.py` (vazio), `sotawhat/evals/golden.py`, `sotawhat/evals/bakeoff.py`, `sotawhat/evals/commands.py`, `tests/test_evals.py`
- Modify: `sotawhat/cli.py`, `tests/test_cli.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_evals.py`:

````python
# tests/test_evals.py
import json

import yaml

from sotawhat.configfiles import Rubric, load_llm_config
from sotawhat.evals.bakeoff import (Outcome, apply_winner, evaluate_model, metrics, pick_winner, ranking,
                                    render_report)
from sotawhat.evals.golden import as_item, import_labels, load_golden, read_vault, sample, write_draft
from sotawhat.llm.gateway import LLMFailure, StructuredResult
from sotawhat.llm.schemas import TriageOutput

NOTE = """---
title: {title}
authors: ["Ana Lima", "Bo Chen"]
date: "2026-06-03"
source: {source}
url: "{url}"
keywords: ["radiology"]
tags: ["medical-ai", "source/{source}"]
added: "2026-06-14"
---

# {raw_title}

{body}

**Conceitos:** [[radiology]]

[Source]({raw_url})
"""


def _note(folder, name, title, source, url, body):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.md").write_text(NOTE.format(title=json.dumps(title), raw_title=title, source=source,
                                                   url=url, raw_url=url, body=body), encoding="utf-8")


def _entry(n, profile, source, label=None, text="t" * 400):
    return {"id": f"{source}:{n}", "profile": profile, "source": source, "title": f"T{n}", "url": "",
            "published_at": "", "authors": [], "text": text, "origin": "store", "label": label, "note": ""}


def test_read_vault_builds_canonical_items(tmp_path):
    _note(tmp_path / "medico" / "arxiv", "a", "BreastGPT: a multimodal LLM", "arxiv",
          "https://arxiv.org/abs/2606.04911v1", "Breast cancer abstract " * 20)
    _note(tmp_path / "medico" / "pubmed", "b", "Sepsis model", "pubmed",
          "https://pubmed.ncbi.nlm.nih.gov/41234567/", "Sepsis abstract " * 20)
    _note(tmp_path / "geral" / "hf_papers", "c", "Agents paper", "hf_papers",
          "https://huggingface.co/papers/2606.00001", "Agents abstract " * 20)
    by_id = {e["id"]: e for e in read_vault(tmp_path)}
    assert set(by_id) == {"arxiv:2606.04911", "pmid:41234567", "arxiv:2606.00001"}
    e = by_id["arxiv:2606.04911"]
    assert e["profile"] == "medico" and e["authors"] == ["Ana Lima", "Bo Chen"] and e["origin"] == "vault"
    assert e["text"].startswith("Breast cancer abstract") and "Conceitos" not in e["text"] and "Source" not in e["text"]


def test_sample_is_stratified_deduplicated_and_reproducible():
    pool = [_entry(n, "medico", "pubmed") for n in range(30)] + [_entry(n, "medico", "crossref") for n in range(3)]
    pool += [_entry(n, "geral", "arxiv") for n in range(30)] + [_entry(99, "geral", "arxiv", text="short")]
    pool += [_entry(1, "medico", "pubmed")]                                   # duplicate id
    picks = sample(pool, n=20, seed=7)
    assert len(picks) == 20 and len({p["id"] for p in picks}) == 20
    assert sum(p["profile"] == "medico" for p in picks) == 10
    assert sum(p["source"] == "crossref" for p in picks) == 3              # round-robin reaches small sources
    assert all(p["id"] != "arxiv:99" for p in picks)                         # too short to judge
    assert [p["id"] for p in sample(pool, n=20, seed=7)] == [p["id"] for p in picks]


def test_draft_and_import_round_trip(tmp_path):
    entries = [_entry(n, "medico", "pubmed") for n in range(4)]
    md, jsonl = write_draft(entries, tmp_path, "g")
    text = md.read_text(encoding="utf-8")
    assert text.count("\nRótulo: \n") == 4 and "`id: pubmed:0`" in text and "**incluir**" in text
    text = text.replace("`id: pubmed:0`\nRótulo: ", "`id: pubmed:0`\nRótulo: incluir")
    text = text.replace("`id: pubmed:1`\nRótulo: ", "`id: pubmed:1`\nRótulo: Excluir — só epidemiologia")
    text = text.replace("`id: pubmed:2`\nRótulo: ", "`id: pubmed:2`\nRótulo: talvez")
    md.write_text(text, encoding="utf-8")
    report = import_labels(tmp_path, "g")
    assert report["labeled"] == 2 and report["unlabeled"] == 1 and report["invalid"] == ["pubmed:2: 'talvez'"]
    golden = load_golden(jsonl)
    assert [(g["id"], g["label"], g["note"]) for g in golden] == [("pubmed:0", "main", ""),
                                                                  ("pubmed:1", "reject", "só epidemiologia")]
    assert as_item(golden[0]).profile == "medico"


def _out(**kw):
    base = dict(summary_pt="Resumo.", hard_exclusion="none", inclusion_rules=[], frontier_ai=4,
                medical_applicability=4, actionability=3, domains=[], problem_types=[], techniques=[],
                evidence_stage="D1", stakeholders=[], br_applicability="F1", cfm_risk="medio", substance=2,
                audience=[], vendor_only=False, reason_pt="Motivo.", why_it_matters_pt="Importa.")
    base.update(kw)
    return TriageOutput(**base)


class FakeGateway:
    def structured_call(self, task, messages, output_model, models=None):
        assert models and len(models) == 1                                    # one model, no fallback
        if "T2" in messages[1]["content"]:
            raise LLMFailure("triage: every model failed")
        low = "T1" in messages[1]["content"]
        return StructuredResult(output=_out(frontier_ai=1 if low else 4, medical_applicability=0 if low else 4), model=models[0],
                                provider="X", cost_usd=0.001, latency_ms=900 if low else 1100, attempts=1,
                                first_try_valid=not low)


def test_evaluate_model_and_metrics():
    golden = [_entry(0, "medico", "pubmed", "main"), _entry(1, "medico", "pubmed", "reject"),
              _entry(2, "medico", "pubmed", "main")]
    outcomes = evaluate_model(FakeGateway(), golden, Rubric(), "a/model", concurrency=2)
    assert [o.predicted for o in outcomes] == ["main", "reject", None]
    m = metrics(outcomes)
    assert (m["precision"], m["recall"], m["failures"]) == (1.0, 0.5, 1)
    assert round(m["f1"], 3) == 0.667 and round(m["accuracy"], 3) == 0.667 and round(m["valid_first_try"], 3) == 0.333
    assert m["confusion"] == {"main": {"main": 1, "falha": 1}, "reject": {"reject": 1}}


def test_winner_report_and_apply(tmp_path):
    results = {"a/x": {"n": 50, "f1": 0.80, "accuracy": 0.7, "valid_first_try": 1.0, "failures": 0, "cost_usd": 0.03,
                       "precision": 0.8, "recall": 0.8, "p50_ms": 1000, "p95_ms": 3000, "confusion": {}},
               "b/y": {"n": 50, "f1": 0.85, "accuracy": 0.7, "valid_first_try": 0.80, "failures": 0, "cost_usd": 0.01,
                       "precision": 0.9, "recall": 0.8, "p50_ms": 1000, "p95_ms": 3000, "confusion": {}},
               "c/z": {"n": 50, "f1": 0.80, "accuracy": 0.7, "valid_first_try": 0.95, "failures": 1, "cost_usd": 0.02,
                       "precision": 0.8, "recall": 0.8, "p50_ms": 1000, "p95_ms": 3000, "confusion": {}}}
    assert pick_winner(results) == "c/z"           # b/y: too much invalid JSON; tie a/x vs c/z -> cheaper
    assert ranking(results, "c/z") == ["c/z", "b/y", "a/x"]
    golden = [_entry(0, "medico", "pubmed", "main")]
    outcomes = {"c/z": [Outcome("pubmed:0", "main", "main", True, 900, "Resumo pt.", "Importa.")]}
    report = render_report("triage", "2026-11-08", results, outcomes, golden, "c/z")
    assert "| **c/z** | 0.80 |" in report and "Resumo pt." in report and "incluir 1" in report
    path = tmp_path / "llm.yaml"
    path.write_text("bakeoff:\n  triage: [a/x, b/y, c/z]\n", encoding="utf-8")
    apply_winner(path, "triage", ["c/z", "b/y", "a/x"], "low", 1500)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["tasks"]["triage"] == {"models": ["c/z", "b/y", "a/x"], "reasoning": "low", "max_tokens": 1500}
    assert data["bakeoff"]["triage"] == ["a/x", "b/y", "c/z"] and load_llm_config(path)["tasks"]["triage"]
````

Acrescentar ao final de `tests/test_cli.py`:

````python
def test_parse_eval_commands():
    ns = parse_args(["eval", "golden", "draft", "--vault", "V", "--n", "40"])
    assert (ns.eval_command, ns.action, ns.vault, ns.n, ns.dir) == ("golden", "draft", "V", 40, "tests/evals/triage")
    ns = parse_args(["eval", "models", "--models", "a/b,c/d", "--apply"])
    assert (ns.eval_command, ns.task, ns.models, ns.apply, ns.limit) == ("models", "triage", "a/b,c/d", True, 0)
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_evals.py tests/test_cli.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.evals'`.

- [ ] **Passo 3: Criar `sotawhat/evals/__init__.py` vazio e `sotawhat/evals/golden.py`**

````python
# sotawhat/evals/golden.py
"""Triage golden set (SDD §6.7, §12). `draft` samples items to label (SQLite store and, optionally, the
old Obsidian vault) into a Markdown file you edit by hand; `import` reads your labels back into the
JSONL that `sotawhat eval models` uses. Labels: incluir (main) · radar · excluir (reject)."""
import json
import random
import re
from pathlib import Path

from sotawhat.items import Item, to_item
from sotawhat.models import Result

LABELS = {"incluir": "main", "radar": "radar", "excluir": "reject"}
FOLDER = Path("tests/evals/triage")
_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_ID = re.compile(r"^`id: (.+?)`\s*$", re.M)
_LABEL = re.compile(r"^r[óo]tulo:[ \t]*(.*)$", re.M | re.I)
_PMID_URL = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)")
_HF_URL = re.compile(r"huggingface\.co/papers/(\d{4}\.\d{4,5})")


def _entry(item, origin) -> dict:
    return {"id": item.id, "profile": item.profile or "", "source": item.source, "title": item.title,
            "url": item.url, "published_at": item.published_at, "authors": item.authors, "text": item.text,
            "origin": origin, "label": None, "note": ""}


def read_vault(vault) -> list:
    """Notes written by sotawhat 2.0: <vault>/<profile>/<source>/<note>.md, JSON-valued frontmatter."""
    out = []
    for path in sorted(Path(vault).glob("*/*/*.md")):
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        match = _FRONT.match(text)
        if not match:
            continue
        meta = {}
        for line in match.group(1).splitlines():
            key, _, value = line.partition(": ")
            try:
                meta[key] = json.loads(value)
            except ValueError:
                meta[key] = value.strip()
        body = re.sub(r"^\s*# .*\n", "", text[match.end():], count=1)
        body = re.sub(r"\*\*Conceitos:\*\*.*", "", body)
        body = re.sub(r"\[Source\]\(.*\)\s*$", "", body.strip()).strip()
        url, source = meta.get("url", ""), meta.get("source", "")
        rid = (_PMID_URL.search(url) or _HF_URL.search(url))
        result = Result(id=rid.group(1) if rid else "", title=meta.get("title", ""), authors=meta.get("authors", []),
                        date=meta.get("date", ""), url=url, abstract=body, source=source)
        out.append(_entry(to_item(result, profile=path.parts[-3]), "vault"))
    return out


def from_store(store) -> list:
    from sotawhat.items import from_row

    return [_entry(from_row(row), "store") for row in store.conn.execute("SELECT * FROM items")]


def sample(candidates, n=60, seed=13, min_chars=300) -> list:
    """Half per profile; inside a profile, round-robin over sources, so no source dominates."""
    rng = random.Random(seed)
    unique = {}
    for c in candidates:
        if c["title"] and len(c["text"] or "") >= min_chars and "removido" not in c["title"]:
            unique.setdefault(c["id"], c)
    by_profile = {}
    for c in unique.values():
        by_profile.setdefault(c["profile"], {}).setdefault(c["source"], []).append(c)
    picks = []
    quota = max(1, n // max(1, len(by_profile)))
    for profile in sorted(by_profile):
        pools = [sorted(v, key=lambda c: c["id"]) for _, v in sorted(by_profile[profile].items())]
        for pool in pools:
            rng.shuffle(pool)
        taken = 0
        while taken < quota and any(pools):
            for pool in pools:
                if pool and taken < quota:
                    picks.append(pool.pop())
                    taken += 1
    rng.shuffle(picks)
    return picks[:n]


def _excerpt(text, n=700) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n - 1] + "…"


def write_draft(entries, folder=FOLDER, name="golden_v1") -> tuple:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    jsonl, md = folder / f"{name}.jsonl", folder / f"{name}.md"
    jsonl.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")
    lines = [f"# Golden set da triagem — {name} ({len(entries)} itens)", "",
             'Como rotular: depois de "Rótulo:", escreva uma destas palavras:',
             "- **incluir**: vai para os principais do digest (IA/ML com aplicação médico-hospitalar plausível);",
             "- **radar**: IA de fronteira sem ponte médica clara (vira 1 linha no radar);",
             "- **excluir**: ruído (pesquisa clínica sem IA, IA genérica, marketing, opinião).",
             "Nota opcional depois de \" — \". Ex.: `Rótulo: excluir — só epidemiologia`. "
             "Itens sem rótulo ficam fora da avaliação.",
             f"Quando terminar: `sotawhat eval golden import` (atualiza `{name}.jsonl`).", ""]
    for n, e in enumerate(entries, 1):
        lines += ["---", "", f"## {n} · {e['profile']} · {e['source']}", f"**{e['title']}**",
                  f"{e['url']} · {e['published_at'] or 's/ data'}", f"> {_excerpt(e['text'])}",
                  f"`id: {e['id']}`", "Rótulo: ", ""]
    md.write_text("\n".join(lines), encoding="utf-8")
    return md, jsonl


def import_labels(folder=FOLDER, name="golden_v1") -> dict:
    folder = Path(folder)
    jsonl, md = folder / f"{name}.jsonl", folder / f"{name}.md"
    entries = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {e["id"]: e for e in entries}
    report = {"labeled": 0, "unlabeled": 0, "invalid": []}
    for block in md.read_text(encoding="utf-8").split("\n## ")[1:]:
        found_id, found_label = _ID.search(block), _LABEL.search(block)
        if not found_id or found_id.group(1) not in by_id:
            continue
        entry = by_id[found_id.group(1)]
        raw = (found_label.group(1) if found_label else "").strip()
        word, _, note = raw.partition(" — ")
        word = word.strip().lower().rstrip(".")
        if not word:
            entry["label"], entry["note"] = None, ""
            report["unlabeled"] += 1
        elif word in LABELS:
            entry["label"], entry["note"] = LABELS[word], note.strip()
            report["labeled"] += 1
        else:
            report["invalid"].append(f"{found_id.group(1)}: '{raw}'")
    jsonl.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")
    return report


def load_golden(path) -> list:
    path = Path(path)
    if not path.exists():
        return []
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [e for e in entries if e.get("label") in LABELS.values()]


def as_item(entry) -> Item:
    return Item(id=entry["id"], kind="paper", source=entry["source"], source_id="", title=entry["title"],
                url=entry["url"], authors=list(entry.get("authors") or []),
                published_at=entry.get("published_at") or "", text=entry.get("text") or "",
                profile=entry.get("profile"))
````

- [ ] **Passo 4: Criar `sotawhat/evals/bakeoff.py`**

````python
# sotawhat/evals/bakeoff.py
"""`sotawhat eval models` (SDD §6.6, §12, D15): the golden set through each candidate model, one model
at a time and without fallbacks, against your labels. Compares agreement (F1 of "incluir", accuracy over
the 3 labels), valid JSON on the first try, failures, latency and real cost; writes a report to
data/evals/ and, with --apply, puts the winner first in config/llm.yaml."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import yaml

from sotawhat.evals.golden import as_item
from sotawhat.llm.gateway import LLMFailure
from sotawhat.llm.schemas import TriageOutput
from sotawhat.pipeline.triage import decide, messages_for, system_prompt

LABEL_PT = {"main": "incluir", "radar": "radar", "reject": "excluir"}


@dataclass
class Outcome:
    item_id: str
    label: str
    predicted: str | None      # None = the model failed on this item
    first_try_valid: bool
    latency_ms: int
    summary: str = ""
    why: str = ""
    error: str | None = None


def evaluate_model(gateway, golden, rubric, model, concurrency=4) -> list:
    system = system_prompt()

    def one(entry):
        item = as_item(entry)
        try:
            res = gateway.structured_call("triage", messages_for(item, rubric, system), TriageOutput, models=(model,))
        except LLMFailure as exc:
            return Outcome(entry["id"], entry["label"], None, False, 0, error=str(exc)[:200])
        decision, _ = decide(res.output, 5, rubric, item.source)   # golden items are judged as new (D = 5)
        return Outcome(entry["id"], entry["label"], decision, res.first_try_valid, res.latency_ms,
                       res.output.summary_pt, res.output.why_it_matters_pt)

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        return list(pool.map(one, golden))


def metrics(outcomes) -> dict:
    n = len(outcomes) or 1
    tp = sum(o.predicted == "main" and o.label == "main" for o in outcomes)
    fp = sum(o.predicted == "main" and o.label != "main" for o in outcomes)
    fn = sum(o.predicted != "main" and o.label == "main" for o in outcomes)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    latencies = sorted(o.latency_ms for o in outcomes if o.predicted is not None)

    def pct(q):
        return latencies[min(len(latencies) - 1, int(q * len(latencies)))] if latencies else 0

    confusion = {}
    for o in outcomes:
        row = confusion.setdefault(o.label, {})
        row[o.predicted or "falha"] = row.get(o.predicted or "falha", 0) + 1
    return {"n": len(outcomes), "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "precision": precision, "recall": recall,
            "accuracy": sum(o.predicted == o.label for o in outcomes) / n,
            "valid_first_try": sum(o.first_try_valid for o in outcomes) / n,
            "failures": sum(o.predicted is None for o in outcomes),
            "p50_ms": pct(0.5), "p95_ms": pct(0.95), "confusion": confusion}


def model_costs(store, run_id) -> dict:
    rows = store.conn.execute("SELECT requested_model, COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE run_id = ?"
                              " GROUP BY requested_model", (run_id,)).fetchall()
    return {r[0]: r[1] for r in rows}


def pick_winner(results, min_valid=0.9, max_failure_rate=0.05):
    """Best F1 among models with enough valid JSON and few failures; ties broken by accuracy, then cost."""
    eligible = [(m, r) for m, r in results.items()
                if r["valid_first_try"] >= min_valid and r["failures"] <= max_failure_rate * r["n"]]
    if not eligible:
        return None
    return max(eligible, key=lambda mr: (round(mr[1]["f1"], 3), round(mr[1]["accuracy"], 3),
                                         -mr[1].get("cost_usd", 0.0)))[0]


def ranking(results, winner) -> list:
    rest = sorted((m for m in results if m != winner), key=lambda m: (-results[m]["f1"], results[m].get("cost_usd", 0)))
    return ([winner] if winner else []) + rest


def render_report(task, day, results, outcomes, golden, winner) -> str:
    def pct(x):
        return f"{100 * x:.0f}%"

    labels = {lab: sum(1 for g in golden if g["label"] == lab) for lab in LABEL_PT}
    out = [f"# Bake-off · {task} · {day}", "",
           f"Golden set: {len(golden)} itens rotulados (incluir {labels['main']} · radar {labels['radar']} · "
           f"excluir {labels['reject']}). Cada modelo roda sozinho, sem fallback, com o prompt e a rubrica atuais.",
           "", "| Modelo | F1 incluir | Precisão | Recall | Acurácia (3 rótulos) | JSON válido de 1ª | Falhas | "
               "Custo total | Custo/item | p50 | p95 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, r in sorted(results.items(), key=lambda mr: -mr[1]["f1"]):
        per_item = r.get("cost_usd", 0.0) / max(1, r["n"])
        out.append(f"| {'**' + m + '**' if m == winner else m} | {r['f1']:.2f} | {pct(r['precision'])} | "
                   f"{pct(r['recall'])} | {pct(r['accuracy'])} | {pct(r['valid_first_try'])} | {r['failures']} | "
                   f"US$ {r.get('cost_usd', 0.0):.4f} | US$ {per_item:.5f} | {r['p50_ms'] / 1000:.1f} s | "
                   f"{r['p95_ms'] / 1000:.1f} s |")
    out += ["", f"**Vencedor:** {winner or 'nenhum modelo passou nos critérios (JSON válido ≥ 90%, falhas ≤ 5%)'}.",
            "Critério: maior F1 de \"incluir\"; desempate por acurácia e depois custo.", ""]
    out += ["## Matrizes de confusão (linha = seu rótulo, coluna = decisão do modelo)", ""]
    for m, r in results.items():
        cols = ["main", "radar", "reject", "falha"]
        out += [f"**{m}**", "", "| | " + " | ".join(LABEL_PT.get(c, c) for c in cols) + " |",
                "|---|" + "---|" * len(cols)]
        for lab in ("main", "radar", "reject"):
            row = r["confusion"].get(lab, {})
            out.append(f"| {LABEL_PT[lab]} | " + " | ".join(str(row.get(c, 0)) for c in cols) + " |")
        out.append("")
    sample = [g for g in golden if g["label"] == "main"][:5] or golden[:5]
    out += ["## Português: amostra para você julgar", ""]
    for g in sample:
        out += [f"### {g['title']}", ""]
        for m, items in outcomes.items():
            o = next((x for x in items if x.item_id == g["id"]), None)
            if o and o.predicted:
                out += [f"- **{m}** ({LABEL_PT[o.predicted]}): {o.summary} — *{o.why}*"]
        out.append("")
    return "\n".join(out)


def apply_winner(path, task, models, reasoning, max_tokens) -> None:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = data or {}
    data.setdefault("tasks", {})[task] = {"models": list(models), "reasoning": reasoning, "max_tokens": max_tokens}
    header = ("# config/llm.yaml — modelos por etapa (SDD §6.6). Reescrito por `sotawhat eval models --apply`;\n"
              "# o relatório que justificou a ordem está em data/evals/. SOTAWHAT_MODEL_<ETAPA> ainda vence.\n")
    path.write_text(header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
````

- [ ] **Passo 5: Criar `sotawhat/evals/commands.py`**

````python
# sotawhat/evals/commands.py
"""`sotawhat eval golden draft|import` and `sotawhat eval models`."""
from datetime import date
from pathlib import Path


def main_golden(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.evals.golden import from_store, import_labels, read_vault, sample, write_draft
    from sotawhat.store.db import Store

    folder = Path(ns.dir)
    if ns.action == "import":
        report = import_labels(folder, ns.name)
        print(f"rotulados {report['labeled']} · sem rótulo {report['unlabeled']}")
        for bad in report["invalid"]:
            print(f"rótulo inválido (use incluir, radar ou excluir): {bad}")
        return 1 if report["invalid"] else 0
    if (folder / f"{ns.name}.md").exists() and not ns.force:
        print(f"{folder / (ns.name + '.md')} já existe (pode ter rótulos seus); use --force para sobrescrever")
        return 2
    settings = load_settings()
    with Store(settings.db_path) as store:
        candidates = from_store(store)
    if ns.vault:
        candidates += read_vault(ns.vault)
    entries = sample(candidates, ns.n, seed=ns.seed)
    md, _ = write_draft(entries, folder, ns.name)
    print(f"{len(entries)} itens em {md}: rotule e rode `sotawhat eval golden import`")
    return 0


def main_models(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.configfiles import load_config
    from sotawhat.evals.bakeoff import (apply_winner, evaluate_model, metrics, model_costs, pick_winner, ranking,
                                        render_report)
    from sotawhat.evals.golden import load_golden
    from sotawhat.llm.gateway import BudgetExceeded, LLMGateway
    from sotawhat.llm.openrouter import InsufficientCredits, OpenRouterClient
    from sotawhat.llm.tasks import resolve
    from sotawhat.pipeline.triage import DEFAULT_COST_PER_ITEM
    from sotawhat.store.db import Store

    settings = load_settings()
    config = load_config(settings.sotawhat_config_dir)
    golden = load_golden(ns.golden)[:ns.limit or None]
    if not golden:
        print("golden set sem rótulos: rode `sotawhat eval golden draft`, rotule o .md e `sotawhat eval golden import`")
        return 2
    if not settings.openrouter_api_key:
        print("sem OPENROUTER_API_KEY no .env")
        return 2
    spec = resolve(ns.task, settings, config.llm["tasks"])
    candidates = ns.models.split(",") if ns.models else (config.llm["bakeoff"].get(ns.task) or list(spec.models))
    results, outcomes = {}, {}
    with Store(settings.db_path) as store:
        run_id = store.start_run("eval")
        client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                                  app_title=settings.openrouter_app_title)
        gateway = LLMGateway(client, store=store, settings=settings, run_id=run_id, tasks=config.llm["tasks"])
        estimate = (store.avg_llm_cost(ns.task) or DEFAULT_COST_PER_ITEM) * len(candidates) * len(golden)
        print(f"bake-off {ns.task}: {len(candidates)} modelos × {len(golden)} itens · estimativa ≈ US$ {estimate:.2f}")
        try:
            for model in candidates:
                outcomes[model] = evaluate_model(gateway, golden, config.rubric, model, ns.concurrency)
                results[model] = metrics(outcomes[model])
                r = results[model]
                print(f"  {model}: F1 {r['f1']:.2f} · acurácia {100 * r['accuracy']:.0f}% · "
                      f"JSON de 1ª {100 * r['valid_first_try']:.0f}% · falhas {r['failures']}")
        except (BudgetExceeded, InsufficientCredits) as exc:
            print(f"interrompido: {exc}")
        for model, cost in model_costs(store, run_id).items():
            if model in results:
                results[model]["cost_usd"] = cost
        store.finish_run(run_id, ok=bool(results), stats={"task": ns.task, "models": list(results),
                                                          "golden": len(golden)})
    winner = pick_winner(results)
    folder = settings.sotawhat_data_dir / "evals"
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{date.today().isoformat()}-{ns.task}-bakeoff.md"
    out.write_text(render_report(ns.task, date.today().isoformat(), results, outcomes, golden, winner), encoding="utf-8")
    print(f"[relatório] {out}\nvencedor: {winner or 'nenhum'}")
    if ns.apply and winner:
        apply_winner(settings.sotawhat_config_dir / "llm.yaml", ns.task, ranking(results, winner),
                     spec.reasoning, spec.max_tokens)
        print(f"config/llm.yaml: {ns.task} agora começa por {winner}")
    return 0 if results else 1


def main_eval(ns) -> int:
    return main_golden(ns) if ns.eval_command == "golden" else main_models(ns)
````

- [ ] **Passo 6: Comando `eval` em `sotawhat/cli.py`**

6a. `_SUBCOMMANDS`: acrescentar `"eval"`.

6b. Logo depois de `p_feedback.add_argument("action", choices=["pull", "listen"])`:

````python

    p_eval = sub.add_parser("eval")
    eval_sub = p_eval.add_subparsers(dest="eval_command", required=True)
    p_golden = eval_sub.add_parser("golden")
    p_golden.add_argument("action", choices=["draft", "import"])
    p_golden.add_argument("--n", type=int, default=60)
    p_golden.add_argument("--vault", default=None, help="also sample notes from the old Obsidian vault")
    p_golden.add_argument("--dir", default="tests/evals/triage")
    p_golden.add_argument("--name", default="golden_v1")
    p_golden.add_argument("--seed", type=int, default=13)
    p_golden.add_argument("--force", action="store_true", help="overwrite an existing draft")
    p_models = eval_sub.add_parser("models")
    p_models.add_argument("--task", default="triage", choices=["triage"])
    p_models.add_argument("--models", default=None, help="comma-separated OpenRouter ids (default: llm.yaml bakeoff)")
    p_models.add_argument("--golden", default="tests/evals/triage/golden_v1.jsonl")
    p_models.add_argument("--limit", type=int, default=0)
    p_models.add_argument("--concurrency", type=int, default=4)
    p_models.add_argument("--apply", action="store_true", help="put the winner first in config/llm.yaml")
````

6c. No `main`, depois do ramo `feedback`:

```python
    elif ns.command == "eval":
        from sotawhat.evals.commands import main_eval
        raise SystemExit(main_eval(ns))
```

- [ ] **Passo 7: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `158 passed`.

- [ ] **Passo 8: Commit**

```bash
git add sotawhat/evals sotawhat/cli.py tests/test_evals.py tests/test_cli.py
git commit -m "feat: golden set (draft, import) and model bake-off with report and --apply"
```

---

## Tarefa 12: `doctor` da P1

O comando passa a verificar também:
- os YAMLs de `config/`;
- os candidatos do bake-off no catálogo do OpenRouter: endpoints ZDR e raciocínio aceito;
- se o modelo de embeddings já está em cache; se não estiver, avisa que o próximo run baixa ~1,2 GB;
- o classificador de cada perfil: votos acumulados, versão e F1;
- a idade da última coleta de votos (o Telegram descarta votos após 24 h);
- o golden set rotulado.

**Files:**
- Modify: `sotawhat/doctor.py` (substituir o conteúdo inteiro)
- Create: `tests/test_doctor_p1.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_doctor_p1.py`:

````python
# tests/test_doctor_p1.py
import json
from datetime import datetime, timedelta, timezone

from sotawhat.config import Settings
from sotawhat.doctor import (check_classifiers, check_config, check_embeddings, check_feedback, check_golden,
                             model_requirements)
from sotawhat.pipeline.feedback import HEARTBEAT_KEY, LAST_PULL_KEY
from sotawhat.store.db import Store

NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)


def test_requirements_cover_llm_yaml_and_bakeoff():
    llm = {"tasks": {"triage": {"models": ["a/x", "b/y"], "reasoning": "low"}},
           "bakeoff": {"triage": ["c/z"]}}
    needs = model_requirements(Settings(_env_file=None), llm)
    assert needs["a/x"] == {"low"} and needs["c/z"] == {"low"}
    assert "deepseek/deepseek-v4.1-flash-1017" in needs     # other tasks keep their defaults


def test_config_check(tmp_path):
    check, config = check_config(tmp_path)
    assert check.status == "warn" and config.rubric.min_total == 3.2       # no files: defaults
    (tmp_path / "rubric.yaml").write_text("weights: {A: 0.5, B: 0.5}\n", encoding="utf-8")
    check, config = check_config(tmp_path)
    assert check.status == "fail" and config is None and "somando 1" in check.detail


def test_embeddings_check(tmp_path):
    assert check_embeddings(Settings(_env_file=None, embeddings_backend="hash")).status == "warn"
    settings = Settings(_env_file=None, sotawhat_data_dir=tmp_path)
    assert check_embeddings(settings).status == "warn"                     # not downloaded yet
    (tmp_path / "models" / "fastembed" / "models--onnx-community--embeddinggemma-300m-ONNX").mkdir(parents=True)
    assert check_embeddings(settings).status == "ok"
    bad = Settings(_env_file=None, embeddings_model="nope/nope")
    assert check_embeddings(bad).status == "fail"


def test_classifier_feedback_and_golden_checks(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        [check] = check_classifiers(st, "m", 100, ["medico"])
        assert "0/100 votos" in check.detail
        st.record_classifier("medico-1", "medico", "m", 120, {"n": 120, "f1": 0.81, "auc": 0.9}, tmp_path / "c.pkl")
        assert "F1 0.81" in check_classifiers(st, "m", 100, ["medico"])[0].detail
        assert check_feedback(st, NOW).status == "warn"
        st.meta_set(LAST_PULL_KEY, (NOW - timedelta(hours=30)).isoformat())
        assert "24 h" in check_feedback(st, NOW).detail
        st.meta_set(LAST_PULL_KEY, (NOW - timedelta(hours=2)).isoformat())
        assert check_feedback(st, NOW).status == "ok"
        st.meta_set(HEARTBEAT_KEY, (NOW - timedelta(seconds=30)).isoformat())
        assert "listen" in check_feedback(st, NOW).detail
    path = tmp_path / "golden.jsonl"
    assert check_golden(path).status == "warn"
    path.write_text("".join(json.dumps({"id": str(i), "label": "main"}) + "\n" for i in range(50)), encoding="utf-8")
    assert check_golden(path).status == "ok"
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_doctor_p1.py -q`
Expected: FAIL com `ImportError: cannot import name 'check_classifiers' from 'sotawhat.doctor'`.

- [ ] **Passo 3: Substituir `sotawhat/doctor.py`**

````python
# sotawhat/doctor.py
"""`sotawhat doctor [--llm]`: configuration, keys, models, last run and spend (SDD §6.12)."""
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pydantic import BaseModel

from sotawhat.llm.tasks import resolve

TASKS = ("triage", "segment", "vision", "extract", "synth")
_BAD_QUANT = {"fp4", "mxfp4", "nvfp4", "int4", "fp6"}


@dataclass
class Check:
    name: str
    status: str   # "ok" | "warn" | "fail"
    detail: str


class Smoke(BaseModel):
    ok: bool
    idioma: str


def model_requirements(settings=None, llm_config=None) -> dict:
    """model -> set of reasoning efforts it must accept, over every task chain and bake-off candidate."""
    overrides = (llm_config or {}).get("tasks")
    chains = [(task, resolve(task, settings, overrides).models) for task in TASKS]
    chains += [(task, tuple(models)) for task, models in ((llm_config or {}).get("bakeoff") or {}).items()]
    needs = {}
    for task, models in chains:
        reasoning = resolve(task, settings, overrides).reasoning
        for model in models:
            needs.setdefault(model, set())
            if reasoning:
                needs[model].add(reasoning)
    return needs


def check_config(config_dir):
    from sotawhat.configfiles import ConfigError, load_config

    try:
        config = load_config(config_dir)
    except ConfigError as exc:
        return Check("config/*.yaml", "fail", str(exc)), None
    present = [n for n in ("rubric.yaml", "mute.yaml", "llm.yaml") if (Path(config_dir) / n).exists()]
    status = "ok" if len(present) == 3 else "warn"
    return Check("config/*.yaml", status, f"{', '.join(present) or 'nenhum arquivo'} (padrões do código no resto)"), config


def check_embeddings(settings) -> Check:
    if settings.embeddings_backend == "hash":
        return Check("embeddings", "warn", "backend hash (só para testes): novidade e classificador fracos")
    cache = settings.models_dir / "fastembed"
    try:
        from fastembed import TextEmbedding

        hf = next(m["sources"]["hf"] for m in TextEmbedding.list_supported_models()
                  if m["model"] == settings.embeddings_model)
    except StopIteration:
        return Check("embeddings", "fail", f"{settings.embeddings_model} não é suportado pelo fastembed")
    except Exception as exc:  # noqa: BLE001
        return Check("embeddings", "fail", f"fastembed indisponível: {exc}")
    if (cache / f"models--{hf.replace('/', '--')}").exists():
        return Check("embeddings", "ok", f"{settings.embeddings_model} em cache")
    return Check("embeddings", "warn", f"{settings.embeddings_model} ainda não baixado: o próximo run baixa ~1,2 GB "
                                       f"para {cache}")


def check_classifiers(store, embed_model, min_ratings, profiles) -> list:
    from sotawhat.store.classifier import NEGATIVE, POSITIVE

    checks = []
    for profile in profiles:
        votes = sum(1 for v in store.item_votes(profile=profile).values() if v in POSITIVE | NEGATIVE)
        row = store.latest_classifier(profile, embed_model)
        if row is None:
            checks.append(Check(f"classificador {profile}", "ok",
                                f"{votes}/{min_ratings} votos; até lá o LLM vê todos os itens"))
            continue
        m = json.loads(row["metrics_json"] or "{}")
        checks.append(Check(f"classificador {profile}", "ok",
                            f"{row['version']}: {m.get('n')} votos · F1 {m.get('f1', '?')} · AUC {m.get('auc', '?')}"))
    return checks


def check_feedback(store, now=None) -> Check:
    from sotawhat.pipeline.feedback import LAST_PULL_KEY, listener_active

    now = now or datetime.now(timezone.utc)
    if listener_active(store, now):
        return Check("votos do Telegram", "ok", "`feedback listen` ativo")
    last = store.meta_get(LAST_PULL_KEY)
    if not last:
        return Check("votos do Telegram", "warn", "nenhuma coleta de votos ainda")
    age = (now - datetime.fromisoformat(last)).total_seconds() / 3600
    if age > 20:
        return Check("votos do Telegram", "warn", f"última coleta há {age:.0f} h; o Telegram descarta votos após "
                                                  "24 h (rode o run diário ou `sotawhat feedback listen`)")
    return Check("votos do Telegram", "ok", f"última coleta há {age:.0f} h")


def check_golden(path) -> Check:
    from sotawhat.evals.golden import load_golden

    labeled = len(load_golden(path))
    if labeled >= 50:
        return Check("golden set", "ok", f"{labeled} itens rotulados")
    if labeled:
        return Check("golden set", "warn", f"{labeled} itens rotulados (meta ≥ 50 para o bake-off)")
    return Check("golden set", "warn", "nenhum item rotulado: `sotawhat eval golden draft --vault <vault>`")


def check_settings(settings) -> list:
    checks = [Check("OPENROUTER_API_KEY", "ok" if settings.openrouter_api_key else "fail",
                    "definida" if settings.openrouter_api_key else "ausente no .env")]
    private = settings.openrouter_zdr and settings.openrouter_data_collection == "deny"
    checks.append(Check("privacidade LLM", "ok" if private else "warn",
                        f"zdr={settings.openrouter_zdr} data_collection={settings.openrouter_data_collection}"))
    telegram = bool(settings.telegram_bot_token and settings.telegram_chat_id)
    checks.append(Check("Telegram", "ok" if telegram else "warn",
                        "configurado" if telegram else "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes"))
    return checks


def check_openrouter_key(client) -> Check:
    try:
        info = client.key_info() or {}
    except Exception as exc:  # noqa: BLE001
        return Check("chave OpenRouter", "fail", str(exc))
    usage = info.get("usage_monthly", info.get("usage")) or 0.0
    limit = info.get("limit")
    if limit is None:
        return Check("chave OpenRouter", "warn",
                     f"válida, SEM limite de gasto (uso no mês US$ {usage:.2f}); defina um limite mensal na chave")
    remaining = info.get("limit_remaining")
    low = remaining is not None and remaining < 0.2 * limit
    rest = f"US$ {remaining:.2f}" if remaining is not None else "?"
    return Check("chave OpenRouter", "warn" if low else "ok",
                 f"limite US$ {limit:.2f} · restante {rest} · uso no mês US$ {usage:.2f}")


def check_models(client, requirements, today=None) -> list:
    today = today or date.today()
    try:
        catalog = {m["id"]: m for m in client.models()}
        zdr = client.zdr_endpoints()
    except Exception as exc:  # noqa: BLE001
        return [Check("catálogo OpenRouter", "fail", str(exc))]
    eligible = {}
    for ep in zdr:
        if ep.get("quantization") in _BAD_QUANT or "structured_outputs" not in (ep.get("supported_parameters") or []):
            continue
        eligible[ep.get("model_id")] = eligible.get(ep.get("model_id"), 0) + 1
    checks = []
    for model, efforts in requirements.items():
        meta = catalog.get(model)
        if meta is None:
            checks.append(Check(model, "fail", "não existe mais no catálogo do OpenRouter"))
            continue
        reasoning = meta.get("reasoning") or {}
        supported = reasoning.get("supported_efforts")
        bad = sorted(e for e in efforts if (supported and e not in supported)
                     or (e == "none" and reasoning.get("mandatory")))
        if bad:
            checks.append(Check(model, "fail", f"não aceita raciocínio {bad} (aceita {supported})"))
            continue
        count = eligible.get(model, 0)
        if count == 0:
            checks.append(Check(model, "fail", "nenhum endpoint ZDR elegível (≥ fp8 + saída estruturada)"))
            continue
        expires = meta.get("expiration_date")
        if expires and date.fromisoformat(expires[:10]) - today <= timedelta(days=30):
            checks.append(Check(model, "warn", f"expira em {expires[:10]}; {count} endpoints ZDR elegíveis"))
            continue
        checks.append(Check(model, "ok", f"{count} endpoints ZDR elegíveis"))
    return checks


def check_telegram(notifier) -> Check:
    try:
        me = notifier.get_me()
    except Exception as exc:  # noqa: BLE001
        return Check("bot do Telegram", "fail", str(exc))
    return Check("bot do Telegram", "ok", f"@{me.get('username', '?')}")


def check_last_run(store, now=None, max_age_hours=36) -> Check:
    now = now or datetime.now(timezone.utc)
    row = store.last_run("daily")
    if row is None:
        return Check("último run diário", "warn", "nenhum run registrado ainda")
    if not row["ok"]:
        return Check("último run diário", "fail", f"falhou em {row['finished_at']}: {row['error']}")
    age = (now - datetime.fromisoformat(row["finished_at"])).total_seconds() / 3600
    if age > max_age_hours:
        return Check("último run diário", "warn", f"último sucesso há {age:.0f} h; o agendamento está ativo?")
    return Check("último run diário", "ok", f"concluído há {age:.0f} h")


def check_month_cost(store, budget_month, now=None) -> Check:
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    spent = store.llm_cost_since(start)
    status = "warn" if spent >= 0.8 * budget_month else "ok"
    return Check("custo LLM no mês", status, f"US$ {spent:.4f} de US$ {budget_month:.2f}")


def llm_smoke(gateway, models) -> list:
    prompt = [{"role": "user", "content": 'Responda apenas com o JSON {"ok": true, "idioma": "pt-BR"}.'}]
    checks = []
    for model in models:
        try:
            out = gateway.structured("smoke", prompt, Smoke, models=(model,))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check(f"fumaça {model}", "fail", f"{type(exc).__name__}: {exc}"))
            continue
        checks.append(Check(f"fumaça {model}", "ok" if out.ok else "warn", f"JSON válido · idioma={out.idioma}"))
    return checks


def render(checks) -> str:
    tag = {"ok": "OK  ", "warn": "WARN", "fail": "FAIL"}
    return "\n".join(f"[{tag[c.status]}] {c.name}: {c.detail}" for c in checks)


def main_doctor(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.llm.gateway import LLMGateway
    from sotawhat.llm.openrouter import OpenRouterClient
    from sotawhat.notify.telegram import TelegramNotifier
    from sotawhat.store.db import Store

    from sotawhat.profiles import PROFILES

    settings = load_settings()
    checks = check_settings(settings)
    config_check, config = check_config(settings.sotawhat_config_dir)
    checks.append(config_check)
    llm_config = config.llm if config else None
    client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url)
    if settings.openrouter_api_key:
        checks.append(check_openrouter_key(client))
    checks += check_models(client, model_requirements(settings, llm_config))
    checks.append(check_embeddings(settings))
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if notifier.configured:
        checks.append(check_telegram(notifier))
    with Store(settings.db_path) as store:
        checks.append(check_last_run(store))
        checks.append(check_month_cost(store, settings.sotawhat_llm_budget_usd_month))
        min_ratings = config.rubric.classifier_min_ratings if config else 100
        checks += check_classifiers(store, settings.embeddings_model, min_ratings, list(PROFILES))
        if notifier.configured:
            checks.append(check_feedback(store))
        checks.append(check_golden("tests/evals/triage/golden_v1.jsonl"))
        if ns.llm:
            if settings.openrouter_api_key:
                overrides = llm_config["tasks"] if llm_config else None
                primaries = list(dict.fromkeys(resolve(t, settings, overrides).models[0] for t in TASKS))
                checks += llm_smoke(LLMGateway(client, store=store, settings=settings, tasks=overrides), primaries)
            else:
                checks.append(Check("fumaça LLM", "fail", "sem OPENROUTER_API_KEY"))
    print(render(checks))
    return 1 if any(c.status == "fail" for c in checks) else 0
````

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `162 passed`.

- [ ] **Passo 5: Commit**

```bash
git add sotawhat/doctor.py tests/test_doctor_p1.py
git commit -m "feat: doctor checks config, embeddings cache, classifiers, vote freshness and golden set"
```

---

## Tarefa 13: Ouvinte de votos no agendamento, README e `.env.example`

**Files:**
- Modify: `scripts/schedule_daily.ps1` (substituir o conteúdo inteiro), `README.md`, `.env.example`

- [ ] **Passo 1: Substituir `scripts/schedule_daily.ps1`** (somente ASCII)

O que muda:
- `-Listener` registra também a tarefa `sotawhat-feedback`, que roda ao fazer logon com `pythonw.exe`, sem janela.
- Ela reinicia sozinha até 3 vezes e não tem limite de tempo.
- Sem a opção, o comportamento é o do P0.

````powershell
# scripts/schedule_daily.ps1 - registers `sotawhat run daily` in Windows Task Scheduler (SDD 6.12).
# Usage, from the repository root in PowerShell:
#   .\scripts\schedule_daily.ps1                         # 07:00, no Obsidian export
#   .\scripts\schedule_daily.ps1 -Vault "D:\Lucas\obsidian_vaults\ml_ai_med_vault"
#   .\scripts\schedule_daily.ps1 -Listener               # also: Telegram feedback listener at logon (P1)
# Runs as the current user while logged on; a missed run starts as soon as possible (StartWhenAvailable).
param(
    [string]$Time = "07:00",
    [string]$Vault = "",
    [string]$TaskName = "sotawhat-daily",
    [switch]$Listener
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
$exe = Join-Path $repo ".venv\Scripts\sotawhat.exe"
if (-not (Test-Path $exe)) { throw "Not found: $exe - install first: uv pip install -e .[dev]" }
if (-not (Test-Path (Join-Path $repo ".env"))) { Write-Warning "No .env in $repo - copy .env.example to .env and fill it in." }

$arguments = "run daily"
if ($Vault) { $arguments += " --vault `"$Vault`"" }

# WorkingDirectory = repo root, so the `.env` file, `config\` and `data\insight.db` are found.
$action = New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "sotawhat 3.0 - coleta diaria + resumo no Telegram" -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State

if ($Listener) {
    # Votes on the Telegram buttons are acknowledged within seconds instead of at the next daily run.
    # pythonw.exe has no console window; output goes to data\logs. Restarts if it crashes.
    $pythonw = Join-Path $repo ".venv\Scripts\pythonw.exe"
    if (-not (Test-Path $pythonw)) { throw "Not found: $pythonw" }
    $listen = New-ScheduledTaskAction -Execute $pythonw -Argument "-m sotawhat.cli feedback listen" -WorkingDirectory $repo
    $logon = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
    $listenSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
    Register-ScheduledTask -TaskName "sotawhat-feedback" -Action $listen -Trigger $logon -Settings $listenSettings `
        -Description "sotawhat 3.0 - votos do Telegram em tempo real" -Force | Out-Null
    Get-ScheduledTask -TaskName "sotawhat-feedback" | Select-Object TaskName, State
}
````

Validar a sintaxe sem registrar nada:

```powershell
$t=$null; $e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile("$PWD\scripts\schedule_daily.ps1",[ref]$t,[ref]$e); if ($e.Count -eq 0) {"parse OK"} else {$e}
```

Expected: `parse OK`.

- [ ] **Passo 2: README**

Na seção `## 3.0 (in progress): insight engine`, substituir o parágrafo que começa com `To set it up, copy` por:

````markdown
Phase P1 adds the triage and the real digest:

- Every new item goes through stage A without LLM: mute filters (`config/mute.yaml`), same-story
  dedup on near-identical titles, local embeddings (EmbeddingGemma-300m via `fastembed`, CPU,
  downloaded once to `data/models/`) and a novelty score. Then the LLM rubric
  (`config/rubric.yaml`, prompt `sotawhat/llm/prompts/triage_v1.md`) scores frontier AI,
  medical applicability and actionability with strict JSON, inside the daily budget.
- The digest goes to Telegram (up to 15 main items with 👍 👎 🧪 buttons, plus a radar of
  frontier AI without a medical bridge) and to `data/digests/YYYY-MM-DD.md` and `.html`.
  Nothing relevant and nothing broken means nothing is sent.
- `sotawhat feedback pull|listen` records the votes; after 100 votes a profile gets its own
  classifier (logistic regression over the embeddings), which then decides what reaches the LLM.
- `sotawhat eval golden draft|import` builds a golden set that you label by editing a Markdown
  file, and `sotawhat eval models [--apply]` runs the bake-off of triage models against it
  and can put the winner first in `config/llm.yaml`.

To set it up, copy `.env.example` to `.env` and fill in at least `OPENROUTER_API_KEY`,
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Then schedule the daily run with
`powershell -ExecutionPolicy Bypass -File scripts\schedule_daily.ps1 [-Vault PATH] [-Listener]`.
````

- [ ] **Passo 3: `.env.example`**

3a. Trocar a linha `EMBEDDINGS_BACKEND=…` por:

```
EMBEDDINGS_BACKEND=fastembed           # fastembed (local, CPU, grátis) | hash (só testes)
EMBEDDINGS_MODEL=google/embeddinggemma-300m   # 768-d, multilíngue, ~1,2 GB baixados uma vez para data/models/
```

3b. Trocar a linha `TELEGRAM_ALLOWED_USER_ID=…` por:

```
TELEGRAM_ALLOWED_USER_ID=              # só este usuário vota/manda links (vazio = o próprio TELEGRAM_CHAT_ID)
```

3c. Trocar `SOTAWHAT_LOG_LEVEL=INFO` por:

```
SOTAWHAT_LOG_LEVEL=INFO                # log diário em data/logs/AAAA-MM-DD.log
# SOTAWHAT_CONFIG_DIR=./config         # rubric.yaml, mute.yaml, llm.yaml
```

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `162 passed`.

- [ ] **Passo 5: Commit**

```bash
git add scripts/schedule_daily.ps1 README.md .env.example
git commit -m "feat: optional Telegram vote listener at logon; P1 docs and env vars"
```

---

## Tarefa 14: Verificação manual com rede (precisa dos pré-requisitos)

1. **`.\.venv\Scripts\sotawhat doctor`**
   - Esperado: `[OK]` para chave, privacidade, YAMLs, os 6 modelos das etapas e os 4 candidatos do bake-off, Telegram e classificadores ("0/100 votos").
   - Também esperado: `[WARN] embeddings … ainda não baixado` e `[WARN] golden set`.
2. **`.\.venv\Scripts\sotawhat doctor --llm`.** Esperado: fumaça OK nos 2 modelos primários.
3. **`.\.venv\Scripts\sotawhat run daily --no-notify --limit 3`**
   - O primeiro run baixa o EmbeddingGemma, ~1,2 GB e alguns minutos.
   - Ele também tria os pendentes do P0 (até `backlog_days`) e os novos, ≈ US$ 0,05.
   - Esperado: o digest impresso, com principais, radar e notas; os arquivos `data/digests/AAAA-MM-DD.md` e `.html`.
   - Conferir as decisões e o custo:

   ```powershell
   .\.venv\Scripts\python -c "import sqlite3; c=sqlite3.connect('data/insight.db'); print(c.execute('select decision, count(*) from triage group by decision').fetchall()); print(c.execute(\"select model, count(*), round(sum(cost_usd),4) from llm_calls where task='triage' group by model\").fetchall())"
   ```

   Ler 5 resumos em português no `.md` do dia. Se o tom ou o critério estiverem ruins, ajustar `triage_v1.md`, salvar como `triage_v2.md` e mudar `PROMPT_VERSION`, sempre com o teste do prompt verde.
4. **`.\.venv\Scripts\sotawhat run daily --limit 3`**
   - Esperado no Telegram: o cabeçalho, uma mensagem por item principal com 👍 👎 🧪 e a mensagem do radar.
   - Tocar 👍 num item e rodar `.\.venv\Scripts\sotawhat feedback pull`. Esperado: `votos 1`, e o botão passa a mostrar ✅👍.
5. **Golden set.**
   - Se ainda não existir: `.\.venv\Scripts\sotawhat eval golden draft --vault "D:\Lucas\obsidian_vaults\ml_ai_med_vault"`.
   - Você rotula `tests/evals/triage/golden_v1.md` e roda `.\.venv\Scripts\sotawhat eval golden import`. Esperado: "rotulados ≥ 50" e nenhum rótulo inválido.
   - Commit: `git add tests/evals/triage && git commit -m "test: triage golden set v1 labeled by the user"`.
6. **Bake-off:** `.\.venv\Scripts\sotawhat eval models`, 4 modelos × ~60 itens, ≈ US$ 0,10–0,30.
   - Ler `data/evals/AAAA-MM-DD-triage-bakeoff.md` com você: tabela, matrizes de confusão e amostra em português.
   - **Se você concordar com o vencedor:** `.\.venv\Scripts\sotawhat eval models --apply`, que roda de novo e reescreve `config/llm.yaml`, e então `git commit -am "chore: triage model chosen by bake-off"`. Para não pagar a segunda rodada, dá para editar `config/llm.yaml` à mão com a ordem do relatório.
7. **Pedir confirmação ao usuário antes de mexer no Task Scheduler**, depois registrar:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\schedule_daily.ps1 -Vault "D:\Lucas\obsidian_vaults\ml_ai_med_vault" -Listener
   Start-ScheduledTask -TaskName sotawhat-feedback
   ```

   Depois de ~1 min, `.\.venv\Scripts\sotawhat doctor` deve mostrar `[OK] votos do Telegram: feedback listen ativo`.

---

## Notas de autorrevisão

- **Cobertura da spec (SDD §11, P1):**

  | Entrega da P1 | Onde |
  |---|---|
  | *mute filters* | Tarefas 1 e 7 |
  | rubrica e prompt v1 | Tarefas 1 e 3 |
  | saída estruturada | Tarefas 3 e 4 |
  | dedup semântico com embeddings locais | Tarefas 5 e 7 (ajustado pela medição: título para fundir, embedding para D) |
  | classificador por perfil a partir de 100 avaliações | Tarefas 6 e 7 |
  | digest MD/HTML/Telegram com botões | Tarefas 8 e 10 |
  | feedback persistido | Tarefas 9, 10 e 13 |
  | golden set inicial (50 itens) | Tarefas 11 e 14 |
  | bake-off e `config/llm.yaml` | Tarefas 1, 11 e 14 |

  Critérios de aceite:
  - "digest diário com ≤ 15 itens": `main_limit` e `test_digest_ranks_limits_and_renders`;
  - "feedback persistido": `test_votes_are_recorded_acknowledged_and_shown`;
  - "modelo de triagem escolhido por dados": Tarefa 14, passo 6.
- **Consistência de nomes:**
  - `TriageStats` é criado em `triage.py`, guardado em `DailyReport.triage` e lido por `deliver.build_digest`.
  - `item_key` e `keyboard` saem de `deliver.py`, e `feedback.py` os reutiliza.
  - `structured_call` é usado pela triagem e pelo bake-off; `structured` continua para o `doctor`.
  - `load_config` é usado por `run daily`, `eval models` e `doctor`.
- **Privacidade:**
  - todas as chamadas continuam pelo gateway do P0, com ZDR e `data_collection: "deny"`;
  - `llm_calls` não guarda texto;
  - o texto de itens com dado de paciente identificável é apagado;
  - só o usuário autorizado vota;
  - o log não grava corpo de requisição nem token.
- **Sem rede nos testes:** fakes, `MockTransport` e `HashEmbedder`. Nenhum modelo é baixado durante os testes.
- **Limites conhecidos, para as próximas fases:**
  - os limiares de D precisam de recalibração depois de 2 semanas de dados (`embeddings_dedup.md`);
  - notícias da mesma história com títulos diferentes ainda não são fundidas; o juiz LLM entra na P2;
  - o classificador ainda não usa sinais sociais (P2);
  - a captura manual fica em `inbox`, sem processamento (P5);
  - o prompt v1 ainda não foi testado contra modelos reais; o bake-off da Tarefa 14 é o primeiro teste e pode levar a um `triage_v2`.

---

## Adendo: execução (2026-11-08)

A P1 foi executada na branch `feature/insight-engine-p1`, criada a partir do P0, com um commit por tarefa. As Tarefas 0 a 13 seguiram o plano sem desvio. Em cada uma, o teste novo falhou antes da implementação e a suíte passou depois, com as mesmas contagens do plano (107 → 162).

### Mudanças além do plano (cada uma com TDD e commit próprio)

| Mudança | Motivo | O que mudou | Suíte |
|---|---|---|---|
| Duas seções | No golden set, 24 dos 51 itens "incluir" eram IA de fronteira sem ligação com saúde. O usuário escolheu "Duas seções" | Nova decisão `frontier`: `A ≥ 4`, substância ≥ 2 e `0,60·A + 0,25·C + 0,15·D − penalidades ≥ limiar`. Limites: 10 em "IA ∩ Saúde", 5 em "Fronteira de IA" (🔭 no Telegram; o excedente desce para o radar) e 10 no radar. O prompt deixou de pedir pontes médicas inventadas, e `generic_ai_no_bridge` vale só para notícia sem substância. O bake-off conta `frontier` como "incluir" e grava as notas de cada item | 162 → 165 |
| Isolamento dos testes | O `.env` real passou a ter chaves vivas | `conftest.py` desliga a leitura de `.env` em todos os testes | 165 → 166 |
| E-mail | Pedido do usuário | `notify/email.py` (STARTTLS na 587, TLS na 465), ativado por `DIGEST_EMAIL_TO`; reaproveita `GMAIL_ADDRESS` e `GMAIL_APP_PASSWORD`. Uma senha sem o formato de senha de app é recusada antes de conectar. HTML só com estilos inline | 166 → 171 |
| `doctor`: Telegram e SMTP | O `TELEGRAM_CHAT_ID` estava com o nome do bot, e o `doctor` do P0 mostrava "configurado" | Um chat id que não é número falha. O `getChat` confirma o chat; se falhar, o `doctor` sugere o número de quem mandou `/start`. Login SMTP sem envio | 171 → 175 |
| `doctor`: modelo fixado no `.env` | `SOTAWHAT_MODEL_TRIAGE` no `.env` passava por cima do vencedor do bake-off | O `doctor` avisa; no `.env.example`, `SOTAWHAT_MODEL_*` agora vem vazio; o bake-off também guarda `vendor_only` | 175 → 176 |
| Português sem CJK | O MiniMax pôs caracteres chineses em 13 de 60 resumos no bake-off e em 15 de 84 no primeiro run real | Um validador em `TriageOutput` trata o texto com CJK como inválido, e o gateway pede de novo ou passa para o próximo modelo | 176 → 178 |

### Tarefa 14: resultados

1. **`.env`**: preenchido pelo usuário, que renomeou o `.env.example`; o modelo foi restaurado do git.
   - O `TELEGRAM_CHAT_ID` continha o nome do bot. Foi trocado pelo número do chat, obtido com `getUpdates` depois do `/start` e confirmado com `getChat`.
   - A `GMAIL_APP_PASSWORD` tinha 9 caracteres, ou seja, não é uma senha de app. A cópia por e-mail fica pendente até o usuário criar uma.
   - A linha `SOTAWHAT_MODEL_TRIAGE` foi esvaziada.
2. **`doctor`** passou: chave com limite de US$ 5, os 6 modelos com endpoints ZDR, embeddings em cache (copiados do benchmark, sem novo download) e bot chegando ao chat privado. A única falha é a esperada no e-mail. **`doctor --llm`**: DeepSeek e MiMo responderam JSON válido em pt-BR.
3. **Golden set**: 60 itens rotulados (incluir 51, radar 6, excluir 3). Commit `test: triage golden set v1 labeled by the user`.
4. **Bake-off** (4 modelos × 60 itens, US$ 0,094, cerca de 25 min), com a rubrica do plano:

   | Modelo | F1 "incluir" | Precisão | Recall | Acurácia | JSON válido de 1ª | US$/item | p50 |
   |---|---|---|---|---|---|---|---|
   | minimax/minimax-m3.1-flash | 0,80 | 85% | 76% | 68% | 100% | 0,00048 | 4,4 s |
   | z-ai/glm-5.3-flash | 0,71 | 88% | 59% | 55% | 100% | 0,00019 | 6,4 s |
   | deepseek/deepseek-v4.1-flash-1017 | 0,63 | 84% | 51% | 48% | 97% | 0,00035 | 6,5 s |
   | xiaomi/mimo-v2.6-flash | 0,62 | 86% | 49% | 48% | 77% | 0,00055 | 4,9 s |

5. **Calibração** (as notas guardadas foram redecididas, sem novas chamadas ao LLM). A rubrica do plano descartava a IA aplicada típica (A3 B3 C1 = 2,8 < 3,2). Valores aplicados em `config/rubric.yaml`:
   - `min_total` 3,2 → 2,8;
   - `frontier_min_total` 3,6 → 3,3;
   - `min_b` 2 → 3: no primeiro run, papers gerais com "ponte plausível" (B2) ocupavam "IA ∩ Saúde"; no golden, a métrica não muda.

   Com a rubrica calibrada, e contando o texto com CJK como inválido:

   | Modelo | F1 | Precisão | Recall | Acurácia | Válido de 1ª |
   |---|---|---|---|---|---|
   | **deepseek/deepseek-v4.1-flash-1017** | 0,89 | 90% | 88% | 80% | 97% |
   | z-ai/glm-5.3-flash | 0,87 | 90% | 84% | 77% | 100% |
   | minimax/minimax-m3.1-flash | 0,92 | 88% | 96% | 85% | 78% (abaixo do mínimo de 90%) |
   | xiaomi/mimo-v2.6-flash | 0,84 | 87% | 80% | 73% | 77% |

   Cadeia em `config/llm.yaml`: DeepSeek → GLM → MiniMax.

   Ressalva: o golden tem só 3 "excluir" e 6 "radar", então a precisão contra ruído real ainda não foi medida. Os votos das primeiras semanas recalibram.
6. **Primeiro run real** (`run daily --limit 5`, cerca de 2,5 min, US$ 0,033):
   - 78 coletados, 44 novos e 84 triados (com os 40 pendentes do P0), ainda pelo MiniMax: 55 em `main`, 9 em `frontier` e 20 em `reject`;
   - o Telegram recebeu 10 + 5 itens com botões e 4 linhas de radar;
   - o e-mail foi recusado antes de conectar (senha de app ausente), como esperado;
   - o Semantic Scholar devolveu 429 de novo (sem chave de API);
   - os dois problemas desse run (texto com CJK e IA geral em "IA ∩ Saúde") levaram às correções das linhas 5 e 6 da tabela de mudanças.
7. **Agendamento** (autorizado pelo usuário): `schedule_daily.ps1 -Vault "D:\Lucas\obsidian_vaults\ml_ai_med_vault" -Listener`.
   - `sotawhat-daily`: pronto, próximo run em 2026-11-09 às 07:00.
   - `sotawhat-feedback`: iniciado com `Start-ScheduledTask`; o sinal de vida aparece em `meta`.
8. **Merge e push** (autorizados): `feature/insight-engine-p0` e `feature/insight-engine-p1` entram no `master` com `--no-ff`, como nas branches anteriores, e o `master` vai para `origin`.

**Pendências do usuário:**
- criar a senha de app do Gmail (`GMAIL_APP_PASSWORD`);
- votar nos itens do digest;
- opcionalmente, obter as chaves do Lens.org e do EPO OPS (usadas só na P4).
