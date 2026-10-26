# -*- coding: utf-8 -*-
"""스테이트 VDP1 명령표 → 스프라이트 목록 + 텍스처를 디스크 파일에서 찾기(2026-10-25)
  python tools/vdp1list.py <work/mem 이름> <디스크 번호>"""
import glob, os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sprites(name):
    v = open(os.path.join(ROOT, 'work', 'mem', name, 'VDP1_VRAM.bin'), 'rb').read()
    vb = bytearray(len(v)); vb[0::2] = v[1::2]; vb[1::2] = v[0::2]           # 이 덤프는 u16 바이트가 뒤집혀 있음(마리카와 같음)
    out = []; o = 0; n = 0; stack = []
    while n < 3000:
        c = struct.unpack_from('>16H', vb, o); ctrl = c[0]
        if ctrl & 0x8000: break
        comm = ctrl & 0xF; jp = (ctrl >> 12) & 7
        if comm in (0, 1, 2) and not ctrl & 0x4000:
            w = ((c[5] >> 8) & 0x3F) * 8; h = c[5] & 0xFF; src = c[4] * 8; mode = (c[2] >> 3) & 7
            bpp = {0: 4, 1: 4, 2: 8, 3: 8, 4: 8, 5: 16}.get(mode, 0)
            if w and h: out.append(dict(o=o, comm=comm, mode=mode, src=src, w=w, h=h, x=c[6] - (c[6] >> 15 << 16), y=c[7] - (c[7] >> 15 << 16), colr=c[3], tex=bytes(vb[src:src + w * h * bpp // 8])))
        if jp == 1: o = c[1] * 8
        elif jp == 2: stack.append(o + 32); o = c[1] * 8
        elif jp == 3: o = stack.pop() if stack else o + 32
        else: o += 32
        n += 1
    return out


def find(tex, files):
    best = None
    for i in range(0, max(1, len(tex) - 32), 16):
        s = tex[i:i + 32]
        if len(set(s)) < 10: continue
        for f, d in files.items():
            p = d.find(s)
            if p >= 0: return f, p - i
    return None


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    name, disc = sys.argv[1], int(sys.argv[2])
    files = {os.path.relpath(f, os.path.join(ROOT, 'work', 'disc%d' % disc)): open(f, 'rb').read()
             for f in glob.glob(os.path.join(ROOT, 'work', 'disc%d' % disc, '**', '*'), recursive=True) if os.path.isfile(f)}
    for s in sprites(name):
        r = find(s['tex'], files)
        print('%5X 명령%d 색%d %3dx%-3d @(%4d,%4d) 텍스처 %05X → %s' % (s['o'], s['comm'], s['mode'], s['w'], s['h'], s['x'], s['y'], s['src'], '%s +0x%X' % r if r else '-'))
