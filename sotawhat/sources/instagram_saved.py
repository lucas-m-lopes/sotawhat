# sotawhat/sources/instagram_saved.py
"""Your saved Instagram posts (strategy B, 2026-11-20), read from the official export.

The account scan (T3) read the newest posts of 51 followed accounts: 212 posts from 2026-11-11 to 20, 1 of them
approved. You asked to read only what you actively save. There is no API for the saved posts, and logging into your
account from a script is against Instagram's terms (SDD §7.2: never the main account), so the list comes from the
export you ask for in the Accounts Center (Download your information → only "Saved items", JSON), dropped in
data/instagram/salvos/. Each post is then read by its URL through Apify, like the links sent to the bot.

- The first sweep, `sotawhat instagram salvos [ZIP]`. Without --yes it is an inventory: how many posts, from which
  accounts, what reading them costs. Nothing is spent. With --yes:
  1. It reads the posts, newest saves first, in batches of 40, up to INSTAGRAM_SAVED_MAX_USD.
  2. It drops what is neither AI nor medicine by the caption (task `saved`, 25 posts a call) before paying for images.
  3. It reads the images, and the speech of reels when faster-whisper is installed.
  4. It imports the rest as `instagram:salvos` items, triaged in the sweep's own run: the backlog goes to the graph
     and to the questions, not to a digest. The daily triage leaves these items alone.
  It is resumable: data/state/instagram_saved.json remembers every post read.
- Afterwards, a collection of saved posts (INSTAGRAM_SAVED_COLLECTION, "IA/Med" by default). For each new export in
  the folder, the daily run reads the posts of that collection as `manual:instagram` items, like the links sent to the
  bot: you chose them when you saved them, so they skip the filters and come first in the digest."""
import hashlib
import json
import logging
import os
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from sotawhat.items import to_item
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import SavedBatch
from sotawhat.sources.apify import ApifyError
from sotawhat.sources.base import Source
from sotawhat.sources.instagram import ACTOR, POST_URL, normalize, to_result
from sotawhat.store.db import utcnow

log = logging.getLogger("sotawhat.instagram_saved")
BACKLOG = "instagram:salvos"     # the first sweep: triaged in its own run, never in a digest
CURATED = "manual:instagram"     # the posts of your collection: like the links sent to the bot
PRICE = 0.0027                   # US$ per post read by Apify (Free plan, measured 2026-11-08)
BATCH = 40                       # posts per Apify run (65 profiles took 662 s on 2026-11-10, past the 600 s wait)
FILTER_BATCH = 25                # captions per call of the `saved` task
PROFILE = {"ia": "geral", "medicina": "medico", "ambos": "medico", "incerto": "medico"}


def folder(settings) -> Path:
    return Path(settings.sotawhat_data_dir) / "instagram" / "salvos"


def state_path(settings) -> Path:
    return Path(settings.sotawhat_data_dir) / "state" / "instagram_saved.json"


# ---- the export -------------------------------------------------------------------------------------------------
def _fix(text) -> str:
    """Meta writes the UTF-8 bytes of its JSON exports as \\u00XX escapes: "SaÃºde" is "Saúde"."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _json_files(path) -> list:
    """(name, data) of the JSON files about saved posts in an export: the zip, or its extracted folder."""
    path = Path(path)
    wanted = lambda name: name.lower().endswith(".json") and ("saved" in name.lower() or "salv" in name.lower())  # noqa: E731
    if path.is_dir():
        return [(f.as_posix(), json.loads(f.read_text(encoding="utf-8"))) for f in sorted(path.rglob("*.json"))
                if wanted(f.as_posix())]
    with zipfile.ZipFile(path) as z:
        return [(name, json.loads(z.read(name).decode("utf-8"))) for name in sorted(z.namelist()) if wanted(name)]


def _records(data) -> list:
    """The records of a file: {"saved_saved_media": [...]} or a bare list."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return next((value for value in data.values() if isinstance(value, list)), [])
    return []


