"""Boundary tests for operator-owned Windows shortcut profiles (no real launches)."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "integrations" / "dodaios" / "windows_shortcuts.py"
spec = importlib.util.spec_from_file_location("kiki_test_windows_shortcuts", MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class WindowsShortcuts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.executable = self.root / "sample.exe"
        self.executable.write_text("synthetic executable, never executed", encoding="utf-8")
        self.config = self.root / "shortcuts.json"

    def save(self, profiles):
        self.config.write_text(json.dumps({"profiles": profiles}), encoding="utf-8")
        return str(self.config)

    def test_list_profiles_never_executes(self):
        path = self.save({"start-lecture": [{"kind": "app", "target": "notepad"}]})
        result = m.describe_profiles(path)
        self.assertEqual(result["shortcuts"][0]["id"], "start-lecture")
        self.assertFalse(result["executed"])

    def test_no_operator_config(self):
        with self.assertRaises(ValueError):
            m.describe_profiles(None)

    def test_reject_model_supplied_shell(self):
        path = self.save({"evil": [{"kind": "shell", "target": "whoami"}]})
        with self.assertRaises(ValueError):
            m.profile_store(path)

    def test_reject_url_with_credentials(self):
        path = self.save({"evil": [{"kind": "url", "target": "https://user:secret@example.org"}]})
        with self.assertRaises(ValueError):
            m.profile_store(path)

    def test_reject_non_https_url(self):
        path = self.save({"evil": [{"kind": "url", "target": "file:///C:/Windows/system32/calc.exe"}]})
        with self.assertRaises(ValueError):
            m.profile_store(path)

    def test_reject_relative_executable(self):
        path = self.save({"evil": [{"kind": "exe", "target": "sample.exe"}]})
        with self.assertRaises(ValueError):
            m.profile_store(path)

    def test_reject_batch_or_powershell(self):
        bad = self.root / "dangerous.ps1"
        bad.write_text("exit", encoding="utf-8")
        path = self.save({"evil": [{"kind": "exe", "target": str(bad)}]})
        with self.assertRaises(ValueError):
            m.profile_store(path)

    def test_reject_unapproved_id(self):
        path = self.save({"allowed": [{"kind": "exe", "target": str(self.executable)}]})
        with self.assertRaises(ValueError):
            m.run_profile(path, "not-allowed", launcher=lambda argv: None)

    def test_reject_model_supplied_path_in_id(self):
        path = self.save({"allowed": [{"kind": "exe", "target": str(self.executable)}]})
        with self.assertRaises(ValueError):
            m.run_profile(path, "C:\\Windows\\evil.exe", launcher=lambda argv: None)

    def test_two_step_workflow_with_mocked_launcher(self):
        opened = []
        launched = []
        path = self.save({"prep": [
            {"kind": "exe", "target": str(self.executable)},
            {"kind": "folder", "target": str(self.root)},
        ]})
        class Proc:
            pid = 123
        result = m.run_profile(path, "prep", launcher=lambda argv: (launched.append(argv) or Proc()),
                               opener=lambda target: opened.append(target))
        self.assertEqual(result["status"], "LAUNCH_REQUESTED")
        self.assertEqual(len(result["actions"]), 2)
        self.assertEqual(launched, [[str(self.executable.resolve())]])
        self.assertEqual(opened, [str(self.root.resolve())])
        self.assertFalse(result["externally_verified"])
        self.assertFalse(result["shared_history_written"])

    def test_power_automate_flow_requires_uuid(self):
        path = self.save({"bad-flow": [{"kind": "power_automate", "target": "powershell -exec bypass"}]})
        with self.assertRaises(ValueError):
            m.profile_store(path)

    def test_power_automate_launch_returns_unverified_run_id(self):
        opened = []
        flow = "dfd0c814-2c30-4cd8-849d-a4b2d2f4f33b"
        path = self.save({"graded-flow": [{"kind": "power_automate", "target": flow}]})
        result = m.run_profile(path, "graded-flow", launcher=lambda _: self.fail("No EXE expected"),
                               opener=lambda value: opened.append(value))
        self.assertEqual(result["status"], "LAUNCH_REQUESTED")
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0].startswith("ms-powerautomate:/console/flow/run?workflowId=" + flow))
        self.assertIn("&runId=", opened[0])
        self.assertEqual(result["actions"][0]["evidence"]["flow_id"], flow)
        self.assertFalse(result["actions"][0]["evidence"]["completion_verified"])
        self.assertFalse(result["shared_history_written"])

    def test_stop_on_first_failed_launch(self):
        path = self.save({"prep": [
            {"kind": "exe", "target": str(self.executable)},
            {"kind": "folder", "target": str(self.root)},
        ]})
        def fail(argv):
            raise OSError("synthetic launch failure")
        result = m.run_profile(path, "prep", launcher=fail, opener=lambda _: self.fail("Should not open"))
        self.assertEqual(result["status"], "PARTIAL_OR_FAILED")
        self.assertEqual(len(result["actions"]), 1)
        self.assertEqual(result["actions"][0]["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
