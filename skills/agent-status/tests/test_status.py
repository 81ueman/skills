"""Tests for the agent-status dashboard (Python stdlib unittest).

Run: python3 -m unittest discover -s skills/agent-status/tests
  or: python3 skills/agent-status/tests/test_status.py
"""
import importlib.machinery
import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "status"
_loader = importlib.machinery.SourceFileLoader("agent_status", str(_SCRIPT))
_spec = importlib.util.spec_from_loader("agent_status", _loader)
status = importlib.util.module_from_spec(_spec)
_loader.exec_module(status)


SCHEMA = """
CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, state TEXT, priority INTEGER,
  role TEXT, assignee TEXT, parent_task_id TEXT, updated_at INTEGER, plan_id TEXT);
CREATE TABLE workers (id TEXT PRIMARY KEY, role TEXT, state TEXT, current_task_id TEXT,
  generation INTEGER, last_progress_at INTEGER, quiet_until INTEGER, quiet_reason TEXT, retired_at INTEGER);
CREATE TABLE worker_runtimes (id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id TEXT, generation INTEGER,
  state TEXT, relay_owned INTEGER, workspace_id TEXT, tab_id TEXT, pane_id TEXT,
  runtime_id TEXT, session_id TEXT, created_at INTEGER);
CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT, state TEXT);
CREATE TABLE task_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, worker_id TEXT,
  kind TEXT, body TEXT, created_at INTEGER);
"""


