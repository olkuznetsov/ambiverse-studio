"""The job engine: queue → run → settle, env whitelisting, and cancellation that
reaches grandchildren (the reason jobs get their own process group)."""
import os
import time
from pathlib import Path

from conftest import TERMINAL, wait_for, wait_for_log


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = Path(f"/proc/{pid}/stat")  # Linux: a killed-but-unreaped process lingers as a zombie
    return not (stat.exists() and stat.read_text().rsplit(")", 1)[-1].split()[0] == "Z")


def test_job_runs_to_done_with_its_log(client):
    job = client.post("/api/jobs", json={"type": "dummy_sleep", "params": {"seconds": 1}}).json()
    done = wait_for(client, job["id"], TERMINAL)
    assert done["status"] == "done"
    assert done["exit_code"] == 0
    assert "dummy job finished" in Path(done["log_path"]).read_text()


def test_cancel_kills_the_whole_process_group(client):
    job = client.post("/api/jobs", json={"type": "dummy_sleep", "params": {"seconds": 60}}).json()
    child_pid = int(wait_for_log(client, job["id"], r"child sleep pid=(\d+)").group(1))

    client.post(f"/api/jobs/{job['id']}/cancel")
    assert wait_for(client, job["id"], TERMINAL)["status"] == "cancelled"

    # the `sleep 600` grandchild dies with the group instead of being orphaned
    deadline = time.time() + 15
    while time.time() < deadline:
        if not _alive(child_pid):
            return
        time.sleep(0.2)
    raise AssertionError(f"grandchild {child_pid} survived the cancel")


def test_cancelling_a_queued_job_never_starts_it(client):
    blocker = client.post("/api/jobs", json={"type": "dummy_sleep", "params": {"seconds": 30}}).json()
    queued = client.post("/api/jobs", json={"type": "dummy_sleep", "params": {"seconds": 1}}).json()
    assert client.post(f"/api/jobs/{queued['id']}/cancel").json()["status"] == "cancelled"
    client.post(f"/api/jobs/{blocker['id']}/cancel")
    wait_for(client, blocker["id"], TERMINAL)
    assert client.get(f"/api/jobs/{queued['id']}").json()["started_at"] is None


def test_only_whitelisted_env_knobs_reach_the_job(client):
    job = client.post("/api/jobs", json={
        "type": "generate_prompts",
        "env": {"MUSIC_SIM_THRESHOLD": "0.5", "PATH": "/tmp/evil", "LD_PRELOAD": "x.so"},
    }).json()
    assert job["env"] == {"MUSIC_SIM_THRESHOLD": "0.5"}
    assert wait_for(client, job["id"], TERMINAL)["status"] == "done"


def test_unknown_job_type_is_rejected(client):
    assert client.post("/api/jobs", json={"type": "rm_rf"}).status_code == 400
