# -*- coding: utf-8 -*-
r"""에너미 제로 그림 읽기·쓰기(2026-10-26) — DG2/DGT = 머리 없는 RGB555 빅 엔디언(비트 15 = 1 이면 색, 0x0000 = 투명).
  read(바이트, 폭, 높이, 시작=0) → PIL RGBA · write(PIL RGBA) → 바이트(투명 = 0x0000, 나머지 비트 15 켬)
  python tools/gfx.py <파일> <폭> <높이> [시작] → work/check/<이름>.png(4배)"""
import os, struct, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def c2rgb(v):
    return ((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31)


def rgb2c(r, g, b):
    return 0x8000 | (b * 31 + 127) // 255 << 10 | (g * 31 + 127) // 255 << 5 | (r * 31 + 127) // 255


def read(d, w, h, off=0):
    im = Image.new('RGBA', (w, h)); px = im.load()
    for y in range(h):
        for x in range(w):
            v = struct.unpack_from('>H', d, off + 2 * (y * w + x))[0]
            px[x, y] = (0, 0, 0, 0) if v == 0 else c2rgb(v) + (255,)
    return im


def read_raw(d, w, h, off=0):
    """[[u16]] 원래 값 그대로"""
    return [list(struct.unpack_from('>%dH' % w, d, off + 2 * y * w)) for y in range(h)]


def write(im):
    im = im.convert('RGBA'); w, h = im.size; px = im.load(); out = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            out += struct.pack('>H', 0 if a < 128 else rgb2c(r, g, b))
    return bytes(out)


if __name__ == '__main__':
    p, w, h = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); off = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0
    im = read(open(p, 'rb').read(), w, h, off)
    bg = Image.new('RGBA', im.size, (60, 0, 60, 255)); bg.alpha_composite(im)
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    q = os.path.join(ROOT, 'work', 'check', os.path.basename(p) + '.png'); bg.resize((w * 4, h * 4), Image.NEAREST).save(q); print(q)
