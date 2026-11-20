"""Your saved Instagram posts (strategy B, 2026-11-20): the official export read without its labels, the inventory that
spends nothing, the sweep (Apify by URL in batches, the caption filter before any image, its own triage, resumable),
the daily collection, and the account scan turned off. No network: Apify, the LLM and the describer are doubles."""
import json
import zipfile
from argparse import Namespace
from datetime import datetime, timezone

import pytest

from sotawhat.configfiles import Mutes, Rubric
from sotawhat.config import load_settings
from sotawhat.items import Item
from sotawhat.llm.gateway import BudgetExceeded, StructuredResult
from sotawhat.llm.schemas import SavedBatch
from sotawhat.pipeline.triage import OWN_RUN_SOURCES, run_triage
from sotawhat.sources import instagram_saved as saved
from sotawhat.sources.apify import ApifyError
from sotawhat.store.db import Store
from tests.test_triage import FakeGateway

T = 1_763_600_000          # 2025-11-20T00:53:20Z


def saved_record(code, owner, ts, kind="p"):
    return {"title": owner, "media_list_data": [], "string_map_data": {
        "Saved on": {"href": f"https://www.instagram.com/{kind}/{code}/", "timestamp": ts}}}


def export_zip(path, posts, collections=()):
    """An export as Instagram writes it: saved_posts.json and, with collections, saved_collections.json (each
    collection is a record with its name, followed by the records of its posts)."""
    records = []
    for name, codes in collections:
        records.append({"title": "Collection", "string_map_data": {"Name": {"value": name},
                                                                   "Creation Time": {"timestamp": T}}})
        records += [{"string_map_data": {"Name": {"href": f"https://www.instagram.com/p/{c}/", "value": "dono"},
                                         "Added Time": {"timestamp": T + 60}}} for c in codes]
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("your_instagram_activity/saved/saved_posts.json",
                   json.dumps({"saved_saved_media": posts}, ensure_ascii=True))
        if collections:
            z.writestr("your_instagram_activity/saved/saved_collections.json",
                       json.dumps({"saved_saved_collections": records}, ensure_ascii=True))
        z.writestr("connections/followers_and_following/following.json", json.dumps({"relationships_following": []}))
    return path


def raw_post(code, owner="dono", caption="", kind="Image"):
    return {"shortCode": code, "ownerUsername": owner, "caption": caption, "type": kind,
            "displayUrl": f"https://scontent.cdninstagram.com/{code}.jpg", "timestamp": "2025-11-01T10:00:00.000Z"}


class FakeApify:
    """Reads the posts it knows by their URL; the others are private or gone."""

    def __init__(self, known, fail_after=None):
        self.known, self.calls, self.fail_after, self.configured = known, [], fail_after, True

    def run(self, actor, payload, max_usd=0.15, max_items=None):
        if self.fail_after is not None and len(self.calls) >= self.fail_after:
            raise ApifyError("Apify: limite mensal atingido (402)")
        self.calls.append(payload["directUrls"])
        codes = [u.rstrip("/").rsplit("/", 1)[-1] for u in payload["directUrls"]]
        return [self.known[c] for c in codes if c in self.known]

    def usage(self):
        return {"used": 2.55, "limit": 5, "cycle_end": "2026-12-07"}


# ---- the export -------------------------------------------------------------------------------------------------
def test_the_export_is_read_by_its_links_and_names(tmp_path):
    zip_path = export_zip(tmp_path / "salvos.zip", [
        saved_record("AAA111", "medica.ia", T + 100),
        saved_record("BBB222", "receitas", T + 50, kind="reel"),
        saved_record("AAA111", "medica.ia", T + 10),               # saved twice: one post, the latest save
        {"title": "sem_link", "string_map_data": {"Saved on": {"href": "https://example.com/x", "timestamp": T}}}],
        collections=[("IA/Med", ["AAA111"]), ("SaÃºde", ["BBB222"])])   # "Saúde" as Meta writes it
    posts = saved.parse_export(zip_path)
    assert [p["shortcode"] for p in posts] == ["AAA111", "BBB222"]   # the latest save first (a collection counts too)
    a = next(p for p in posts if p["shortcode"] == "AAA111")
    assert a == {"shortcode": "AAA111", "owner": "medica.ia", "saved_at": "2025-11-20T00:55:00+00:00",
                 "collections": ["IA/Med"], "url": "https://www.instagram.com/p/AAA111/"}
    b = next(p for p in posts if p["shortcode"] == "BBB222")
    assert b["url"] == "https://www.instagram.com/reel/BBB222/" and b["collections"] == ["Saúde"]