def _dicts(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from _dicts(value)


def _links(record) -> list:
    """[(code, kind, timestamp, value)] of the post links inside a record."""
    out = []
    for d in _dicts(record):
        match = POST_URL.search(d["href"]) if isinstance(d.get("href"), str) else None
        if match:
            out.append((match.group(2), match.group(1), d.get("timestamp"), d.get("value")))
    return out


def _stamp(record):
    return max((d["timestamp"] for d in _dicts(record) if isinstance(d.get("timestamp"), (int, float))), default=None)


def _name(record) -> str | None:
    """The name of a collection: the first text `value` of a record without links, else its title."""
    for d in _dicts(record):
        value = d.get("value")
        if isinstance(value, str) and value.strip() and not d.get("href"):
            return _fix(value.strip())
    title = record.get("title") if isinstance(record, dict) else None
    return _fix(title.strip()) if isinstance(title, str) and title.strip() else None


def _iso(timestamp) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds") if timestamp else ""


def parse_export(path) -> list:
    """-> [{"shortcode", "url", "owner", "saved_at", "collections"}], one per post, the newest save first.

    The saved posts file has one record per post: {"title": owner, "string_map_data": {"Saved on": {"href",
    "timestamp"}}}. The collections file lists each collection (a record with its name and no link) followed by its
    posts; an export that nests the posts inside the collection record is read too. The labels ("Saved on", "Salvo
    em") are not read: only links, timestamps and names."""
    posts = {}

    def add(code, kind, owner, timestamp, collection=None):
        post = posts.setdefault(code, {"shortcode": code, "owner": "", "saved_at": "", "collections": [],
                                       "url": f"https://www.instagram.com/{'reel' if kind in ('reel', 'reels') else 'p'}/{code}/"})
        if owner and not post["owner"]:
            post["owner"] = _fix(str(owner)).lstrip("@")
        when = _iso(timestamp)
        if when > post["saved_at"]:
            post["saved_at"] = when
        if collection and collection not in post["collections"]:
            post["collections"].append(collection)

    is_collection = lambda name: "collection" in name.lower() or "colec" in name.lower()      # noqa: E731
    # the saved posts file first: it names the owner of each post, the collections file only adds where it is
    for name, data in sorted(_json_files(path), key=lambda f: is_collection(f[0])):
        records = _records(data)
        if is_collection(name):
            current = None
            for record in records:
                links = _links(record)
                if not links:
                    current = _name(record) or current
                    continue
                # nested (several links, or one with no collection open): the record's title is the collection
                own = record.get("title") if isinstance(record, dict) and (len(links) > 1 or current is None) else None
                collection = _fix(own) if isinstance(own, str) and own.strip() else current
                for code, kind, timestamp, value in links:
                    add(code, kind, value, timestamp or _stamp(record), collection)
        else:
            for record in records:
                owner = record.get("title") if isinstance(record, dict) else None
                for code, kind, timestamp, value in _links(record):
                    add(code, kind, owner or value, timestamp or _stamp(record))
    return sorted(posts.values(), key=lambda p: p["saved_at"], reverse=True)


def exports_in(path) -> list:
    """The exports dropped in the folder (zips and extracted folders), oldest first."""
    path = Path(path)
    if not path.exists():
        return []
    found = [p for p in path.iterdir() if p.suffix.lower() == ".zip" or p.is_dir()]
    return sorted(found, key=lambda p: p.stat().st_mtime)


def fingerprint(path) -> str:
    """Of the bytes of a zip, or of the names and sizes of a folder: an export is read once."""
    path = Path(path)
    digest = hashlib.sha256()
    if path.is_dir():
        for f in sorted(path.rglob("*")):
            if f.is_file():
                digest.update(f"{f.relative_to(path).as_posix()}:{f.stat().st_size}".encode())
    else:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                digest.update(chunk)
    return digest.hexdigest()[:16]


# ---- what was already read ----------------------------------------------------------------------------------------
class SavedState:
    """data/state/instagram_saved.json: every saved post read (imported, out of scope, unavailable, already in the
    store) and every export the daily run read."""

    def __init__(self, path):
        self.path = Path(path)
        data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.posts, self.exports = data.get("posts", {}), data.get("exports", {})

    def mark(self, code, status, **info) -> None:
        self.posts[code] = {"status": status, "at": utcnow(), **info}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"posts": self.posts, "exports": self.exports}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, self.path)


