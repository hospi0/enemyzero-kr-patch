# -*- coding: utf-8 -*-
r"""그림 글자 한글화 공용(2026-10-26) — 갈무리 비트맵 한 색 글자 + 원본 테두리 색, 넘치면 실패(글자 단위 자르기 없음).
  lines(…) → [[u16]] · preview(원본 바이트, 새 바이트, 폭, 높이, 바탕) → 원본|새것 나란히 3배 PNG"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import bdf, gfx, voicedata
from PIL import Image

FONTS = {}


def font(name):
    if name not in FONTS:
        FONTS[name] = bdf.Font(r'C:\claude\utils\font\Galmuri-v2.40.3\%s.bdf' % name)
    return FONTS[name]


def ink_box(f, sample='가각힣맑앙RAM()'):
    ys = [y for x, y in f.draw(sample)[0]]
    return min(ys), max(ys)


def text_width(fname, s):
    return font(fname).draw(s)[1]


def render(grid, fname, text, x, y, color):
    """grid[y][x] 에 글자(윗선 y = 잉크 맨 윗줄 기준) — 넘치면 실패"""
    f = font(fname); top, _ = ink_box(f)
    pts, w = f.draw(text)
    for px, py in pts:
        X, Y = x + px, y + py - top
        assert 0 <= X < len(grid[0]) and 0 <= Y < len(grid), ('그림 밖', text, X, Y)
        grid[Y][X] = color
    return w


def outline(grid, color, ink, diag=True):
    """ink 칸 둘레(투명 칸만)를 color 로"""
    h, w = len(grid), len(grid[0]); out = [r[:] for r in grid]
    nb = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)] if diag else [(0, -1), (-1, 0), (1, 0), (0, 1)]
    for y in range(h):
        for x in range(w):
            if grid[y][x] == ink:
                for dx, dy in nb:
                    X, Y = x + dx, y + dy
                    if 0 <= X < w and 0 <= Y < h and grid[Y][X] == 0:
                        out[Y][X] = color
    return out


def block_lines(w, h, lines, fname, y0, y1, line_h, color, align='center', x0=None, margin=2):
    """lines 를 [y0, y1] 세로 가운데에 쌓아 그림 — 폭·높이 넘치면 실패"""
    grid = [[0] * w for _ in range(h)]
    f = font(fname); top, bot = ink_box(f); ih = bot - top + 1
    tot = line_h * (len(lines) - 1) + ih
    assert tot <= y1 - y0 + 1 + 4, ('줄 수 넘침', lines, tot, y1 - y0 + 1)
    y = max(margin, (y0 + y1 + 1 - tot) // 2); y = min(y, h - margin - tot)
    for ln in lines:
        ln = voicedata.squeeze(ln)
        tw = text_width(fname, ln)
        assert tw <= w - 2 * margin, ('줄 폭 넘침', ln, tw, w - 2 * margin)
        x = (w - tw) // 2 if align == 'center' else x0
        render(grid, fname, ln, x, y, color); y += line_h
    return grid


def to_bytes(grid):
    return b''.join(struct.pack('>%dH' % len(r), *r) for r in grid)


def preview(pairs, path, bg=(0, 0, 0), scale=3):
    """pairs = [(이름, 원본 바이트, 새 바이트, 폭, 높이)] → 원본|새것 세로로 쌓은 PNG"""
    from PIL import ImageDraw
    rows = []
    for nm, a, b, w, h in pairs:
        ia, ib = gfx.read(a, w, h), gfx.read(b, w, h)
        im = Image.new('RGBA', (w * 2 + 6, h), bg + (255,))
        t = Image.new('RGBA', (w, h), bg + (255,)); t.alpha_composite(ia); im.paste(t, (0, 0))
        t = Image.new('RGBA', (w, h), bg + (255,)); t.alpha_composite(ib); im.paste(t, (w + 6, 0))
        rows.append((nm, im.resize((im.width * scale, h * scale), Image.NEAREST)))
    W = max(r[1].width for r in rows); H = sum(r[1].height + 18 for r in rows)
    out = Image.new('RGB', (W, H), (60, 0, 60)); d = ImageDraw.Draw(out); y = 0
    for nm, im in rows:
        d.text((4, y + 2), nm, fill=(255, 255, 0)); y += 16; out.paste(im, (0, y)); y += im.height + 2
    os.makedirs(os.path.dirname(path), exist_ok=True); out.save(path)
    return path
