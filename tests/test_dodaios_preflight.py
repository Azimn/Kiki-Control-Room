"""Model-free, synthetic acceptance checks for the Kiki/DODAIOS integration boundary.

These tests execute the actual Kiki MCP adapter, not Dodaios itself. They do
NOT prove voice, browser, Telegram, Society, or Windows laptop deployment.
No network calls, model inference, real app launches, or university data.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_PATH = ROOT / "integrations" / "dodaios" / "kiki_workflows_mcp.py"
WIN_PATH = ROOT / "integrations" / "dodaios" / "windows_shortcuts.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mcp = load("preflight_mcp", MCP_PATH)
shortcuts = load("preflight_shortcuts", WIN_PATH)


class SyntheticKikiSessionContracts(unittest.TestCase):
    def call(self, tool, args):
        response = mcp.reply({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        })
        self.assertIsNotNone(response)
        return response["result"]

    def test_text_and_voice_simulation_identify_the_same_single_action(self):
        # Two inputs are modeled as two turns; this is NOT a voice engine test.
        snapshot = [
            {"id": "old", "title": "Completed report", "status": "completed",
             "priority": 10},
            {"id": "paused", "title": "Deferred work", "status": "paused",
             "priority": 9},
            {"id": "now", "title": "Open approved test document",
             "next_action": "Open the synthetic document", "status": "open",
             "priority": 2},
        ]
        before = json.dumps(snapshot, sort_keys=True)
        first = self.call("kiki_choose_next_action", {"tasks": snapshot})
        second = self.call("kiki_choose_next_action", {"tasks": snapshot})
        for result in (first, second):
            self.assertFalse(result["isError"])
            outcome = json.loads(result["content"][0]["text"])
            self.assertEqual(outcome["candidate"]["id"], "now")
            self.assertFalse(outcome["task_state_changed"])
        self.assertEqual(first, second)
        self.assertEqual(json.dumps(snapshot, sort_keys=True), before)

    def test_user_confirmed_completion_is_suppressed_even_if_high_priority(self):
        tasks = [
            {"id": "report", "title": "Previously sent report",
             "status": "done", "priority": 10},
            {"id": "followup", "title": "Synthetic follow-up",
             "status": "queued", "priority": 1},
        ]
        answer = mcp.choose_next_action({"tasks": tasks})
        self.assertEqual(answer["candidate"]["id"], "followup")

    def test_no_eligible_work_creates_no_task_and_no_invented_action(self):
        result = mcp.choose_next_action({"tasks": [
            {"id": "one", "title": "Declined", "status": "declined"},
            {"id": "two", "title": "Blocked", "status": "blocked"},
        ]})
        self.assertIsNone(result["candidate"])
        self.assertEqual(result["eligible_count"], 0)
        self.assertFalse(result["task_state_changed"])

    def test_dictated_brain_dump_is_only_a_proposal_even_when_repeated(self):
        msg = {"text": "I need to review a test; remember to open a demo"}
        first = mcp.compile_brain_dump(msg)
        second = mcp.compile_brain_dump(msg)
        self.assertEqual(first, second)
        self.assertEqual(first["created_task_count"], 0)
        self.assertTrue(all(item["needs_review"] for item in first["candidates"]))

    def test_false_specialist_pass_never_counts_as_external_verification(self):
        result = mcp.review_handoff({
            "task_id": "synthetic-step",
            "outcome": "external_action_claimed",
            "summary": "Specialist said PASS but supplied no file receipt",
        })
        self.assertFalse(result["provider_verified"])
        self.assertTrue(result["requires_authoritative_receipt"])
        self.assertFalse(result["task_state_changed"])

    def test_user_reported_completion_keeps_distinct_provenance(self):
        result = mcp.review_handoff({
            "task_id": "synthetic-step", "outcome": "user_reported_complete",
            "summary": "User says this step is finished",
        })
        self.assertEqual(result["outcome"], "user_reported_complete")
        self.assertFalse(result["provider_verified"])
        self.assertFalse(result["task_state_changed"])

    def test_model_cannot_call_unlisted_shell_tool(self):
        result = self.call("execute_shell", {"command": "echo should-not-run"})
        self.assertTrue(result["isError"])

    def test_model_cannot_make_recipe_perform_unreviewed_action(self):
        result = self.call("kiki_get_recipe", {
            "recipe": "start_work", "send_telegram": True,
        })
        self.assertTrue(result["isError"])


class SyntheticWindowsShortcutContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "shortcuts.json"

    def write(self, profiles):
        self.config.write_text(json.dumps({"profiles": profiles}), encoding="utf-8")
        return str(self.config)

    def test_operator_approved_folder_action_stays_unverified(self):
        path = self.write({"open-synthetic-folder": [
            {"kind": "folder", "target": str(self.root)}
        ]})
        seen = []
        result = shortcuts.run_profile(
            path, "open-synthetic-folder",
            launcher=lambda _: self.fail("No executable should launch"),
            opener=lambda target: seen.append(target),
        )
        self.assertEqual(seen, [str(self.root.resolve())])
        self.assertEqual(result["status"], "LAUNCH_REQUESTED")
        self.assertFalse(result["externally_verified"])
        self.assertFalse(result["shared_history_written"])

    def test_unapproved_profile_cannot_execute(self):
        path = self.write({"allowed": [
            {"kind": "folder", "target": str(self.root)}
        ]})
        with self.assertRaises(ValueError):
            shortcuts.run_profile(
                path, "unapproved", launcher=lambda _: self.fail("Launched"),
                opener=lambda _: self.fail("Opened"),
            )

    def test_local_or_credential_url_is_rejected_before_launch(self):
        for target in ("http://127.0.0.1:1234", "https://u:p@example.com/",
                       "file:///tmp/evil"):
            with self.subTest(target=target):
                path = self.write({"bad": [{"kind": "url", "target": target}]})
                with self.assertRaises(ValueError):
                    shortcuts.profile_store(path)


if __name__ == "__main__":
    unittest.main()