def known_codes(store, codes) -> set:
    """Shortcodes already in the store (the account scan or the bot brought them)."""
    found, codes = set(), list(codes)
    for start in range(0, len(codes), 500):
        chunk = [f"ig:{c}" for c in codes[start:start + 500]]
        found |= {row[0][3:] for row in store.conn.execute(
            f"SELECT id FROM items WHERE id IN ({','.join('?' * len(chunk))})", chunk)}
    return found


def inventory(posts, state, store, accounts=(), collection=None) -> dict:
    """What a sweep would read, and what it costs. Spends nothing."""
    chosen = [p for p in posts if collection is None or collection in p["collections"]]
    read = [p for p in chosen if p["shortcode"] in state.posts]
    left = [p for p in chosen if p["shortcode"] not in state.posts]
    known = known_codes(store, [p["shortcode"] for p in left])
    todo = [p for p in left if p["shortcode"] not in known]
    followed = {a["username"].lower(): a.get("category") for a in accounts}
    of = Counter(followed.get(p["owner"].lower(), "desconhecida") for p in todo)
    dates = sorted(p["saved_at"][:10] for p in posts if p["saved_at"])
    return {"total": len(posts), "chosen": len(chosen), "read": len(read), "known": len(known), "todo": len(todo),
            "owners": len({p["owner"] for p in posts}), "first": dates[0] if dates else None,
            "last": dates[-1] if dates else None,
            "collections": Counter(c for p in posts for c in p["collections"]).most_common(),
            "years": sorted(Counter(p["saved_at"][:4] for p in posts if p["saved_at"]).items()),
            "accounts": {"ia": of.get("ia", 0), "saude": of.get("saude", 0), "fora": of.get("fora", 0),
                         "desconhecida": of.get("desconhecida", 0)},
            "reels": sum("/reel/" in p["url"] for p in todo), "usd": round(len(todo) * PRICE, 2),
            "top": Counter(p["owner"] for p in todo).most_common(8)}


def money(value, digits=2) -> str:
    """US$ the Brazilian way: 1.234,56."""
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def render_inventory(inv, usage=None, collection=None) -> str:
    n = lambda value: f"{value:,}".replace(",", ".")          # noqa: E731
    lines = [f"Exportação: {n(inv['total'])} posts salvos, de {n(inv['owners'])} contas"
             + (f", salvos de {inv['first']} a {inv['last']}" if inv["first"] else "") + "."]
    if inv["years"]:
        lines.append("Por ano: " + ", ".join(f"{y} {n(c)}" for y, c in inv["years"]) + ".")
    if inv["collections"]:
        lines.append("Coleções: " + ", ".join(f"“{c}” {n(k)}" for c, k in inv["collections"]) + ".")
    if collection:
        lines.append(f"Só a coleção “{collection}”: {n(inv['chosen'])} posts.")
    lines.append(f"Já lidos numa varredura anterior: {n(inv['read'])} · já no banco (varredura das contas ou bot): "
                 f"{n(inv['known'])} · a ler: {n(inv['todo'])} ({n(inv['reels'])} reels).")
    acc = inv["accounts"]
    lines.append(f"Das contas a ler: {n(acc['ia'] + acc['saude'])} posts de contas de IA ou saúde que você segue, "
                 f"{n(acc['fora'])} de contas fora do tema que você segue e {n(acc['desconhecida'])} de contas que você"
                 " não segue (ou que não foram classificadas).")
    if inv["top"]:
        lines.append("Mais salvos: " + ", ".join(f"@{o} {k}" for o, k in inv["top"] if o) + ".")
    cost = f"Ler tudo no Apify: ~US$ {money(inv['usd'])} ({n(inv['todo'])} × US$ {money(PRICE, 4)})"
    if usage and usage.get("limit"):
        left = max(0.0, usage["limit"] - usage["used"])
        cost += f"; restam US$ {money(left)} de US$ {money(usage['limit'])} no ciclo, que fecha em {usage['cycle_end']}"
    lines.append(cost + ".")
    lines.append("A legenda decide antes de qualquer gasto com imagens: o que não é IA nem medicina é descartado por um "
                 "LLM barato (~US$ 0,001 por 25 posts).")
    return "\n".join(lines)


