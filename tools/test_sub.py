# -*- coding: utf-8 -*-
"""게임 안 음성 자막 훅 검산(2026-10-25) — 패치 0.BIN 을 흉내기 램(0x06004000)에 올려
   ① 리터럴 바꿈 ② vwrap(번호·지연·원래 함수로) ③ 프레임마다 vbo: 게임 DMA 표 흉내(매 프레임 새로 짬) → 쪽 고르기·render = ref_render·
   TEX/LUT 복사·표 끝에 스프라이트+END 덧붙임·쪽 사이 안 붙임·재생 깃발 꺼짐 → 끝 ④ 효과음 칸(DFINE) 새로 켜짐 → 시작
   ⑤ 미리보기 그림 work/check/sub_*.png
   python tools/test_sub.py"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import sh2sim as S, subdata as D, subhook as H

DMA_TBL = 0x060C0000
SYS_END = 0x0605D1AE


def game_table(m, n=3):
    """게임이 짠 표 흉내: 명령 n 개 + END(비트 31)"""
    m.w32(H.DMA_PTR, DMA_TBL)
    for k in range(n):
        p = DMA_TBL + 12 * k
        m.w32(p, 0x1E); m.w32(p + 4, 0x25C00060 + 0x20 * k)
        m.w32(p + 8, (0x8000_0000 | SYS_END) if k == n - 1 else 0x060C57F8 + 0x24 * k)
    for k in range(n, n + 3):
        m.w32(DMA_TBL + 12 * k, 0xAAAAAAAA); m.w32(DMA_TBL + 12 * k + 4, 0xAAAAAAAA); m.w32(DMA_TBL + 12 * k + 8, 0xAAAAAAAA)


def save_png(tex, path):
    from PIL import Image
    col = {0: (40, 60, 80), 1: (0, 0, 0), 2: (255, 255, 255), 3: (0, 0, 0)}
    im = Image.new('RGB', (H.W_, H.H_))
    for y in range(H.H_):
        for x in range(0, H.W_, 2):
            b = tex[y * H.ROWB + x // 2]; im.putpixel((x, y), col[b >> 4]); im.putpixel((x + 1, y), col[b & 15])
    im.resize((H.W_ * 3, H.H_ * 3), Image.NEAREST).save(path)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    idx, bits, advs, lists, pages_all, npage = D.build()
    b0 = open(os.path.join(ROOT, 'work', 'disc1', '0.BIN'), 'rb').read()
    s, lab, lay = H.patch_bin(b0, bits, advs, lists)
    m = S.Mem(); ram = m.add(0x06000000, 0x100000); m.add(0x05C00000, 0x80000)
    ram[0x4000:0x4000 + len(s)] = s
    ok = True
    c0 = all(m.r32(l) == lab['vwrap'] for l in H.STREAM_LITS) and m.r32(H.VBO_LIT) == lab['vbo']
    print('① 리터럴 16곳·VBO 등록', c0); ok &= c0
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    called = []

    def stream_fn(r, mm):
        called.append(r[4]); mm.w32(H.STREAM_FLAG, 1)
    # ② vwrap — 번호 0(VOICE001)
    m.w32(H.STREAM_FLAG, 0)
    S.run(m, lab['vwrap'], regs=[0, 0, 0, 0, 0], calls={H.STREAM_FN: stream_fn})
    c1 = called == [0] and m.r32(H.VAR) == 0 and S.s32(m.r32(H.VAR + 4)) == -H.DELAY and m.r32(H.STREAM_FLAG) == 1
    print('② vwrap 번호 0·프레임 −%d·원래 함수 호출' % H.DELAY, c1); ok &= c1
    # 이미 재생 중이면 안 바꿈
    m.w32(H.VAR + 4, 5)
    S.run(m, lab['vwrap'], regs=[0, 0, 0, 0, 3], calls={H.STREAM_FN: lambda r, mm: None})
    c1b = m.r32(H.VAR) == 0 and m.r32(H.VAR + 4) == 5
    print('   재생 중 다시 부름 → 그대로', c1b); ok &= c1b
    m.w32(H.VAR + 4, (-H.DELAY) & 0xFFFFFFFF)

    def frame(rebuild=True):
        if rebuild: game_table(m)
        S.run(m, lab['vbo'], calls={H.VBO_ORIG: lambda r, mm: None})

    def check_voice(no, nframes, tag):
        nonlocal ok
        pages = pages_all[no]; seen = []; bad = 0; gaps = 0
        for f in range(nframes):
            frame()
            fr = S.s32(m.r32(H.VAR + 4))
            cur = next((k for k, p in enumerate(pages) if p[0] <= fr < p[1]), None)
            end_e = DMA_TBL + 12 * 2
            patched = m.r32(end_e + 8) == H.SPR and m.r32(end_e + 12 + 8) == (H.ENDC | 0x80000000) and m.r32(end_e + 12 + 4) == 0x25C000A0 + 0x20 and m.r32(end_e + 12) == 0x1E
            if cur is None:
                if patched: bad += 1
                gaps += 1
                continue
            if not patched: bad += 1
            if not seen or seen[-1] != cur:
                seen.append(cur)
                tex = bytes(m.r8(H.TEX + i) for i in range(H.BMPSZ)); ref = H.ref_render(pages[cur], bits, advs)
                lut = [m.r16(H.LUT + 2 * i) for i in range(4)]
                if tex != ref or lut != list(H.COLORS):
                    print('  ✗ %s 쪽 %d 그림/색 다름' % (tag, cur)); bad += 1
                if len(seen) <= 3:
                    save_png(tex, os.path.join(ROOT, 'work', 'check', 'sub_%s_%d.png' % (tag, cur)))
        c = bad == 0 and len(seen) == len(pages)
        print('%s 쪽 %d/%d 그림 일치·표 덧붙임 · 빈 프레임 %d · 오류 %d' % (tag, len(seen), len(pages), gaps, bad), c)
        ok &= c
    # ③ VOICE001 끝까지
    last = pages_all[0][-1][1] + H.DELAY + 5
    check_voice(0, last, 'VOICE001')
    c3 = m.r32(H.VAR) == 0xFFFFFFFF
    print('   마지막 쪽 지나면 끝(cur = −1)', c3); ok &= c3
    # 같은 표로 두 번(게임이 안 새로 짠 프레임) → 한 번만 덧붙임
    m.w32(H.STREAM_FLAG, 0)
    S.run(m, lab['vwrap'], regs=[0, 0, 0, 0, 1], calls={H.STREAM_FN: stream_fn})
    for _ in range(H.DELAY + pages_all[1][0][0] + 2): frame()
    frame(rebuild=False)
    c4 = m.r32(DMA_TBL + 12 * 3 + 8) == (H.ENDC | 0x80000000) and m.r32(DMA_TBL + 12 * 4) == 0xAAAAAAAA
    print('④ 표 안 새로 짠 프레임 → 두 번 안 붙임', c4); ok &= c4
    # 재생 깃발 꺼짐 → 끝
    m.w32(H.STREAM_FLAG, 0); frame(); frame()
    c5 = m.r32(H.VAR) == 0xFFFFFFFF and m.r32(DMA_TBL + 12 * 2 + 8) == (0x80000000 | SYS_END)
    print('⑤ 재생 멈춤 → 자막 끝·표 그대로', c5); ok &= c5
    # ⑥ 효과음 칸: DFINE(18) 칸 2 에 켜짐
    no = H.SE_BASE + 18
    if no in pages_all:
        sl = H.SE_SLOTS + 12 * 2
        m.w8(sl, 18); m.w32(sl + 4, 1)
        frame()
        c6 = m.r32(H.VAR) == no and m.r32(H.VAR + 12) == 1
        print('⑥ 효과음 칸 DFINE 켜짐 → 시작', c6); ok &= c6
        check_voice(no, pages_all[no][-1][1] + 3, 'DFINE')
        m.w32(sl + 4, 0); frame()
        m.w8(sl, 11); m.w32(sl + 4, 1); frame()
        c7 = m.r32(H.VAR) == H.SE_BASE + 11
        print('   같은 칸에 DFRONT 다시 켜짐 → 시작', c7); ok &= c7
        m.w8(sl, 0); m.w32(sl + 4, 1); m.w32(H.VAR, 0xFFFFFFFF); frame(); frame()
        c8 = m.r32(H.VAR) == 0xFFFFFFFF
        print('   번호 0(ENEMY) 효과음 → 무시', c8); ok &= c8
    print('★전체', '통과' if ok else '실패')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
