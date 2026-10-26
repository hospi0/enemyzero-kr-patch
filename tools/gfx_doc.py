# -*- coding: utf-8 -*-
r"""네트 컴퓨터 문서 그림(AKI·CHAT·DAVID.DGT, 4장 같은 파일) 한글화(2026-10-26)
  꼴: 머리 172 화소(344 B, CHAT 은 173) 뒤 184×806 RGB555 — 검정 바탕 + 연보라 글자(줄 간격 10).
  AKI·DAVID: 일본어 줄만(원본 줄 윗행 → 한글) 그 줄 행을 지우고 갈무리9 0xDE94 로. 영문·숫자 줄은 원본 그대로.
  CHAT: 행 16 아래를 통째로 지우고 data/그림/chat.txt 를 줄 간격 11 로 다시 조판(폭 182 에서 공백·부호 뒤 접기, 넘치면 실패).
  → work/build/gfx/<이름>.DGT · 미리보기 work/check/preview_doc_<이름>.png"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import gfx, gfxtext as T, voicedata
from PIL import Image

W, H = 184, 806; F = 'Galmuri9'; INK = 0xDE94; PITCH = 11      # 글자 색 = 원본 연보라 중간 밝기(165,165,190) · CHAT 줄 간격 11(갈무리9 잉크 9행이라 10 이면 붙음)
LINES = {
    'AKI': [(77, 0, '1.항행 기간'), (147, 0, '2.항행 구간'), (157, 0, '>지구 (Bolt.S.C.)'), (177, 10, '지구 (Bolt.S.C.)'),
            (197, 0, '3.항행 목적'), (207, 0, '>행성 X-GIL 에서 에너미 포획'), (217, 10, '에너미를 지구로 운반'),
            (237, 0, '4.비상시'), (247, 0, '>승무원이 전원 사망해도'), (257, 10, '에너미를 지구로 운반할 것.'),
            (267, 10, '그때는 프로그램(x-sa)을'), (277, 10, '사용할 것.')],
    'DAVID': [(37, 0, '(데이비드 버나드)'), (297, 0, '이름) 데이비드 버나드'), (307, 0, '제조 번호) David008a'),
              (317, 0, '목적) 생물 병기 에너미 포획'), (327, 40, '승무원 행동 기록'), (337, 40, '비상시 Pilot')],
}
START = {'AKI': 172, 'CHAT': 173, 'DAVID': 172}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    for nm in ('AKI', 'DAVID', 'CHAT'):
        d = bytearray(open(os.path.join(ROOT, 'work', 'disc0', nm + '.DGT'), 'rb').read()); orig = bytes(d)
        s = 2 * START[nm]
        g = gfx.read_raw(orig, W, H, s)
        if nm == 'CHAT':
            for y in range(16, H):
                g[y] = [0] * W
            y = 17; n = 0
            for para in open(os.path.join(ROOT, 'data', '그림', 'chat.txt'), encoding='utf-8').read().rstrip('\n').split('\n'):
                ls = voicedata.wrap(voicedata.squeeze(para), lambda t: T.text_width(F, t), W - 2) if para.strip() else ['']
                for ln in ls:
                    assert y + PITCH <= H, ('CHAT 넘침', para)
                    if ln: T.render(g, F, ln, 0, y, INK)
                    y += PITCH; n += 1
            print('CHAT %d줄 · 끝 행 %d / %d' % (n, y, H))
        else:
            for top, x, text in LINES[nm]:
                for yy in range(top - 1, top + 9):
                    g[yy] = [0] * W
                tw = T.text_width(F, voicedata.squeeze(text)); assert x + tw <= W, (nm, text, tw)
                T.render(g, F, voicedata.squeeze(text), x, top, INK)
        d[s:s + W * H * 2] = T.to_bytes(g); assert len(d) == len(orig)
        open(os.path.join(ROOT, 'work', 'build', 'gfx', nm + '.DGT'), 'wb').write(d)
        a, b = gfx.read(orig, W, H, s), gfx.read(bytes(d), W, H, s)
        used = max(y for y in range(H) if any(g[y]) or any(gfx.read_raw(orig, W, 1, s + 2 * W * y)[0])) + 4
        out = Image.new('RGB', (W * 4 + 16, used * 2), (60, 0, 60))
        for k, im in enumerate((a, b)):
            bg = Image.new('RGBA', (W, used), (0, 0, 0, 255)); bg.alpha_composite(im.crop((0, 0, W, used)))
            out.paste(bg.resize((W * 2, used * 2), Image.NEAREST), (k * (W * 2 + 16), 0))
        p = os.path.join(ROOT, 'work', 'check', 'preview_doc_%s.png' % nm); out.save(p); print(p)


if __name__ == '__main__':
    main()
