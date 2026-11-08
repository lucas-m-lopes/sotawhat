# Insight Engine · P0 Fundação — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA — use `superpowers:subagent-driven-development` (recomendado) ou `superpowers:executing-plans` para executar este plano tarefa a tarefa. Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** criar a fundação do sotawhat 3.0:
- configuração por `.env`;
- registro operacional em SQLite;
- itens normalizados com ids canônicos;
- gateway de LLM pelo OpenRouter, com modelos chineses, só endpoints ZDR, JSON estrito e custo real;
- correção dos feeds da Nature, que devolvem HTML anti-bot;
- `run daily` agendável com resumo no Telegram;
- `doctor`.

**Arquitetura:** o `run daily` reaproveita os adapters e os perfis atuais (`collect` + `filter_relevant`). Cada `Result` vira um `Item` com id canônico (DOI > arXiv > PMID > URL), deduplicado no SQLite. A saúde de cada fonte e subfeed fica em `source_state`. O resumo vai pelo Telegram. A camada LLM (cliente OpenRouter + gateway por tarefa) ainda não tem consumidores no pipeline. Ela entra pronta e testada, e o `doctor --llm` a exercita contra a API real; a triagem a usa na P1.

**Stack:** Python 3.12 · `httpx` · `feedparser` · `pydantic` 2 · `pydantic-settings` 2 · `truststore` · `sqlite3` (stdlib) · `pytest`. APIs: OpenRouter (Chat Completions, `/key`, `/models`, `/endpoints/zdr`), Telegram Bot API e Crossref REST.

**Spec:** `docs/sdd/2026-11-07-insight-engine-sdd.md`: §6.4 (SQLite), §6.6 (camada LLM), §6.12 (operação), §6.13 (segurança) e §11 (P0). Evidência dos modelos e preços: `docs/research/2026-11-07-insight-engine/llm_openrouter.md`.

**Validação prévia (2026-11-07):** todo o código abaixo rodou numa cópia isolada do repositório, com venv próprio.
- 107 testes passando: os 49 antigos e 58 novos.
- `sotawhat doctor` contra o catálogo real do OpenRouter: os 6 modelos configurados têm endpoints ZDR elegíveis e níveis de raciocínio compatíveis.
- `sotawhat run daily --no-notify --limit 2` real: 39 itens de 10 fontes; Crossref/npj Digital Medicine OK; o `429` do Semantic Scholar sem chave foi sinalizado como fonte com falha.

**Convenções:**
- Comandos em PowerShell, a partir da raiz do repositório; o venv é `.venv` (Python 3.12.4).
- Testes **sem rede** (fixtures, `httpx.MockTransport`, `monkeypatch`); rede só na verificação manual da Tarefa 11.
- O repositório usa `core.autocrlf=true`. Prefira edições pontuais em arquivos existentes; quando o plano manda substituir o arquivo inteiro, o git normaliza o final de linha no commit.
- Um commit por tarefa, na branch `feature/insight-engine-p0`.

**Fora do escopo do P0:** triagem/rubrica, embeddings, classificador, digest com ranking e *bake-off* (P1); novas fontes como Gmail, GitHub, HF Hub e registries (P2); Neo4j/`compose.yaml` (P3); ideação (P4); Instagram (P5).

---

## Pré-requisitos do usuário (só para a verificação manual da Tarefa 11)

1. **OpenRouter:**
   - Credits: comprar US$ 10.
   - Keys: criar a chave `sotawhat` com **limite mensal de US$ 30**.
   - Settings → Privacy: ligar ZDR em "All other models" e manter o *logging* desligado.
2. **Telegram:**
   - No @BotFather, rodar `/newbot` e guardar o token.
   - Mandar `/start` para o bot.
   - Abrir `https://api.telegram.org/bot<TOKEN>/getUpdates` e copiar `message.chat.id`.
3. **`.env`:** `Copy-Item .env.example .env` e preencher `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` e, opcionalmente, `CROSSREF_MAILTO`.

---

## Estrutura de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `pyproject.toml` | Modificar | versão 3.0.0.dev0, Python ≥ 3.11, deps `pydantic`, `pydantic-settings`, `truststore` |
| `sotawhat/config.py` | Criar | `Settings` (env + `.env`), sobrescrita de modelo por tarefa |
| `sotawhat/store/__init__.py`, `sotawhat/store/db.py` | Criar | SQLite: `items`, `runs`, `source_state`, `llm_calls`, `meta` |
| `sotawhat/items.py` | Criar | `Item`, `canonical_id`, `normalize_url`, `to_item` |
| `sotawhat/sources/rss.py` | Substituir | `FeedError` para HTML, 1 fetch por feed por run, `feed_errors` |
| `sotawhat/sources/crossref.py` | Criar | `CrossrefJournalSource` (periódicos por ISSN) |
| `sotawhat/profiles.py` | Modificar | Nature/npj/NEJM AI via Crossref; remove The Gradient; `build_sources(..., crossref_mailto)` |
| `sotawhat/llm/__init__.py`, `sotawhat/llm/openrouter.py` | Criar | cliente HTTP: payload com ZDR/JSON estrito/fallbacks, retries, `usage.cost` |
| `sotawhat/llm/tasks.py` | Criar | matriz tarefa → modelos/raciocínio/max_tokens |
| `sotawhat/llm/gateway.py` | Criar | `structured()`: schema estrito, reparo, fallback, orçamento, ledger |
| `sotawhat/notify/__init__.py`, `sotawhat/notify/telegram.py` | Criar | envio com quebra em 4.096 caracteres; erros sem o token |
| `sotawhat/digest.py` | Modificar | `collect(..., on_source_error=)` |
| `sotawhat/pipeline/__init__.py`, `sotawhat/pipeline/daily.py` | Criar | `run_daily`, `render_summary`, `main_daily` |
| `sotawhat/doctor.py` | Criar | verificações e teste de fumaça dos modelos |
| `sotawhat/cli.py` | Modificar | subcomandos `run daily` e `doctor`; `truststore`; stdout tolerante |
| `scripts/schedule_daily.ps1` | Criar | registra `sotawhat-daily` no Task Scheduler |
| `README.md` | Modificar | seção 3.0 e Python 3.11+ |
| `tests/conftest.py` + `tests/test_{config,store,items,crossref,openrouter,gateway,telegram,daily,doctor}.py` | Criar | testes novos |
| `tests/test_{rss,profiles,digest,cli}.py` | Modificar | casos novos |
| `tests/fixtures/{nature_challenge.html,crossref_works.json,openrouter/chat_ok.json}` | Criar | fixtures |

---

## Tarefa 0: Branch e linha de base

- [ ] **Passo 1: Criar a branch**

```powershell
git checkout -b feature/insight-engine-p0
```

- [ ] **Passo 2: Confirmar a suíte atual**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `49 passed`.

---

## Tarefa 1: Dependências e `Settings`

**Files:**
- Modify: `pyproject.toml`
- Create: `sotawhat/config.py`, `tests/conftest.py`, `tests/test_config.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/conftest.py`:

````python
# tests/conftest.py
import os

import pytest

_PREFIXES = ("SOTAWHAT_", "OPENROUTER_", "TELEGRAM_", "CROSSREF_")


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    """Tests never see the developer's real keys (a real `.env` is avoided per test)."""
    for key in list(os.environ):
        if key.startswith(_PREFIXES):
            monkeypatch.delenv(key, raising=False)
````

Create `tests/test_config.py`:

````python
# tests/test_config.py
from pathlib import Path

import pytest

from sotawhat.config import Settings, load_settings


@pytest.fixture(autouse=True)
def _in_empty_dir(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no stray `.env` from the repository root


def test_defaults_are_private_and_cheap():
    s = load_settings()
    assert s.openrouter_zdr is True
    assert s.openrouter_data_collection == "deny"
    assert s.quantizations == ["fp8", "bf16", "fp16", "fp32", "unknown"]
    assert s.sotawhat_llm_budget_usd_day == 1.0
    assert s.db_path == Path("data") / "insight.db"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("OPENROUTER_ZDR", "false")
    monkeypatch.setenv("SOTAWHAT_MODEL_TRIAGE", "xiaomi/mimo-v2.6-flash")
    monkeypatch.setenv("SOTAWHAT_LLM_BUDGET_USD_DAY", "0.5")
    s = load_settings()
    assert s.openrouter_zdr is False
    assert s.model_override("triage") == "xiaomi/mimo-v2.6-flash"
    assert s.model_override("extract") == ""
    assert s.sotawhat_llm_budget_usd_day == 0.5


def test_reads_dotenv_in_working_directory(tmp_path):
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=sk-test\nTELEGRAM_CHAT_ID=42\n", encoding="utf-8")
    s = Settings()
    assert s.openrouter_api_key == "sk-test"
    assert s.telegram_chat_id == "42"
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_config.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.config'`.

- [ ] **Passo 3: Atualizar `pyproject.toml`** (substituir o conteúdo inteiro)

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
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
sotawhat = "sotawhat.cli:main"

[tool.setuptools.packages.find]
include = ["sotawhat*"]
````

- [ ] **Passo 4: Instalar as dependências**

Run: `uv pip install --python .\.venv\Scripts\python.exe -e ".[dev]"`
Expected: instala `pydantic`, `pydantic-settings` e `truststore` (versões validadas: 2.14.3, 2.16.2, 0.10.x).

- [ ] **Passo 5: Criar `sotawhat/config.py`**

````python
# sotawhat/config.py
"""Runtime settings: environment variables + optional `.env` in the working directory."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_QUANTIZATIONS = "fp8,bf16,fp16,fp32,unknown"
LLM_TASKS = ("triage", "segment", "vision", "extract", "synth")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    sotawhat_data_dir: Path = Path("./data")
    sotawhat_tz: str = "America/Sao_Paulo"
    sotawhat_log_level: str = "INFO"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_zdr: bool = True
    openrouter_data_collection: str = "deny"
    openrouter_quantizations: str = DEFAULT_QUANTIZATIONS
    openrouter_app_title: str = ""

    sotawhat_model_triage: str = ""
    sotawhat_model_segment: str = ""
    sotawhat_model_vision: str = ""
    sotawhat_model_extract: str = ""
    sotawhat_model_synth: str = ""

    sotawhat_llm_budget_usd_day: float = 1.0
    sotawhat_llm_budget_usd_run_weekly: float = 8.0
    sotawhat_llm_budget_usd_month: float = 25.0

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    crossref_mailto: str = ""

    @property
    def db_path(self) -> Path:
        return self.sotawhat_data_dir / "insight.db"

    @property
    def quantizations(self) -> list[str]:
        return [q.strip() for q in self.openrouter_quantizations.split(",") if q.strip()]

    def model_override(self, task: str) -> str:
        return getattr(self, f"sotawhat_model_{task}", "") or ""


def load_settings(**overrides) -> Settings:
    return Settings(**overrides)
````

- [ ] **Passo 6: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `52 passed`.

- [ ] **Passo 7: Commit**

```bash
git add pyproject.toml sotawhat/config.py tests/conftest.py tests/test_config.py
git commit -m "feat: settings from .env with private-by-default LLM config"
```

---

## Tarefa 2: Registro operacional em SQLite

**Files:**
- Create: `sotawhat/store/__init__.py` (vazio), `sotawhat/store/db.py`, `tests/test_store.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_store.py`:

````python
# tests/test_store.py
import json
from types import SimpleNamespace

from sotawhat.store.db import Store


def _item(iid, concepts=("k1",)):
    return SimpleNamespace(
        id=iid, kind="paper", source="arxiv", source_id=iid.split(":")[-1], url=f"https://x/{iid}",
        doi=None, arxiv_id=None, pmid=None, title=f"T {iid}", authors=["A"], published_at="2026-11-07",
        text="abstract", content_hash="h", concepts=list(concepts), profile="geral")


def test_schema_created(tmp_path):
    with Store(tmp_path / "db" / "insight.db") as st:
        names = {r[0] for r in st.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"items", "runs", "source_state", "llm_calls", "meta"} <= names
        version = st.conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        assert version == "1"


def test_upsert_dedupes_and_merges_concepts(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        assert st.upsert_items([_item("arxiv:1"), _item("arxiv:2")], run) == ["arxiv:1", "arxiv:2"]
        assert st.upsert_items([_item("arxiv:1", concepts=("k2",))], run) == []
        assert st.count_items() == 2
        row = st.conn.execute("SELECT concepts_json FROM items WHERE id='arxiv:1'").fetchone()
        assert json.loads(row[0]) == ["k1", "k2"]


def test_run_lifecycle_sums_llm_cost(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        run = st.start_run("daily")
        for cost in (0.01, 0.02):
            st.record_llm_call(run_id=run, task="triage", requested_model="m", status="ok", cost_usd=cost)
        st.finish_run(run, ok=True, stats={"collected": 3})
        last = st.last_run("daily")
        assert last["ok"] == 1
        assert abs(last["cost_usd"] - 0.03) < 1e-9
        assert json.loads(last["stats_json"]) == {"collected": 3}


def test_source_failures_count_and_reset(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        assert st.record_source_error("medical/nature", "HTML") == 1
        assert st.record_source_error("medical/nature", "HTML") == 2
        st.record_source_ok("medical/nature")
        assert st.source_states()[0]["consecutive_failures"] == 0


def test_llm_cost_since_and_unknown_field_guard(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        st.record_llm_call(task="smoke", requested_model="m", status="ok", cost_usd=0.5)
        assert st.llm_cost_since("2000-01-01T00:00:00+00:00") == 0.5
        assert st.llm_cost_since("2999-01-01T00:00:00+00:00") == 0
        try:
            st.record_llm_call(task="x", requested_model="m", status="ok", prompt="secret")
        except ValueError as exc:
            assert "prompt" in str(exc)
        else:
            raise AssertionError("unknown field accepted")
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_store.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.store'`.

- [ ] **Passo 3: Implementar**

Create `sotawhat/store/__init__.py` vazio e `sotawhat/store/db.py`:

````python
# sotawhat/store/db.py
"""SQLite operational store (SDD §6.4): items, runs, source health and LLM cost ledger."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1

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

_LLM_FIELDS = ("run_id", "task", "requested_model", "model", "provider", "generation_id",
               "input_tokens", "output_tokens", "reasoning_tokens", "cached_tokens",
               "cost_usd", "latency_ms", "status", "error")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)",
                          (str(SCHEMA_VERSION),))
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

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
        cur = self.conn.execute(
            f"INSERT INTO llm_calls({', '.join(cols)}) VALUES({', '.join('?' * len(cols))})", vals)
        self.conn.commit()
        return cur.lastrowid

    def llm_cost_since(self, since_iso: str) -> float:
        return self.conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM llm_calls WHERE created_at >= ?",
                                 (since_iso,)).fetchone()[0]
