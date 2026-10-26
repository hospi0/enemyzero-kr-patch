# -*- coding: utf-8 -*-
r"""화상전화 이름표(NETVP.DGT 안 96×16 ×7, +0x29E0 + k×0xC00 — 스테이트 d1_4 VRAM 과 일치) 한글화(2026-10-26)
  «Laura [ローラ]» → «Laura [로라]»: 글자 칸(x 13~87, y 2~9)을 바탕 0x8421 로 지우고 갈무리7 0xDB12(원본 글자 청록 회색)로 다시(가운데).
  → work/build/gfx/NETVP.DGT · 미리보기 work/check/preview_netvp.png"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx, gfxtext as T

NAMES = ['Laura [로라]', 'David [데이비드]', 'George [조지]', 'Kimberly [킴벌리]', 'Parker [파커]', 'Ronny [로니]', 'Marcus [마커스]']
X0, X1, Y0, Y1 = 13, 87, 2, 9


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = bytearray(open(os.path.join(ROOT, 'work', 'disc0', 'NETVP.DGT'), 'rb').read()); orig = bytes(d); pairs = []
    for k, nm in enumerate(NAMES):
        o = 0x29E0 + k * 0xC00
        g = gfx.read_raw(orig, 96, 16, o)
        for y in range(Y0, Y1 + 1):
            for x in range(X0, X1 + 1):
                g[y][x] = 0x8421
        w = T.text_width('Galmuri7', nm); assert w <= X1 - X0, nm
        T.render(g, 'Galmuri7', nm, X0 + (X1 - X0 + 1 - w) // 2, Y0, 0xDB12)
        d[o:o + 3072] = T.to_bytes(g); pairs.append((nm, orig[o:o + 3072], bytes(d[o:o + 3072]), 96, 16))
    # 안내문 «アクセスコードがちがいます。»(+0x7DE0, 128×10, 바탕 투명) → «접속 코드가 틀립니다.»(2026-10-26 하스피 «일어 (2)»)
    o = 0x7DE0; g = gfx.read_raw(orig, 128, 10, o); msg = '접속 코드가 틀립니다.'
    g = [[0] * 128 for _ in range(10)]
    w = T.text_width('Galmuri9', msg); assert w <= 128, w
    T.render(g, 'Galmuri9', msg, 0, 0, 0xC630)
    d[o:o + 2560] = T.to_bytes(g); pairs.append((msg, orig[o:o + 2560], bytes(d[o:o + 2560]), 128, 10))
    open(os.path.join(ROOT, 'work', 'build', 'gfx', 'NETVP.DGT'), 'wb').write(d)
    print(T.preview(pairs, os.path.join(ROOT, 'work', 'check', 'preview_netvp.png'), bg=(20, 50, 60), scale=4))


if __name__ == '__main__':
    main()
