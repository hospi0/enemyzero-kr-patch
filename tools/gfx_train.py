# -*- coding: utf-8 -*-
r"""트레이닝 모드 설명(디스크 0 W0F0.TEX 안 160×42 8비트 3장, +0x11640 + k×0x1B40) 한글화(2026-10-26)
  8비트 색 뱅크 0x200(스테이트 d0_2 명령 COLR) — 색 RAM 0x200~0x20B = 회색 단계(0 → 거의 흰색) → 글자 = 11(흰), 테두리 = 1(짙은 회색), 바탕 0(투명).
  갈무리11, 세 줄 간격 14, 가운데. → work/build/gfx/W0F0.TEX(통째) · 미리보기 work/check/preview_train.png"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfxtext as T
from PIL import Image, ImageDraw

TEXTS = [['에너미는 1마리입니다.', '에너미가 눈에 보입니다.', '지도가 표시됩니다.'],
         ['에너미는 1마리입니다.', '에너미가 보이지 않습니다.', '지도가 표시됩니다.'],
         ['에너미는 3마리입니다.', '에너미가 보이지 않습니다.', '지도가 표시되지 않습니다.']]
W, H = 160, 42; OFF0, STEP = 0x11640, 0x1B40; INK, EDGE = 11, 1


def cram_col():
    c = open(os.path.join(ROOT, 'work', 'mem', 'd0_2', 'CRAM.bin'), 'rb').read()
    cs = bytearray(len(c)); cs[0::2] = c[1::2]; cs[1::2] = c[0::2]
    def col(i):
        v = struct.unpack_from('>I', cs, 4 * i)[0]; return (v & 255, v >> 8 & 255, v >> 16 & 255)
    return col


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t = bytearray(open(os.path.join(ROOT, 'work', 'disc0', 'W0F0.TEX'), 'rb').read()); orig = bytes(t)
    for k, lines in enumerate(TEXTS):
        g = T.block_lines(W, H, lines, 'Galmuri11', 0, H - 1, 14, INK, margin=1)
        g = T.outline(g, EDGE, INK)
        o = OFF0 + k * STEP
        t[o:o + W * H] = bytes(v for row in g for v in row)
    os.makedirs(os.path.join(ROOT, 'work', 'build', 'gfx'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'build', 'gfx', 'W0F0.TEX'), 'wb').write(t)
    assert len(t) == len(orig) and all(t[i] == orig[i] for i in range(len(t)) if not any(OFF0 + k * STEP <= i < OFF0 + k * STEP + W * H for k in range(3)))
    col = cram_col(); S = 4
    out = Image.new('RGB', ((W * 2 + 8) * S, 3 * (H + 4) * S), (60, 0, 60))
    for k in range(3):
        o = OFF0 + k * STEP
        for j, src in enumerate((orig, t)):
            im = Image.new('RGB', (W, H), (150, 20, 30))          # 게임 화면의 빨간 판 흉내
            for y in range(H):
                for x in range(W):
                    v = src[o + y * W + x]
                    if v: im.putpixel((x, y), col(0x200 + v))
            out.paste(im.resize((W * S, H * S), Image.NEAREST), (j * (W + 8) * S, k * (H + 4) * S))
    p = os.path.join(ROOT, 'work', 'check', 'preview_train.png'); out.save(p); print(p)


if __name__ == '__main__':
    main()