def test_an_extracted_folder_with_other_labels_and_nested_collections(tmp_path):
    root = tmp_path / "instagram-lucas" / "your_instagram_activity" / "saved"
    root.mkdir(parents=True)
    (root / "saved_posts.json").write_text(json.dumps({"saved_saved_media": [
        {"title": "radiologista", "string_map_data": {"Salvo em": {"href": "https://instagram.com/p/CCC333/",
                                                                   "timestamp": T}}}]}), encoding="utf-8")
    (root / "saved_collections.json").write_text(json.dumps([
        {"title": "IA/Med", "media": [{"href": "https://www.instagram.com/p/CCC333/", "value": "radiologista"},
                                      {"href": "https://www.instagram.com/reel/DDD444/", "value": "lab"}]}]),
        encoding="utf-8")
    posts = {p["shortcode"]: p for p in saved.parse_export(tmp_path / "instagram-lucas")}
    assert posts["CCC333"]["collections"] == ["IA/Med"] and posts["CCC333"]["owner"] == "radiologista"
    assert posts["DDD444"]["collections"] == ["IA/Med"] and posts["DDD444"]["owner"] == "lab"
    assert saved.exports_in(tmp_path) == [tmp_path / "instagram-lucas"]
    assert saved.fingerprint(tmp_path / "instagram-lucas") == saved.fingerprint(tmp_path / "instagram-lucas")


# ---- inventory, filter, sweep -------------------------------------------------------------------------------------
@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path / "insight.db")
    run = store.start_run("daily")
    store.upsert_items([Item(id="ig:KNOWN1", kind="instagram_post", source="instagram", source_id="KNOWN1", title="t",
                             url="https://www.instagram.com/p/KNOWN1/", text="x", profile="geral")], run)
    posts = [{"shortcode": c, "owner": o, "saved_at": f"2025-11-{20 - n:02d}T00:00:00+00:00", "collections": col,
              "url": f"https://www.instagram.com/p/{c}/"}
             for n, (c, o, col) in enumerate([("P1", "medica.ia", ["IA/Med"]), ("P2", "receitas", []),
                                               ("P3", "lab.ia", []), ("GONE", "x", []), ("KNOWN1", "y", [])])]
    yield store, posts, saved.SavedState(tmp_path / "state" / "instagram_saved.json")
    store.close()


def test_the_inventory_spends_nothing(world):
    store, posts, state = world
    accounts = [{"username": "medica.ia", "category": "saude"}, {"username": "receitas", "category": "fora"}]
    inv = saved.inventory(posts, state, store, accounts)
    assert (inv["total"], inv["known"], inv["todo"], inv["usd"]) == (5, 1, 4, round(4 * saved.PRICE, 2))
    assert inv["accounts"] == {"ia": 0, "saude": 1, "fora": 1, "desconhecida": 2}
    text = saved.render_inventory(inv, {"used": 2.55, "limit": 5, "cycle_end": "2026-12-07"})
    assert "5 posts salvos, de 5 contas" in text and "a ler: 4 (0 reels)" in text
    assert "~US$ 0,01 (4 × US$ 0,0027); restam US$ 2,45 de US$ 5,00 no ciclo, que fecha em 2026-12-07" in text
    only = saved.inventory(posts, state, store, accounts, collection="IA/Med")
    assert (only["chosen"], only["todo"]) == (1, 1) and "Só a coleção “IA/Med”: 1 posts." in saved.render_inventory(
        only, collection="IA/Med")


class SavedGateway:
    def __init__(self, verdicts, budget_at=None):
        self.verdicts, self.calls, self.budget_at = verdicts, [], budget_at

    def structured_call(self, task, messages, output_model, models=None):
        assert task == "saved" and output_model is SavedBatch
        self.calls.append(messages[1]["content"])
        if self.budget_at is not None and len(self.calls) > self.budget_at:
            raise BudgetExceeded("daily LLM budget of US$ 1.00 reached")
        lines = messages[1]["content"].splitlines()
        posts = [{"codigo": line.split(" | ")[0], "categoria": self.verdicts.get(line.split(" | ")[0], "incerto"),
                  "motivo": "teste"} for line in lines]
        return StructuredResult(output=SavedBatch(posts=posts), model="m", provider="p", cost_usd=0.0, latency_ms=1,
                                attempts=1, first_try_valid=True)


def test_the_caption_filter_keeps_the_doubtful(world):
    gw = SavedGateway({"A": "fora", "B": "ia"}, budget_at=1)
    notes = []
    classify = saved.make_classifier(gw, notes)
    posts = [{"shortcode": c, "owner": "o", "type": "image", "caption": "legenda " * 200} for c in ("A", "B", "C")]
    assert classify(posts) == {"A": ("fora", "teste"), "B": ("ia", "teste"), "C": ("incerto", "teste")}
    assert len(gw.calls[0].splitlines()[0]) < 440                    # the caption goes cut at 400 characters
    many = [{"shortcode": f"X{n}", "owner": "o", "type": "reel", "caption": ""} for n in range(30)]
    assert len(classify(many)) == 0 and notes == ["filtro interrompido: daily LLM budget of US$ 1.00 reached"]


