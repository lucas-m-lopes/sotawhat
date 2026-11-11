# tests/test_graph_fixes.py
"""`sotawhat repair entities` (2026-11-11): merges, renames and drops of the entity graph, by hand
(config/entity_fixes.yaml) and by the current naming rule (an acronym inside a name)."""
import json

import pytest

from sotawhat.cli import parse_args
from sotawhat.configfiles import ConfigError, load_config, load_entity_fixes
from sotawhat.graph import fixes as fx
from sotawhat.items import Item
from sotawhat.store.db import Store

SEEN = {1: "2026-11-08T10:00:00+00:00", 2: "2026-11-09T10:00:00+00:00", 3: "2026-11-10T10:00:00+00:00",
        4: "2026-11-11T10:00:00+00:00"}
FIXES = {"merge": [(("regulation", "Model Context Protocol"), ("technique", "Model Context Protocol")),
                   (("model", "GPT4"), ("model", "GPT-4")),
                   (("dataset", "Nothing Like This"), ("dataset", "MIMIC-IV"))],
         "rename": [(("technique", "nn-UNet"), "nnU-Net")],
         "drop": [("organization", "level 3 delivery NICU")]}


@pytest.fixture
def st(tmp_path):
    store = Store(tmp_path / "insight.db")
    run = store.start_run("daily")
    store.upsert_items([Item(id=f"pmid:{n}", kind="paper", source="pubmed", source_id=str(n), title=f"Paper {n}",
                             url=f"https://example.org/{n}", text="t", pmid=str(n)) for n in SEEN], run)
    for n, seen in SEEN.items():
        store.conn.execute("UPDATE items SET fetched_at = ? WHERE id = ?", (seen, f"pmid:{n}"))
        store.record_triage(f"pmid:{n}", run, "main", total=4.0)
    store.conn.commit()
    ids = {}
    for key, type_, name, norm, category in [
            ("mcp_t", "technique", "Model Context Protocol", "model context protocol", "C07"),
            ("mcp_r", "regulation", "Model Context Protocol", "model context protocol", None),
            ("health", "product", "HealthAPI", "healthapi", None), ("codex", "product", "Codex", "codex", None),
            ("gpt4", "model", "GPT-4", "gpt 4", None), ("gpt4b", "model", "GPT4", "gpt4", None),
            ("nn", "technique", "nn-UNet", "nn unet", None),
            ("nicu", "organization", "level 3 delivery NICU", "level 3 delivery nicu", None),
            ("agent", "technique", "large language model agent", "large language model agent", None),
            ("agent_paren", "technique", "large language model (LLM) agent", "large language model llm agent", None),
            ("cac", "technique", "coronary artery calcium (CAC) scoring", "coronary artery calcium cac scoring", None)]:
        ids[key] = store.add_entity(type_, name, norm, category=category)
        store.add_alias("artifact" if type_ in ("model", "product") else type_, norm, ids[key], name)
    store.add_alias("regulation", "mcp", ids["mcp_r"], "MCP")
    for n, key, role in [(1, "mcp_t", "used"), (1, "health", "main"), (2, "mcp_r", "main"), (2, "codex", "main"),
                         (3, "mcp_r", "mentioned"), (3, "mcp_t", "used"), (1, "gpt4", "used"), (4, "gpt4b", "main"),
                         (4, "codex", "used"), (2, "nn", "used"), (4, "nicu", "mentioned"), (1, "agent", "used"),
                         (3, "agent_paren", "main"), (4, "cac", "main")]:
        store.add_mention(f"pmid:{n}", ids[key], role, SEEN[n])
    store.add_relation(ids["health"], "uses", ids["mcp_t"], "pmid:1")
    store.add_relation(ids["codex"], "regulated_by", ids["mcp_r"], "pmid:2")    # needs a regulation: dropped
    store.add_relation(ids["mcp_r"], "compared_with", ids["mcp_t"], "pmid:3")    # becomes a self-relation: dropped
    store.add_relation(ids["gpt4b"], "compared_with", ids["codex"], "pmid:4")
    store.conn.execute("INSERT INTO communities(run_id, community, label, size, top_entity_id) VALUES(9, 0, 'x', 3, ?)",
                       (ids["mcp_r"],))
    store.conn.executemany("INSERT INTO entity_communities(run_id, entity_id, community) VALUES(9, ?, 0)",
                           [(ids["mcp_r"],), (ids["mcp_t"],), (ids["nicu"],)])
    store.conn.commit()
    lesson = store.create_lesson("MCP", [ids["mcp_r"], ids["gpt4"]])
    yield store, ids, lesson
    store.close()