````

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `57 passed`.

- [ ] **Passo 5: Commit**

```bash
git add sotawhat/store tests/test_store.py
git commit -m "feat: SQLite operational store (items, runs, source health, LLM ledger)"
```

---

## Tarefa 3: `Item` e ids canônicos

**Files:**
- Create: `sotawhat/items.py`, `tests/test_items.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_items.py`:

````python
# tests/test_items.py
from sotawhat.items import canonical_id, normalize_url, to_item
from sotawhat.models import Result


def _r(rid, source, url="", **extra):
    return Result(id=rid, title="T", authors=["A"], date="2026-11-07", url=url,
                  abstract="abs", source=source, extra=extra)


def test_arxiv_and_hf_share_the_same_id():
    a = canonical_id(_r("2511.01234", "arxiv", "http://arxiv.org/abs/2511.01234v2"))
    h = canonical_id(_r("2511.01234", "hf_papers", "https://huggingface.co/papers/2511.01234"))
    assert a[0] == h[0] == "arxiv:2511.01234"


def test_doi_wins_over_url_and_is_lowercased():
    iid, ids = canonical_id(_r("10.1038/S41746-026-03450-3", "semantic_scholar", "https://x.org/p"))
    assert iid == "doi:10.1038/s41746-026-03450-3"
    assert ids == {"doi": "10.1038/s41746-026-03450-3"}
    assert canonical_id(_r("doi:10.1056/aie2601363", "crossref:nejm-ai"))[0] == "doi:10.1056/aie2601363"


def test_pubmed_pmid_and_url_fallback():
    assert canonical_id(_r("41234567", "pubmed"))[0] == "pmid:41234567"
    iid, _ = canonical_id(_r("https://Lab.example/Post/?utm_source=x&id=7#frag", "rss:lab",
                             "https://Lab.example/Post/?utm_source=x&id=7#frag"))
    assert iid == "url:https://lab.example/Post?id=7"


def test_normalize_url_strips_tracking_only():
    assert normalize_url("https://a.com/x/?fbclid=1&q=2") == "https://a.com/x?q=2"


def test_to_item_maps_fields_and_concepts():
    it = to_item(_r("2511.01234", "arxiv", "u", concepts=["agent"]), profile="geral")
    assert (it.id, it.kind, it.arxiv_id, it.concepts, it.profile) == (
        "arxiv:2511.01234", "paper", "2511.01234", ["agent"], "geral")
    assert to_item(_r("https://b.org/p", "rss:lab", "https://b.org/p")).kind == "article"
    assert len(it.content_hash) == 40
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_items.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.items'`.

- [ ] **Passo 3: Implementar `sotawhat/items.py`**

````python
# sotawhat/items.py
"""Normalized `Item` (SDD §6.4) and canonical ids for exact dedup across sources."""
import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+)", re.I)
_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
_ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", re.I)
_PMID_RE = re.compile(r"^\d{1,9}$")
_TRACKING = {"fbclid", "gclid", "ref", "ref_src", "_hsenc", "_hsmi", "mc_cid", "mc_eid", "_bhlid",
             "ck_subscriber_id"}


@dataclass
class Item:
    id: str
    kind: str
    source: str
    source_id: str
    title: str
    url: str
    authors: list = field(default_factory=list)
    published_at: str = ""
    text: str = ""
    doi: str | None = None
    arxiv_id: str | None = None
    pmid: str | None = None
    concepts: list = field(default_factory=list)
    profile: str | None = None

    @property
    def content_hash(self) -> str:
        basis = " ".join(f"{self.title} {self.text}".lower().split())
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in _TRACKING]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def _clean_doi(doi: str) -> str:
    return doi.strip().rstrip(".,;)").lower()


def canonical_id(result) -> tuple[str, dict]:
    """Return (id, extra ids). Priority: DOI > arXiv > PMID > URL > content hash."""
    extra = result.extra or {}
    rid = (result.id or "").strip()
    url = (result.url or "").strip()

    doi = extra.get("doi")
    if not doi and rid.lower().startswith("doi:"):
        doi = rid[4:]
    if not doi:
        match = _DOI_RE.search(rid) or _DOI_RE.search(url)
        doi = match.group(1) if match else None
    if doi:
        doi = _clean_doi(doi)
        return f"doi:{doi}", {"doi": doi}

    arxiv = None
    if result.source in ("arxiv", "hf_papers") and _ARXIV_ID_RE.match(rid):
        arxiv = rid
    else:
        match = _ARXIV_URL_RE.search(url) or _ARXIV_URL_RE.search(rid)
        arxiv = match.group(1) if match else None
    if arxiv:
        return f"arxiv:{arxiv}", {"arxiv_id": arxiv}

    if result.source == "pubmed" and _PMID_RE.match(rid):
        return f"pmid:{rid}", {"pmid": rid}

    if url.startswith(("http://", "https://")):
        return f"url:{normalize_url(url)}", {}
    if rid:
        return f"{result.source}:{rid}", {}
    digest = hashlib.sha1(f"{result.title}|{result.source}".encode("utf-8")).hexdigest()[:16]
    return f"hash:{digest}", {}


def kind_for(source: str) -> str:
    if source.startswith("rss:"):
        return "article"
    return "paper"


def to_item(result, profile: str | None = None) -> Item:
    iid, ids = canonical_id(result)
    return Item(
        id=iid, kind=kind_for(result.source), source=result.source, source_id=result.id or "",
        title=result.title, url=result.url, authors=list(result.authors or []),
        published_at=result.date or "", text=result.abstract or "",
        doi=ids.get("doi"), arxiv_id=ids.get("arxiv_id"), pmid=ids.get("pmid"),
        concepts=list((result.extra or {}).get("concepts", [])), profile=profile)
````

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `62 passed`.

- [ ] **Passo 5: Commit**

```bash
git add sotawhat/items.py tests/test_items.py
git commit -m "feat: normalized Item with canonical ids (DOI > arXiv > PMID > URL)"
```

---

## Tarefa 4: RSS — HTML anti-bot vira erro; 1 fetch por feed por run

Por quê: os feeds da Nature devolvem uma página HTML de desafio, e o `parse_feed` atual produz 0 itens sem avisar (SDD §1.3, item 9, e §5.1). Além disso, `RSSSource.search` baixava cada feed uma vez **por palavra-chave**.

**Files:**
- Modify: `sotawhat/sources/rss.py` (substituir o conteúdo inteiro)
- Create: `tests/fixtures/nature_challenge.html`
- Modify: `tests/test_rss.py` (acrescentar ao final)

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/fixtures/nature_challenge.html`:

````html
<!DOCTYPE html>
<html lang="en">
<head><title>Just a moment...</title></head>
<body><noscript>Enable JavaScript and cookies to continue</noscript></body>
</html>
````

Acrescentar ao final de `tests/test_rss.py`:

````python
def _response(content, content_type):
    import httpx
    return httpx.Response(200, headers={"content-type": content_type}, content=content,
                          request=httpx.Request("GET", "https://www.nature.com/npjdigitalmed.rss"))

def test_fetch_feed_rejects_html_challenge(monkeypatch):
    import pytest
    html = open("tests/fixtures/nature_challenge.html", "rb").read()
    monkeypatch.setattr(rssmod.httpx, "get", lambda *a, **k: _response(html, "text/html; charset=utf-8"))
    with pytest.raises(rssmod.FeedError):
        rssmod.fetch_feed("https://www.nature.com/npjdigitalmed.rss")

def test_fetch_feed_rejects_html_even_with_xml_content_type(monkeypatch):
    import pytest
    monkeypatch.setattr(rssmod.httpx, "get", lambda *a, **k: _response(b"  <html><body>x</body></html>", "application/rss+xml"))
    with pytest.raises(rssmod.FeedError):
        rssmod.fetch_feed("https://x/feed")

def test_search_records_feed_errors_and_fetches_each_feed_once(monkeypatch):
    fixture = open("tests/fixtures/sample_feed.xml", "rb").read()
    calls = []
    def fake_fetch(url):
        calls.append(url)
        if "bad" in url:
            raise rssmod.FeedError("HTML instead of a feed")
        return fixture
    monkeypatch.setattr(rssmod, "fetch_feed", fake_fetch)
    src = RSSSource("medical", [("bad", "http://bad/feed"), ("good", "http://good/feed")])
    src.search("transformer", 10)
    src.search("attention", 10)
    assert calls == ["http://bad/feed", "http://good/feed"]
    assert list(src.feed_errors) == ["bad"]
    assert "FeedError" in src.feed_errors["bad"]
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_rss.py -q`
Expected: FAIL com `AttributeError: module 'sotawhat.sources.rss' has no attribute 'FeedError'`.

