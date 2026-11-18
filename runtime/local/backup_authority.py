"""WAL-safe, read-only source backup with independent integrity/count verification.

The destination contains private task/history data. Keep it outside Git and
shared folders. This utility does not claim independently encrypted backup.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sqlite3


def backup(source,destination):
    source=Path(source).resolve(strict=True);destination=Path(destination).resolve()
    if source==destination or destination.exists():raise ValueError('A new distinct backup destination is required')
    destination.parent.mkdir(parents=True,exist_ok=True)
    src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    dst=sqlite3.connect(destination)
    try:src.backup(dst)
    finally:dst.close();src.close()
    verify=sqlite3.connect(destination.as_uri()+'?mode=ro',uri=True)
    try:
        integrity=verify.execute('PRAGMA integrity_check').fetchall()
        if integrity!=[('ok',)]:raise ValueError('Backup integrity check failed')
        tables=[r[0] for r in verify.execute('SELECT name FROM sqlite_master WHERE type=?',('table',))]
        counts={name:verify.execute('SELECT COUNT(*) FROM "'+name.replace('"','""')+'"').fetchone()[0]
                for name in tables if not name.startswith('sqlite_')}
    finally:verify.close()
    report={'backup':str(destination),'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
            'integrity':'ok','table_counts':counts,'created_at':datetime.now(timezone.utc).isoformat(),
            'encrypted':False,'source_opened_read_only':True}
    destination.with_suffix(destination.suffix+'.verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default=str(Path.home()/'.kiki'/'control-room.sqlite3'))
    parser.add_argument('--destination',required=True)
    args=parser.parse_args();print(json.dumps(backup(args.source,args.destination),indent=2))
