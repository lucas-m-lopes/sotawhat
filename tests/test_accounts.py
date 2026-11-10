# tests/test_accounts.py
"""Curation of the Instagram accounts (P5, SDD §7.2): the Accounts Center export, the profiles, the
classification in batches and the YAML you review."""
import json
import re
from types import SimpleNamespace

from sotawhat.llm.gateway import BudgetExceeded, StructuredResult
from sotawhat.llm.schemas import AccountBatch
from sotawhat.pipeline import accounts as acc
from sotawhat.sources.instagram import load_accounts

FOLLOWING = {"relationships_following": [
    {"title": "", "media_list_data": [], "string_list_data": [
        {"href": "https://www.instagram.com/medai.br", "value": "medai.br", "timestamp": 1}]},
    {"title": "airesearch", "string_list_data": [{"href": "https://www.instagram.com/_u/airesearch", "timestamp": 2}]},
    {"title": "", "string_list_data": [{"href": "https://www.instagram.com/tia.maria", "value": "tia.maria"}]},
    {"title": "", "string_list_data": [{"href": "https://www.instagram.com/clinica.priv", "value": "clinica.priv"}]}]}
PROFILES = [{"username": "medai.br", "fullName": "Med AI Brasil", "biography": "IA na medicina", "private": False},
            {"username": "airesearch", "fullName": "AI Research", "biography": "papers de ML", "private": False},
            {"username": "tia.maria", "fullName": "Maria", "biography": "", "private": False},
            {"username": "clinica.priv", "fullName": "Clínica X", "biography": "IA em radiologia", "private": True},
            {"username": "novo.lab", "fullName": "Novo Lab", "biography": "agentes de IA", "private": False}]
VERDICTS = {"medai.br": "saude", "airesearch": "ia", "tia.maria": "fora", "clinica.priv": "saude", "novo.lab": "ia"}


class FakeApify:
    configured = True

    def __init__(self):
        self.calls = []

    def run(self, actor, payload, max_usd=0.15, max_items=None, partial=False):
        self.calls.append((actor, payload, max_usd, max_items))
        wanted = {u.rstrip("/").rsplit("/", 1)[-1] for u in payload["directUrls"]}
        return [p for p in PROFILES if p["username"] in wanted]

    def items(self, run_id):
        self.calls.append(("items", run_id))
        return [PROFILES[0]]


class FakeGateway:
    def __init__(self, budget_after=None):
        self.calls, self.budget_after = [], budget_after

    def structured_call(self, task, messages, model_cls, models=None):
        self.calls.append(task)
        if self.budget_after is not None and len(self.calls) > self.budget_after:
            raise BudgetExceeded("daily LLM budget of US$ 1.00 reached")
        names = re.findall(r"^- @(\S+) \|", messages[1]["content"], re.M)
        contas = [{"usuario": "@" + n, "categoria": VERDICTS.get(n, "fora"), "motivo": "teste"} for n in names]
        out = AccountBatch(contas=contas + [{"usuario": "intruso", "categoria": "ia", "motivo": "não estava na lista"}])
        return StructuredResult(output=out, model="deepseek/x", provider=None, cost_usd=0.0002, latency_ms=1, attempts=1,
                                first_try_valid=True)


class Bot:
    configured = True

    def __init__(self):
        self.sent = []

    def send_message(self, text, reply_markup=None, disable_notification=False):
        self.sent.append(text)


def _setup(tmp_path, following=FOLLOWING):
    path = tmp_path / "following.json"
    path.write_text(json.dumps(following), encoding="utf-8")
    config = tmp_path / "config"
    config.mkdir(exist_ok=True)
    return path, SimpleNamespace(sotawhat_config_dir=config)


def test_parse_following_old_and_new_layouts(tmp_path):
    path, _ = _setup(tmp_path)
    assert acc.parse_following(path) == ["medai.br", "airesearch", "tia.maria", "clinica.priv"]
    old = tmp_path / "old.json"
    old.write_text(json.dumps([{"string_list_data": [{"value": "medai.br"}]}, {"string_list_data": [{"value": "x y!"}]}]),
                   encoding="utf-8")
    assert acc.parse_following(old) == ["medai.br"]


def test_without_yes_only_the_plan_is_printed(tmp_path):
    path, settings = _setup(tmp_path)
    apify, lines = FakeApify(), []
    assert acc.run_import(settings, path, apify, FakeGateway(), out=lines.append) == 0
    assert apify.calls == [] and "US$ 0.01" in lines[0] and "--yes" in lines[1]
    assert not (settings.sotawhat_config_dir / "instagram_accounts.yaml").exists()


