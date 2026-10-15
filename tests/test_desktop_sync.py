import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]/'runtime/local'
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
runtime=load('sync_runtime','kiki_local.py')
sync_module=load('desktop_sync_test','desktop_sync.py')

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'tasks.sqlite3'
        self.app=runtime.Kiki(self.path)
        self.sync=sync_module.DesktopSync(self.app,'https://kiki.example.chatgpt.site','x'*64,'y'*64)
        self.id='task-11111111-1111-4111-8111-111111111111'
    def tearDown(self):self.app.close();self.temp.cleanup()
    def action(self,kind='create',rid='request-00001',payload=None):
        return {'request_id':rid,'task_id':self.id,'action':kind,'payload':payload or {'title':'Review syllabus'},'payload_json':'ignored transport field'}
    def test_repeated_action_survives_restart_without_duplicate(self):
        a=self.action();self.assertEqual(self.sync.apply(a),'applied');self.app.close();self.app=runtime.Kiki(self.path);self.sync.app=self.app
        self.sync.apply(a);self.assertEqual(len(self.app.state()['tasks']),1)
        self.assertEqual(len(self.sync.snapshot()['results']),1)
        with self.assertRaises(ValueError):self.sync.apply(self.action(payload={'title':'Changed'}))
    def test_complete_and_snooze_reuse_same_sqlite_task(self):
        self.sync.apply(self.action());self.sync.apply(self.action('snooze','request-00002',{}))
        self.assertIsNotNone(self.sync.snapshot()['snapshot']['tasks'][0]['snoozed_until'])
        self.sync.apply(self.action('complete','request-00003',{}));self.assertEqual(self.app.state()['tasks'][0]['status'],'done')
    def test_import_keeps_cloud_id_completed_status_and_long_title(self):
        self.sync.apply(self.action('import',payload={'title':'a'*400,'status':'done','created_at':'2026-10-13T12:00:00Z'}))
        row=self.sync.snapshot()['snapshot']['tasks'][0];self.assertEqual(row['id'],self.id);self.assertEqual(row['status'],'done')
    def test_local_and_telegram_created_tasks_are_exported(self):
        self.app.command('/add From Telegram');rows=self.sync.snapshot()['snapshot']['tasks'];self.assertEqual(rows[0]['title'],'From Telegram');self.assertTrue(rows[0]['id'].startswith('task-'))
    def test_bad_action_is_recorded_failed_without_changes(self):
        self.assertEqual(self.sync.apply(self.action('complete')),'failed');self.assertEqual(self.app.state()['tasks'],[])
    def test_snapshot_sequence_and_device_identity_survive_restart(self):
        first=self.sync.snapshot();self.app.close();self.app=runtime.Kiki(self.path);self.sync.app=self.app;second=self.sync.snapshot();self.assertEqual(first['device_id'],second['device_id']);self.assertGreater(second['seq'],first['seq'])

if __name__=='__main__':unittest.main()
