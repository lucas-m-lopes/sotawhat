# sotawhat/graph/resolve.py
"""Entity resolution (SDD §6.8): each extraction becomes rows of the entity graph in SQLite.

1. `normalize`: lowercase, no accents, punctuation or leading "the"; techniques and problems singular.
   `split_acronym`: a trailing acronym in parentheses becomes an alias ("retrieval-augmented generation
   (RAG)"); any other trailing parenthesis is dropped from the name.
2. Exact match by (group, normalized name) in the aliases, seeded from config/aliases.yaml. Model and
   product form one group ("artifact"), because texts draw the line between them differently.
3. Similar names, always with the same numbers ("GPT-4o" never meets "GPT-4.1"): similar text, one name
   inside the other ("DeepMind" ⊂ "Google DeepMind") or close name embeddings. They go to the LLM judge
   (task `resolve`), at most `max_judge_calls` per run. Without a judge, past the cap or on a "no", the
   name becomes a new entity: two nodes are cheaper than a wrong merge. Every merge is recorded.
4. Mentions (main, used, mentioned), relations inside the allowed patterns, and the taxonomy
   categories: the triage tags of the item and the category of each technique, model or problem.
"""
import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

import numpy as np

from sotawhat import taxonomy as tx
from sotawhat.llm.gateway import BudgetExceeded, LLMFailure
from sotawhat.llm.openrouter import InsufficientCredits
from sotawhat.llm.prompts import load as load_prompt
from sotawhat.llm.schemas import _CJK, SameEntity

TYPES = ("technique", "model", "dataset", "organization", "product", "problem", "regulation")
GROUPS = {"model": "artifact", "product": "artifact"}
CATEGORY_AXES = {"domains": ("domain", tx.DOMAINS), "problem_types": ("problem_type", tx.PROBLEMS),
                 "techniques": ("technique_family", tx.TECHNIQUES)}
ENTITY_CATEGORY = {"technique": ("technique_family", tx.TECHNIQUES), "model": ("technique_family", tx.TECHNIQUES),
                   "problem": ("problem_type", tx.PROBLEMS)}
SINGULAR_TYPES = {"technique", "problem"}
# words that end in s without being plurals (acronyms, short words and words with symbols are kept anyway)
NOT_PLURAL = {"diabetes", "herpes", "measles", "rabies", "scabies", "mumps", "series", "species", "news", "lens",
              "aids", "lupus", "bias", "atlas", "alias", "canvas", "pancreas", "caries", "chaos", "ethos", "cosmos",
              "means"}
ES_PLURAL = {"bias", "lens", "atlas", "alias", "canvas", "gas", "bus", "virus", "status", "bonus", "campus", "census",
             "consensus", "corpus", "sinus", "fetus", "focus", "plexus", "nexus", "apparatus", "syllabus"}  # "biases"
CHE_WORDS = {"cache", "niche", "headache", "toothache", "earache", "backache", "stomachache", "heartache",
             "avalanche", "moustache", "psyche", "tranche", "cliche", "quiche"}       # "caches" → "cache", not "cach"
IE_WORDS = {"cookie", "movie", "calorie", "selfie", "zombie", "rookie"}               # "cookies" → "cookie"
IRREGULAR = {"diagnoses": "diagnosis", "prognoses": "prognosis", "metastases": "metastasis", "stenoses": "stenosis",
             "thromboses": "thrombosis", "crises": "crisis", "axes": "axis", "matrices": "matrix", "indices": "index",
             "vertices": "vertex", "cortices": "cortex", "criteria": "criterion", "phenomena": "phenomenon",
             "foci": "focus", "nuclei": "nucleus", "stimuli": "stimulus", "thrombi": "thrombus", "emboli": "embolus",
             "vertebrae": "vertebra"}
PREPOSITIONS = {"of", "for", "in", "on", "with", "to", "from", "by", "via", "at", "as", "about", "after", "before",
                "during", "under", "over", "across", "between", "among", "against", "without", "within", "into",
                "through", "toward", "towards", "per", "versus", "vs", "de", "da", "do", "das", "dos", "em", "para",
                "com"}
GENERIC = {"ai", "artificial intelligence", "machine learning", "ml", "deep learning", "model", "ai model",
           "algorithm", "method", "framework", "system", "ai system", "tool", "ai tool", "dataset", "data",
           "study", "patient", "clinician", "doctor", "physician", "nurse", "hospital", "healthcare",
           "health care", "medicine", "research", "researcher", "benchmark", "platform", "application",
           "approach", "technology", "software", "paper", "company", "startup", "user", "problem"}
