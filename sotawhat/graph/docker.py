# sotawhat/graph/docker.py
"""`sotawhat graph up` (SDD §6.12): opens Docker Desktop when it is closed, starts the Neo4j service of
compose.yaml and waits until Bolt answers. Compose gets NEO4J_* through the process environment and an
empty --env-file, so it never parses the project `.env` (which holds unrelated secrets)."""
import os
import subprocess
import time
from pathlib import Path

DOCKER_DESKTOP = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe"


def docker_ready(run=subprocess.run) -> bool:
    try:
        return run(["docker", "info"], capture_output=True, text=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _bolt_ok(settings) -> bool:
    from sotawhat.graph.neo4j_sync import Neo4jMirror

    mirror = Neo4jMirror.from_settings(settings)
    if mirror is None:
        return False
    try:
        return mirror.ping()
    finally:
        mirror.close()


def graph_up(settings, repo_dir, run=subprocess.run, popen=subprocess.Popen, sleep=time.sleep, connect=None,
             wait_docker=120, wait_neo4j=180, step=5) -> tuple:
    """-> (ok, message)."""
    if not settings.neo4j_password:
        return False, ("defina NEO4J_PASSWORD no .env (uma senha longa qualquer; ela só vale para o Neo4j local "
                       "em 127.0.0.1)")
    if not docker_ready(run):
        if not DOCKER_DESKTOP.exists():
            return False, f"Docker Desktop não encontrado em {DOCKER_DESKTOP}"
        popen([str(DOCKER_DESKTOP)])
        waited = 0
        while not docker_ready(run):
            if waited >= wait_docker:
                return False, f"o Docker Desktop não respondeu em {wait_docker} s"
            sleep(step)
            waited += step
    empty = Path(settings.sotawhat_data_dir) / "compose.env"
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_text("", encoding="utf-8")
    env = {**os.environ, "NEO4J_PASSWORD": settings.neo4j_password, "NEO4J_HEAP_MAX": settings.neo4j_heap_max,
           "NEO4J_PAGECACHE": settings.neo4j_pagecache}
    try:
        up = run(["docker", "compose", "--env-file", str(empty), "up", "-d", "neo4j"], cwd=repo_dir, env=env,
                 capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"docker compose falhou: {exc}"
    if up.returncode != 0:
        return False, f"docker compose falhou: {(up.stderr or up.stdout or '').strip()[-400:]}"
    connect = connect or (lambda: _bolt_ok(settings))
    waited = 0
    while not connect():
        if waited >= wait_neo4j:
            return False, f"o Neo4j não respondeu em {wait_neo4j} s (veja `docker compose logs neo4j`)"
        sleep(step)
        waited += step
    return True, f"Neo4j no ar em {settings.neo4j_uri}; Neo4j Browser em http://127.0.0.1:7474 (usuário neo4j)"