def _summary(plan):
    return [(s.action, s.source["name"], s.target["name"] if s.target is not None else s.new_name) for s in plan.steps]


def test_the_plan_lists_every_change_and_writes_nothing(st):
    store, ids, _ = st
    before = store.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    plan = fx.plan_fixes(store, FIXES)
    assert _summary(plan) == [
        ("merge", "Model Context Protocol", "Model Context Protocol"), ("merge", "GPT4", "GPT-4"),
        ("rename", "nn-UNet", "nnU-Net"), ("drop", "level 3 delivery NICU", None),
        ("merge", "large language model (LLM) agent", "large language model agent"),
        ("rename", "coronary artery calcium (CAC) scoring", "coronary artery calcium scoring")]
    assert [s.source["type"] + "→" + s.target["type"] for s in plan.steps if s.action == "merge"][0] == \
        "regulation→technique"
    assert len(plan.skipped) == 1 and "Nothing Like This" in plan.skipped[0]
    assert store.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == before
    assert store.meta_get("graph_rebuild") is None


def test_a_merge_moves_mentions_relations_aliases_and_what_points_to_the_entity(st):
    store, ids, lesson = st
    report = fx.apply_fixes(store, fx.plan_fixes(store, FIXES))
    assert report == {"merged": 3, "renamed": 2, "dropped": 1, "relations_dropped": 2}
    assert store.get_entity(ids["mcp_r"]) is None
    mcp = store.get_entity(ids["mcp_t"])
    assert (mcp["mention_count"], mcp["first_seen"], mcp["last_seen"], mcp["category"]) == (3, SEEN[1], SEEN[3], "C07")
    roles = {r[0]: r[1] for r in store.conn.execute("SELECT item_id, role FROM entity_mentions WHERE entity_id = ?",
                                                     (ids["mcp_t"],))}
    assert roles == {"pmid:1": "used", "pmid:2": "main", "pmid:3": "used"}    # the stronger role of each item
    for alias in ("model context protocol", "mcp"):                          # the next extraction lands here
        assert store.entity_by_alias("regulation", alias)["id"] == ids["mcp_t"]
    assert {tuple(r) for r in store.conn.execute("SELECT subject_id, predicate, object_id FROM entity_relations")} == {
        (ids["health"], "uses", ids["mcp_t"]), (ids["gpt4"], "compared_with", ids["codex"])}
    assert tuple(store.conn.execute("SELECT entity_id, method FROM entity_merges WHERE name = 'GPT4'").fetchone()) == (
        ids["gpt4"], "repair")
    assert store.get_entity(ids["gpt4"])["mention_count"] == 2 and store.get_entity(ids["gpt4b"]) is None
    assert [r[0] for r in store.conn.execute("SELECT entity_id FROM entity_communities")] == [ids["mcp_t"]]
    assert store.conn.execute("SELECT top_entity_id FROM communities").fetchone()[0] == ids["mcp_t"]
    assert json.loads(store.get_lesson(lesson)["entities_json"]) == [ids["mcp_t"], ids["gpt4"]]
    assert store.meta_get("graph_rebuild") == "1"                            # the mirror is rebuilt at the next sync


def test_renames_drops_and_names_with_an_inner_acronym(st):
    store, ids, _ = st
    fx.apply_fixes(store, fx.plan_fixes(store, FIXES))
    nn = store.get_entity(ids["nn"])
    assert (nn["name"], nn["norm"]) == ("nnU-Net", "nnu net")
    assert store.entity_by_alias("technique", "nn unet")["id"] == ids["nn"]          # the old key stays an alias
    assert store.entity_by_alias("technique", "nnu net")["id"] == ids["nn"]
    assert store.get_entity(ids["agent_paren"]) is None and store.get_entity(ids["agent"])["mention_count"] == 2
    cac = store.get_entity(ids["cac"])
    assert (cac["name"], cac["norm"]) == ("coronary artery calcium scoring", "coronary artery calcium scoring")
    assert store.get_entity(ids["nicu"]) is None
    for table in ("entity_mentions", "entity_aliases"):
        assert not store.conn.execute(f"SELECT 1 FROM {table} WHERE entity_id = ?", (ids["nicu"],)).fetchone()


