import sys,tempfile,unittest,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'/'local'))
from backup_authority import backup
from kiki_local import Kiki

class BackupTests(unittest.TestCase):
 def test_wal_backup_is_independently_readable_and_restores_additively(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'source.sqlite3';target=Path(tmp)/'backup.sqlite3'
   db=sqlite3.connect(source);db.execute('PRAGMA journal_mode=WAL')
   db.execute('CREATE TABLE tasks(id INTEGER PRIMARY KEY,title TEXT NOT NULL,status TEXT DEFAULT \'open\',created_at TEXT NOT NULL,done_at TEXT,sync_id TEXT,snoozed_until TEXT)')
   db.execute("INSERT INTO tasks VALUES(1,'Synthetic legacy task','open','2026-10-19T10:00:00Z',NULL,'task-existing-id',NULL)");db.commit()
   report=backup(source,target)
   self.assertEqual('ok',report['integrity']);self.assertEqual(1,report['table_counts']['tasks'])
   restored=Kiki(target)
   self.assertEqual('task-existing-id',restored.conn.execute('SELECT sync_id FROM tasks').fetchone()[0]);restored.close()
   self.assertNotIn('queue_json',[r[1] for r in db.execute('PRAGMA table_info(tasks)')])
   db.close()
   with self.assertRaises(ValueError):backup(source,target)
