# -*- coding: utf-8 -*-
r"""저장 장치 고르기 화면(BUP.DGT) «本体RAM»·«カートリッジRAM» 한글화(2026-10-26)
  BUP.DGT 안: +0 208×98 큰 타원 · +0x9F40 / +0xDAA0 200×38 위·아래 반쪽 · +0x11600 72×18 «本体RAM» · +0x12020 96×14 «カートリッジRAM»
    · +0x12AA0 288×144 바탕 · +0x26EA0 272×20 ATTENTION(영문 그대로).
  글자: 연분홍 0xFEBF + 8방향 짙은 남색 테두리 0x9C00(원본 색), 갈무리11 Bold. 바탕 투명.
  큰 그림 안의 같은 글자: 원본 글자(0 아닌 화소)가 «그대로» 들어 있는 자리를 찾아 그 화소만 투명으로 지우고 새 글자를 같은 가운데에.
  ⚠️큰 타원(208×98) 윗부분의 흐린 «잔상» 큰 글자는 그림 일부라 안 건드림. → work/build/gfx/BUP.DGT · 미리보기 work/check/preview_ram.png"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx, gfxtext as T

FILL, EDGE = 0xFEBF, 0x9C00
PARTS = [(0, 208, 98), (0x9F40, 200, 38), (0xDAA0, 200, 38)]
LABELS = [(0x11600, 72, 18, '본체 RAM'), (0x12020, 96, 14, '카트리지 RAM')]


def label(w, h, text):
    g = T.block_lines(w, h, [text], 'Galmuri11-Bold', 0, h - 1, h, FILL, margin=1)
    return T.outline(g, EDGE, FILL)


def find(big, lab):
    H, W = len(big), len(big[0]); h, w = len(lab), len(lab[0])
    pts = [(x, y, lab[y][x]) for y in range(h) for x in range(w) if lab[y][x]]
    out = []
    for oy in range(H - h + 1):
        for ox in range(W - w + 1):
            if all(big[oy + y][ox + x] == v for x, y, v in pts):
                out.append((ox, oy))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = bytearray(open(os.path.join(ROOT, 'work', 'disc0', 'BUP.DGT'), 'rb').read()); orig = bytes(d)
    pairs = []
    news = []
    for o, w, h, text in LABELS:
        old = gfx.read_raw(orig, w, h, o); new = label(w, h, text)
        d[o:o + w * h * 2] = T.to_bytes(new); news.append((old, new))
        pairs.append(('BUP.DGT +0x%X %s' % (o, text), orig[o:o + w * h * 2], bytes(d[o:o + w * h * 2]), w, h))
    for o, w, h in PARTS:
        g = gfx.read_raw(orig, w, h, o); hit = 0
        for old, new in news:
            for ox, oy in find(g, old):
                hit += 1
                for y in range(len(old)):
                    for x in range(len(old[0])):
                        if old[y][x]: g[oy + y][ox + x] = 0
                for y in range(len(new)):
                    for x in range(len(new[0])):
                        if new[y][x]: g[oy + y][ox + x] = new[y][x]
        print('BUP.DGT +0x%X %d×%d 글자 자리 %d곳' % (o, w, h, hit))
        d[o:o + w * h * 2] = T.to_bytes(g)
        pairs.append(('BUP.DGT +0x%X' % o, orig[o:o + w * h * 2], bytes(d[o:o + w * h * 2]), w, h))
    assert len(d) == len(orig)
    os.makedirs(os.path.join(ROOT, 'work', 'build', 'gfx'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'build', 'gfx', 'BUP.DGT'), 'wb').write(d)
    print(T.preview(pairs, os.path.join(ROOT, 'work', 'check', 'preview_ram.png'), bg=(0, 0, 0), scale=3))


if __name__ == '__main__':
    main()
