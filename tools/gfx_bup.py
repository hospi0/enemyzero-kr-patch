# -*- coding: utf-8 -*-
r"""저장·디스크 안내 그림 BUP*.DG2(256×109) 한글화(2026-10-26) — data/그림/bup.tsv → work/build/gfx/<이름>
  원본: 흰 글자(31,31,31 계열 안티에일리어스) + 짙은 테두리 0x8400, 바탕 투명. 새것: 갈무리11 흰색 + 8방향 테두리 0x8400.
  글자 세로 자리 = 원본 잉크 행 범위 가운데. python tools/gfx_bup.py → 미리보기 work/check/preview_bup.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx, gfxtext as T

W, H = 256, 109; WHITE = 0xFFFF; EDGE = 0x8400; FONT = 'Galmuri11'; LINE = 14


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = [l.split('\t') for l in open(os.path.join(ROOT, 'data', '그림', 'bup.tsv'), encoding='utf-8').read().split('\n')[1:] if l.strip()]
    pairs = []; out = os.path.join(ROOT, 'work', 'build', 'gfx'); os.makedirs(out, exist_ok=True)
    for nm, tr, _ in rows:
        src = open(os.path.join(ROOT, 'work', 'disc0', nm), 'rb').read()
        r = gfx.read_raw(src, W, H)
        ys = [y for y in range(H) if any(r[y])]
        if '#' in tr:                    # BUPDISK0: 아래 세 줄은 원본 큰 괄호(x 13~23 · 229~240, 행 65~107) 안 — 괄호는 원본 화소 그대로
            up, dn = tr.split('#')
            g = T.block_lines(W, H, up.split('|'), FONT, 0, 62, LINE, WHITE)
            g2 = T.block_lines(W, H, dn.split('|'), FONT, 66, 106, LINE, WHITE)
            for y in range(H):
                for x in range(W):
                    if g2[y][x]:
                        assert 26 <= x <= 226, ('괄호와 겹침', x, y); g[y][x] = g2[y][x]
            g = T.outline(g, EDGE, WHITE)
            for y in range(60, H):
                for x in list(range(0, 25)) + list(range(228, W)):
                    g[y][x] = r[y][x]
        else:
            g = T.block_lines(W, H, tr.split('|'), FONT, ys[0], ys[-1], LINE if tr.count('|') < 7 else 13, WHITE)
            g = T.outline(g, EDGE, WHITE)
        b = T.to_bytes(g); assert len(b) == len(src)
        open(os.path.join(out, nm), 'wb').write(b); pairs.append((nm, src, b, W, H))
    print(T.preview(pairs, os.path.join(ROOT, 'work', 'check', 'preview_bup.png'), bg=(30, 40, 50)))


if __name__ == '__main__':
    main()
