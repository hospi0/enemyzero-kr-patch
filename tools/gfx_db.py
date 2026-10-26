# -*- coding: utf-8 -*-
r"""데이터베이스 그림 한글화(2026-10-26) — data/그림/db.tsv → work/build/gfx/DBNxx.DG2(이름 112×8)·DBTxx.DG2(설명 168×47)
  DBN: 바탕 투명 + 하늘색 글자(원본 0xF30E 계열 안티에일리어스) → 갈무리7 0xF30E 한 색, 가운데.
  DBT: 초록 테두리 1px + 남색 0x8800 바탕 + 하늘색 글자(8px, 줄 간격 11, 첫 줄 y 3) → 안을 0x8800 으로 지우고 갈무리9 0xDA6B,
       x 6, 줄 간격 11, 공백·부호 뒤에서 접어 4줄까지(넘치면 실패). «@3…» = 셋째 줄 자리만 바꿈(35·36 앞 두 줄은 무의미 문자 그대로).
  이름 «-» 또는 영문 그대로(VPS)는 안 바꿈. python tools/gfx_db.py → 미리보기 work/check/preview_db.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx, gfxtext as T, voicedata

OUT = os.path.join(ROOT, 'work', 'build', 'gfx')
NC = 0xF30E; TC = 0xDA6B; BG = 0x8800; NF = 'Galmuri7'; TF = 'Galmuri9'


def name_img(text):
    return T.block_lines(112, 8, [text], NF, 0, 7, 8, NC, margin=0)


def desc_img(src, text):
    g = gfx.read_raw(src, 168, 47)
    if text.startswith('@3'):
        lines, y0 = [text[2:]], 3 + 22
    else:
        lines, y0 = voicedata.wrap(voicedata.squeeze(text), lambda s: T.text_width(TF, s), 168 - 12), 3
        assert len(lines) <= 4, ('설명 4줄 넘음', text, lines)
    for y in range(y0 - 1, 46):
        for x in range(1, 167):
            g[y][x] = BG
    top, bot = T.ink_box(T.font(TF))
    for k, ln in enumerate(lines):
        T.render(g, TF, ln, 6, y0 + 11 * k - 1, TC)
    return g, lines


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True); pairs = []
    for l in open(os.path.join(ROOT, 'data', '그림', 'db.tsv'), encoding='utf-8').read().split('\n')[1:]:
        if not l.strip(): continue
        no, name, desc, _ = l.split('\t')
        if name not in ('-', 'VPS'):
            a = open(os.path.join(ROOT, 'work', 'disc0', 'DBN%s.DG2' % no), 'rb').read()
            b = T.to_bytes(name_img(name)); assert len(a) == len(b)
            open(os.path.join(OUT, 'DBN%s.DG2' % no), 'wb').write(b); pairs.append(('DBN%s' % no, a, b, 112, 8))
        a = open(os.path.join(ROOT, 'work', 'disc0', 'DBT%s.DG2' % no), 'rb').read()
        g, lines = desc_img(a, desc); b = T.to_bytes(g); assert len(a) == len(b)
        open(os.path.join(OUT, 'DBT%s.DG2' % no), 'wb').write(b); pairs.append(('DBT%s (%d줄)' % (no, len(lines)), a, b, 168, 47))
    for k in range(0, len(pairs), 24):
        print(T.preview(pairs[k:k + 24], os.path.join(ROOT, 'work', 'check', 'preview_db_%d.png' % (k // 24)), bg=(0, 0, 0), scale=3))


if __name__ == '__main__':
    main()