- [ ] **Passo 3: Substituir `sotawhat/sources/rss.py`**

````python
# sotawhat/sources/rss.py
import feedparser
import httpx
from sotawhat.models import Result
from sotawhat.sources.base import Source

_UA = {"User-Agent": "Mozilla/5.0 (sotawhat/2.0)"}


class FeedError(Exception):
    """The URL answered, but not with a feed (e.g. an anti-bot HTML challenge page)."""


def _looks_like_html(content_type, body):
    head = body[:512].lstrip().lower()
    return "text/html" in (content_type or "").lower() or head.startswith((b"<!doctype html", b"<html"))


def fetch_feed(url):
    r = httpx.get(url, headers=_UA, timeout=30, follow_redirects=True)
    r.raise_for_status()
    if _looks_like_html(r.headers.get("content-type"), r.content):
        raise FeedError(f"HTML instead of a feed (anti-bot page?) from {url}")
    return r.content


def parse_feed(url_or_path, source):
    feed = feedparser.parse(url_or_path)
    results = []
    for e in feed.entries:
        summary = getattr(e, "summary", "") or ""
        authors = []
        if getattr(e, "author", ""):
            authors = [e.author]
        link = getattr(e, "link", "")
        results.append(Result(
            id=link or getattr(e, "id", "") or getattr(e, "title", ""),
            title=getattr(e, "title", ""), authors=authors,
            date=getattr(e, "published", "")[:16], url=link,
            abstract=summary, source=source))
    return results


class RSSSource(Source):
    def __init__(self, name, feeds):
        # feeds: list of (label, url)
        self.name = name
        self.feeds = feeds
        self.feed_errors = {}   # label -> error message (last search)
        self._cache = {}        # url -> content or exception; one fetch per feed per run

    @staticmethod
    def _filter(results, keyword, limit):
        kw = keyword.lower()
        hits = [r for r in results if kw in (r.title + " " + r.abstract).lower()]
        return hits[:limit]

    def _fetch_once(self, url):
        if url not in self._cache:
            try:
                self._cache[url] = fetch_feed(url)
            except Exception as exc:  # noqa: BLE001 - cached so a failing feed is hit once per run
                self._cache[url] = exc
        cached = self._cache[url]
        if isinstance(cached, Exception):
            raise cached
        return cached

    def search(self, keyword, limit):
        collected = []
        self.feed_errors = {}
        for label, url in self.feeds:
            try:
                content = self._fetch_once(url)
            except Exception as exc:  # noqa: BLE001 - a failing feed must not abort the others
                self.feed_errors[label] = f"{type(exc).__name__}: {exc}"
                continue
            collected.extend(parse_feed(content, source=f"rss:{label}"))
        return self._filter(collected, keyword, limit)
````

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `65 passed`. O teste antigo `test_search_skips_failing_feed` continua verde, porque `_fetch_once` chama a função global `fetch_feed`, que o teste substitui via monkeypatch.

- [ ] **Passo 5: Commit**

```bash
git add sotawhat/sources/rss.py tests/test_rss.py tests/fixtures/nature_challenge.html
git commit -m "fix: treat HTML anti-bot pages as feed errors and fetch each feed once per run"
```

---

## Tarefa 5: Fonte Crossref por ISSN e perfis atualizados

Por quê: Nature Machine Intelligence, npj Digital Medicine, Nature Medicine e NEJM AI passam a vir da API do Crossref, com ISSNs verificados em 2026-11-07. The Gradient está parado desde fevereiro de 2026 (SDD §5.1).

**Files:**
- Create: `sotawhat/sources/crossref.py`, `tests/fixtures/crossref_works.json`, `tests/test_crossref.py`
- Modify: `sotawhat/profiles.py`, `tests/test_profiles.py`

- [ ] **Passo 1: Escrever os testes da fonte (falham)**

Create `tests/fixtures/crossref_works.json` (dados sintéticos, no formato real da API):

````json
{"status": "ok", "message-type": "work-list", "message": {"total-results": 2, "items": [
 {"DOI": "10.1000/EXAMPLE.SEPSIS.1", "type": "journal-article",
  "title": ["Deep learning for early sepsis prediction in the ICU"],
  "abstract": "<jats:title>Abstract</jats:title>\n  <jats:p>We trained a transformer on 40,000 ICU stays and validated it externally.</jats:p>",
  "author": [{"given": "Ana", "family": "Souza"}, {"family": "Lima"}],
  "published": {"date-parts": [[2026, 11, 7]]},
  "container-title": ["npj Digital Medicine"], "URL": "https://doi.org/10.1000/example.sepsis.1"},
 {"DOI": "10.1000/example.ppg.2", "type": "journal-article",
  "title": ["Wrist photoplethysmography encodes dietary information"],
  "author": [{"given": "Bruno", "family": "Costa"}],
  "published": {"date-parts": [[2026, 11]]},
  "container-title": ["npj Digital Medicine"], "URL": "https://doi.org/10.1000/example.ppg.2"},
 {"type": "journal-article", "title": ["Item without DOI is skipped"]}
]}}
````

Create `tests/test_crossref.py`:

````python
# tests/test_crossref.py
import json

import httpx

import sotawhat.sources.crossref as crmod
from sotawhat.sources.crossref import CrossrefJournalSource, parse_works, strip_jats

PAYLOAD = json.load(open("tests/fixtures/crossref_works.json", encoding="utf-8"))


def test_parse_works_maps_fields_and_skips_items_without_doi():
    out = parse_works(PAYLOAD, source="crossref:npj-digital-medicine")
    assert [r.id for r in out] == ["doi:10.1000/example.sepsis.1", "doi:10.1000/example.ppg.2"]
    first = out[0]
    assert first.title == "Deep learning for early sepsis prediction in the ICU"
    assert first.authors == ["Ana Souza", "Lima"]
    assert first.date == "2026-11-07"
    assert first.abstract.startswith("We trained a transformer")
    assert first.extra == {"doi": "10.1000/example.sepsis.1", "journal": "npj Digital Medicine"}
    assert out[1].date == "2026-11"


def test_strip_jats():
    assert strip_jats("<jats:title>Abstract</jats:title><jats:p>A  b</jats:p>") == "A b"


def test_search_filters_by_keyword_fetches_once_and_sends_polite_params(monkeypatch):
    calls = []

    def fake_get(url, params=None, **kwargs):
        calls.append((url, params, kwargs["headers"]["User-Agent"]))
        return httpx.Response(200, json=PAYLOAD, request=httpx.Request("GET", url))

    monkeypatch.setattr(crmod.httpx, "get", fake_get)
    src = CrossrefJournalSource([("npj-digital-medicine", "2398-6352")], mailto="me@example.org")
    assert [r.id for r in src.search("sepsis", 10)] == ["doi:10.1000/example.sepsis.1"]
    assert src.search("photoplethysmography", 10)[0].source == "crossref:npj-digital-medicine"
    assert len(calls) == 1
    url, params, ua = calls[0]
    assert url == "https://api.crossref.org/journals/2398-6352/works"
    assert params["filter"].startswith("from-pub-date:")
    assert params["mailto"] == "me@example.org" and "mailto:me@example.org" in ua


def test_search_records_errors_per_journal(monkeypatch):
    def fake_get(url, params=None, **kwargs):
        if "0000-0000" in url:
            return httpx.Response(503, request=httpx.Request("GET", url))
        return httpx.Response(200, json=PAYLOAD, request=httpx.Request("GET", url))

    monkeypatch.setattr(crmod.httpx, "get", fake_get)
    src = CrossrefJournalSource([("down", "0000-0000"), ("npj", "2398-6352")])
    assert len(src.search("sepsis", 10)) == 1
    assert list(src.feed_errors) == ["down"]
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_crossref.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.sources.crossref'`.

- [ ] **Passo 3: Implementar `sotawhat/sources/crossref.py`**

````python
# sotawhat/sources/crossref.py
"""Recent works of a journal by ISSN via the Crossref REST API.

Replaces the Nature/npj RSS feeds, which serve an anti-bot HTML page to non-browser clients (SDD §5.1).
"""
import re
from datetime import date, timedelta

import httpx

from sotawhat.models import Result
from sotawhat.sources.base import Source

_API = "https://api.crossref.org/journals/{issn}/works"
_SELECT = "DOI,title,abstract,author,published,URL,type,container-title"
_TAG = re.compile(r"<[^>]+>")


def strip_jats(text):
    plain = " ".join(_TAG.sub(" ", text or "").split())
    return plain[9:] if plain.lower().startswith("abstract ") else plain


def _published(item):
    parts = ((item.get("published") or {}).get("date-parts") or [[]])[0]
    if not parts or parts[0] is None:
        return ""
    return "-".join([str(parts[0])] + [f"{p:02d}" for p in parts[1:3]])


def parse_works(payload, source):
    results = []
    for it in (payload.get("message") or {}).get("items", []):
        doi = (it.get("DOI") or "").lower()
        title = " ".join(it.get("title") or []).strip()
        if not doi or not title:
            continue
        authors = [" ".join(p for p in (a.get("given"), a.get("family")) if p) for a in it.get("author", [])]
        results.append(Result(
            id=f"doi:{doi}", title=" ".join(title.split()), authors=[a for a in authors if a],
            date=_published(it), url=it.get("URL") or f"https://doi.org/{doi}",
            abstract=strip_jats(it.get("abstract", "")), source=source,
            extra={"doi": doi, "journal": (it.get("container-title") or [""])[0]}))
    return results


