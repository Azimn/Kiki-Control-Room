"""Contract tests for the read-only, dependency-free complexity reviewer."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'runtime' / 'improvement' / 'audit.py'
spec = importlib.util.spec_from_file_location('kiki_audit', MODULE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class ImprovementAuditTests(unittest.TestCase):
    def test_ignores_private_storage_and_generated_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'runtime').mkdir()
            (root / 'runtime' / 'agent.py').write_text('def task():\n    return 1\n', encoding='utf-8')
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_agent.py').write_text('def test_task():\n    assert True\n', encoding='utf-8')
            (root / 'node_modules').mkdir()
            (root / 'node_modules' / 'malicious.js').write_text('test(1)\n', encoding='utf-8')
            (root / 'private.sqlite3').write_text('not touched', encoding='utf-8')
            report = audit.inventory(root)
            self.assertEqual(report['metrics']['source_files'], 1)
            self.assertEqual(report['metrics']['test_cases'], 1)
            self.assertEqual(report['metrics']['test_files'], 1)
            self.assertEqual((root / 'private.sqlite3').read_text(), 'not touched')

    def test_growth_proposals_do_not_authorize_changes(self):
        current = {'schema': 1, 'generated_at': 'synthetic', 'metrics': {
            'source_files': 2, 'source_loc': 130, 'test_cases': 1,
            'integration_patches': 1, 'maintenance_markers': 0},
            'largest_source_files': []}
        previous = {'schema': 1, 'metrics': {'source_loc': 100, 'test_cases': 1}}
        result = audit.assess(current, previous)
        self.assertEqual(result['deltas']['source_loc'], 30)
        self.assertEqual([p['id'] for p in result['suggestions']],
                         ['reconcile-integration-patches', 'test-growth-mismatch'])
        self.assertTrue(all(not p['automatic_execution'] for p in result['suggestions']))

    def test_missing_baseline_is_not_faked(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = audit.assess(audit.inventory(Path(tmp)))
            self.assertFalse(report['baseline_available'])
            self.assertFalse(report['deltas'])
            self.assertIn('n/a', audit.markdown(report))

    def test_output_paths_are_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = audit.main(['--root', str(root),
                                 '--json-out', str(root/'audit-output'/'snapshot.json'),
                                 '--markdown-out', str(root/'audit-output'/'report.md')])
            self.assertEqual(result, 0)
            self.assertTrue((root/'audit-output'/'snapshot.json').is_file())
            self.assertTrue((root/'audit-output'/'report.md').is_file())

if __name__ == '__main__':
    unittest.main()