MAX_NAME, MAX_ENTITIES, MAX_RELATIONS = 80, 12, 10
SIMILAR_TEXT, SIMILAR_VECTOR, MAX_CANDIDATES = 0.88, 0.90, 3
PATTERNS = {   # relation -> (allowed source types, allowed target types); compared_with: same group
    "uses": ({"technique", "model", "product", "organization"}, {"technique", "model", "dataset", "product"}),
    "addresses": ({"technique", "model", "product", "organization"}, {"problem"}),
    "developed_by": ({"model", "product", "dataset", "technique"}, {"organization"}),
    "evaluated_on": ({"model", "technique", "product"}, {"dataset"}),
    "builds_on": ({"model", "technique", "product"}, {"model", "technique"}),
    "regulated_by": ({"product", "model", "technique", "organization"}, {"regulation"}),
}
_MINOR = {"and", "of", "the", "for", "in", "on", "with", "to", "a", "an", "de", "da", "do", "e"}
_PAREN = re.compile(r"^(.+?)\s*\(([^()]{1,60})\)$")
log = logging.getLogger("sotawhat.resolve")


def group(type_) -> str:
    return GROUPS.get(type_, type_)


def _singular(word) -> str:
    """One word in the singular, keeping its case. Short words, acronyms ("ARDS", "CAMS"), words with digits or
    symbols ("Harness-S", "Alzheimer's") and words that only look plural ("bias", "diabetes") stay as they are."""
    lower = word.lower()
    if len(word) <= 3 or not word.isalpha() or word.isupper() or lower in NOT_PLURAL:
        return word
    if lower in IRREGULAR:
        return word[0] + IRREGULAR[lower][1:]
    if lower.endswith("ies"):
        return word[:-1] if lower[:-1] in IE_WORDS else word[:-3] + "y"
    if lower.endswith(("yses", "heses")):                                  # analyses, hypotheses
        return word[:-2] + "is"
    if lower.endswith("es") and (lower[:-2] in ES_PLURAL or lower.endswith(("sses", "xes", "shes"))
                                 or (lower.endswith("ches") and lower[:-1] not in CHE_WORDS)):
        return word[:-2]
    if lower.endswith("s") and not lower.endswith(("ss", "us", "is", "ics")):
        return word[:-1]
    return word


def _preposition(word) -> bool:
    return word.lower() in PREPOSITIONS and not word.isupper()                 # "AS" is a disease, not "as"


def display_name(name, type_) -> str:
    """The name with whitespace collapsed and, for techniques and problems, its head noun in the singular. The
    head is the word before the first preposition ("attacks on LLMs" → "attack on LLMs", "mixture of experts"
    keeps its experts), else the last word. The parts of a hyphenated last word count as words
    ("mixture-of-experts", "AI-agents" → "AI-agent"); earlier compounds do not ("state-of-the-art models")."""
    words = name.split()
    if type_ not in SINGULAR_TYPES or not words:
        return " ".join(words)
    units = [[w] for w in words[:-1]] + [words[-1].split("-")]
    flat = [(i, j) for i, parts in enumerate(units) for j in range(len(parts))]
    stops = [k for k, (i, j) in enumerate(flat) if _preposition(units[i][j])]
    head = stops[0] - 1 if stops else len(flat) - 1
    if head >= 0:
        i, j = flat[head]
        lead, core, tail = re.fullmatch(r"(\W*)(.*?)(\W*)", units[i][j], re.S).groups()
        units[i][j] = lead + _singular(core) + tail
    return " ".join("-".join(parts) for parts in units)


def normalize(name, type_=None) -> str:
    """The identity key of a name: the display name without case, accents, punctuation or a leading "the"."""
    text = unicodedata.normalize("NFKD", display_name(name or "", type_))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower().replace("&", " and ")
    words = re.sub(r"[\W_]+", " ", text).split()
    if len(words) > 1 and words[0] == "the":
        words = words[1:]
    return " ".join(words)


def digits(norm) -> frozenset:
    return frozenset(w for w in norm.split() if any(c.isdigit() for c in w))


def _initials(text) -> str:
    words = [w for w in re.split(r"[\s\-/]+", text.lower()) if w and w not in _MINOR]
    return "".join(w[0] for w in words)


def _is_acronym_of(acronym, text) -> bool:
    if not re.fullmatch(r"[A-Z][A-Za-z0-9]{1,9}", acronym) or sum(c.isupper() for c in acronym) < 2:
        return False
    letters = acronym[:-1] if acronym.endswith("s") and acronym[:-1].isupper() else acronym
    return re.sub(r"[^a-z]", "", letters.lower()) == _initials(text)


