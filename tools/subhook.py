# -*- coding: utf-8 -*-
r"""에너미 제로 게임 안 음성 자막 훅 (2026-10-25) — 마리카 tools/subhook.py(SBL) 를 SGL 게임에 맞게 다시 짠 것.
  ■ 게임(0.BIN, 램 0x06004000, BSS 0x06073980~0x0609F178 — 진입점이 지움)
    · 스트림 음성 재생 0x060327B8(r4 = 번호 0~36: VOICE001~022 = 0~21 · AN01 22 · KIM1 24 · KIM2 25 · END3MIN 26 …),
      재생 중 깃발 0x06072738(=1) — 이 함수를 가리키는 리터럴 16곳을 vwrap 으로.
    · 효과음 재생 0x06032904(번호 → 사운드 램에 미리 실린 소리): 칸 4개 0x060977D0 + 12×칸 {+0 바이트 번호, +4 재생 중 1}.
      데이비드 안내 음성 DFRONT~DFINE = 번호 11~18 → 매 프레임 칸을 훑어 «새로 켜진» 칸을 잡음(함수는 안 건드림).
    · SGL: VBlank-OUT 처리기 0x0605C99E(등록 표 리터럴 0x0605CBB0) 가 VDP1 명령을 «간접 DMA 표»(포인터 0x0605D788 → 0x060C0000)
      로 보낸다 — 항목 12 B {바이트 수 0x1E, VDP1 쓸 곳, 읽을 곳(마지막 항목은 비트 31 = 끝)}.
  ■ 훅: vbo(우리 처리기) → sub → 원래 처리기. sub 는 DMA 시작 «전»에 표 끝 항목(END 명령)을 우리 스프라이트로 바꾸고
      다음 칸에 END 항목을 덧붙인다(이미 붙어 있으면 그대로 — 게임이 표를 안 새로 짠 프레임).
  ■ 그림: VDP1 VRAM 0x78000(320×40 4비트, 색 참조표 0x79900) — 스테이트 8장 모두 «빈 END 명령만» 있는 0x76000~0x7A000 구역.
      스프라이트 PMOD 0x0088(색 참조표·끝 코드 끔) · 지역 좌표(SGL 화면 가운데 원점) x −160, y 66 · 352×224.
      색: 1 띠(검정) · 2 글자(흰) · 3 그림자(검정, 띠 위만).
  ■ 자리: BLOCK 0x060A0000(BSS 끝 0x0609F178 뒤 — 스테이트 8장 모두 0, 0.BIN 리터럴 참조 없음) → 0.BIN 을 0 으로 늘려 붙임.
  ■ 시각: 60/초 VBlank 수. 스트림은 CD 읽기 지연만큼 −DELAY 에서 시작(재생 깃발 확인은 프레임 ≥ 0 부터).
  쪽 자료(빅 엔디언 u16): 크기 · 시작 · 끝 · 줄 수 · 띠 바이트 열 bx0 · bx1 · 띠 행 by0 · by1 · [x0 · y · 글자 수 · 글자 번호…]…"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from sh2asm import A

BIN_BASE = 0x06004000
BLOCK = 0x060A0000; BLOCK_END = 0x060A7000          # 0x060A7000 = 게임 버퍼(0x060137CE·0x06031C56)
VAR = BLOCK + 0x10                                  # 0 cur · 4 frame · 8 shown · 12 kind · 16~31 칸 4개 이전 상태
SPR = BLOCK + 0x40; ENDC = BLOCK + 0x60             # 스프라이트 명령 32 B · END 명령 32 B
CODE = BLOCK + 0x80
STREAM_FN = 0x060327B8; STREAM_FLAG = 0x06072738
SE_SLOTS = 0x060977D0; SE_MIN, SE_MAX = 11, 18; SE_BASE = 64
DMA_PTR = 0x0605D788
VBO_ORIG = 0x0605C99E; VBO_LIT = 0x0605CBB0
DELAY = 30                                          # 스트림 시작 지연(프레임) — 실기 보고 맞출 것
W_, H_ = 320, 40; ROWB = W_ // 2; BMPSZ = ROWB * H_
TEXO = 0x78000; LUTO = TEXO + BMPSZ                 # VDP1 VRAM 안 자리
TEX = 0x25C00000 + TEXO; LUT = 0x25C00000 + LUTO
GROWS = 14                                          # 글꼴 칸 16×14(1비트, 28 B)
FONT_B = 2 * GROWS
XA, YA = -160, 112 - H_ - 6
NIDX = 128
COLORS = (0x0000, 0x8000, 0xFFFF, 0x8000)          # 0 투명 · 1 띠 · 2 글자 · 3 그림자
STREAM_LITS = (0x0600A5EC, 0x06011E38, 0x06016E8C, 0x0602A2E4, 0x0602A42C, 0x0602A584, 0x0602A6B0, 0x0602C74C,
               0x0602DADC, 0x0602DEB8, 0x0602E0BC, 0x0602E748, 0x0602ED60, 0x0602F5A4, 0x060331F8, 0x06033498)


class S(A):
    """A + 중간 리터럴 풀(ltorg) — 마리카 subhook.S"""
    def __init__(s, base): super().__init__(base); s.pools = []; s.cur = []
    def ld(s, rn, val): s.fix.append((len(s.c), 'lit', (rn, val, len(s.pools)))); s.c.append(0); s.cur.append(val)
    def ltorg(s):
        if (s.base + 2 * len(s.c)) % 4: s.c.append(0x0009)
        vals = list(dict.fromkeys(s.cur)); s.pools.append((len(s.c), vals)); s.c.extend([0, 0] * len(vals)); s.cur = []
    def build(s):
        if s.cur: s.ltorg()
        def val(v): return s.lab[v] if isinstance(v, str) else v
        for k, (at, vals) in enumerate(s.pools):
            for j, v in enumerate(vals):
                x = val(v) & 0xFFFFFFFF; s.c[at + 2 * j] = x >> 16; s.c[at + 2 * j + 1] = x & 0xFFFF
        for i, op, a in s.fix:
            pc = s.base + 2 * i
            if op == 'lit':
                rn, v, pk = a; at, vals = s.pools[pk]
                la = s.base + 2 * at + 4 * vals.index(v)
                d = la - ((pc & ~3) + 4); assert d >= 0 and d % 4 == 0 and d // 4 < 256, (hex(pc), d); s.c[i] = 0xD000 | (rn << 8) | d // 4
            else:
                d = (s.lab[a] - (pc + 4)) // 2
                if op in ('bra', 'bsr'): assert -2048 <= d < 2048; s.c[i] = (0xA000 if op == 'bra' else 0xB000) | (d & 0xFFF)
                else: assert -128 <= d < 128, (op, a, d); s.c[i] = {'bt': 0x8900, 'bf': 0x8B00, 'bts': 0x8D00, 'bfs': 0x8F00}[op] | (d & 0xFF)
        return b''.join(struct.pack('>H', x) for x in s.c)

    def mov(s, m, n): s.w(0x6003 | n << 8 | m << 4)
    def movi(s, i, n): s.w(0xE000 | n << 8 | (i & 0xFF))
    def addi(s, i, n): s.w(0x7000 | n << 8 | (i & 0xFF))
    def add(s, m, n): s.w(0x300C | n << 8 | m << 4)
    def sub(s, m, n): s.w(0x3008 | n << 8 | m << 4)
    def ldb(s, m, n): s.w(0x6000 | n << 8 | m << 4)          # mov.b @Rm,Rn
    def ldw(s, m, n): s.w(0x6001 | n << 8 | m << 4)          # mov.w @Rm,Rn
    def ldl(s, m, n): s.w(0x6002 | n << 8 | m << 4)
    def ldwp(s, m, n): s.w(0x6005 | n << 8 | m << 4)         # mov.w @Rm+,Rn
    def stb(s, m, n): s.w(0x2000 | n << 8 | m << 4)          # mov.b Rm,@Rn
    def stw(s, m, n): s.w(0x2001 | n << 8 | m << 4)
    def stl(s, m, n): s.w(0x2002 | n << 8 | m << 4)
    def ldld(s, d, m, n): assert d % 4 == 0 and d < 64; s.w(0x5000 | n << 8 | m << 4 | d // 4)     # mov.l @(d,Rm),Rn
    def stld(s, m, d, n): assert d % 4 == 0 and d < 64; s.w(0x1000 | n << 8 | m << 4 | d // 4)     # mov.l Rm,@(d,Rn)
    def ldwd(s, d, m): assert d % 2 == 0 and d < 32; s.w(0x8500 | m << 4 | d // 2)                # mov.w @(d,Rm),R0 (부호 확장)
    def extub(s, m, n): s.w(0x600C | n << 8 | m << 4)
    def extuw(s, m, n): s.w(0x600D | n << 8 | m << 4)
    def cmpeq(s, m, n): s.w(0x3000 | n << 8 | m << 4)        # T = Rn == Rm
    def cmphs(s, m, n): s.w(0x3002 | n << 8 | m << 4)        # T = Rn >= Rm (부호 없음)
    def cmphi(s, m, n): s.w(0x3006 | n << 8 | m << 4)        # T = Rn > Rm (부호 없음)
    def cmpgt(s, m, n): s.w(0x3007 | n << 8 | m << 4)        # T = Rn > Rm (부호)
    def cmpge(s, m, n): s.w(0x3003 | n << 8 | m << 4)        # T = Rn >= Rm (부호)
    def cmppz(s, n): s.w(0x4011 | n << 8)                    # T = Rn >= 0
    def tst(s, m, n): s.w(0x2008 | n << 8 | m << 4)
    def or_(s, m, n): s.w(0x200B | n << 8 | m << 4)
    def andi(s, i): s.w(0xC900 | i)
    def tsti(s, i): s.w(0xC800 | i)
    def cmpeqi(s, i): s.w(0x8800 | (i & 0xFF))
    def shll(s, n): s.w(0x4000 | n << 8)
    def shlr(s, n): s.w(0x4001 | n << 8)
    def shll2(s, n): s.w(0x4008 | n << 8)
    def shlr2(s, n): s.w(0x4009 | n << 8)
    def shll16(s, n): s.w(0x4028 | n << 8)
    def dt(s, n): s.w(0x4010 | n << 8)
    def push(s, n): s.w(0x2F06 | n << 4)
    def pop(s, n): s.w(0x60F6 | n << 8)
    def pushpr(s): s.w(0x4F22)
    def poppr(s): s.w(0x4F26)
    def jsr(s, m): s.w(0x400B | m << 8)
    def jmp(s, m): s.w(0x402B | m << 8)
    def rts(s): s.w(0x000B)
    def nop(s): s.w(0x0009)


def code(lay):
    a = S(CODE)
    # ── vwrap(r4 = 번호): 이미 재생 중이면(원래 함수가 그냥 돌아감) 안 건드림
    a.L('vwrap'); a.ld(1, STREAM_FLAG); a.ldl(1, 0); a.cmpeqi(1); a.br('bt', 'vgo')
    a.ld(1, VAR); a.extuw(4, 0); a.ld(2, SE_BASE); a.cmphs(2, 0); a.br('bt', 'vgo')       # 번호 ≥ 64 는 안 받음
    a.stld(0, 0, 1); a.movi(-DELAY, 0); a.stld(0, 4, 1); a.movi(0, 0); a.stld(0, 8, 1); a.stld(0, 12, 1)
    a.L('vgo'); a.ld(0, STREAM_FN); a.jmp(0); a.nop()
    # ── vbo: sub → 원래 처리기
    a.L('vbo'); a.pushpr(); a.br('bsr', 'sub'); a.nop(); a.ld(0, VBO_ORIG); a.jsr(0); a.nop(); a.poppr(); a.rts(); a.nop()
    a.ltorg()
    # ── sub
    a.L('sub'); a.ld(6, VAR)
    # 효과음 칸 훑기: 새로 켜진 칸의 번호가 11~18 이면 그 음성 시작
    a.ld(1, SE_SLOTS); a.mov(6, 2); a.addi(16, 2); a.movi(4, 3)
    a.L('se'); a.ldld(4, 1, 0); a.cmpeqi(1); a.br('bf', 'se_off')
    a.ldb(1, 4); a.extub(4, 4); a.ld(5, 0x100); a.or_(4, 5); a.br('bra', 'se_cmp'); a.nop()
    a.L('se_off'); a.movi(0, 5)
    a.L('se_cmp'); a.ldl(2, 0); a.cmpeq(5, 0); a.br('bt', 'se_nx')
    a.stl(5, 2); a.tst(5, 5); a.br('bt', 'se_nx')
    a.movi(SE_MIN, 0); a.cmphs(0, 4); a.br('bf', 'se_nx')
    a.movi(SE_MAX, 0); a.cmphi(0, 4); a.br('bt', 'se_nx')
    a.mov(4, 0); a.addi(SE_BASE, 0); a.stld(0, 0, 6); a.movi(0, 0); a.stld(0, 4, 6); a.stld(0, 8, 6); a.movi(1, 0); a.stld(0, 12, 6)
    a.L('se_nx'); a.addi(12, 1); a.addi(4, 2); a.dt(3); a.br('bf', 'se')
    # 지금 음성
    a.ldld(0, 6, 7); a.cmppz(7); a.br('bf', 'ret')
    a.ldld(4, 6, 3); a.addi(1, 3); a.stld(3, 4, 6)                                       # r3 = 프레임(부호)
    a.ldld(12, 6, 0); a.tst(0, 0); a.br('bf', 'pg')                                      # 효과음은 깃발 안 봄
    a.cmppz(3); a.br('bf', 'pg')                                                          # 지연 중엔 안 봄
    a.ld(1, STREAM_FLAG); a.ldl(1, 0); a.cmpeqi(1); a.br('bf', 'kill')
    a.L('pg'); a.ld(1, lay['IDX']); a.mov(7, 0); a.shll2(0); a.add(1, 0); a.ldl(0, 1)
    a.tst(1, 1); a.br('bt', 'kill')
    a.ldwp(1, 5); a.extuw(5, 5)                                                           # r5 = 쪽 수, r1 = 첫 쪽
    a.L('pl'); a.tst(5, 5); a.br('bt', 'kill')
    a.ldwd(2, 1); a.cmpge(0, 3); a.br('bf', 'ret')                                       # 프레임 < 시작 → 쪽 사이(안 그림)
    a.ldwd(4, 1); a.cmpgt(3, 0); a.br('bt', 'found')                                     # 끝 > 프레임 → 이 쪽
    a.ldwd(0, 1); a.extuw(0, 0); a.add(0, 1); a.addi(-1, 5); a.br('bra', 'pl'); a.nop()
    a.L('found'); a.ldld(8, 6, 0); a.cmpeq(1, 0); a.br('bt', 'patch')
    a.stld(1, 8, 6)
    a.pushpr(); a.mov(1, 4); a.br('bsr', 'render'); a.nop(); a.poppr()
    a.ld(1, lay['COMP']); a.ld(2, TEX); a.ld(5, BMPSZ // 4)
    a.L('cp'); a.ldl(1, 0); a.stl(0, 2); a.addi(4, 1); a.addi(4, 2); a.dt(5); a.br('bf', 'cp')
    a.ld(2, LUT)
    for c in COLORS:
        a.ld(0, c); a.stw(0, 2); a.addi(2, 2)
    # DMA 표 끝 항목 → 우리 스프라이트 + END 덧붙임
    a.L('patch'); a.ld(1, DMA_PTR); a.ldl(1, 1); a.ld(5, 4000)
    a.L('dl'); a.ldld(8, 1, 0); a.cmppz(0); a.br('bf', 'dend'); a.addi(12, 1); a.dt(5); a.br('bf', 'dl'); a.rts(); a.nop()
    a.L('dend'); a.ld(2, ENDC | 0x80000000); a.cmpeq(2, 0); a.br('bt', 'ret')
    a.ld(0, SPR); a.stld(0, 8, 1)
    a.ldld(0, 1, 0); a.stld(0, 12, 1)
    a.ldld(4, 1, 0); a.addi(32, 0); a.stld(0, 16, 1)
    a.stld(2, 20, 1)
    a.L('ret'); a.rts(); a.nop()
    a.L('kill'); a.movi(-1, 0); a.stld(0, 0, 6); a.movi(0, 0); a.stld(0, 8, 6); a.rts(); a.nop()
    a.ltorg()

    # ── render(r4 = 쪽) → COMP: r8~r14 보존
    a.L('render')
    for n in (8, 9, 10, 11, 12, 13, 14): a.push(n)
    a.pushpr()
    a.mov(4, 14)
    a.ld(1, lay['COMP']); a.ld(2, BMPSZ // 4); a.movi(0, 0)
    a.L('rc'); a.stl(0, 1); a.addi(4, 1); a.dt(2); a.br('bf', 'rc')
    # 띠: 행 by0..by1−1, 바이트 열 bx0..bx1−1 = 0x11
    a.ldwd(8, 14); a.extuw(0, 8); a.ldwd(10, 14); a.extuw(0, 9); a.ldwd(12, 14); a.extuw(0, 10); a.ldwd(14, 14); a.extuw(0, 11)
    a.mov(10, 1); a.shll2(1); a.shll2(1); a.shll(1); a.mov(1, 0); a.shll2(0); a.add(1, 0)   # by0×160
    a.ld(12, lay['COMP']); a.add(0, 12)
    a.mov(11, 13); a.sub(10, 13); a.ld(3, 0x11)
    a.L('brow'); a.mov(12, 1); a.add(8, 1); a.mov(9, 2); a.sub(8, 2)
    a.L('bcol'); a.stb(3, 1); a.addi(1, 1); a.dt(2); a.br('bf', 'bcol')
    a.ld(0, ROWB); a.add(0, 12); a.dt(13); a.br('bf', 'brow')
    # 줄들 — 스택 [줄 y, 남은 줄]
    a.ldwd(6, 14); a.extuw(0, 0); a.push(0)
    a.mov(14, 12); a.addi(16, 12)
    a.L('ln'); a.ldl(15, 0); a.tst(0, 0); a.br('bt', 'rdone'); a.addi(-1, 0); a.stl(0, 15)
    a.ldwp(12, 8); a.extuw(8, 8)                                                          # x0
    a.ldwp(12, 0); a.extuw(0, 0); a.push(0)                                               # 줄 y
    a.ldwp(12, 13); a.extuw(13, 13)                                                       # 글자 수
    a.tst(13, 13); a.br('bt', 'lend')
    a.L('gl'); a.ldw(12, 0); a.extuw(0, 0)
    a.mov(0, 1); a.shll2(1); a.shll2(0); a.shll2(0); a.shll(0); a.sub(1, 0)               # 번호×28
    a.ld(10, lay['FONT']); a.add(0, 10)
    a.ldl(15, 9); a.movi(GROWS, 11)
    a.L('grow'); a.ldwp(10, 14); a.extuw(14, 14); a.tst(14, 14); a.br('bt', 'gnext')
    a.shll16(14); a.mov(8, 4)
    a.L('gcol'); a.shll(14); a.br('bf', 'gskip')
    a.mov(4, 0); a.push(0); a.addi(1, 4); a.mov(9, 5); a.addi(1, 5); a.movi(3, 6); a.movi(1, 7); a.br('bsr', 'pix'); a.nop()
    a.pop(4); a.mov(9, 5); a.movi(2, 6); a.movi(0, 7); a.br('bsr', 'pix'); a.nop()
    a.L('gskip'); a.addi(1, 4); a.tst(14, 14); a.br('bf', 'gcol')
    a.L('gnext'); a.addi(1, 9); a.dt(11); a.br('bf', 'grow')
    a.ldw(12, 0); a.extuw(0, 0); a.ld(1, lay['ADV']); a.add(0, 1); a.ldb(1, 0); a.extub(0, 0); a.add(0, 8)
    a.addi(2, 12); a.dt(13); a.br('bf', 'gl')
    a.L('lend'); a.pop(0); a.br('bra', 'ln'); a.nop()
    a.L('rdone'); a.pop(0); a.poppr()
    for n in (14, 13, 12, 11, 10, 9, 8): a.pop(n)
    a.rts(); a.nop()
    a.ltorg()
    # ── pix(r4 = x, r5 = y, r6 = 색, r7 = 1 이면 띠(1) 위에만) — r0~r3 씀
    a.L('pix'); a.ld(0, W_); a.cmphs(0, 4); a.br('bt', 'pret'); a.movi(H_, 0); a.cmphs(0, 5); a.br('bt', 'pret')
    a.mov(5, 1); a.shll2(1); a.shll2(1); a.shll(1); a.mov(1, 0); a.shll2(0); a.add(1, 0)
    a.mov(4, 1); a.shlr(1); a.add(1, 0); a.ld(2, lay['COMP']); a.add(0, 2)
    a.ldb(2, 1); a.extub(1, 1); a.mov(4, 0); a.tsti(1); a.br('bf', 'podd')
    a.mov(1, 3); a.shlr2(3); a.shlr2(3)
    a.tst(7, 7); a.br('bt', 'pe1'); a.movi(1, 0); a.cmpeq(0, 3); a.br('bf', 'pret')
    a.L('pe1'); a.mov(1, 0); a.andi(0x0F); a.mov(6, 3); a.shll2(3); a.shll2(3); a.or_(3, 0); a.stb(0, 2); a.rts(); a.nop()
    a.L('podd'); a.mov(1, 0); a.andi(0x0F); a.mov(0, 3)
    a.tst(7, 7); a.br('bt', 'po1'); a.movi(1, 0); a.cmpeq(0, 3); a.br('bf', 'pret')
    a.L('po1'); a.mov(1, 0); a.andi(0xF0); a.or_(6, 0); a.stb(0, 2)
    a.L('pret'); a.rts(); a.nop()
    return a


def layout(nfont, pages_len):
    tmp = {'IDX': 0x0A0B0C00, 'COMP': 0x0A0B0D00, 'FONT': 0x0A0B0E00, 'ADV': 0x0A0B0F00}
    n0 = len(code(tmp).build())
    lay = {}; p = (CODE + n0 + 15) & ~15
    lay['IDX'] = p; p += 4 * NIDX
    lay['PAGES'] = p; p += (pages_len + 3) & ~3
    lay['COMP'] = p; p += BMPSZ
    lay['FONT'] = p; p += FONT_B * nfont
    lay['ADV'] = p; p += nfont
    lay['END'] = (p + 15) & ~15
    a = code(lay); c = a.build(); assert len(c) == n0
    return lay, a, c


def block(font_bits, advs, lists):
    """lists: {번호: 쪽 목록 바이트(u16 쪽 수 + 쪽들)} → (블록 바이트, 라벨, 자리)"""
    body = b''; offs = {}
    for k in sorted(lists):
        offs[k] = len(body); body += lists[k] + (b'\0\0' if len(lists[k]) & 2 else b'')
    lay, a, c = layout(len(advs), len(body))
    blk = bytearray(lay['END'] - BLOCK)
    blk[0:4] = b'EZS1'
    struct.pack_into('>4I', blk, VAR - BLOCK, 0xFFFFFFFF, 0, 0, 0)
    spr = struct.pack('>16H', 0x0000, 0, 0x0088, LUTO >> 3, TEXO >> 3, (W_ // 8) << 8 | H_, XA & 0xFFFF, YA & 0xFFFF, *[0] * 8)
    blk[SPR - BLOCK:SPR - BLOCK + 32] = spr
    blk[ENDC - BLOCK:ENDC - BLOCK + 32] = struct.pack('>16H', 0x8000, *[0] * 15)
    blk[CODE - BLOCK:CODE - BLOCK + len(c)] = c
    for k, o in offs.items():
        struct.pack_into('>I', blk, lay['IDX'] - BLOCK + 4 * k, lay['PAGES'] + o)
    blk[lay['PAGES'] - BLOCK:lay['PAGES'] - BLOCK + len(body)] = body
    f = lay['FONT'] - BLOCK
    for i, g in enumerate(font_bits): blk[f + FONT_B * i:f + FONT_B * (i + 1)] = g
    blk[lay['ADV'] - BLOCK:lay['ADV'] - BLOCK + len(advs)] = bytes(advs)
    assert lay['END'] <= BLOCK_END, ('블록이 0x060A7000 을 넘음', hex(lay['END']))
    return bytes(blk), a.lab, lay


def patch_bin(b0, font_bits, advs, lists):
    blk, lab, lay = block(font_bits, advs, lists)
    s = bytearray(b0)
    assert len(s) == 457084, '원본 0.BIN 이 아님'
    for lit in STREAM_LITS:
        assert struct.unpack_from('>I', s, lit - BIN_BASE)[0] == STREAM_FN, hex(lit); struct.pack_into('>I', s, lit - BIN_BASE, lab['vwrap'])
    assert struct.unpack_from('>I', s, VBO_LIT - BIN_BASE)[0] == VBO_ORIG; struct.pack_into('>I', s, VBO_LIT - BIN_BASE, lab['vbo'])
    s += bytes(BLOCK - BIN_BASE - len(s)); s += blk
    return bytes(s), lab, lay


def ref_render(page, font_bits, advs):
    """render 와 같은 셈(검산용) — page = (시작, 끝, bx0, bx1, by0, by1, [(x0, y, [글자])]) → BMPSZ B"""
    f0, f1, bx0, bx1, by0, by1, lines = page
    px = [[0] * W_ for _ in range(H_)]
    for y in range(by0, by1):
        for b in range(bx0, bx1): px[y][2 * b] = px[y][2 * b + 1] = 1
    for x, ly, gl in lines:
        for g in gl:
            bits = font_bits[g]
            for r in range(GROWS):
                v = bits[2 * r] << 8 | bits[2 * r + 1]
                for c in range(16):
                    if v & (0x8000 >> c):
                        xx, yy = x + c, ly + r
                        if xx + 1 < W_ and yy + 1 < H_ and px[yy + 1][xx + 1] == 1: px[yy + 1][xx + 1] = 3
                        if xx < W_ and yy < H_: px[yy][xx] = 2
            x += advs[g]
    return bytes(px[y][x] << 4 | px[y][x + 1] for y in range(H_) for x in range(0, W_, 2))
