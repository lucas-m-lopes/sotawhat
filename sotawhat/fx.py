# sotawhat/fx.py
"""US$ → R$ at the official rate: the PTAX of the Banco Central do Brasil (selling rate of the closing bulletin),
read from its open-data API (Olinda, `CotacaoDolarPeriodo`). The latest business day wins: before about 13h the
day's closing is not out yet and the previous one is the official rate.

The rate is kept in the store's meta table and asked again after `MAX_AGE`, so a lesson or a report costs at most
one request; with no network the last rate seen is used, and with none at all the caller shows only US$."""
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

OLINDA = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
META_KEY = "fx_ptax_usd"
MAX_AGE = timedelta(hours=6)
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Rate:
    brl: float            # reais per dollar (PTAX, venda)
    day: str              # date of the bulletin, ISO
    source: str = "PTAX/BCB"

    def convert(self, usd) -> float:
        return round(usd * self.brl, 2)


def parse_period(payload) -> Rate | None:
    """Olinda JSON -> the closing rate of the latest day in it."""
    rows = [r for r in (payload or {}).get("value") or [] if r.get("cotacaoVenda") and r.get("dataHoraCotacao")]
    if not rows:
        return None
    last = max(rows, key=lambda r: r["dataHoraCotacao"])
    return Rate(float(last["cotacaoVenda"]), last["dataHoraCotacao"][:10])


def fetch_ptax(client, today) -> Rate | None:
    start = today - timedelta(days=10)          # covers long weekends and holidays
    res = client.get(OLINDA + "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)",
                     params={"@dataInicial": f"'{start:%m-%d-%Y}'", "@dataFinalCotacao": f"'{today:%m-%d-%Y}'",
                             "$select": "cotacaoVenda,dataHoraCotacao", "$top": "100", "$format": "json"})
    res.raise_for_status()
    return parse_period(res.json())


def usd_brl(store=None, client=None, today=None, now=None) -> Rate | None:
    """The PTAX to use now (cached in `store`), or None when it was never read."""
    now = now or datetime.now(timezone.utc)
    today = today or date.today()
    cached = None
    if store is not None:
        try:
            cached = json.loads(store.meta_get(META_KEY) or "null")
        except ValueError:
            cached = None
    if cached and now - datetime.fromisoformat(cached["checked_at"]) < MAX_AGE:
        return Rate(cached["brl"], cached["day"])
    rate = None
    try:
        own = client is None
        client = client or httpx.Client(timeout=20, headers={"User-Agent": "sotawhat"})
        try:
            rate = fetch_ptax(client, today)
        finally:
            if own:
                client.close()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("PTAX do BCB indisponível: %s", exc)
    if rate is not None:
        if store is not None:
            store.meta_set(META_KEY, json.dumps({"brl": rate.brl, "day": rate.day,
                                                 "checked_at": now.isoformat(timespec="seconds")}))
        return rate
    return Rate(cached["brl"], cached["day"]) if cached else None


def brl_text(value) -> str:
    """2.7338 -> "R$ 2,73"."""
    whole, cents = f"{value:,.2f}".split(".")
    return f"R$ {whole.replace(',', '.')},{cents}"
