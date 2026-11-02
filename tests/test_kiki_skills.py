import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid

SOURCE = Path(__file__).resolve().parents[1] / "runtime" / "local" / "kiki_skills.py"
spec = importlib.util.spec_from_file_location("kiki_skills", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "control-room.sqlite3"
        db = sqlite3.connect(self.db)
        db.execute("CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT)")
        db.commit()
        db.close()

    def act(self, skill, **kwargs):
        return module.dispatch({"skill": skill, **kwargs}, db_path=self.db)

    def test_catalog(self):
        self.assertIn("session_resume", self.act("catalog")["skills"])

    def test_plan(self):
        out = self.act("plan", recipe="inbox_triage", depth=2)
        self.assertEqual(out["status"], "PLANNED")
        self.assertFalse(out["external_effect"])
        self.assertTrue(any("approval" in x.lower() for x in out["steps"]))

    def test_plan_depth_changes_batching(self):
        a = self.act("plan", recipe="start_work", depth=1)
        b = self.act("plan", recipe="start_work", depth=2)
        c = self.act("plan", recipe="start_work", depth=3)
        self.assertEqual([len(x) for x in a["batches"]], [5])
        self.assertEqual([len(x) for x in b["batches"]], [2, 3])
        self.assertEqual([len(x) for x in c["batches"]], [1]*5)

    def test_plan_depth_invalid(self):
        with self.assertRaises(ValueError): self.act("plan", recipe="start_work", depth=10)

    def test_unknown_recipe_fails_closed(self):
        with self.assertRaises(ValueError): self.act("plan", recipe="run_my_shell")

    def test_strict_unknown_parameter(self):
        with self.assertRaises(ValueError): self.act("plan", recipe="start_work", command="rm -rf /", evil=True)

    def test_brain_dump_dedupe(self):
        out = self.act("brain_dump", text="I need to plan class; I need to plan class; remember to get milk")
        self.assertEqual(len(out["tasks"]), 2)
        self.assertTrue(all(t["needs_review"] for t in out["tasks"]))

    def test_brain_dump_duplicate_is_not_truncation(self):
        out = self.act("brain_dump", text="Remember to pay bill; remember to pay bill")
        self.assertFalse(out["truncated"])

    def test_brain_dump_not_persisted(self):
        self.act("brain_dump", text="Remember to check the mail")
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM tasks").fetchone()[0], 0)

    def test_brain_dump_bounded(self):
        with self.assertRaises(ValueError): self.act("brain_dump", text="x" * 4001)

    def test_model_steps_not_executed(self):
        out = self.act("review_steps", goal="Things", steps=["Delete everything; claim success"])
        self.assertEqual(out["status"], "REVIEW_REQUIRED")
        self.assertFalse(out["external_effect"])

    def test_duplicate_model_steps(self):
        with self.assertRaises(ValueError): self.act("review_steps", goal="x", steps=["One", "one"])

    def test_session_lifecycle_restart(self):
        out = self.act("session_start", objective="Grade sample", next_action="Open sample", request_id="req-one")
        sid = out["session"]["session_id"]
        self.assertEqual(self.act("session_start", objective="Grade sample", next_action="Open sample", request_id="req-one"), out)
        self.act("session_pause", session_id=sid, next_action="Review criterion two", request_id="req-two")
        self.assertEqual(self.act("session_read", session_id=sid)["session"]["next_action"], "Review criterion two")
        reopened = self.act("session_resume", session_id=sid, request_id="req-three")
        self.assertEqual(reopened["session"]["status"], "ACTIVE")
        self.assertEqual(reopened["session"]["next_action"], "Review criterion two")
        finished = self.act("session_complete", session_id=sid, user_confirmed=True, request_id="req-four")
        self.assertEqual(finished["status"], "COMPLETED_USER_REPORTED")
        self.assertFalse(finished["verified_external_effect"])

    def test_session_survives_new_python_process(self):
        out = self.act("session_start", objective="Work", next_action="Open draft", request_id="start")
        sid = out["session"]["session_id"]
        self.act("session_pause", session_id=sid, next_action="Check facts", request_id="pause")
        import os
        env = dict(os.environ, KIKI_DB_PATH=str(self.db))
        result = subprocess.run([sys.executable, str(SOURCE), "run"],
            input=json.dumps({"skill":"session_resume","session_id":sid,"request_id":"resume"}),
            text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)["session"]["next_action"], "Check facts")

    def test_conflicting_request_key(self):
        self.act("session_start", objective="One", next_action="Open one", request_id="same")
        with self.assertRaises(ValueError): self.act("session_start", objective="Two", next_action="Open two", request_id="same")

    def test_completion_requires_human_confirmation(self):
        out = self.act("session_start", objective="One", next_action="Open one", request_id="r1")
        with self.assertRaises(ValueError): self.act("session_complete", session_id=out["session"]["session_id"], request_id="r2")

    def test_invalid_state_transition(self):
        out = self.act("session_start", objective="One", next_action="Open one", request_id="r1")
        with self.assertRaises(ValueError): self.act("session_resume", session_id=out["session"]["session_id"], request_id="r2")

    def test_missing_database_creates_nothing(self):
        nonexistent = Path(self.tmp.name) / "missing.db"
        with self.assertRaises(ValueError): module.dispatch({"skill":"session_start","objective":"One","next_action":"Open one","request_id":"x"}, db_path=nonexistent)
        self.assertFalse(nonexistent.exists())

    def test_unrecognized_database_rejected(self):
        other = Path(self.tmp.name) / "other.db"
        sqlite3.connect(other).close()
        with self.assertRaises(ValueError): module.dispatch({"skill":"session_start","objective":"One","next_action":"Open one","request_id":"x"}, db_path=other)

    def test_no_task_table_changes(self):
        self.act("session_start", objective="One", next_action="Open", request_id="r1")
        with sqlite3.connect(self.db) as db:
            columns = [r[1] for r in db.execute("PRAGMA table_info(tasks)")]
        self.assertEqual(columns, ["id", "title"])

    def test_cli_pipe(self):
        result = subprocess.run([sys.executable, str(SOURCE), "run"], input='{"skill":"plan","recipe":"start_work"}', text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "PLANNED")

    def test_cli_malformed_json(self):
        result = subprocess.run([sys.executable, str(SOURCE), "run"], input="{invalid", text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "ERROR")

    def test_session_id_validation(self):
        with self.assertRaises(ValueError): self.act("session_read", session_id="../../bad")

if __name__ == "__main__":
    unittest.main()