def test_the_sweep_reads_filters_imports_and_resumes(world):
    store, posts, state = world
    apify = FakeApify({"P1": raw_post("P1", "medica.ia", "Modelo de IA lê raio-X"),
                       "P2": raw_post("P2", "receitas", "Bolo de cenoura"),
                       "P3": raw_post("P3", "lab.ia", "", kind="Video")})
    verdicts = {"P1": ("ambos", "IA na radiologia"), "P2": ("fora", "receita"), "P3": ("incerto", "sem legenda")}
    described, triaged, lines = [], [], []
    run = store.start_run("salvos")

    def describe(post):
        described.append(post["shortcode"])
        return f"imagem de {post['shortcode']}"

    report = saved.sweep(store, posts, state, apify, lambda found: {p["shortcode"]: verdicts[p["shortcode"]] for p in found},
                         describe, lambda rid: triaged.append(rid) or {"main": 1}, run, max_usd=1.0, out=lines.append)
    assert apify.calls == [[p["url"] for p in posts[:4]]]               # KNOWN1 is already in the store
    assert (report["read"], report["fora"], report["kept"], report["imported"], report["missing"]) == (3, 1, 2, 2, 1)
    assert sorted(described) == ["P1", "P3"] and triaged == [run] and report["triage"] == {"main": 1}
    rows = {r["id"]: r for r in store.conn.execute("SELECT id, source, profile, text FROM items WHERE source = ?",
                                                   (saved.BACKLOG,))}
    assert set(rows) == {"ig:P1", "ig:P3"} and rows["ig:P1"]["profile"] == "medico" and "imagem de P1" in rows["ig:P1"]["text"]
    assert {c: v["status"] for c, v in state.posts.items()} == {"KNOWN1": "ja_no_banco", "P1": "importado", "P2": "fora",
                                                                "P3": "importado", "GONE": "indisponivel"}
    assert lines == ["[salvos] lote 1: 3 lidos, 1 fora do tema, 2 importados · US$ 0,01 no Apify"]
    again = saved.sweep(store, posts, saved.SavedState(state.path), apify, lambda found: {}, describe,
                        lambda rid: None, run, out=lines.append)
    assert again["todo"] == 0 and len(apify.calls) == 1                  # resumable: nothing is paid twice


def test_the_sweep_stops_at_its_cap_and_on_apify_errors(world):
    store, posts, state = world
    many = [{"shortcode": f"Q{n}", "owner": "o", "saved_at": "", "collections": [], "url": f"https://www.instagram.com/p/Q{n}/"}
            for n in range(100)]
    apify = FakeApify({f"Q{n}": raw_post(f"Q{n}") for n in range(100)})
    run = store.start_run("salvos")
    capped = saved.sweep(store, many, state, apify, lambda found: {}, None, lambda rid: {}, run, max_usd=0.15)
    assert len(apify.calls) == 1 and capped["read"] == 40 and capped["stopped"].startswith("teto de US$ 0.15")
    broken = saved.sweep(store, many, state, FakeApify({}, fail_after=0), lambda found: {}, None, lambda rid: {}, run)
    assert broken["stopped"] == "Apify: Apify: limite mensal atingido (402)" and broken["read"] == 0


def test_the_daily_triage_leaves_the_backlog_to_its_own_run(tmp_path):
    store = Store(tmp_path / "insight.db")
    run = store.start_run("daily")
    old = Item(id="ig:OLD", kind="instagram_post", source=saved.BACKLOG, source_id="OLD", title="Modelo lê exames",
               url="https://www.instagram.com/p/OLD/", text="IA em radiologia", profile="medico")
    fresh = Item(id="pmid:9", kind="paper", source="pubmed", source_id="9", title="Sepsis model", url="u", text="t",
                 profile="medico")
    store.upsert_items([old, fresh], run)
    store.conn.execute("UPDATE items SET fetched_at = '2020-01-01T00:00:00+00:00' WHERE id = 'ig:OLD'")
    store.conn.commit()
    gw = FakeGateway({})
    daily = run_triage(store, run, gw, Rubric(concurrency=1), Mutes(), None)
    assert daily.candidates == 1 and gw.calls == ["Sepsis model"]
    own = run_triage(store, run, gw, Rubric(concurrency=1), Mutes(), None, sources=(saved.BACKLOG,))
    assert own.candidates == 1 and gw.calls[-1] == "Modelo lê exames"   # however old: the sweep owns it
    assert saved.BACKLOG in OWN_RUN_SOURCES
    store.close()


