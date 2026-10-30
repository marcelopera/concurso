from __future__ import annotations

import concurrent.futures
import json
import sys
from pathlib import Path

import pdfplumber
from pdfminer.layout import LTTextLine, LTChar

BASE = Path(__file__).resolve().parent
RUN = BASE / 'execucoes/2026-10-29'


def process(d):
    target = RUN / 'paginas' / (d['documento_id'] + '.json')
    if target.exists():
        return {'id': d['documento_id'], 'status': 'cache'}
    pages = []
    with pdfplumber.open(d['arquivo'], laparams={'char_margin': 1.5, 'line_margin': 0.2}) as pdf:
        for number, p in enumerate(pdf.pages, 1):
            lines = []
            def walk(node, block=0):
                if isinstance(node, LTTextLine):
                    words = []
                    chars = []
                    def flush():
                        nonlocal chars
                        if chars:
                            words.append({'texto': ''.join(c.get_text() for c in chars), 'bbox': [min(c.x0 for c in chars), p.height-max(c.y1 for c in chars), max(c.x1 for c in chars), p.height-min(c.y0 for c in chars)]})
                            chars = []
                    last = None
                    for c in node:
                        if not isinstance(c, LTChar) or c.get_text().isspace():
                            flush()
                            last = None
                            continue
                        if last is not None and c.x0-last.x1 > max(1.5, c.size * 0.25):
                            flush()
                        chars.append(c)
                        last = c
                    flush()
                    text = node.get_text().strip()
                    if text:
                        lines.append({'texto':text, 'bbox':[node.x0,p.height-node.y1,node.x1,p.height-node.y0], 'fluxo':block, 'bloco':block, 'palavras':words})
                elif hasattr(node, '__iter__'):
                    for i, child in enumerate(node):
                        walk(child, block if block else i+1)
            walk(p.layout)
            pages.append({'numero':number,'largura':p.width,'altura':p.height,'linhas':lines,'imagens':[{'bbox':[i['x0'],i['top'],i['x1'],i['bottom']],'largura_original':i.get('srcsize')} for i in p.images], 'possui_vetores':bool(p.rects or p.curves)})
            p.close()
    target.write_text(json.dumps({'documento':d,'metodo':'pdfplumber_pdfminer_layout','paginas':pages},ensure_ascii=False),encoding='utf-8')
    return {'id':d['documento_id'],'paginas':len(pages),'status':'ok'}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    docs=json.loads((RUN/'documentos.json').read_text(encoding='utf-8'))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for r in pool.map(process,docs):
            print(json.dumps(r),flush=True)
