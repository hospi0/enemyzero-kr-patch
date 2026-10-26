# -*- coding: utf-8 -*-
r"""게임 안 음성 자막 자료 (2026-10-25) — tools/voicedata.load() 의 «게임 안» 줄 → 글꼴(갈무리14 1비트 16×14·너비) + 소리 번호별 쪽 목록.
  · 소리 번호: 스트림 표(0.BIN 0x0607273C) 순서 VOICE001~022 = 0~21 · AN01 22 · DBREAK 23 · KIM1 24 · KIM2 25 · END3MIN 26
    · 효과음 표(0x060727D0) DFRONT 11 · DBACK 12 · DRIGHT 13 · DLEFT 14 · DDANGER 15 · DCARE 16 · DNEAR 17 · DFINE 18 → +64.
  · 쪽 = 두 줄(줄 폭 ≤ 300 px, 띄어쓰기에서 나눔), 시간은 줄 글자 수 비율. 쪽 끝 = 다음 줄 시작(1초 넘게 비면 끝+0.5초).
  · 한 줄 쪽은 아랫줄 자리(띠도 아래만).
  python tools/subdata.py → 통계"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import voicedata, subhook as H

GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'
NANUM = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
MAXW = 300; FPS = 60
STREAM = ['VOICE%03d' % i for i in range(1, 23)] + ['AN01', 'DBREAK', 'KIM1', 'KIM2', 'END3MIN']
SE = {'DFRONT': 11, 'DBACK': 12, 'DRIGHT': 13, 'DLEFT': 14, 'DDANGER': 15, 'DCARE': 16, 'DNEAR': 17, 'DFINE': 18}
LY = (4, 21)                     # 윗줄·아랫줄 글자 윗선(16×14 칸, 줄 간격 17)


def sound_no(name):
    if name in STREAM:
        return STREAM.index(name)
    if name in SE:
        return H.SE_BASE + SE[name]
    return None


def build_font(chars):
    """갈무리14 비트맵(한글 잉크 윗선 = 0행) — 없는 글자만 나눔고딕 1비트"""
    import bdf
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    g = bdf.Font(GALMURI)
    ys = [y for c in '가각힣맑앙' for x, y in g.draw(c)[0]]
    top, bot = min(ys), max(ys); off = -top + max(0, (H.GROWS - (bot - top + 1)) // 2)
    order = sorted(chars); idx = {c: i for i, c in enumerate(order)}
    bits, advs, miss = [], [], []
    for c in order:
        rows = [0] * H.GROWS
        if ord(c) in g.g:
            pts, w = g.draw(c)
            for x, y in pts:
                yy = y + off
                if 0 <= yy < H.GROWS and 0 <= x < 16: rows[yy] |= 0x8000 >> x
            adv = 4 if c == ' ' else max(1, min(16, w))
        else:
            fb = ImageFont.truetype(NANUM, 56); im = Image.new('L', (64, 64), 0)
            ImageDraw.Draw(im).text((0, -fb.getbbox('가')[1]), c, font=fb, fill=255)
            cov = np.array(im.resize((16, 16), Image.BOX), float) / 255
            for y in range(H.GROWS):
                rows[y] = sum(0x8000 >> x for x in range(16) if cov[y, x] > 0.45)
            adv = max(1, min(16, int(round(ImageFont.truetype(NANUM, 14).getlength(c))))); miss.append(c)
        bits.append(b''.join(struct.pack('>H', r) for r in rows)); advs.append(adv)
    if miss: print('  갈무리14 에 없는 글자(나눔으로):', ''.join(miss))
    return idx, bits, advs


def build():
    by = {}
    for key, rs in voicedata.load().items():
        if rs[0]['kind'] != '게임 안':
            continue
        n = sound_no(key.split('_', 1)[1])
        if n is None:
            print('  번호 없는 소리(뺌):', key); continue
        by[n] = rs
    chars = set(' '.join(r['ko'] for rs in by.values() for r in rs)) | {' '}
    idx, bits, advs = build_font(chars)
    W = lambda s: sum(advs[idx[c]] for c in s)
    lists = {}; pages_all = {}; npage = 0
    for n, rs in sorted(by.items()):
        pages = []
        for i, r in enumerate(rs):
            nxt = rs[i + 1]['a'] if i + 1 < len(rs) else None
            end = nxt if nxt is not None and nxt - r['b'] <= 1.0 and nxt > r['a'] else r['b'] + 0.5
            ls = voicedata.wrap(r['ko'], W, MAXW)
            grp = [ls[k:k + 2] for k in range(0, len(ls), 2)]
            tot = sum(len(''.join(g)) for g in grp); a = r['a']
            for g in grp:
                b = a + (end - r['a']) * len(''.join(g)) / tot
                pages.append((int(a * FPS), max(int(b * FPS), int(a * FPS) + 1), g)); a = b
        body = struct.pack('>H', len(pages)); pp = []
        for f0, f1, g in pages:
            ys = LY if len(g) == 2 else LY[1:]
            lines = []
            for ln, y in zip(g, ys):
                w = W(ln); lines.append(((H.W_ - w) // 2, y, [idx[c] for c in ln], w))
            x0 = min(l[0] for l in lines); x1 = max(l[0] + l[3] for l in lines)
            bx0 = max(0, x0 - 6) >> 1; bx1 = (min(H.W_, x1 + 6) + 1) >> 1
            by0 = ys[0] - 3; by1 = min(H.H_ - 1, ys[-1] + H.GROWS + 3)
            pb = struct.pack('>7H', f0, f1, len(lines), bx0, bx1, by0, by1)
            for x, y, gl, w in lines:
                pb += struct.pack('>3H', x, y, len(gl)) + b''.join(struct.pack('>H', k) for k in gl)
            pb = struct.pack('>H', 2 + len(pb)) + pb
            body += pb; pp.append((f0, f1, bx0, bx1, by0, by1, [(x, y, gl) for x, y, gl, w in lines]))
        lists[n] = body; pages_all[n] = pp; npage += len(pages)
    return idx, bits, advs, lists, pages_all, npage


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    idx, bits, advs, lists, pages_all, npage = build()
    print('글자 %d · 소리 %d · 쪽 %d · 쪽 자료 %d B · 글꼴 %d B' % (len(idx), len(lists), npage, sum(len(v) for v in lists.values()), 29 * len(idx)))
    blk, lab, lay = H.block(bits, advs, lists)
    print('블록 %d B (0x%08X~0x%08X) · 코드 %d B' % (len(blk), H.BLOCK, lay['END'], lay['IDX'] - H.CODE))