def test_import_classifies_writes_and_keeps_your_choices(tmp_path):
    path, settings = _setup(tmp_path)
    apify, gateway, bot, lines = FakeApify(), FakeGateway(), Bot(), []
    assert acc.run_import(settings, path, apify, gateway, bot, yes=True, out=lines.append) == 0
    actor, payload, max_usd, max_items = apify.calls[0]
    assert payload["resultsType"] == "details" and max_items == 4 and max_usd == 0.06 and gateway.calls == ["accounts"]
    yaml_path = settings.sotawhat_config_dir / "instagram_accounts.yaml"
    accounts = {a["username"]: a for a in load_accounts(yaml_path)}
    assert set(accounts) == {"medai.br", "airesearch", "tia.maria", "clinica.priv"}          # "intruso" ignored
    assert (accounts["medai.br"]["category"], accounts["medai.br"]["enabled"]) == ("saude", True)
    assert (accounts["airesearch"]["category"], accounts["airesearch"]["enabled"]) == ("ia", True)
    assert accounts["tia.maria"]["enabled"] is False
    assert accounts["clinica.priv"]["enabled"] is False and "captura manual" in accounts["clinica.priv"]["note"]
    assert yaml_path.read_text(encoding="utf-8").startswith("# config/instagram_accounts.yaml")
    assert "IA 1, saúde 2, fora 1" in lines[-1] and bot.sent and "2 habilitadas" in bot.sent[0]

    text = yaml_path.read_text(encoding="utf-8").replace("username: airesearch\n  category: ia\n  enabled: true",
                                                         "username: airesearch\n  category: ia\n  enabled: false")
    yaml_path.write_text(text, encoding="utf-8")                                        # your choice
    more = {"relationships_following": FOLLOWING["relationships_following"] + [
        {"title": "", "string_list_data": [{"value": "novo.lab"}]}]}
    path.write_text(json.dumps(more), encoding="utf-8")
    assert acc.run_import(settings, path, apify, FakeGateway(), yes=True, out=lines.append) == 0
    assert apify.calls[1][1]["directUrls"] == ["https://www.instagram.com/novo.lab/"]        # only the new one
    accounts = {a["username"]: a for a in load_accounts(yaml_path)}
    assert accounts["airesearch"]["enabled"] is False and accounts["novo.lab"]["enabled"] is True


def test_enabled_cap_and_budget_stop(tmp_path):
    path, settings = _setup(tmp_path)
    lines = []
    assert acc.run_import(settings, path, FakeApify(), FakeGateway(), max_enabled=1, yes=True, out=lines.append) == 0
    accounts = load_accounts(settings.sotawhat_config_dir / "instagram_accounts.yaml")
    assert [a["username"] for a in accounts if a["enabled"]] == ["medai.br"]
    profiles = {p["username"]: {"full_name": "", "bio": "", "private": False, "followers": 0, "category_name": ""}
                for p in PROFILES}
    notes = []
    verdicts = acc.classify(FakeGateway(budget_after=1), profiles, batch=2, notes=notes)
    assert set(verdicts) == {"medai.br", "airesearch"} and notes[0].startswith("classificação interrompida")


def test_profiles_go_in_batches_with_a_cache_and_an_aborted_run_is_salvaged(tmp_path, monkeypatch):
    path, settings = _setup(tmp_path)
    cache = tmp_path / "state" / "instagram_profiles.json"
    apify, lines = FakeApify(), []
    monkeypatch.setattr(acc, "BATCH", 2)
    fetched = acc.fetch_profiles(apify, ["medai.br", "airesearch", "tia.maria"], batch=2, cache={},
                                 save=lambda p: acc.write_cache(cache, p), out=lines.append)
    assert set(fetched) == {"medai.br", "airesearch", "tia.maria"} and len(apify.calls) == 2   # 2 + 1
    assert [len(c[1]["directUrls"]) for c in apify.calls] == [2, 1] and lines == ["[apify] perfis 2/3", "[apify] perfis 3/3"]
    assert set(acc.read_cache(cache)) == {"medai.br", "airesearch", "tia.maria"}
    # the import: what the aborted run fetched comes back free, the cache is not fetched again
    cache.unlink()
    apify = FakeApify()
    assert acc.run_import(settings, path, apify, FakeGateway(), out=lines.append, cache_path=cache, salvage="r1") == 0
    assert apify.calls == [("items", "r1")] and "1 perfis recuperados do run r1" in lines[-3]
    assert "(1 perfis já buscados)" in lines[-2] and not (settings.sotawhat_config_dir / "instagram_accounts.yaml").exists()
    assert acc.run_import(settings, path, apify, FakeGateway(), yes=True, out=lines.append, cache_path=cache) == 0
    urls = [u for c in apify.calls[1:] for u in c[1]["directUrls"]]
    assert "https://www.instagram.com/medai.br/" not in urls and len(urls) == 3
    assert len(load_accounts(settings.sotawhat_config_dir / "instagram_accounts.yaml")) == 4


def test_cli_instagram_import():
    from sotawhat.cli import parse_args

    ns = parse_args(["instagram", "import", "following.json", "--yes", "--max", "30"])
    assert (ns.command, ns.instagram_action, ns.file, ns.yes, ns.max, ns.limit) == \
        ("instagram", "import", "following.json", True, 30, None)
    assert parse_args(["instagram", "import", "f.json"]).yes is False
