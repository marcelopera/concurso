from __future__ import annotations

import concurrent.futures
import json
import subprocess
from pathlib import Path

BASE=Path(__file__).resolve().parent
RUN=BASE/'execucoes/2026-10-29'
EXE=Path(r'C:\Users\marce\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe')


def render(d):
    folder=BASE/'dados/fontes-visuais'/d['documento_id']
    folder.mkdir(parents=True,exist_ok=True)
    if len(list(folder.glob('pagina-*.png')))==d['paginas']:
        return {'documento_id':d['documento_id'],'paginas':d['paginas'],'status':'cache'}
    p=subprocess.run([str(EXE),'-r','100','-png',d['arquivo'],str(folder/'pagina')],capture_output=True)
    return {'documento_id':d['documento_id'],'paginas':len(list(folder.glob('pagina-*.png'))),'status':'ok' if p.returncode==0 else 'erro','erro':p.stderr.decode('utf-8',errors='replace')[:500] if p.returncode else None}


if __name__=='__main__':
    docs=[d for d in json.loads((RUN/'documentos.json').read_text(encoding='utf-8')) if d['tipo']=='provas']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(render,docs))
    (RUN/'fontes-visuais.relatorio.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'documentos':len(rows),'paginas':sum(x['paginas'] for x in rows),'falhas':[x for x in rows if x['status']=='erro']}))
