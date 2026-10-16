const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
for (const file of ['hosted/app/room.tsx','hosted/app/api/kiki/route.ts']) {
  const input=fs.readFileSync(file,'utf8');
  const kind=file.endsWith('.tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS;
  const tree=ts.createSourceFile(file,input,ts.ScriptTarget.Latest,true,kind);
  const failures=tree.parseDiagnostics.map(d=>{
    const at=tree.getLineAndCharacterOfPosition(d.start||0);
    return file+':'+(at.line+1)+':'+(at.character+1)+' '+ts.flattenDiagnosticMessageText(d.messageText,' ');
  });
  assert.deepEqual(failures,[],file+' contains invalid TypeScript or JSX syntax.');
  process.stdout.write('Syntax checked: '+file+'\n');
}