class CrossrefJournalSource(Source):
    name = "crossref"

    def __init__(self, journals, days=7, rows=50, mailto=""):
        # journals: list of (label, ISSN) — same shape as RSSSource.feeds
        self.feeds = journals
        self.days = days
        self.rows = rows
        self.mailto = mailto
        self.feed_errors = {}
        self._cache = {}

    def _params(self):
        since = (date.today() - timedelta(days=self.days)).isoformat()
        params = {"filter": f"from-pub-date:{since}", "sort": "published", "order": "desc",
                  "rows": self.rows, "select": _SELECT}
        if self.mailto:
            params["mailto"] = self.mailto
        return params

    def _fetch_once(self, issn):
        if issn not in self._cache:
            ua = f"sotawhat/3.0 (mailto:{self.mailto})" if self.mailto else "sotawhat/3.0"
            r = httpx.get(_API.format(issn=issn), params=self._params(), timeout=30,
                          follow_redirects=True, headers={"User-Agent": ua})
            r.raise_for_status()
            self._cache[issn] = r.json()
        return self._cache[issn]

    def search(self, keyword, limit):
        collected = []
        self.feed_errors = {}
        for label, issn in self.feeds:
            try:
                payload = self._fetch_once(issn)
            except Exception as exc:  # noqa: BLE001 - one journal failing must not abort the others
                self.feed_errors[label] = f"{type(exc).__name__}: {exc}"
                continue
            collected.extend(parse_works(payload, source=f"crossref:{label}"))
        kw = keyword.lower()
        return [r for r in collected if kw in (r.title + " " + r.abstract).lower()][:limit]
````

- [ ] **Passo 4: Atualizar os testes de perfis (falham)**

Em `tests/test_profiles.py`, substituir `test_medical_feeds_curated` por:

````python
def test_medical_feeds_curated():
    from sotawhat.profiles import MEDICAL_FEEDS
    labels = [name for name, _ in MEDICAL_FEEDS]
    assert "jmir-medinform" in labels
    assert "radiology-ai" not in labels
    assert "npj-digital-medicine" not in labels   # moved to Crossref (anti-bot HTML on nature.com RSS)

def test_nature_journals_come_from_crossref():
    from sotawhat.profiles import MEDICAL_JOURNALS
    sources = build_sources("medico", crossref_mailto="me@example.org")
    cr = [s for s in sources if s.name == "crossref"][0]
    assert cr.feeds == MEDICAL_JOURNALS
    assert ("npj-digital-medicine", "2398-6352") in MEDICAL_JOURNALS
    assert cr.mailto == "me@example.org"

def test_stalled_feeds_removed():
    from sotawhat.profiles import LAB_FEEDS
    assert "the-gradient" not in [name for name, _ in LAB_FEEDS]
````

Run: `.\.venv\Scripts\python -m pytest tests/test_profiles.py -q`
Expected: FAIL (`npj-digital-medicine` ainda está em `MEDICAL_FEEDS`; `MEDICAL_JOURNALS` não existe).

- [ ] **Passo 5: Atualizar `sotawhat/profiles.py`**

5a. Acrescentar o import, logo depois de `from sotawhat.sources.rss import RSSSource`:

```python
from sotawhat.sources.crossref import CrossrefJournalSource
```

5b. Em `LAB_FEEDS`, remover a linha `("the-gradient", "https://thegradient.pub/rss/"),`.

5c. Substituir o bloco `MEDICAL_FEEDS` por:

````python
# Medical journal feeds (verified to return entries via httpx + User-Agent).
MEDICAL_FEEDS = [
    ("jmir-ai", "https://ai.jmir.org/feed/atom"),
    ("jmir-medinform", "https://medinform.jmir.org/feed/atom"),
]

# Nature/npj RSS serve an anti-bot HTML page to non-browser clients (SDD §5.1),
# so these journals come from Crossref by ISSN (verified 2026-11-07).
MEDICAL_JOURNALS = [
    ("nature-machine-intelligence", "2522-5839"),
    ("npj-digital-medicine", "2398-6352"),
    ("nature-medicine", "1546-170X"),
    ("nejm-ai", "2836-9386"),
]
````

5d. Trocar `def build_sources(profile):` por `def build_sources(profile, crossref_mailto=""):` e, no ramo `medico`, trocar `RSSSource("medical", MEDICAL_FEEDS)]` por:

```python
                RSSSource("medical", MEDICAL_FEEDS),
                CrossrefJournalSource(MEDICAL_JOURNALS, mailto=crossref_mailto)]
```

- [ ] **Passo 6: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `71 passed`.

- [ ] **Passo 7: Commit**

```bash
git add sotawhat/sources/crossref.py sotawhat/profiles.py tests/test_crossref.py tests/test_profiles.py tests/fixtures/crossref_works.json
git commit -m "fix: fetch Nature/npj/NEJM AI via Crossref by ISSN; drop stalled feed"
```

---

## Tarefa 6: Cliente OpenRouter

Pontos de projeto (SDD §6.6):
- **Privacidade obrigatória:** toda requisição leva `provider` com `zdr: true`, `data_collection: "deny"`, `require_parameters: true`, quantização ≥ fp8 e `sort: "price"`.
- **Saída estruturada:** `json_schema` com `strict` e o plugin `response-healing`.
- **Retries:** 408, 429 e 5xx são retentados com `Retry-After` ou backoff exponencial. 402 levanta `InsufficientCredits`; demais 4xx falham sem retentar.
- **Custo:** vem de `usage.cost`.
- **Endpoints públicos:** `/models` e `/endpoints/zdr` não exigem chave; sem chave, o cabeçalho `Authorization` não é enviado.

**Files:**
- Create: `sotawhat/llm/__init__.py` (vazio), `sotawhat/llm/openrouter.py`, `tests/fixtures/openrouter/chat_ok.json`, `tests/test_openrouter.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/fixtures/openrouter/chat_ok.json`:

````json
{
  "id": "gen-1762500000-abc123",
  "object": "chat.completion",
  "created": 1762500000,
  "model": "deepseek/deepseek-v4.1-flash-1017",
  "provider": "DeepInfra",
  "system_fingerprint": null,
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {"role": "assistant", "content": "{\"ok\": true, \"lang\": \"pt-BR\"}"}
    }
  ],
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 30,
    "total_tokens": 150,
    "prompt_tokens_details": {"cached_tokens": 64},
    "completion_tokens_details": {"reasoning_tokens": 12},
    "cost": 0.0000187,
    "is_byok": false
  }
}
````

Create `tests/test_openrouter.py`:

````python
# tests/test_openrouter.py
import json

import httpx
import pytest

from sotawhat.llm.openrouter import (InsufficientCredits, OpenRouterClient, OpenRouterError, Privacy,
                                     build_payload)

OK = json.load(open("tests/fixtures/openrouter/chat_ok.json", encoding="utf-8"))
MESSAGES = [{"role": "user", "content": "ping"}]


def _client(handler, sleeps=None):
    return OpenRouterClient("sk-test", transport=httpx.MockTransport(handler),
                            sleep=(sleeps.append if sleeps is not None else (lambda s: None)))


def test_build_payload_enforces_privacy_schema_and_fallbacks():
    p = build_payload(["a/primary", "b/fallback"], MESSAGES, schema={"type": "object"},
                      schema_name="triage", reasoning="low", max_tokens=900)
    assert p["model"] == "a/primary" and p["models"] == ["a/primary", "b/fallback"]
    assert p["response_format"] == {"type": "json_schema", "json_schema": {
        "name": "triage", "strict": True, "schema": {"type": "object"}}}
    assert p["plugins"] == [{"id": "response-healing"}]
    assert p["reasoning"] == {"effort": "low", "exclude": True}
    assert p["max_tokens"] == 900
    assert p["provider"] == {"require_parameters": True, "allow_fallbacks": True, "data_collection": "deny",
                             "zdr": True, "quantizations": ["fp8", "bf16", "fp16", "fp32", "unknown"],
                             "sort": "price"}


def test_build_payload_single_model_and_reasoning_off():
    p = build_payload(["a/only"], MESSAGES, reasoning="none", privacy=Privacy(zdr=False, quantizations=[]))
    assert "models" not in p and "response_format" not in p
    assert p["reasoning"] == {"effort": "none"}
    assert "zdr" not in p["provider"] and "quantizations" not in p["provider"]


def test_chat_posts_and_parses_usage_cost_and_provider():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=OK)

    c = _client(handler).chat(build_payload(["deepseek/deepseek-v4.1-flash-1017"], MESSAGES))
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["provider"]["zdr"] is True
    assert json.loads(c.content) == {"ok": True, "lang": "pt-BR"}
    assert (c.model, c.provider, c.generation_id) == ("deepseek/deepseek-v4.1-flash-1017", "DeepInfra",
                                                      "gen-1762500000-abc123")
    assert (c.input_tokens, c.output_tokens, c.reasoning_tokens, c.cached_tokens) == (120, 30, 12, 64)
    assert c.cost_usd == pytest.approx(0.0000187)


def test_chat_retries_429_then_succeeds():
    responses = iter([httpx.Response(429, headers={"retry-after": "0"}, json={"error": {"message": "slow"}}),
                      httpx.Response(200, json=OK)])
    sleeps = []
    c = _client(lambda request: next(responses), sleeps).chat(build_payload(["m"], MESSAGES))
    assert c.cost_usd > 0 and sleeps == [0.0]


def test_chat_raises_on_402_without_retry():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(402, json={"error": {"message": "Insufficient credits"}})

    with pytest.raises(InsufficientCredits):
        _client(handler).chat(build_payload(["m"], MESSAGES))
    assert len(calls) == 1


def test_chat_does_not_retry_400_and_gives_up_after_max_retries():
    with pytest.raises(OpenRouterError) as bad:
        _client(lambda r: httpx.Response(400, json={"error": {"message": "bad schema"}})).chat({"model": "m"})
    assert bad.value.status == 400 and not bad.value.retryable
    sleeps = []
    with pytest.raises(OpenRouterError):
        _client(lambda r: httpx.Response(503, text="down"), sleeps).chat({"model": "m"})
    assert len(sleeps) == 3


def test_key_info_and_models():
    def handler(request):
        if request.url.path.endswith("/key"):
            return httpx.Response(200, json={"data": {"limit": 30, "usage": 1.5, "limit_remaining": 28.5}})
        return httpx.Response(200, json={"data": [{"id": "deepseek/deepseek-v4.1-flash-1017"}]})

    client = _client(handler)
    assert client.key_info()["limit_remaining"] == 28.5
    assert client.models()[0]["id"] == "deepseek/deepseek-v4.1-flash-1017"
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_openrouter.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.llm'`.

- [ ] **Passo 3: Implementar**

Create `sotawhat/llm/__init__.py` vazio e `sotawhat/llm/openrouter.py`:

````python
# sotawhat/llm/openrouter.py
"""Thin OpenRouter Chat Completions client over httpx (SDD §6.6). No third-party SDK.

Every request carries the privacy policy: ZDR endpoints only, no data collection,
quantization >= fp8 and only providers that honour all request parameters.
"""
import time
from dataclasses import dataclass, field

import httpx

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_RETRYABLE = {408, 429, 500, 502, 503, 504}


