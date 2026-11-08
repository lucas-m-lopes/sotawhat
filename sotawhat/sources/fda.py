# sotawhat/sources/fda.py
"""FDA list of AI-enabled medical devices (SDD §5.3, Tier 1 #9), a CSV that the FDA updates every few
months with decisions that are often months old. So the first run only records every submission number
as a baseline (`data/state/`), and later runs emit the numbers that were not there, whatever their date.
The state is written only after a successful download and parse."""
import csv
import io
import json
from datetime import datetime
from pathlib import Path

import httpx

from sotawhat.models import Result
from sotawhat.sources.base import Source

CSV_URL = "https://www.fda.gov/media/178541/download?attachment"
LIST_PAGE = ("https://www.fda.gov/medical-devices/software-medical-device-samd/"
             "artificial-intelligence-enabled-medical-devices")


class FDAAIDevicesSource(Source):
    keywordless = True
    ai_specific = True

    def __init__(self, state_path, name="fda-ai-devices", max_items=30, client=None, url=CSV_URL):
        self.name, self.max_items, self.url = name, max_items, url
        self.state_path = Path(state_path)
        self._client = client

    @staticmethod
    def _url(number) -> str:
        if number.startswith("K"):
            return f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={number}"
        if number.startswith("DEN"):
            return f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/denovo.cfm?ID={number}"
        if number.startswith("P"):
            return f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?id={number}"
        return LIST_PAGE

    def fetch(self, limit):
        client = self._client or httpx.Client(timeout=60, follow_redirects=True)
        try:
            r = client.get(self.url, headers={"User-Agent": "Mozilla/5.0 (sotawhat/3.0)"})
            r.raise_for_status()
        finally:
            if self._client is None:
                client.close()
        rows = [row for row in csv.DictReader(io.StringIO(r.text.lstrip("﻿"))) if row.get("Submission Number")]
        numbers = [row["Submission Number"].strip() for row in rows]
        known = set(json.loads(self.state_path.read_text(encoding="utf-8"))["known"]) if self.state_path.exists() else None
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({"known": sorted(set(numbers) | (known or set()))}), encoding="utf-8")
        if known is None:
            return []                                  # baseline: the list as it is today is not news
        fresh = [row for row in rows if row["Submission Number"].strip() not in known]
        fresh.sort(key=lambda row: self._date(row), reverse=True)
        return [self._result(row) for row in fresh[:limit]]

    @staticmethod
    def _date(row) -> str:
        try:
            return datetime.strptime(row["Date of Final Decision"].strip(), "%m/%d/%Y").date().isoformat()
        except ValueError:
            return ""

    def _result(self, row) -> Result:
        number, device = row["Submission Number"].strip(), " ".join(row["Device"].split())
        company, panel = " ".join(row["Company"].split()), (row.get("Panel (Lead)") or "?").strip()
        decided = self._date(row)
        text = (f"AI-enabled medical device authorized by the FDA on {decided} · submission {number} · panel {panel} · "
                f"product code {(row.get('Primary Product Code') or '?').strip()}\nDevice: {device}. Company: {company}.")
        return Result(id=self._url(number), title=f"FDA autoriza dispositivo com IA: {device} ({company})",
                      authors=[company], date=decided, url=self._url(number), abstract=text, source="fda",
                      extra={"kind": "regulation", "submission": number})