# ---- reading ----------------------------------------------------------------------------------------------------
def make_classifier(gateway, notes=None):
    """-> classify(posts) -> {code: (category, reason)}. A post the model skips, or a batch that fails, stays
    "incerto": a lost answer must not drop a post."""
    system = load_prompt("saved_v1")

    def classify(posts) -> dict:
        out = {}
        for start in range(0, len(posts), FILTER_BATCH):
            chunk = posts[start:start + FILTER_BATCH]
            user = "\n".join(f"{p['shortcode']} | @{p['owner']} | {p['type']} | "
                             + " ".join((p["caption"] or "").split())[:400] for p in chunk)
            try:
                res = gateway.structured_call("saved", [{"role": "system", "content": system},
                                                        {"role": "user", "content": user}], SavedBatch)
            except (BudgetExceeded, InsufficientCredits) as exc:
                if notes is not None:
                    notes.append(f"filtro interrompido: {exc}")
                break
            except LLMFailure as exc:
                if notes is not None:
                    notes.append(f"filtro, lote {start // FILTER_BATCH + 1}: {exc}")
                continue
            codes = {p["shortcode"] for p in chunk}
            for verdict in res.output.posts:
                if verdict.codigo in codes:
                    out[verdict.codigo] = (verdict.categoria, verdict.motivo)
        return out

    return classify


def _results(found, saved, describe, source, manual, workers=4, verdicts=None) -> list:
    """The posts read, described (images, speech) in parallel, as Results."""
    posts = list(found)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        texts = list(pool.map(lambda post: describe(post) if describe else "", posts))
    out = []
    for post, text in zip(posts, texts):
        result = to_result(post, source, text, manual=manual)
        info = saved.get(post["shortcode"]) or {}
        result.extra["instagram"].update(saved_at=info.get("saved_at") or "", collections=info.get("collections") or [])
        if verdicts is not None:
            result.extra["instagram"]["filtro"] = verdicts.get(post["shortcode"], ("incerto", ""))[0]
        out.append(result)
    return out


def read_posts(apify, posts, max_usd, batch=BATCH):
    """Reads the posts by URL in batches, up to `max_usd`. Yields (batch, {code: post}, US$) per batch; stops at the
    cap (raising nothing). ApifyError goes up to the caller."""
    spent = 0.0
    for start in range(0, len(posts), batch):
        chunk = posts[start:start + batch]
        if spent + len(chunk) * PRICE > max_usd + 1e-9:
            return
        raw = apify.run(ACTOR, {"directUrls": [p["url"] for p in chunk], "resultsType": "posts", "resultsLimit": 1},
                        max_usd=round(len(chunk) * PRICE * 1.5 + 0.01, 2), max_items=len(chunk))
        found = {}
        for item in raw:
            post = normalize(item)
            if post is not None:            # (a post its owner pinned is still the post you saved)
                found[post["shortcode"]] = post
        cost = len(raw) * PRICE
        spent += cost
        yield chunk, found, cost


