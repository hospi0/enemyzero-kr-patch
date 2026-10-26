# -*- coding: utf-8 -*-
r"""화상전화 안내 영상(176×96 TrueMotion 1) 일본어 줄 → 한글(2026-10-26 하스피 «일어.state»: NO ONE IN THE ROOM)
  NETDEF.AVI «NO ONE IN THE ROOM / (部屋に誰もいません。)» · NETCON.AVI «CONNECTION REFUSED / (アクセスが拒否されました。)»
  영어 줄(37~44줄)은 원본 그대로, 44줄 아래 띠만 movsub.burn 으로 다시 부호화. 글자는 프레임마다 밝아졌다 어두워짐 →
  영어 줄의 가장 밝은 화소 색을 매 프레임 재서 한글 줄을 그 색으로(갈무리9 비트맵).
  python tools/netmsg.py [미리보기]   → work/movsub/NETDEF.AVI·NETCON.AVI (+ 미리보기 = work/check/netmsg_<이름>.png 만)"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from PIL import Image
import bdf, disc, movsub, tm1

GAL9 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.bdf'
MSG = {'NETDEF': '(방에 아무도 없습니다.)', 'NETCON': '(접속이 거부되었습니다.)'}
EN = (37, 45)          # 영어 줄
JP = (45, 59)          # 지우고 한글을 그릴 줄
Y0 = 44                # 다시 부호화하는 띠 시작(4의 배수)
SRC = os.path.join(ROOT, 'work', 'movie', 'net')
_F = None


def font():
    global _F
    if _F is None:
        _F = bdf.Font(GAL9); _F.top = min(y for c in '가각힣맑앙(' for x, y in _F.draw(c)[0])
    return _F


def make_render(text):
    pts, w = font().draw(text)
    def render(img, disp, hgt, lines, ww):
        px = img.load()
        col = max((px[x, y] for y in range(*EN) for x in range(disp)), key=sum)   # 이 프레임 영어 줄의 가장 밝은 색
        for y in range(*JP):
            for x in range(disp): px[x, y] = (0, 0, 0)
        if sum(col) < 30: return img                                              # 글자가 꺼진 프레임
        x0 = (disp - w) // 2; y0 = 48
        for x, y in pts:
            px[x0 + x, y0 + y - font().top] = col
        return img
    return render


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(SRC, exist_ok=True)
    for nm, text in MSG.items():
        p = os.path.join(SRC, nm + '.AVI')
        if not os.path.exists(p): open(p, 'wb').write(disc.read(nm + '.AVI', disc.bin_path(1)))
        movsub.render = make_render(text)
        movsub.STYLE[176] = (12, 14, 96 - Y0)
        fs, st = movsub.burn(p, [(0.0, 1e9, text, 0)], log=lambda *a: None)
        # 미리보기: 다시 짠 영상을 풀어서 가장 밝은 프레임
        D = tm1.GDecoder(); best = None
        for k, b in enumerate(fs):
            if len(b) > 16 and movsub.is_real(b): D.decode(b)
            if D.frame:
                im = Image.frombytes('RGB', (176, 96), tm1.game_rgb(D.frame, D.dframe))
                s = sum(sum(c) for c in im.crop((0, 30, 176, 60)).getdata())
                if best is None or s > best[0]: best = (s, im)
        best[1].resize((176 * 4, 96 * 4), 0).save(os.path.join(ROOT, 'work', 'check', 'netmsg_%s.png' % nm))
        print(nm, st)
        if '미리보기' not in sys.argv:
            a, b = movsub.write_avi(p, fs, os.path.join(movsub.OUT, nm + '.AVI')); print('  →', a, b)


if __name__ == '__main__':
    main()