def split_acronym(name) -> tuple:
    """(name, acronym or None). 'retrieval-augmented generation (RAG)' and 'RAG (retrieval-augmented
    generation)' give the same answer; 'MedGemma 1.5 (Google)' gives ('MedGemma 1.5', None)."""
    name = " ".join((name or "").split())
    match = _PAREN.match(name)
    if not match:
        return name, None
    outer, inner = match.group(1).strip(), match.group(2).strip()
    if _is_acronym_of(inner, outer):
        return outer, inner
    if _is_acronym_of(outer, inner):
        return inner, outer
    return outer, None


def allowed(relation, source_type, target_type) -> bool:
    if relation == "compared_with":
        return group(source_type) == group(target_type)
    sources, targets = PATTERNS.get(relation, (set(), set()))
    return source_type in sources and target_type in targets


@dataclass
class ResolveOutcome:
    new_entities: int = 0
    mentions: int = 0
    relations: int = 0
    dropped: int = 0
    judge_calls: int = 0
    merges: int = 0


@dataclass
class _Known:
    id: int
    name: str
    norm: str
    tokens: frozenset
    nums: frozenset
    vector: object = None


def _field(row, key, default=None):
    return row[key] if key in row.keys() else default


class Resolver:
    def __init__(self, store, embedder=None, judge=None, aliases=None, max_judge_calls=40):
        self.store, self.embedder, self.judge = store, embedder, judge
        self.max_judge_calls, self.judge_calls = max_judge_calls, 0
        self._seeds = {}         # (group, normalized alias) -> canonical name, from config/aliases.yaml
        for type_, table in (aliases or {}).items():
            for canonical, names in table.items():
                for alias in [canonical] + list(names):
                    self._seeds[(group(type_), normalize(alias, type_))] = canonical
        self._groups = {}        # group -> [_Known], loaded on first use
        self._categories = {}    # (category type, key) -> entity id

    # --- taxonomy categories ------------------------------------------------
    def _category(self, type_, key, table) -> int:
        if (type_, key) not in self._categories:
            eid = self.store.add_entity(type_, table[key], key.lower(), category=key)
            self.store.add_alias(type_, key.lower(), eid, key)
            self._categories[(type_, key)] = eid
        return self._categories[(type_, key)]

    def link_categories(self, item_id, tags, seen) -> int:
        """Triage tags (domains A, problem types B, technique families C) as 'tag' mentions; idempotent."""
        new = 0
        for axis, (type_, table) in CATEGORY_AXES.items():
            for key in (tags or {}).get(axis) or []:
                if key in table and self.store.add_mention(item_id, self._category(type_, key, table), "tag", seen):
                    new += 1
        return new

    # --- matching -----------------------------------------------------------
    def _known(self, grp) -> list:
        if grp not in self._groups:
            rows = self.store.entities_of_types([t for t in TYPES if group(t) == grp])
            vectors = (self.store.load_entity_embeddings(self.embedder.name, [r["id"] for r in rows])
                       if self.embedder is not None else {})
            self._groups[grp] = [_Known(r["id"], r["name"], r["norm"], frozenset(r["norm"].split()), digits(r["norm"]),
                                        vectors.get(r["id"])) for r in rows]
        return self._groups[grp]

    def _embed(self, type_, name):
        if self.embedder is None:
            return None
        try:
            return np.asarray(self.embedder.embed([f"{type_}: {name}"])[0], dtype=np.float32)
        except Exception as exc:  # noqa: BLE001 - e.g. the model is unavailable: text matching still works
            log.warning("entity embeddings off for this run: %s", exc)
            self.embedder = None
            return None

    def _candidates(self, grp, norm, vector) -> list:
        tokens, nums = frozenset(norm.split()), digits(norm)
        # one name inside the other points to a synonym for names ("DeepMind" ⊂ "Google DeepMind"), but to a
        # narrower concept for techniques and problems ("large language model" ⊂ "large language model agent")
        by_containment = grp not in SINGULAR_TYPES
        found = []
        for known in self._known(grp):
            if known.nums != nums or known.norm == norm:
                continue
            shared = tokens & known.tokens
            contained = by_containment and (tokens < known.tokens or known.tokens < tokens) \
                and any(len(t) >= 4 for t in shared)
            matcher = SequenceMatcher(None, norm, known.norm)
            ratio = (matcher.ratio() if matcher.real_quick_ratio() >= SIMILAR_TEXT
                     and matcher.quick_ratio() >= SIMILAR_TEXT else 0.0)
            cosine = float(np.dot(vector, known.vector)) if vector is not None and known.vector is not None else 0.0
            if ratio >= SIMILAR_TEXT or contained or cosine >= SIMILAR_VECTOR:
                found.append((max(ratio, cosine, 0.9 if contained else 0.0), known))
        found.sort(key=lambda pair: -pair[0])
        return found[:MAX_CANDIDATES]

    def _ask_judge(self, type_, grp, name, norm, vector, context, item_id, out):
        if self.judge is None:
            return None
        for score, known in self._candidates(grp, norm, vector):
            if self.judge_calls >= self.max_judge_calls:
                return None
            self.judge_calls += 1
            out.judge_calls += 1
            if self.judge(type_, name, context, known.name, self.store.entity_context(known.id)):
                self.store.add_alias(grp, norm, known.id, name)
                self.store.record_merge(known.id, name, "judge", score=round(score, 3), item_id=item_id)
                out.merges += 1
                return known.id
        return None

    def _create(self, type_, grp, name, norm, category, vector, out) -> int:
        known = self._known(grp)                 # load the group before the new row exists
        table = ENTITY_CATEGORY.get(type_, (None, {}))[1]
        eid = self.store.add_entity(type_, name, norm, category if category in table else None)
        self.store.add_alias(grp, norm, eid, name)
        if vector is not None and self.embedder is not None:
            self.store.save_entity_embeddings(self.embedder.name, [(eid, vector)])
        known.append(_Known(eid, name, norm, frozenset(norm.split()), digits(norm), vector))
        out.new_entities += 1
        return eid

    def resolve(self, type_, name, norm, category, context, item_id, out) -> int:
        grp, extra = group(type_), []
        canonical = self._seeds.get((grp, norm))
        if canonical is not None:
            canonical_norm = normalize(canonical, type_)
            if canonical_norm != norm:
                extra.append((norm, name))
            name, norm = canonical, canonical_norm
        hit = self.store.entity_by_alias(grp, norm)
        if hit is not None:
            eid = hit["id"]
        else:
            vector = self._embed(type_, name)
            eid = self._ask_judge(type_, grp, name, norm, vector, context, item_id, out)
            if eid is None:
                eid = self._create(type_, grp, name, norm, category, vector, out)
        for alias_norm, alias in extra:
            self.store.add_alias(grp, alias_norm, eid, alias)
        return eid

    # --- one item -----------------------------------------------------------
    def apply(self, row, extraction) -> ResolveOutcome:
        out = ResolveOutcome()
        item_id, seen, context = row["id"], row["fetched_at"], row["title"]
        tags = json.loads(_field(row, "tags_json") or "{}")
        out.mentions += self.link_categories(item_id, tags, seen)
        foreign_ok = bool(_CJK.search(f"{row['title']} {row['text'] or ''}"))
        names = {}
        for ent in extraction.entities[:MAX_ENTITIES]:
            base, acronym = split_acronym(ent.name)
            shown, norm = display_name(base, ent.type), normalize(base, ent.type)
            if not norm or len(base) > MAX_NAME or norm in GENERIC or (_CJK.search(base) and not foreign_ok):
                out.dropped += 1
                continue
            eid = self.resolve(ent.type, shown, norm, ent.category, context, item_id, out)
            if acronym:
                self.store.add_alias(group(ent.type), normalize(acronym, ent.type), eid, acronym)
            if self.store.add_mention(item_id, eid, ent.role, seen):
                out.mentions += 1
            if ent.type in ENTITY_CATEGORY and ent.category in ENTITY_CATEGORY[ent.type][1]:
                cat_type, table = ENTITY_CATEGORY[ent.type]
                if self.store.add_relation(eid, "in_category", self._category(cat_type, ent.category, table), item_id):
                    out.relations += 1
            for key in {ent.name.strip().lower(), base.lower(), shown.lower(), (acronym or "").lower()} - {""}:
                names.setdefault(key, (eid, ent.type))
        for rel in extraction.relations[:MAX_RELATIONS]:
            source, target = names.get(rel.source.strip().lower()), names.get(rel.target.strip().lower())
            if source is None or target is None or source[0] == target[0] or not allowed(rel.relation, source[1], target[1]):
                out.dropped += 1
                continue
            if self.store.add_relation(source[0], rel.relation, target[0], item_id):
                out.relations += 1
        return out


def make_judge(gateway):
    """Judge for `Resolver`: True only when the `resolve` task says both names are the same entity.
    Any failure answers False, so a name is never merged without a clear yes."""
    system = load_prompt("resolve_v1")

    def judge(type_, name_a, context_a, name_b, context_b) -> bool:
        message = (f"Entity type: {type_}\nA: {name_a}\n   seen in: {context_a or '?'}\n"
                   f"B: {name_b}\n   seen in: {context_b or '?'}")
        try:
            out = gateway.structured("resolve", [{"role": "system", "content": system},
                                                 {"role": "user", "content": message}], SameEntity)
        except (LLMFailure, BudgetExceeded, InsufficientCredits) as exc:
            log.warning("resolve judge: %s", exc)
            return False
        return bool(out.same)

    return judge
