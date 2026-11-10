# sotawhat/notify/brand.py
"""How the digests sign themselves: the name in e-mail subjects and Telegram titles, the date as people read it, and
one emoji per section. The emoji of a section is the same in Telegram, in the e-mail and in the files."""
NAME = "SOTA What"

DAILY = "🗞️"          # the daily digest
RUN = "🛰️"            # the console summary of a daily run (no LLM triage)
WEEKLY = "🧭"         # the Sunday report: where things are heading
ON_DEMAND = "🎯"      # ideation on a theme you asked for
STATS = "📊"
HEALTH = "🩺"         # IA ∩ Saúde
FRONTIER = "🔭"       # Fronteira de IA
RADAR = "📡"
EXTRA = "➕"
FAILING = "⚠️"
QUIET = "😴"
NEW = "🆕"
IDEAS = "💡"
TRENDS = "📈"
MAP = "🗺️"
GAPS = "🧩"           # the missing piece
RULES = "📜"
DISCARDED = "🗑️"
TOOLS = "🧰"
FRONTS = {"skills_mcp": "🔌", "agents_evals": "🤖", "tokens_context": "🪙", "lessons_media": "🎬"}   # the tools radar


def br_date(day, year=True) -> str:
    """'2026-11-10' -> '10/11/2026', or '10/11' without the year."""
    y, m, d = str(day)[:10].split("-")
    return f"{d}/{m}/{y}" if year else f"{d}/{m}"


def front(key) -> str:
    """The emoji of a front of the tools radar (🛠️ for a front added later)."""
    return FRONTS.get(key, "🛠️")