def _cfg(overrides=None):
    return status.deep_merge(status.DEFAULT_CONFIG, overrides or {})


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="agent-status-test-"))
        (self.dir / ".relay").mkdir(parents=True, exist_ok=True)
        self.db = self.dir / ".relay" / "state.db"
        con = sqlite3.connect(self.db)
        con.executescript(SCHEMA)
        con.commit()
        con.close()
        self._old_env = os.environ.pop("HERDR_ENV", None)
        self._old_herdr = status.herdr_json
        self._panes = []

    def tearDown(self):
        status.herdr_json = self._old_herdr
        if self._old_env is not None:
            os.environ["HERDR_ENV"] = self._old_env
        else:
            os.environ.pop("HERDR_ENV", None)

    # ---- fixtures ----------------------------------------------------------
    def sql(self, q, rows=()):
        con = sqlite3.connect(self.db)
        for r in rows:
            con.execute(q, r)
        con.commit()
        con.close()

    def add_task(self, tid, title=None, state="queued", parent=None, role=None, assignee=None, priority=0):
        self.sql("INSERT INTO tasks (id,title,state,priority,role,assignee,parent_task_id,updated_at) "
                 "VALUES (?,?,?,?,?,?,?,?)",
                 [(tid, title or tid, state, priority, role, assignee, parent, 0)])

    def add_worker(self, wid, state="idle", task=None, generation=1, quiet_until=None, quiet_reason=None,
                   retired=None, progress_ms_ago=1000):
        import time
        self.sql("INSERT INTO workers (id,role,state,current_task_id,generation,last_progress_at,"
                 "quiet_until,quiet_reason,retired_at) VALUES (?,?,?,?,?,?,?,?,?)",
                 [(wid, wid, state, task, generation, int(time.time() * 1000) - progress_ms_ago,
                   quiet_until, quiet_reason, retired)])

    def add_runtime(self, wid, generation=1, pane=None, state="active", workspace="w1"):
        self.sql("INSERT INTO worker_runtimes (worker_id,generation,state,relay_owned,workspace_id,"
                 "tab_id,pane_id,runtime_id,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                 [(wid, generation, state, 0, workspace, "t1", pane, pane, 0)])

    def put_herdr_env(self):
        os.environ["HERDR_ENV"] = "1"
        status.herdr_json = lambda args: (
            {"result": {"panes": self._panes}} if args[:2] == ["pane", "list"] else None)

    def render(self, width=120, links=False, cfg=None):
        data = status.collect(str(self.dir), cfg or _cfg(), [])
        return status.render_text(data, False, links, width), data


class RelayRequired(Base):
    def test_1_missing_relay_is_an_error_not_a_fallback(self):
        self.db.unlink()
        err = None
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = status.cmd_render(type("A", (), {"json": False, "workspaces": []})(), str(self.dir), _cfg())
        err = buf.getvalue()
        self.assertEqual(rc, 2)
        self.assertIn("Relay control plane not found", err)
        self.assertIn("relay init", err)
        with self.assertRaises(status.RelayNotFound):
            status.collect(str(self.dir), _cfg(), [])


class TaskTree(Base):
    def test_2_parent_task_id_renders_a_tree(self):
        self.add_task("T1", "parent", state="running")
        self.add_task("T2", "child", state="running", parent="T1")
        out, _ = self.render()
        lines = out.splitlines()
        t1 = next(i for i, l in enumerate(lines) if "T1" in l)
        t2 = next(i for i, l in enumerate(lines) if "T2" in l)
        self.assertLess(t1, t2)
        self.assertIn("─", lines[t2], "child carries a tree glyph")
        # id/state columns are aligned across depths (fixed left columns).
        self.assertTrue(lines[t2].startswith("T2"))

    def test_3_done_child_stays_in_the_tree(self):
        self.add_task("T1", "parent", state="running")
        self.add_task("T2", "child", state="done", parent="T1")
        out, _ = self.render()
        self.assertIn("T2", out)
        t2 = next(l for l in out.splitlines() if "T2" in l)
        self.assertIn("─", t2)

    def test_4_fully_done_subtree_collapses(self):
        self.add_task("T1", "root", state="done")
        self.add_task("T2", "a", state="done", parent="T1")
        self.add_task("T3", "b", state="done", parent="T1")
        out, _ = self.render()
        self.assertIn("T1", out)
        self.assertIn("✓", out)
        self.assertIn("(3/3 done)", out)
        self.assertNotIn("T3", out)  # children folded away


class WorkersOverlay(Base):
    def test_5_worker_rows_are_primary(self):
        self.add_worker("dp-1", state="working", task="T1")
        self.add_runtime("dp-1", pane="w1:p1")
        self.add_task("T1", "work", state="running", assignee="dp-1")
        self.put_herdr_env()
        self._panes = [{"pane_id": "w1:p1", "agent": "opencode", "agent_status": "working",
                        "cwd": str(self.dir), "workspace_id": "w1", "tab_id": "t1"}]
        out, data = self.render()
        self.assertIn("WORKERS", out)
        self.assertIn("dp-1", out)
        self.assertEqual(data["workers"][0]["exec"], "busy")

    def test_6_working_plus_herdr_busy(self):
        self.add_worker("w", state="working", task="T1")
        self.add_runtime("w", pane="w1:p1")
        self.put_herdr_env()
        self._panes = [{"pane_id": "w1:p1", "agent": "opencode", "agent_status": "working",
                        "cwd": str(self.dir), "workspace_id": "w1"}]
        _, data = self.render()
        self.assertEqual(data["workers"][0]["exec"], "busy")

    def test_7_working_idle_with_quiet(self):
        import time
        self.add_worker("w", state="working", task="T1",
                        quiet_until=int(time.time() * 1000) + 60000, quiet_reason="benchmark running")
        self.add_runtime("w", pane="w1:p1")
        self.put_herdr_env()
        self._panes = [{"pane_id": "w1:p1", "agent": "opencode", "agent_status": "idle",
                        "cwd": str(self.dir), "workspace_id": "w1"}]
        _, data = self.render()
        self.assertTrue(data["workers"][0]["exec"].startswith("quiet"))

    def test_8_working_idle_without_quiet_is_attention(self):
        self.add_worker("w", state="working", task="T1")
        self.add_runtime("w", pane="w1:p1")
        self.put_herdr_env()
        self._panes = [{"pane_id": "w1:p1", "agent": "opencode", "agent_status": "idle",
                        "cwd": str(self.dir), "workspace_id": "w1"}]
        out, data = self.render()
        self.assertEqual(data["workers"][0]["exec"], "!idle")
        self.assertTrue(any("runtime idle" in a["text"] for a in data["attention"]))
        self.assertIn("ATTENTION", out)

    def test_9_relay_idle_plus_herdr_idle_is_normal(self):
        self.add_worker("w", state="idle")
        self.add_runtime("w", pane="w1:p1")
        self.put_herdr_env()
        self._panes = [{"pane_id": "w1:p1", "agent": "opencode", "agent_status": "idle",
                        "cwd": str(self.dir), "workspace_id": "w1"}]
        _, data = self.render()
        self.assertEqual(data["workers"][0]["exec"], "idle")
        self.assertEqual(data["attention"], [])


class Attention(Base):
    def test_10_dead_and_stalled_workers(self):
        import time
        self.add_worker("dead-w", state="dead", generation=4)
        self.add_worker("stalled-w", state="stalled")
        _, data = self.render()
        texts = " ".join(a["text"] for a in data["attention"])
        self.assertIn("dead generation=4", texts)
        self.assertIn("stalled", texts)

    def test_11_blocked_and_failed_tasks(self):
        self.add_task("T1", "blocked", state="blocked_human")
        self.sql("INSERT INTO task_notes (task_id,worker_id,kind,body,created_at) VALUES (?,?,?,?,?)",
                 [("T1", "w", "blocked_human", "need API semantics", 0)])
        self.add_task("T2", "failed", state="failed")
        _, data = self.render()
        texts = " ".join(a["text"] for a in data["attention"])
        self.assertIn("blocked_human: need API semantics", texts)
        self.assertIn("failed", texts)

    def test_12_unread_message_count(self):
        self.add_worker("w")
        self.sql("INSERT INTO messages (recipient,state) VALUES (?,?)", [("w", "queued"), ("w", "queued")])
        _, data = self.render()
        self.assertTrue(any("unread messages=2" in a["text"] for a in data["attention"]))

    def test_14_unplaced_worker_is_visible(self):
        self.add_worker("lonely", state="working", task="T1")
        self.add_task("T1", "x", state="running", assignee="lonely")
        self.put_herdr_env()
        out, data = self.render(width=120)
        self.assertIn("no-pane", out)
        self.assertTrue(any("no visible runtime pane" in a["text"] for a in data["attention"]))


class Visibility(Base):
    def test_13_retired_workers_hidden(self):
        self.add_worker("live")
        self.add_worker("gone", retired=123456)
        out, _ = self.render()
        self.assertIn("live", out)
        self.assertNotIn("gone", out)

    def test_15_unmanaged_panes_hidden_by_default(self):
        self.add_worker("w")
        self.put_herdr_env()
        self._panes = [{"pane_id": "w9:pX", "agent": "opencode", "agent_status": "idle",
                        "cwd": str(self.dir), "workspace_id": "w9"}]
        out, _ = self.render()
        self.assertNotIn("w9:pX", out)
        out2, _ = self.render(cfg=_cfg({"herdr": {"show_unmanaged": True}}))
        self.assertIn("w9:pX", out2)

    def test_16_pane_osc8_link(self):
        self.add_worker("w")
        self.add_runtime("w", pane="w1:p1")
        self.put_herdr_env()
        self._panes = [{"pane_id": "w1:p1", "agent": "opencode", "agent_status": "idle",
                        "cwd": str(self.dir), "workspace_id": "w1"}]
        out, _ = self.render(links=True)
        self.assertIn("\033]8;;https://agent-status.local/pane/w1:p1", out)

    def test_17_narrow_width_degrades(self):
        self.add_task("T1", "a very long title " * 5, state="running")
        self.add_task("T2", "child " * 10, state="running", parent="T1")
        self.add_worker("w", state="working", task="T1")
        self.add_runtime("w", pane="w1:p1")
        self.put_herdr_env()
        self._panes = [{"pane_id": "w1:p1", "agent": "opencode", "agent_status": "working",
                        "cwd": str(self.dir), "workspace_id": "w1"}]
        for width in (36, 44, 60, 80, 120):
            out, _ = self.render(width=width)
            for line in out.splitlines():
                self.assertLessEqual(status._dwidth(line), width, f"width={width}: {line!r}")


class JsonModel(Base):
    def test_18_json_has_no_plan_fields(self):
        self.add_task("T1", "x", state="running")
        data = status.collect(str(self.dir), _cfg(), [])
        payload = json.loads(status.render_json(data))
        for k in ("summary", "tasks", "task_tree", "workers", "attention", "runtimes", "git"):
            self.assertIn(k, payload)
        flat = json.dumps(payload)
        for banned in ("plan_id", "intent", "drift", "plan"):
            self.assertNotIn(banned, flat)


if __name__ == "__main__":
    unittest.main(verbosity=2)
