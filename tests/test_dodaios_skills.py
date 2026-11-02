"""Contract tests for the read-only Dodaios MCP microtools."""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "integrations" / "dodaios" / "kiki_workflows_mcp.py"
spec = importlib.util.spec_from_file_location("kiki_workflows_mcp", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class WorkflowMicrotools(unittest.TestCase):
    def test_recipe_has_exact_first_step(self):
        result = m.get_recipe({"recipe": "start_work"})
        self.assertEqual(result["next_action"], result["steps"][0])
        self.assertFalse(result["performed_external_action"])

    def test_no_unknown_recipe(self):
        with self.assertRaises(ValueError):
            m.get_recipe({"recipe": "unreviewed_script"})

    def test_no_surprise_parameters(self):
        with self.assertRaises(ValueError):
            m.get_recipe({"recipe": "start_work", "shell": "whoami"})

    def test_brain_dump_returns_candidates_not_tasks(self):
        result = m.compile_brain_dump({"text": "I need to grade tests; remember to buy soap"})
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["created_task_count"], 0)

    def test_brain_dump_deduplicates(self):
        result = m.compile_brain_dump({"text": "buy soap; buy soap"})
        self.assertEqual(len(result["candidates"]), 1)

    def test_brain_dump_is_bounded(self):
        with self.assertRaises(ValueError):
            m.compile_brain_dump({"text": "x" * 4001})

    def test_completed_tasks_are_suppressed(self):
        result = m.choose_next_action({"tasks": [
            {"id": "one", "title": "Already done", "status": "VERIFIED", "priority": 10},
            {"id": "two", "title": "New job", "status": "QUEUED", "priority": 1}]})
        self.assertEqual(result["candidate"]["id"], "two")
        self.assertFalse(result["task_state_changed"])

    def test_paused_and_deferred_tasks_are_suppressed(self):
        result = m.choose_next_action({"tasks": [
            {"id": "one", "title": "Deferred", "status": "deferred"},
            {"id": "two", "title": "Paused", "status": "paused"}]})
        self.assertIsNone(result["candidate"])

    def test_priority_is_deterministic(self):
        result = m.choose_next_action({"tasks": [
            {"id": "one", "title": "Low", "status": "open", "priority": 0},
            {"id": "two", "title": "High", "status": "open", "priority": 5}]})
        self.assertEqual(result["candidate"]["id"], "two")

    def test_expired_deadline_before_priority(self):
        result = m.choose_next_action({"tasks": [
            {"id": "one", "title": "Normal", "status": "open", "priority": 5},
            {"id": "two", "title": "Overdue", "status": "open", "priority": 0,
             "deadline": "2001-01-01T00:00:00Z"}]})
        self.assertEqual(result["candidate"]["id"], "two")

    def test_future_snooze_is_respected(self):
        result = m.choose_next_action({"tasks": [
            {"id": "one", "title": "Snoozed", "status": "open",
             "snoozed_until": "2099-01-01T00:00:00Z"}]})
        self.assertIsNone(result["candidate"])

    def test_handoff_never_claims_verified(self):
        result = m.review_handoff({"task_id": "task-one",
                                  "outcome": "external_action_claimed",
                                  "summary": "The worker said it clicked Save"})
        self.assertFalse(result["provider_verified"])
        self.assertTrue(result["requires_authoritative_receipt"])
        self.assertFalse(result["task_state_changed"])

    def test_handoff_does_not_accept_custom_outcome(self):
        with self.assertRaises(ValueError):
            m.review_handoff({"task_id": "task-one", "outcome": "VERIFIED",
                              "summary": "Trust me"})

    def test_initialize_returns_tools(self):
        init = m.reply({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
        ls = m.reply({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(len(ls["result"]["tools"]), 6)

    def test_notification_does_not_reply(self):
        self.assertIsNone(m.reply({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_mcp_call_returns_structured_text(self):
        response = m.reply({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                            "params": {"name": "kiki_get_recipe",
                                       "arguments": {"recipe": "email_triage"}}})
        self.assertFalse(response["result"]["isError"])
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["recipe"], "email_triage")

    def test_mcp_rejects_unknown_tool(self):
        response = m.reply({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                            "params": {"name": "run_shell", "arguments": {"cmd": "whoami"}}})
        self.assertTrue(response["result"]["isError"])

    def test_real_stdio_lifecycle(self):
        input_lines = "\n".join(json.dumps(x) for x in [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "kiki_get_recipe", "arguments": {"recipe": "start_work"}}}
        ]) + "\n"
        proc = subprocess.run([sys.executable, str(PATH)], input=input_lines,
                              capture_output=True, text=True, timeout=8)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        replies = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(replies), 3)
        self.assertEqual(replies[2]["id"], 3)


if __name__ == "__main__":
    unittest.main()
