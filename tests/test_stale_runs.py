"""Runs a dead process left open (2026-11-21: the Task Scheduler killed the daily at its 1 h limit; 2026-11-08: the
first weekly died with its console window) close as failed when the next daily starts, so the Hoje tab no longer
shows them "rodando" forever."""
from datetime import datetime, time, timedelta, timezone

from sotawhat.pipeline.daily import daily_due
from sotawhat.store.db import Store

NOW = datetime(2026, 11, 22, 10, 0, tzinfo=timezone.utc)
BRT = timezone(timedelta(hours=-3))


def _run(st, kind, started, finished=None, ok=None):
    cur = st.conn.execute("INSERT INTO runs(kind, started_at, finished_at, ok) VALUES(?, ?, ?, ?)",
                          (kind, started, finished, ok))
    st.conn.commit()
    return cur.lastrowid


def _call(st, run_id, at, cost):
    st.conn.execute("INSERT INTO llm_calls(run_id, task, requested_model, status, cost_usd, created_at)"
                    " VALUES(?, 'triage', 'm', 'ok', ?, ?)", (run_id, cost, at))
    st.conn.commit()


def _row(st, run_id):
    return st.conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()


def test_old_open_runs_close_as_failed_at_their_last_sign_of_life(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        weekly = _run(st, "weekly", "2026-11-08T23:00:04+00:00")
        _call(st, weekly, "2026-11-08T23:12:00+00:00", 0.02)
        _call(st, weekly, "2026-11-08T23:20:00+00:00", 0.03)
        killed = _run(st, "daily", "2026-11-21T10:36:28+00:00")          # killed before its first LLM call
        done = _run(st, "daily", "2026-11-20T12:50:16+00:00", "2026-11-20T13:01:08+00:00", 1)
        alive = _run(st, "graph", "2026-11-22T09:00:00+00:00")            # an hour old: maybe still running

        assert st.close_stale_runs(now=NOW) == [weekly, killed]

        row = _row(st, weekly)
        assert (row["finished_at"], row["ok"], round(row["cost_usd"], 4)) == ("2026-11-08T23:20:00+00:00", 0, 0.05)
        assert row["error"].startswith("interrompido") and "2026-11-22" in row["error"]
        row = _row(st, killed)
        assert (row["finished_at"], row["ok"], row["cost_usd"]) == ("2026-11-21T10:36:28+00:00", 0, 0)
        assert tuple(_row(st, done))[3:5] == ("2026-11-20T13:01:08+00:00", 1)
        assert _row(st, alive)["finished_at"] is None
        assert st.close_stale_runs(now=NOW) == []                           # once
        assert st.close_stale_runs(older_than_h=0.5, now=NOW) == [alive]


def test_a_closed_run_still_counts_as_a_daily_that_did_not_finish_ok(tmp_path):
    with Store(tmp_path / "insight.db") as st:
        _run(st, "daily", "2026-11-21T10:36:28+00:00")                    # 07:36 in Brasília, then killed
        st.close_stale_runs(now=datetime(2026, 11, 21, 17, 0, tzinfo=timezone.utc))
        due, _ = daily_due(st, time(7, 0), now=datetime(2026, 11, 21, 14, 0, tzinfo=BRT))   # the 14:00 retry
    assert due
