# -*- coding: utf-8 -*-
r"""작은 안내 그림 한글화(2026-10-26) → work/build/gfx/<이름> · 미리보기 work/check/preview_small.png
  MERRMESS.DG2 96×10 «現在使用できません» — 회색 글자 0xC630 + 8방향 테두리 0x9421, 바탕 투명(원본과 같은 꼴).
  VCBASE.DG2 136×63(디스크 1) «"ロニー"さんから/ビデオコールがあります/ビデオトークしますか?» — 글자 상자(x 22~113, y 9~38)를
    남색 0xAC00 으로 지우고 갈무리9 밝은 초록 흰색 0xFBFD 세 줄(줄 간격 11, 원본 줄 자리)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx, gfxtext as T

OUT = os.path.join(ROOT, 'work', 'build', 'gfx')


def merrmess():
    src = open(os.path.join(ROOT, 'work', 'disc0', 'MERRMESS.DG2'), 'rb').read()
    g = T.block_lines(96, 10, ['사용할 수 없습니다.'], 'Galmuri9', 1, 9, 10, 0xC630, margin=1)
    g = T.outline(g, 0x9421, 0xC630)
    return 'MERRMESS.DG2', src, T.to_bytes(g), 96, 10


def vcbase():
    src = open(os.path.join(ROOT, 'work', 'disc1', 'VCBASE.DG2'), 'rb').read()
    g = gfx.read_raw(src, 136, 63)
    for y in range(9, 39):
        for x in range(22, 114):
            g[y][x] = 0xAC00
    for k, ln in enumerate(['"로니" 님의', '화상 전화입니다.', '받으시겠습니까?']):
        T.render(g, 'Galmuri9', ln, 25, 10 + 11 * k, 0xFBFD)
        assert 25 + T.text_width('Galmuri9', ln) <= 113, ln
    return 'VCBASE.DG2', src, T.to_bytes(g), 136, 63


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True); pairs = []
    for f in (merrmess, vcbase):
        nm, a, b, w, h = f(); assert len(a) == len(b)
        open(os.path.join(OUT, nm), 'wb').write(b); pairs.append((nm, a, b, w, h))
    print(T.preview(pairs, os.path.join(ROOT, 'work', 'check', 'preview_small.png'), bg=(30, 40, 50), scale=4))
