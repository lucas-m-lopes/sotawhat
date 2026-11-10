"""US$ → R$ by the PTAX of the Banco Central (Olinda API): the latest closing wins, the rate is cached in the store's
meta table, and with no network the last rate seen is used."""
from datetime import date, datetime, timedelta, timezone

import httpx

from sotawhat import fx
from sotawhat.store.db import Store

# what Olinda answered on 2026-11-10 (CotacaoDolarPeriodo, $select=cotacaoVenda,dataHoraCotacao)
PAYLOAD = {"@odata.context": "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata$metadata#_CotacaoDolarPeriodo",
           "value": [{"cotacaoVenda": 5.5013, "dataHoraCotacao": "2026-11-06 13:06:13.966"},
                     {"cotacaoVenda": 5.584, "dataHoraCotacao": "2026-11-10 13:06:01.353"},
                     {"cotacaoVenda": 5.5146, "dataHoraCotacao": "2026-11-09 13:11:19.041"}]}


def client_answering(payload, status=200, seen=None):
    def handler(request):
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, json=payload)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_the_latest_closing_of_the_period_is_the_rate():
    rate = fx.parse_period(PAYLOAD)
    assert (rate.brl, rate.day) == (5.584, "2026-11-10")
    assert fx.parse_period({"value": []}) is None
    assert rate.convert(0.4897) == 2.73 and fx.brl_text(2.7338) == "R$ 2,73" and fx.brl_text(1234.5) == "R$ 1.234,50"


def test_the_request_asks_the_official_period_query():
    seen = []
    fx.fetch_ptax(client_answering(PAYLOAD, seen=seen), date(2026, 11, 10))
    url = str(seen[0].url)
    assert url.startswith(fx.OLINDA + "CotacaoDolarPeriodo") and "11-10-2026" in url and "10-31-2026" in url


def test_the_rate_is_cached_and_survives_an_outage(tmp_path):
    now = datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc)
    with Store(tmp_path / "insight.db") as st:
        assert fx.usd_brl(st, client_answering(PAYLOAD), date(2026, 11, 10), now).brl == 5.584
        # within MAX_AGE the cache answers (a failing client is never called)
        assert fx.usd_brl(st, client_answering({}, status=500), date(2026, 11, 10), now + timedelta(hours=1)).brl == 5.584
        # later the BCB is asked again; when it fails, the last rate seen is used
        late = now + fx.MAX_AGE + timedelta(minutes=1)
        assert fx.usd_brl(st, client_answering({}, status=503), date(2026, 11, 10), late).day == "2026-11-10"
    with Store(tmp_path / "empty.db") as st:
        assert fx.usd_brl(st, client_answering({}, status=503), date(2026, 11, 10), now) is None