# ---- the daily part: the collection of each new export -------------------------------------------------------------
def test_the_daily_run_reads_the_collection_of_each_new_export(tmp_path):
    folder = tmp_path / "salvos"
    folder.mkdir()
    export_zip(folder / "semana1.zip", [saved_record("CCC111", "medica.ia", T), saved_record("CCC222", "receitas", T)],
               collections=[("IA/Med", ["CCC111"])])
    apify = FakeApify({"CCC111": raw_post("CCC111", "medica.ia", "IA no pronto-socorro"), "CCC222": raw_post("CCC222")})
    state_file = tmp_path / "state.json"
    source = saved.SavedSource(folder, state_file, apify, describer=lambda post: "imagens", collection="IA/Med")
    results = source.fetch(60)
    assert [r.id for r in results] == ["CCC111"] and results[0].source == saved.CURATED and results[0].extra["manual"]
    assert results[0].extra["instagram"]["collections"] == ["IA/Med"]
    assert apify.calls == [["https://www.instagram.com/p/CCC111/"]]
    assert source.fetch(60) == [] and len(apify.calls) == 1             # an export is read once
    export_zip(folder / "semana2.zip", [saved_record("CCC333", "lab", T)])  # no such collection: noted, nothing read
    assert source.fetch(60) == []
    notes = [e.get("note") for e in json.loads(state_file.read_text(encoding="utf-8"))["exports"].values()]
    assert "sem a coleção “IA/Med”" in notes
    assert saved.SavedSource(folder, state_file, apify, collection="").fetch(60) == []


def test_the_account_scan_can_be_off_and_the_collection_on(tmp_path):
    from sotawhat.profiles import build_sources
    from sotawhat.sources.instagram import InstagramSource

    class On:
        configured = True

    def names(profile, **kw):
        settings = load_settings(sotawhat_data_dir=tmp_path, **kw)
        with Store(tmp_path / "insight.db") as st:
            return [type(s).__name__ for s in build_sources(profile, settings=settings, store=st, apify=On())]

    assert "InstagramSource" in names("geral") and "SavedSource" in names("medico")
    off = names("medico", instagram_account_scan=False)
    assert "InstagramSource" not in off and "InstagramSource" not in names("geral", instagram_account_scan=False)
    assert "SavedSource" in off and "SavedSource" not in names("medico", instagram_saved_collection="")
    assert InstagramSource.__name__ == "InstagramSource"


# ---- the command --------------------------------------------------------------------------------------------------
def test_the_command_shows_the_inventory_and_reads_only_with_yes(tmp_path, world):
    from sotawhat.configfiles import load_config
    from sotawhat.pipeline.accounts import run_saved

    store = world[0]
    settings = load_settings(sotawhat_data_dir=tmp_path, sotawhat_config_dir=tmp_path / "cfg")
    zip_path = export_zip(tmp_path / "export.zip", [saved_record("ZZZ111", "medica.ia", T),
                                                    saved_record("ZZZ222", "x", T - 5)])
    apify = FakeApify({"ZZZ111": raw_post("ZZZ111", "medica.ia", "IA e sepse"), "ZZZ222": raw_post("ZZZ222", "x", "viagem")})
    lines = []
    ns = Namespace(file=str(zip_path), yes=False, colecao=None, limit=None, max_usd=None)
    assert run_saved(settings, ns, store, None, apify, None, out=lines.append) == 0
    assert apify.calls == [] and "2 posts salvos" in "\n".join(lines) and "Nada foi gasto" in lines[-1]
    gateway = SavedGateway({"ZZZ111": "ambos", "ZZZ222": "fora"})
    ns.yes = True
    config = load_config(tmp_path / "cfg") if (tmp_path / "cfg").exists() else None
    code = run_saved(settings, ns, store, config, apify, gateway, out=lines.append,
                     triage_runner=lambda rid: {"main": 1, "radar": 0}, describer=lambda post: "")
    text = "\n".join(lines)
    assert code == 0 and "[salvos] lidos 2 · fora do tema 1 · importados 1" in text and "[triagem] IA ∩ saúde 1" in text
    assert "o acervo não vai para o digest" in lines[-1]
    run = store.conn.execute("SELECT kind, ok FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    assert (run["kind"], run["ok"]) == ("salvos", 1)
    state = saved.SavedState(saved.state_path(settings))
    assert saved.fingerprint(zip_path) in state.exports and state.posts["ZZZ222"]["status"] == "fora"
    empty = Namespace(file=None, yes=False, colecao=None, limit=None, max_usd=None)
    assert run_saved(settings, empty, store, None, apify, None, out=lines.append) == 2 and "Itens salvos" in lines[-1]