class OpenRouterError(Exception):
    def __init__(self, message, status=None, retryable=False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class InsufficientCredits(OpenRouterError):
    """HTTP 402 — buy credits or raise the key limit; never retried."""


@dataclass
class Privacy:
    zdr: bool = True
    data_collection: str = "deny"
    quantizations: list = field(default_factory=lambda: ["fp8", "bf16", "fp16", "fp32", "unknown"])
    sort: str | None = "price"

    def provider_prefs(self) -> dict:
        prefs = {"require_parameters": True, "allow_fallbacks": True,
                 "data_collection": self.data_collection}
        if self.zdr:
            prefs["zdr"] = True
        if self.quantizations:
            prefs["quantizations"] = list(self.quantizations)
        if self.sort:
            prefs["sort"] = self.sort
        return prefs


@dataclass
class Completion:
    content: str
    model: str
    provider: str | None
    generation_id: str | None
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cached_tokens: int
    cost_usd: float
    latency_ms: int
    finish_reason: str | None


def build_payload(models, messages, schema=None, schema_name="output", reasoning=None,
                  max_tokens=None, privacy=None, healing=True) -> dict:
    """models: primary first, then fallbacks. reasoning: None | "none" | "minimal" | "low" | "medium" | "high"."""
    models = list(models)
    payload = {"model": models[0], "messages": messages}
    if len(models) > 1:
        payload["models"] = models
    if schema is not None:
        payload["response_format"] = {"type": "json_schema",
                                      "json_schema": {"name": schema_name, "strict": True, "schema": schema}}
        if healing:
            payload["plugins"] = [{"id": "response-healing"}]
    if reasoning:
        payload["reasoning"] = {"effort": reasoning} if reasoning == "none" else {"effort": reasoning, "exclude": True}
    if max_tokens:
        payload["max_tokens"] = max_tokens
    payload["provider"] = (privacy or Privacy()).provider_prefs()
    return payload


def _provider_of(data):
    if data.get("provider"):
        return data["provider"]
    meta = data.get("openrouter_metadata") or {}
    for ep in (meta.get("endpoints") or {}).get("available", []):
        if ep.get("selected"):
            return ep.get("provider")
    return None


def parse_response(data, latency_ms) -> Completion:
    if data.get("error"):
        err = data["error"]
        raise OpenRouterError(f"upstream error: {err.get('message', err)}", status=err.get("code"))
    choice = (data.get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content") or ""
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    usage = data.get("usage") or {}
    return Completion(
        content=content, model=data.get("model", ""), provider=_provider_of(data),
        generation_id=data.get("id"),
        input_tokens=usage.get("prompt_tokens") or 0, output_tokens=usage.get("completion_tokens") or 0,
        reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0,
        cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
        cost_usd=float(usage.get("cost") or 0.0), latency_ms=latency_ms,
        finish_reason=choice.get("finish_reason"))


def _error_from(response) -> OpenRouterError:
    try:
        message = (response.json().get("error") or {}).get("message") or response.text[:200]
    except ValueError:
        message = response.text[:200]
    status = response.status_code
    if status == 402:
        return InsufficientCredits(f"HTTP 402: {message}", status=status)
    return OpenRouterError(f"HTTP {status}: {message}", status=status, retryable=status in _RETRYABLE)


class OpenRouterClient:
    def __init__(self, api_key, base_url=DEFAULT_BASE_URL, app_title="", timeout=120.0,
                 max_retries=3, backoff_s=2.0, transport=None, sleep=time.sleep):
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}   # catalog endpoints are public
        if app_title:
            headers["X-Title"] = app_title
        self._http = httpx.Client(base_url=base_url, headers=headers, timeout=timeout, transport=transport)
        self.max_retries = max_retries
        self.backoff_s = backoff_s
        self._sleep = sleep

    def close(self):
        self._http.close()

    def _delay(self, response, attempt):
        retry_after = response.headers.get("retry-after") if response is not None else None
        if retry_after:
            try:
                return min(float(retry_after), 60.0)
            except ValueError:
                pass
        return min(self.backoff_s * (2 ** attempt), 60.0)

    def chat(self, payload) -> Completion:
        attempt = 0
        while True:
            started = time.monotonic()
            response = None
            try:
                response = self._http.post("/chat/completions", json=payload)
            except httpx.TransportError as exc:
                error = OpenRouterError(f"transport error: {type(exc).__name__}", retryable=True)
            else:
                if response.status_code == 200:
                    return parse_response(response.json(), int((time.monotonic() - started) * 1000))
                error = _error_from(response)
            if not error.retryable or attempt >= self.max_retries:
                raise error
            self._sleep(self._delay(response, attempt))
            attempt += 1

    def _get(self, path, **params):
        response = self._http.get(path, params=params or None)
        if response.status_code != 200:
            raise _error_from(response)
        return response.json().get("data")

    def key_info(self) -> dict:
        return self._get("/key")

    def models(self) -> list:
        return self._get("/models")

    def zdr_endpoints(self) -> list:
        return self._get("/endpoints/zdr")
````

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `78 passed`.

- [ ] **Passo 5: Commit**

```bash
git add sotawhat/llm tests/test_openrouter.py tests/fixtures/openrouter
git commit -m "feat: OpenRouter client with ZDR-only routing, strict JSON and real cost"
```

---

## Tarefa 7: Matriz de modelos e gateway LLM

**Restrição verificada no catálogo em 2026-11-07:**
- GLM-5.3 e GLM-5.3-Flash têm raciocínio obrigatório; MiniMax-M3.1-Flash também. Nenhum dos três aceita `effort: "none"`.
- O DeepSeek V4.1 Flash 1017 aceita só `max`/`high`/`low`/`none`, ou seja, não aceita `medium`.

Por isso a matriz usa apenas `low` e `high`, níveis aceitos por todos os modelos de cada cadeia. O `doctor` da Tarefa 10 verifica isso contra o catálogo vivo.

**Files:**
- Create: `sotawhat/llm/tasks.py`, `sotawhat/llm/gateway.py`, `tests/test_gateway.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_gateway.py`:

````python
# tests/test_gateway.py
from datetime import datetime, timezone

import pytest
from pydantic import BaseModel

from sotawhat.config import Settings
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure, LLMGateway, extract_json, strict_schema
from sotawhat.llm.openrouter import Completion, InsufficientCredits, OpenRouterError
from sotawhat.llm.tasks import DEFAULT_TASKS, resolve
from sotawhat.store.db import Store


class Verdict(BaseModel):
    title: str
    score: int
    note: str | None = None


def _completion(content, model="deepseek/deepseek-v4.1-flash-1017", cost=0.001):
    return Completion(content=content, model=model, provider="DeepInfra", generation_id="gen-1",
                      input_tokens=100, output_tokens=20, reasoning_tokens=5, cached_tokens=0,
                      cost_usd=cost, latency_ms=50, finish_reason="stop")


class FakeClient:
    def __init__(self, *results):
        self.results = list(results)
        self.payloads = []

    def chat(self, payload):
        self.payloads.append(payload)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _settings(**kw):
    return Settings(_env_file=None, **kw)


def test_strict_schema_requires_every_field_and_keeps_title_property():
    schema = strict_schema(Verdict)
    assert schema["required"] == ["title", "score", "note"]
    assert schema["additionalProperties"] is False
    assert "title" in schema["properties"]
    assert "default" not in schema["properties"]["note"]


def test_extract_json_strips_fences_and_chatter():
    assert extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert extract_json('Sure! {"a": 1} hope it helps') == '{"a": 1}'


def test_structured_returns_model_and_records_real_cost(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        client = FakeClient(_completion('{"title": "x", "score": 4, "note": null}', cost=0.002))
        gw = LLMGateway(client, store=st, settings=_settings(), run_id=7)
        out = gw.structured("triage", [{"role": "user", "content": "rate"}], Verdict)
        assert out == Verdict(title="x", score=4)
        sent = client.payloads[0]
        assert sent["models"] == list(DEFAULT_TASKS["triage"].models)
        assert sent["response_format"]["json_schema"]["name"] == "verdict"
        assert sent["provider"]["zdr"] is True
        row = st.conn.execute("SELECT * FROM llm_calls").fetchone()
        assert (row["run_id"], row["task"], row["status"], row["provider"]) == (7, "triage", "ok", "DeepInfra")
        assert row["cost_usd"] == pytest.approx(0.002)


def test_structured_repairs_invalid_json_once(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        client = FakeClient(_completion('{"title": "x"}'), _completion('{"title": "x", "score": 3, "note": null}'))
        out = LLMGateway(client, store=st, settings=_settings()).structured("triage", [], Verdict)
        assert out.score == 3
        assert "did not validate" in client.payloads[1]["messages"][-1]["content"]
        statuses = [r[0] for r in st.conn.execute("SELECT status FROM llm_calls ORDER BY id")]
        assert statuses == ["invalid", "ok"]


def test_structured_moves_to_next_model_after_error():
    client = FakeClient(OpenRouterError("HTTP 400: no endpoint"),
                        _completion('{"title": "y", "score": 1, "note": "ok"}', model="xiaomi/mimo-v2.6-flash"))
    out = LLMGateway(client).structured("triage", [], Verdict)
    assert out.title == "y"
    assert client.payloads[1]["model"] == "xiaomi/mimo-v2.6-flash"


def test_structured_raises_after_all_models_fail():
    errors = [OpenRouterError("down")] * len(DEFAULT_TASKS["triage"].models)
    with pytest.raises(LLMFailure):
        LLMGateway(FakeClient(*errors)).structured("triage", [], Verdict)


def test_insufficient_credits_is_not_swallowed():
    with pytest.raises(InsufficientCredits):
        LLMGateway(FakeClient(InsufficientCredits("HTTP 402"))).structured("triage", [], Verdict)


def test_budget_blocks_call_before_spending(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        st.record_llm_call(task="triage", requested_model="m", status="ok", cost_usd=1.5)
        client = FakeClient()
        gw = LLMGateway(client, store=st, settings=_settings(), budget_day=1.0,
                        now=lambda: datetime.now(timezone.utc))
        with pytest.raises(BudgetExceeded):
            gw.structured("triage", [], Verdict)
        assert client.payloads == []


def test_env_override_puts_model_first():
    spec = resolve("triage", _settings(sotawhat_model_triage="z-ai/glm-5.3-flash"))
    assert spec.models[0] == "z-ai/glm-5.3-flash"
    assert spec.models.count("z-ai/glm-5.3-flash") == 1
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_gateway.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.llm.gateway'`.

- [ ] **Passo 3: Criar `sotawhat/llm/tasks.py`**

````python
# sotawhat/llm/tasks.py
"""Default task -> models matrix (SDD §6.6). Primary first, fallbacks from other model families."""
from dataclasses import dataclass, replace

DEEPSEEK_FLASH = "deepseek/deepseek-v4.1-flash-1017"
MIMO_FLASH = "xiaomi/mimo-v2.6-flash"
MIMO_PRO = "xiaomi/mimo-v2.6-pro"
GLM = "z-ai/glm-5.3"
GLM_FLASH = "z-ai/glm-5.3-flash"
MINIMAX_FLASH = "minimax/minimax-m3.1-flash"


@dataclass(frozen=True)
class TaskSpec:
    models: tuple
    reasoning: str | None = None   # None = model default; otherwise "low" or "high" (accepted by every
                                   # model below: GLM/MiniMax reject "none", DeepSeek V4.1 rejects "medium")
    max_tokens: int = 2000


DEFAULT_TASKS = {
    "triage": TaskSpec((DEEPSEEK_FLASH, MIMO_FLASH, GLM_FLASH), "low", 1500),
    "segment": TaskSpec((MIMO_FLASH, DEEPSEEK_FLASH), "low", 4000),
    "vision": TaskSpec((MIMO_FLASH, GLM_FLASH, MINIMAX_FLASH), "low", 1500),
    "extract": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO, GLM), "high", 12000),
    "synth": TaskSpec((DEEPSEEK_FLASH, MIMO_PRO), "high", 12000),
    "smoke": TaskSpec((DEEPSEEK_FLASH,), "low", 600),
}


def resolve(task, settings=None) -> TaskSpec:
    spec = DEFAULT_TASKS[task]
    override = settings.model_override(task) if settings is not None else ""
    if override:
        spec = replace(spec, models=(override,) + tuple(m for m in spec.models if m != override))
    return spec
````

- [ ] **Passo 4: Criar `sotawhat/llm/gateway.py`**

````python
# sotawhat/llm/gateway.py
"""Task-level LLM gateway (SDD §6.6): strict JSON output, repair + fallback, budget, cost ledger."""
import json
import re
from datetime import datetime, timezone

from pydantic import ValidationError

from sotawhat.llm.openrouter import InsufficientCredits, OpenRouterError, Privacy, build_payload
from sotawhat.llm.tasks import resolve

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class BudgetExceeded(Exception):
    pass


class LLMFailure(Exception):
    pass


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
                 budget_month=None, now=lambda: datetime.now(timezone.utc)):
        self.client = client
        self.store = store
        self.settings = settings
        self.run_id = run_id
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
        """Return a validated `output_model`. Tries each model (with the remaining ones as server-side
        fallbacks); one repair round per model when the JSON does not validate."""
        spec = resolve(task, self.settings)
        chain = tuple(models) if models else spec.models
        schema = strict_schema(output_model)
        name = re.sub(r"[^a-z0-9_]+", "_", output_model.__name__.lower())
        last_error = None
        for i, model in enumerate(chain):
            convo = list(messages)
            for _attempt in range(2):
                self._check_budget()
                payload = build_payload(chain[i:], convo, schema=schema, schema_name=name,
                                        reasoning=spec.reasoning, max_tokens=spec.max_tokens,
                                        privacy=self.privacy)
                try:
                    completion = self.client.chat(payload)
                except InsufficientCredits as exc:
                    self._record(task, model, status="error", error=str(exc))
                    raise
                except OpenRouterError as exc:
                    self._record(task, model, status="error", error=str(exc))
                    last_error = exc
                    break
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
                return result
        raise LLMFailure(f"{task}: every model failed; last error: {last_error}")
````

- [ ] **Passo 5: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `87 passed`.

- [ ] **Passo 6: Commit**

```bash
git add sotawhat/llm/tasks.py sotawhat/llm/gateway.py tests/test_gateway.py
git commit -m "feat: LLM gateway with strict schemas, repair, fallbacks, budget and ledger"
```

---

## Tarefa 8: Notificador do Telegram

**Files:**
- Create: `sotawhat/notify/__init__.py` (vazio), `sotawhat/notify/telegram.py`, `tests/test_telegram.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_telegram.py`:

````python
# tests/test_telegram.py
import json

import httpx
import pytest

from sotawhat.notify.telegram import TelegramError, TelegramNotifier, chunk, esc

TOKEN = "123456:SECRET-TOKEN"


def _notifier(handler):
    return TelegramNotifier(TOKEN, "42", transport=httpx.MockTransport(handler))


def test_send_posts_html_message_to_bot_api():
    seen = []

    def handler(request):
        seen.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    assert _notifier(handler).send("<b>oi</b>") == 1
    path, body = seen[0]
    assert path == f"/bot{TOKEN}/sendMessage"
    assert body == {"chat_id": "42", "text": "<b>oi</b>", "parse_mode": "HTML", "disable_web_page_preview": True}


def test_long_text_is_split_on_lines():
    text = "\n".join(["x" * 100] * 50)          # 5.049 characters
    parts = chunk(text)
    assert len(parts) == 2 and all(len(p) <= 4096 for p in parts)
    assert "\n".join(parts) == text
    assert chunk("y" * 5000) == ["y" * 4096, "y" * 904]


def test_errors_never_leak_the_token():
    def handler(request):
        return httpx.Response(401, json={"ok": False, "description": "Unauthorized"})

    with pytest.raises(TelegramError) as err:
        _notifier(handler).send("x")
    assert "SECRET" not in str(err.value) and "401" in str(err.value)


def test_esc_and_configured():
    assert esc("a < b & c") == "a &lt; b &amp; c"
    assert TelegramNotifier("", "").configured is False
````

- [ ] **Passo 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python -m pytest tests/test_telegram.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.notify'`.

- [ ] **Passo 3: Implementar**

Create `sotawhat/notify/__init__.py` vazio e `sotawhat/notify/telegram.py`:

````python
# sotawhat/notify/telegram.py
"""Send-only Telegram notifier (SDD §7.7). The bot token never appears in raised errors."""
import html

import httpx

API = "https://api.telegram.org"
LIMIT = 4096


class TelegramError(Exception):
    pass


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
    def __init__(self, token, chat_id, transport=None, timeout=30.0):
        self.token = token
        self.chat_id = chat_id
        self._http = httpx.Client(base_url=f"{API}/bot{token}", timeout=timeout, transport=transport)

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def _call(self, method, payload=None) -> dict:
        try:
            response = self._http.post(f"/{method}", json=payload or {})
        except httpx.TransportError as exc:
            raise TelegramError(f"{method}: transport error {type(exc).__name__}") from None
        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code != 200 or not data.get("ok"):
            raise TelegramError(f"{method}: HTTP {response.status_code} {data.get('description', '')}".strip())
        return data.get("result") or {}

    def send(self, text, parse_mode="HTML") -> int:
        parts = chunk(text)
        for part in parts:
            self._call("sendMessage", {"chat_id": self.chat_id, "text": part, "parse_mode": parse_mode,
                                       "disable_web_page_preview": True})
        return len(parts)

    def get_me(self) -> dict:
        return self._call("getMe")
````

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `91 passed`.

- [ ] **Passo 5: Commit**

```bash
git add sotawhat/notify tests/test_telegram.py
git commit -m "feat: Telegram notifier that never leaks the bot token"
```

---

## Tarefa 9: Erro por fonte no `collect`, `run daily` e CLI

**Files:**
- Modify: `sotawhat/digest.py`, `tests/test_digest.py`, `sotawhat/cli.py`, `tests/test_cli.py`
- Create: `sotawhat/pipeline/__init__.py` (vazio), `sotawhat/pipeline/daily.py`, `tests/test_daily.py`

- [ ] **Passo 1: Teste de `collect` com erro por fonte (falha)**

Acrescentar ao final de `tests/test_digest.py`:

````python
def test_collect_reports_which_source_failed():
    from sotawhat.sources.base import Source

    class Down(Source):
        name = "down"
        def search(self, keyword, limit):
            raise RuntimeError("503")

    failures = []
    out = collect([Down(), FakeSource("arxiv", [_r("1", "arxiv")])], ["k"], 10,
                  on_source_error=lambda src, msg: failures.append((src.name, msg)))
    assert [r.id for r in out] == ["1"]
    assert failures == [("down", "[down] failed: 503")]
````

Run: `.\.venv\Scripts\python -m pytest tests/test_digest.py -q`
Expected: FAIL com `TypeError: collect() got an unexpected keyword argument 'on_source_error'`.

- [ ] **Passo 2: Implementar em `sotawhat/digest.py`**

Substituir o início de `collect`:

```python
def collect(sources, keywords, limit, on_error=None):
    by_id = {}
    out = []
    for source in sources:
        for kw in keywords:
            for r in source.safe_search(kw, limit, on_error=on_error):
```

por:

````python
def collect(sources, keywords, limit, on_error=None, on_source_error=None):
    by_id = {}
    out = []
    for source in sources:
        def handler(msg, _source=source):
            if on_error:
                on_error(msg)
            if on_source_error:
                on_source_error(_source, msg)
        for kw in keywords:
            for r in source.safe_search(kw, limit, on_error=handler):
````

Run: `.\.venv\Scripts\python -m pytest tests/test_digest.py -q`
Expected: `4 passed`.

- [ ] **Passo 3: Testes do pipeline (falham)**

Create `tests/test_daily.py`:

````python
# tests/test_daily.py
from datetime import date

from sotawhat.models import Result
from sotawhat.pipeline.daily import ALERT_AFTER, render_summary, run_daily, to_plain
from sotawhat.store.db import Store

DAY = date(2026, 11, 8)


class FakeSource:
    def __init__(self, name, results=(), error=None, feeds=(), feed_errors=None):
        self.name = name
        self.results = list(results)
        self.error = error
        self.feeds = list(feeds)
        self.feed_errors = dict(feed_errors or {})

    def safe_search(self, keyword, limit, on_error=None):
        if self.error:
            if on_error:
                on_error(f"[{self.name}] failed: {self.error}")
            return []
        return list(self.results)


def _r(rid, source, title="Deep learning for sepsis", url=None):
    return Result(id=rid, title=title, authors=["A"], date="2026-11-07",
                  url=url or f"https://arxiv.org/abs/{rid}", abstract="machine learning model", source=source)


def test_new_items_are_stored_once_across_runs(tmp_path):
    sources = {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv"), _r("2511.00002", "arxiv")])]}
    with Store(tmp_path / "insight.db") as st:
        first = run_daily(st, sources, today=DAY)
        assert first.ok and first.collected == {"geral": 2} and len(first.new_items) == 2
        second = run_daily(st, sources, today=DAY)
        assert second.new_items == [] and st.count_items() == 2


def test_same_paper_from_arxiv_and_hf_counts_once(tmp_path):
    sources = {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv")]),
                         FakeSource("hf_papers", [_r("2511.00001", "hf_papers",
                                                     url="https://huggingface.co/papers/2511.00001")])]}
    with Store(tmp_path / "insight.db") as st:
        report = run_daily(st, sources, today=DAY)
        assert report.collected == {"geral": 1}
        assert [it.id for it in report.new_items] == ["arxiv:2511.00001"]


def test_medico_keeps_only_ai_items(tmp_path):
    clinical = Result(id="41000001", title="Aspirin dosing trial", authors=[], date="", url="",
                      abstract="no method here", source="pubmed")
    ai = _r("41000002", "pubmed", url="https://pubmed.ncbi.nlm.nih.gov/41000002/")
    sources = {"medico": [FakeSource("pubmed", [clinical, ai])]}
    with Store(tmp_path / "insight.db") as st:
        report = run_daily(st, sources, today=DAY)
        assert [it.id for it in report.new_items] == ["pmid:41000002"]


def test_failing_sources_and_feeds_raise_alert_after_three_runs(tmp_path):
    rss = FakeSource("medical", feeds=[("nature", "u1"), ("jmir-ai", "u2")],
                     feed_errors={"nature": "FeedError: HTML instead of a feed"})
    down = FakeSource("pubmed", error="HTTP 503")
    with Store(tmp_path / "insight.db") as st:
        for _ in range(ALERT_AFTER):
            report = run_daily(st, {"medico": [rss, down]}, today=DAY)
        assert report.failing["medical/nature"][0] == ALERT_AFTER
        assert report.failing["pubmed"][0] == ALERT_AFTER
        assert "medical/jmir-ai" not in report.failing and "medical" not in report.failing
        text = render_summary(report)
        assert "medical/nature" in text and f"alerta: {ALERT_AFTER}ª falha seguida" in text


def test_summary_escapes_html_and_links_new_items(tmp_path):
    evil = _r("2511.00009", "arxiv", title='<script>x</script> & "LLM"')
    with Store(tmp_path / "insight.db") as st:
        text = render_summary(run_daily(st, {"geral": [FakeSource("arxiv", [evil])]}, today=DAY))
    assert "&lt;script&gt;" in text and "<script>" not in text
    assert '<a href="https://arxiv.org/abs/2511.00009">' in text
    assert "run diário 2026-11-08" in to_plain(text)


def test_unexpected_error_closes_run_as_failed(tmp_path, monkeypatch):
    with Store(tmp_path / "insight.db") as st:
        def boom(items, run_id):
            raise RuntimeError("disk full")
        monkeypatch.setattr(st, "upsert_items", boom)
        report = run_daily(st, {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv")])]}, today=DAY)
        assert not report.ok and "disk full" in report.error
        assert st.last_run("daily")["ok"] == 0
        assert "❌" in render_summary(report)


def test_vault_export_keeps_obsidian_notes_during_transition(tmp_path):
    vault = tmp_path / "vault"
    with Store(tmp_path / "insight.db") as st:
        run_daily(st, {"geral": [FakeSource("arxiv", [_r("2511.00001", "arxiv")])]}, vault=vault, today=DAY)
    notes = list((vault / "geral").rglob("*.md"))
    assert len(notes) == 1
````

Run: `.\.venv\Scripts\python -m pytest tests/test_daily.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.pipeline'`.

- [ ] **Passo 4: Implementar o pipeline**

Create `sotawhat/pipeline/__init__.py` vazio e `sotawhat/pipeline/daily.py`:

````python
# sotawhat/pipeline/daily.py
"""`sotawhat run daily`, P0 scope: collect -> normalize -> exact dedup -> SQLite -> Telegram summary.

Triage, extraction and the real digest arrive in P1 (SDD §11).
"""
import html
import re
import sys
from dataclasses import dataclass, field
from datetime import date

from sotawhat.digest import collect, filter_relevant
from sotawhat.items import to_item
from sotawhat.notify.telegram import esc, esc_attr
from sotawhat.profiles import PROFILES

ALERT_AFTER = 3   # consecutive failures before a source is flagged as an alert


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


def run_daily(store, sources_by_profile, limit=10, vault=None, today=None) -> DailyReport:
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
            if vault:
                from sotawhat.obsidian import write_notes
                write_notes(results, vault=vault, profile_name=name, tags=profile["tags"],
                            keywords=profile["keywords"], added=day)
    except Exception as exc:  # noqa: BLE001 - the run must always be closed and reported
        report.ok = False
        report.error = f"{type(exc).__name__}: {exc}"
    stats = {"collected": report.collected, "new": len(report.new_items), "failing": sorted(report.failing)}
    store.finish_run(report.run_id, ok=report.ok, stats=stats, error=report.error)
    row = store.conn.execute("SELECT cost_usd FROM runs WHERE id = ?", (report.run_id,)).fetchone()
    report.cost_usd = row[0]
    return report


def render_summary(report, max_items=10) -> str:
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


def main_daily(ns) -> int:
    from sotawhat.config import load_settings
    from sotawhat.notify.telegram import TelegramError, TelegramNotifier
    from sotawhat.profiles import build_sources
    from sotawhat.store.db import Store

    settings = load_settings()
    sources = {name: build_sources(name, crossref_mailto=settings.crossref_mailto) for name in PROFILES}
    with Store(settings.db_path) as store:
        report = run_daily(store, sources, limit=ns.limit, vault=ns.vault)
    text = render_summary(report)
    print(to_plain(text))
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if not ns.no_notify and notifier.configured:
        try:
            notifier.send(text)
        except TelegramError as exc:
            print(f"[telegram] {exc}", file=sys.stderr)
    return 0 if report.ok else 1
````

- [ ] **Passo 5: Teste do CLI (falha)**

Acrescentar ao final de `tests/test_cli.py`:

````python
def test_parse_run_daily():
    ns = parse_args(["run", "daily", "--vault", "V", "--no-notify", "--limit", "5"])
    assert (ns.command, ns.kind, ns.vault, ns.no_notify, ns.limit) == ("run", "daily", "V", True, 5)
    ns = parse_args(["run", "daily"])
    assert ns.vault is None and ns.no_notify is False and ns.limit == 10
````

Run: `.\.venv\Scripts\python -m pytest tests/test_cli.py -q`
Expected: FAIL. Sem o subcomando, `run` vira uma busca (`search`) e `ns.kind` não existe.

- [ ] **Passo 6: Subcomando `run` em `sotawhat/cli.py`**

6a. `_SUBCOMMANDS = {"search", "digest", "backfill-links"}` → `_SUBCOMMANDS = {"search", "digest", "backfill-links", "run"}`

6b. Logo depois de `p_backfill.add_argument("--profile", default="all")`, acrescentar:

````python

    p_run = sub.add_parser("run")
    p_run.add_argument("kind", choices=["daily"])
    p_run.add_argument("--limit", type=int, default=10)
    p_run.add_argument("--vault", default=None, help="also write Obsidian notes (transition, SDD §9)")
    p_run.add_argument("--no-notify", action="store_true")
````

6c. No `main`, depois do ramo `backfill-links`, acrescentar:

````python
    elif ns.command == "run":
        from sotawhat.pipeline.daily import main_daily
        raise SystemExit(main_daily(ns))
````

- [ ] **Passo 7: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `100 passed`.

- [ ] **Passo 8: Commit**

```bash
git add sotawhat/digest.py sotawhat/pipeline sotawhat/cli.py tests/test_digest.py tests/test_daily.py tests/test_cli.py
git commit -m "feat: run daily collects, dedupes into SQLite, tracks source health and reports"
```

---

## Tarefa 10: `doctor`

O comando verifica:
- `.env` e política de privacidade;
- chave do OpenRouter (limite de gasto e saldo);
- cada modelo configurado: existe no catálogo, tem endpoints ZDR com quantização ≥ fp8 e saída estruturada, aceita o nível de raciocínio de cada tarefa e não expira nos próximos 30 dias;
- bot do Telegram;
- idade e resultado do último run;
- gasto do mês.

`--llm` faz uma chamada de fumaça com JSON estrito por modelo primário: 2 modelos, ≈ US$ 0,001.

**Files:**
- Create: `sotawhat/doctor.py`, `tests/test_doctor.py`
- Modify: `sotawhat/cli.py`, `tests/test_cli.py`

- [ ] **Passo 1: Escrever os testes (falham)**

Create `tests/test_doctor.py`:

````python
# tests/test_doctor.py
from datetime import date, datetime, timedelta, timezone

from sotawhat.config import Settings
from sotawhat.doctor import (Smoke, check_last_run, check_models, check_month_cost, check_openrouter_key,
                             check_settings, llm_smoke, model_requirements, render)
from sotawhat.store.db import Store

DS = "deepseek/deepseek-v4.1-flash-1017"
GLM = "z-ai/glm-5.3-flash"


class FakeClient:
    def __init__(self, key=None, catalog=(), zdr=()):
        self._key, self._catalog, self._zdr = key, list(catalog), list(zdr)

    def key_info(self):
        return self._key

    def models(self):
        return self._catalog

    def zdr_endpoints(self):
        return self._zdr


def _ep(model, quant="fp8", structured=True):
    return {"model_id": model, "quantization": quant,
            "supported_parameters": ["response_format"] + (["structured_outputs"] if structured else [])}


def test_settings_checks_flag_missing_key_and_weak_privacy():
    s = Settings(_env_file=None, openrouter_zdr=False)
    by_name = {c.name: c.status for c in check_settings(s)}
    assert by_name == {"OPENROUTER_API_KEY": "fail", "privacidade LLM": "warn", "Telegram": "warn"}


def test_key_without_spend_limit_is_a_warning():
    assert check_openrouter_key(FakeClient(key={"limit": None, "usage_monthly": 2.0})).status == "warn"
    ok = check_openrouter_key(FakeClient(key={"limit": 30, "limit_remaining": 25.0, "usage_monthly": 5.0}))
    assert ok.status == "ok" and "restante US$ 25.00" in ok.detail


def test_models_need_zdr_endpoints_compatible_reasoning_and_no_close_expiry():
    catalog = [{"id": DS, "reasoning": {"supported_efforts": ["max", "high", "low", "none"]}},
               {"id": GLM, "reasoning": {"mandatory": True, "supported_efforts": ["max", "high", "low"]},
                "expiration_date": "2026-11-20"},
               {"id": "x/fp4-only"}]
    zdr = [_ep(DS), _ep(DS, quant="unknown"), _ep(GLM), _ep("x/fp4-only", quant="fp4")]
    reqs = {DS: {"low", "high"}, GLM: {"low"}, "x/fp4-only": set(), "gone/model": set(),
            "x/medium": {"medium"}}
    catalog.append({"id": "x/medium", "reasoning": {"supported_efforts": ["high", "low"]}})
    zdr.append(_ep("x/medium"))
    result = {c.name: (c.status, c.detail) for c in check_models(FakeClient(catalog=catalog, zdr=zdr), reqs,
                                                                  today=date(2026, 11, 7))}
    assert result[DS] == ("ok", "2 endpoints ZDR elegíveis")
    assert result[GLM][0] == "warn" and "2026-11-20" in result[GLM][1]
    assert result["x/fp4-only"][0] == "fail"
    assert result["gone/model"][0] == "fail"
    assert result["x/medium"][0] == "fail" and "medium" in result["x/medium"][1]


def test_default_matrix_only_uses_efforts_every_model_accepts():
    reqs = model_requirements()
    assert all(efforts <= {"low", "high"} for efforts in reqs.values())


def test_last_run_and_month_cost(tmp_path):
    now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
    with Store(tmp_path / "insight.db") as st:
        assert check_last_run(st, now=now).status == "warn"
        run = st.start_run("daily")
        st.finish_run(run, ok=True, stats={})
        assert check_last_run(st, now=datetime.now(timezone.utc)).status == "ok"
        assert check_last_run(st, now=datetime.now(timezone.utc) + timedelta(hours=40)).status == "warn"
        st.record_llm_call(task="triage", requested_model=DS, status="ok", cost_usd=21.0)
        assert check_month_cost(st, 25.0, now=datetime.now(timezone.utc)).status == "warn"


def test_llm_smoke_reports_each_model():
    class FakeGateway:
        def structured(self, task, messages, model, models=None):
            if models[0] == "bad/model":
                raise RuntimeError("HTTP 400")
            return Smoke(ok=True, idioma="pt-BR")

    checks = llm_smoke(FakeGateway(), [DS, "bad/model"])
    assert [c.status for c in checks] == ["ok", "fail"]
    assert "[FAIL] fumaça bad/model" in render(checks)
````

Acrescentar ao final de `tests/test_cli.py`:

````python
def test_parse_doctor():
    assert parse_args(["doctor"]).llm is False
    assert parse_args(["doctor", "--llm"]).llm is True
````

Run: `.\.venv\Scripts\python -m pytest tests/test_doctor.py tests/test_cli.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sotawhat.doctor'`; `test_parse_doctor` também falha.

- [ ] **Passo 2: Implementar `sotawhat/doctor.py`**

````python
# sotawhat/doctor.py
"""`sotawhat doctor [--llm]`: configuration, keys, models, last run and spend (SDD §6.12)."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

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


def model_requirements(settings=None) -> dict:
    """model -> set of reasoning efforts it must accept, over every task chain."""
    needs = {}
    for task in TASKS:
        spec = resolve(task, settings)
        for model in spec.models:
            needs.setdefault(model, set())
            if spec.reasoning:
                needs[model].add(spec.reasoning)
    return needs


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

    settings = load_settings()
    checks = check_settings(settings)
    client = OpenRouterClient(settings.openrouter_api_key, base_url=settings.openrouter_base_url)
    if settings.openrouter_api_key:
        checks.append(check_openrouter_key(client))
    checks += check_models(client, model_requirements(settings))
    notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    if notifier.configured:
        checks.append(check_telegram(notifier))
    with Store(settings.db_path) as store:
        checks.append(check_last_run(store))
        checks.append(check_month_cost(store, settings.sotawhat_llm_budget_usd_month))
        if ns.llm:
            if settings.openrouter_api_key:
                primaries = list(dict.fromkeys(resolve(t, settings).models[0] for t in TASKS))
                checks += llm_smoke(LLMGateway(client, store=store, settings=settings), primaries)
            else:
                checks.append(Check("fumaça LLM", "fail", "sem OPENROUTER_API_KEY"))
    print(render(checks))
    return 1 if any(c.status == "fail" for c in checks) else 0
````

- [ ] **Passo 3: Subcomando `doctor` em `sotawhat/cli.py`**

3a. Acrescentar `"doctor"` a `_SUBCOMMANDS`.

3b. Depois do parser `run`, acrescentar:

````python

    p_doctor = sub.add_parser("doctor")
    p_doctor.add_argument("--llm", action="store_true", help="smoke-test each primary model (cents)")
````

3c. No `main`, depois do ramo `run`, acrescentar:

````python
    elif ns.command == "doctor":
        from sotawhat.doctor import main_doctor
        raise SystemExit(main_doctor(ns))
````

- [ ] **Passo 4: Rodar os testes**

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `107 passed`.

- [ ] **Passo 5: Commit**

```bash
git add sotawhat/doctor.py sotawhat/cli.py tests/test_doctor.py tests/test_cli.py
git commit -m "feat: doctor checks keys, models (ZDR, reasoning, expiry), last run and spend"
```

---

## Tarefa 11: TLS, console, agendamento, README e verificação ponta a ponta

**Por quê:**
- **TLS:** esta máquina tem inspeção TLS local intermitente. Em 2026-11-07, `CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain` apareceu em `openrouter.ai` com o bundle `certifi`. O `truststore` passa a usar o repositório de certificados do Windows; `verify=False` nunca.
- **Console:** consoles e pipes em cp1252 não podem quebrar com emoji no resumo.

**Files:**
- Modify: `sotawhat/cli.py`, `README.md`
- Create: `scripts/schedule_daily.ps1`

- [ ] **Passo 1: `truststore` e stdout tolerante em `sotawhat/cli.py`**

No início de `main()`, antes de `ns = parse_args(...)`:

````python
    import truststore
    truststore.inject_into_ssl()   # trust the Windows store (local TLS inspection; never verify=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")   # cp1252 consoles/pipes must not crash on emoji
````

Run: `.\.venv\Scripts\python -m pytest -q`
Expected: `107 passed`.

- [ ] **Passo 2: Criar `scripts/schedule_daily.ps1`** (somente ASCII; o PowerShell 5.1 lê `.ps1` sem BOM como ANSI)

````powershell
# scripts/schedule_daily.ps1 - registers `sotawhat run daily` in Windows Task Scheduler (SDD 6.12).
# Usage, from the repository root in PowerShell:
#   .\scripts\schedule_daily.ps1                         # 07:00, no Obsidian export
#   .\scripts\schedule_daily.ps1 -Vault "D:\Lucas\obsidian_vaults\ml_ai_med_vault"
# Runs as the current user while logged on; a missed run starts as soon as possible (StartWhenAvailable).
param(
    [string]$Time = "07:00",
    [string]$Vault = "",
    [string]$TaskName = "sotawhat-daily"
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
$exe = Join-Path $repo ".venv\Scripts\sotawhat.exe"
if (-not (Test-Path $exe)) { throw "Not found: $exe - install first: uv pip install -e .[dev]" }
if (-not (Test-Path (Join-Path $repo ".env"))) { Write-Warning "No .env in $repo - copy .env.example to .env and fill it in." }

$arguments = "run daily"
if ($Vault) { $arguments += " --vault `"$Vault`"" }

# WorkingDirectory = repo root, so the `.env` file and `data\insight.db` are found.
$action = New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "sotawhat 3.0 - coleta diaria + resumo no Telegram" -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State
````

Validar a sintaxe sem registrar nada:

```powershell
$t=$null; $e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile("$PWD\scripts\schedule_daily.ps1",[ref]$t,[ref]$e); if ($e.Count -eq 0) {"parse OK"} else {$e}
```
Expected: `parse OK`.

- [ ] **Passo 3: README**

3a. Trocar `Requires Python 3.9+.` por `Requires Python 3.11+.`

3b. Logo antes de `## Install`, acrescentar:

````markdown
## 3.0 (in progress): insight engine

sotawhat is becoming an insight engine for AI/ML ∩ medicine. The design is in
`docs/sdd/2026-11-07-insight-engine-sdd.md` and the phase plans are in `docs/superpowers/plans/`.
Phase P0 adds:

- `sotawhat run daily [--vault PATH] [--no-notify] [--limit N]` collects every
  profile, normalizes and de-duplicates items into `data/insight.db` (SQLite),
  tracks the health of every source and feed, and sends a run summary to
  Telegram. A feed that returns an HTML anti-bot page now counts as an error
  instead of silently yielding 0 items. `--vault` keeps writing Obsidian notes
  during the transition.
- `sotawhat doctor [--llm]` checks `.env`, the OpenRouter key and its spend
  limit, and every configured model: still in the catalog, Zero-Data-Retention
  endpoints available, reasoning level accepted, not about to expire. It also
  checks the Telegram bot, the last run and this month's LLM spend. `--llm`
  makes one tiny structured call per primary model, for well under one cent.
- The LLMs are Chinese open-weight models (DeepSeek, Xiaomi MiMo, Z.ai GLM,
  Moonshot Kimi) reached through OpenRouter, ZDR endpoints only. See
  `sotawhat/llm/` and SDD §6.6.

To set it up, copy `.env.example` to `.env` and fill in at least `OPENROUTER_API_KEY`,
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Then schedule the daily run with
`powershell -ExecutionPolicy Bypass -File scripts\schedule_daily.ps1 [-Vault PATH]`.

````

3c. Logo abaixo do título `## Scheduled daily digest (Windows)`, acrescentar a linha:

```markdown
> 2.0 path. For 3.0 use `scripts\schedule_daily.ps1` (see "3.0 (in progress)" above).
```

- [ ] **Passo 4: Commit**

```bash
git add sotawhat/cli.py scripts/schedule_daily.ps1 README.md
git commit -m "feat: system trust store, emoji-safe console, daily scheduler script, 3.0 docs"
```

- [ ] **Passo 5: Verificação manual com rede** (precisa dos pré-requisitos do usuário)

1. `.\.venv\Scripts\sotawhat doctor`. Esperado:
   - `[OK]` para OPENROUTER_API_KEY, privacidade, chave (com limite), os 6 modelos e o bot do Telegram;
   - `[WARN] último run diário: nenhum run registrado ainda`;
   - código de saída 0.
2. `.\.venv\Scripts\sotawhat doctor --llm`. Esperado: `[OK] fumaça deepseek/deepseek-v4.1-flash-1017` e `[OK] fumaça xiaomi/mimo-v2.6-flash`. Para conferir o custo:
   ```powershell
   .\.venv\Scripts\python -c "import sqlite3; print(sqlite3.connect('data/insight.db').execute('select model, provider, cost_usd from llm_calls').fetchall())"
   ```
   O provedor deve ser um endpoint ZDR, e o custo total deve ficar abaixo de US$ 0,01.
3. `.\.venv\Scripts\sotawhat run daily --no-notify --limit 3`. Esperado: resumo impresso, `✅`, contagens por perfil e `crossref/*` sem falha. O Semantic Scholar pode aparecer com `429` (sem chave); é esperado e não derruba o run.
4. `.\.venv\Scripts\sotawhat run daily --limit 3`. Esperado: a mensagem chega no Telegram.
5. **Pedir confirmação ao usuário antes de registrar a tarefa**, que altera o Task Scheduler da máquina:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\schedule_daily.ps1 -Vault "D:\Lucas\obsidian_vaults\ml_ai_med_vault"
   Start-ScheduledTask -TaskName sotawhat-daily
   ```
   Depois de ~2 min, `.\.venv\Scripts\sotawhat doctor` deve mostrar `[OK] último run diário: concluído há 0 h`.

---

## Notas de autorrevisão

- **Cobertura da spec (SDD §11, P0):**

  | Entrega do P0 | Onde |
  |---|---|
  | `config.py` | Tarefa 1 |
  | SQLite + schema | Tarefa 2 |
  | `Item` + ids canônicos | Tarefa 3 |
  | Gateway LLM com custo, ZDR e orçamento | Tarefas 6–7 |
  | Adapters ligados ao `collect` | Tarefa 9 |
  | Correção da Nature e remoção de feed morto | Tarefas 4–5 |
  | `run daily` agendado | Tarefas 9 e 11 |
  | `doctor` com teste de fumaça | Tarefa 10 |
  | Telegram de alerta | Tarefas 8–9 |

  Critérios de aceite: "nenhum feed devolve HTML em silêncio" (testes da Tarefa 4 + `source_state`); "testes antigos verdes" (49 → 107); "`doctor --llm` valida JSON estrito" (Tarefa 11, passo 5).
- **Consistência de nomes:**
  - `feeds` e `feed_errors` existem em `RSSSource` e em `CrossrefJournalSource`, e o `run_daily` lê os dois.
  - `Settings.model_override(task)` é usado por `resolve()`.
  - `Store.record_llm_call` aceita só os campos de `_LLM_FIELDS`, o que impede gravar texto de prompt.
  - `LLMGateway.structured(..., models=)` é usado pelo `doctor`.
- **Privacidade:** `test_build_payload_enforces_privacy_schema_and_fallbacks` e `test_structured_returns_model_and_records_real_cost` garantem `zdr: true` por padrão. O token do Telegram não aparece em exceções (`test_errors_never_leak_the_token`).
- **Sem rede nos testes:** todos usam fixtures, `MockTransport` ou fakes. A rede aparece só na Tarefa 11, passo 5.
- **Limites conhecidos** (tratados nas próximas fases):
  - o resumo diário ainda não tem ranking nem "por que importa" (P1);
  - o Semantic Scholar sem chave toma 429 (P2 adiciona `SEMANTIC_SCHOLAR_API_KEY` e cadência);
  - não há log em arquivo, só a tabela `runs` + Telegram (P1).