def sweep(store, posts, state, apify, classify, describe, triage, run_id, max_usd=1.0, limit=None, collection=None,
          out=print, workers=4) -> dict:
    """The first sweep (see the module doc). `classify(posts)` -> {code: (category, reason)}; `describe(post)` ->
    text; `triage(run_id)` -> a summary of the triage of the imported items. -> what happened."""
    chosen = [p for p in posts if collection is None or collection in p["collections"]]
    todo = [p for p in chosen if p["shortcode"] not in state.posts]
    known = known_codes(store, [p["shortcode"] for p in todo])
    for code in known:
        state.mark(code, "ja_no_banco")
    todo = [p for p in todo if p["shortcode"] not in known]
    if limit:
        todo = todo[:limit]
    saved = {p["shortcode"]: p for p in todo}
    report = {"todo": len(todo), "read": 0, "missing": 0, "fora": 0, "kept": 0, "imported": 0, "usd": 0.0,
              "stopped": None, "categories": Counter()}
    batches = 0
    try:
        for chunk, found, cost in read_posts(apify, todo, max_usd):
            batches += 1
            report["usd"] += cost
            for p in chunk:
                if p["shortcode"] not in found:
                    state.mark(p["shortcode"], "indisponivel")
                    report["missing"] += 1
            verdicts = classify(list(found.values())) if found else {}
            keep = []
            for code, post in found.items():
                category, reason = verdicts.get(code, ("incerto", "sem veredito"))
                report["categories"][category] += 1
                if category == "fora":
                    state.mark(code, "fora", motivo=reason)
                    report["fora"] += 1
                else:
                    keep.append(post)
            results = _results(keep, saved, describe, BACKLOG, False, workers, verdicts)
            items = [to_item(r, profile=PROFILE[verdicts.get(r.id, ("incerto",))[0]]) for r in results]
            new = set(store.upsert_items(items, run_id))
            for post in keep:
                state.mark(post["shortcode"], "importado", categoria=verdicts.get(post["shortcode"], ("incerto",))[0])
            state.save()
            report["read"] += len(found)
            report["kept"] += len(keep)
            report["imported"] += len(new)
            out(f"[salvos] lote {batches}: {len(found)} lidos, {len(found) - len(keep)} fora do tema, {len(keep)} "
                f"importados · US$ {money(report['usd'])} no Apify")
    except ApifyError as exc:
        report["stopped"] = f"Apify: {exc}"
    state.save()
    remaining = len(todo) - report["read"] - report["missing"]
    if remaining > 0 and report["stopped"] is None:
        report["stopped"] = f"teto de US$ {max_usd:.2f} desta execução: faltam {remaining} posts"
    report["triage"] = triage(run_id) if report["imported"] else None
    return report


class SavedSource(Source):
    """The daily run's part: the posts of your collection in each new export of the folder (see the module doc)."""
    keywordless = True
    ai_specific = True          # you put them in the collection: no keyword filter
    name = "instagram-salvos"
    max_items = 60

    def __init__(self, path, state_file, apify, describer=None, collection="IA/Med", max_usd=1.0):
        self.path, self.state_file, self.apify = Path(path), Path(state_file), apify
        self.describer, self.collection, self.max_usd = describer, collection, max_usd

    def fetch(self, limit):
        if not self.collection or not self.apify.configured:
            return []
        exports = exports_in(self.path)
        if not exports:
            return []
        state = SavedState(self.state_file)
        out = []
        for export in exports:
            key = fingerprint(export)
            if key in state.exports:
                continue
            posts = parse_export(export)
            mine = [p for p in posts if self.collection in p["collections"] and p["shortcode"] not in state.posts]
            entry = {"file": export.name, "at": utcnow(), "posts": len(posts), "collection": len(mine)}
            if not any(self.collection in p["collections"] for p in posts):
                entry["note"] = f"sem a coleção “{self.collection}”"
            saved = {p["shortcode"]: p for p in mine}
            done = True
            try:
                for chunk, found, _ in read_posts(self.apify, mine, self.max_usd):
                    for p in chunk:
                        if p["shortcode"] not in found:
                            state.mark(p["shortcode"], "indisponivel")
                    out += _results(found.values(), saved, self.describer, CURATED, True)
                    for code in found:
                        state.mark(code, "importado", categoria="colecao")
                    state.save()
            except ApifyError as exc:
                log.warning("salvos: Apify falhou (%s); a exportação fica para o próximo run", exc)
                done = False
            if done and all(p["shortcode"] in state.posts for p in mine):
                state.exports[key] = entry
            elif done:
                log.info("salvos: teto de US$ %.2f; o resto da coleção fica para o próximo run", self.max_usd)
            state.save()
        return out