def test_a_second_run_has_nothing_left_to_do(st):
    store, _, _ = st
    fx.apply_fixes(store, fx.plan_fixes(store, FIXES))
    again = fx.plan_fixes(store, FIXES)
    assert again.steps == []
    assert len(again.skipped) == 1 and "Nothing Like This" in again.skipped[0]     # the dropped one is just gone


def test_a_rename_onto_a_taken_name_becomes_a_merge(st):
    store, ids, _ = st
    plan = fx.plan_fixes(store, {"merge": [], "drop": [],
                                 "rename": [(("technique", "large language model (LLM) agent"),
                                             "large language model agent")]})
    assert _summary(plan)[0] == ("merge", "large language model (LLM) agent", "large language model agent")


def test_entity_fixes_yaml_is_validated(tmp_path):
    path = tmp_path / "entity_fixes.yaml"
    path.write_text('merge:\n  "regulation: Model Context Protocol": "technique: Model Context Protocol"\n'
                    'rename:\n  "technique: nn-UNet": nnU-Net\ndrop:\n  - "organization: level 3 delivery NICU"\n',
                    encoding="utf-8")
    assert load_entity_fixes(path) == {
        "merge": [(("regulation", "Model Context Protocol"), ("technique", "Model Context Protocol"))],
        "rename": [(("technique", "nn-UNet"), "nnU-Net")], "drop": [("organization", "level 3 delivery NICU")]}
    for bad in ('merge:\n  "lei: X": "technique: Y"\n', 'drop: "technique: X"\n', 'merge:\n  "X": "technique: Y"\n',
                'rename:\n  "technique: X": ""\n', 'other: 1\n', 'merge:\n  "model: A": "model: A"\n'):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(ConfigError):
            load_entity_fixes(path)
    assert load_entity_fixes(tmp_path / "missing.yaml") == {"merge": [], "rename": [], "drop": []}


def test_the_repository_fixes_load_and_the_command_exists():
    config = load_config("config")
    assert ("organization", "level 3 delivery NICU") in config.entity_fixes["drop"]
    assert (("regulation", "Model Context Protocol"), ("technique", "Model Context Protocol")) in \
        config.entity_fixes["merge"]
    assert parse_args(["repair", "entities", "--dry-run"]).repair_action == "entities"


def test_a_retyped_entity_keeps_its_comparisons_and_uses_of_a_task_become_addresses(tmp_path):
    store = Store(tmp_path / "insight.db")
    run = store.start_run("daily")
    store.upsert_items([Item(id="pmid:1", kind="paper", source="pubmed", source_id="1", title="Paper 1",
                             url="https://example.org/1", text="t", pmid="1")], run)
    store.record_triage("pmid:1", run, "main", total=4.0)
    ids = {key: store.add_entity(type_, name, name.lower()) for key, type_, name in [
        ("nn_m", "model", "nnU-Net"), ("nn_t", "technique", "nnU-Net"), ("swin", "model", "Swin-Unet"),
        ("rrg_t", "technique", "radiology report generation"), ("rrg_p", "problem", "radiology report generation"),
        ("radref", "technique", "RadRef")]}
    for key in ids:
        store.add_mention("pmid:1", ids[key], "used", SEEN[1])
    store.add_relation(ids["nn_m"], "compared_with", ids["swin"], "pmid:1")
    store.add_relation(ids["radref"], "uses", ids["rrg_t"], "pmid:1")
    fx.apply_fixes(store, fx.plan_fixes(store, {"rename": [], "drop": [], "merge": [
        (("model", "nnU-Net"), ("technique", "nnU-Net")),
        (("technique", "radiology report generation"), ("problem", "radiology report generation"))]}))
    assert {tuple(r) for r in store.conn.execute("SELECT subject_id, predicate, object_id FROM entity_relations")} == {
        (ids["nn_t"], "compared_with", ids["swin"]), (ids["radref"], "addresses", ids["rrg_p"])}
    store.close()
