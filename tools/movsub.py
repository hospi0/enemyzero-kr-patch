# -*- coding: utf-8 -*-
r"""에너미 제로 동영상 자막 굽기 (2026-10-25) — 카오스 시드 tools/moviesub.py(24비트 게임 모델, 실기 통과) + VIRUS tools/movsub2.py(실기 통과) 합침.
  ★실기 규칙(메모리 reference_truemotion1_encoder): iddx(있으면) 고침 · 채널 범위(24비트 = 새턴 GDecoder 모델, tm1band.BandEnc24G)
    · 탈출 뒤 0(tm1enc.rebuild DP) · 덩어리 ≤ 원본 avih 권장 버퍼 · 데이터율 ≤ 원본 «누적 − 2배속×시간» 최대 + 여유.
  영상 = 전부 Duck TrueMotion 1 24비트(압축 10·16 + NOP 0) 288×144(화면 288폭) · 화상전화 176×96, 15fps.
  자막 = tools/voicedata.load() 의 «동영상» 줄(시각 = tools/retime.py) — 폭에 맞춰 접고 두 줄씩 나눠 시간은 글자 수 비율.
  글씨: 나눔고딕 Bold 흰색 + 검은 1px 테두리, 아래 가운데. 위쪽은 원본 델타 그대로(tm1enc.trace), 아래 띠만 다시 부호화.
  python tools/movsub.py check                 → 줄 폭·줄 수 검사 + 자막 목록
  python tools/movsub.py R12M03 [끝프레임]      → work/movsub/R12M03.AVI (+ work/movsub/mp4/R12M03.mp4 미리보기)
  python tools/movsub.py all [--j=6]           → 자막 있는 영상 전부(병렬) → work/movsub/<이름>.AVI
"""
import copy, os, struct, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tm1, tm1enc, tm1band, voicedata
from PIL import Image, ImageDraw, ImageFont

FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
STYLE = {288: (13, 15, 32), 176: (12, 14, 32)}      # 화면 폭 → (글자 px, 줄 간격, 띠 높이 — 4의 배수)
MOV = os.path.join(ROOT, 'work', 'movie')
OUT = os.path.join(ROOT, 'work', 'movsub')
RATE = 307200.0 * 0.95          # 2배속 CD 의 95%
MARGIN = 128 * 1024             # 원본 선행량에 더해 허용(VIRUS 실기 통과 값)


def movie_cues():
    """{영상 이름: [(시작, 끝, 한글)]} + 영상이 든 장 목록"""
    out = {}
    for key, rs in voicedata.load().items():
        if rs[0]['kind'] != '동영상':
            continue
        nm = key.split('_', 1)[1]
        out[nm] = ([(r['a'], r['b'], r['ko'], r['id']) for r in rs], rs[0]['discs'])
    return out


def src_of(nm, discs):
    for d in discs:
        p = os.path.join(MOV, d, nm + '.AVI')
        if os.path.exists(p):
            return p
    raise FileNotFoundError(nm)


def split_cues(cues, w):
    """[(a, b, 글)] → [(a, b, [줄…≤2])] — 두 줄 넘으면 «문장 끝» 우선으로 나눠 시간은 글자 수 비율"""
    px, line, band = STYLE[w]
    f = ImageFont.truetype(FONT, px); d = ImageDraw.Draw(Image.new('RGB', (8, 8)))
    out = []
    for a, b, text, _id in cues:
        ls = voicedata.wrap(text, lambda t: d.textlength(t, font=f), w - 10)
        groups = []
        i = 0
        while i < len(ls):
            if len(ls) - i <= 2:
                groups.append(ls[i:]); break
            # 두 줄 묶음 — 첫 줄이 문장 끝이면 한 줄만
            if ls[i].endswith(('.', '?', '!', '…')) and not ls[i + 1].endswith(('.', '?', '!', '…')) and len(ls) - i > 2:
                groups.append(ls[i:i + 1]); i += 1
            else:
                groups.append(ls[i:i + 2]); i += 2
        n = [sum(len(x) for x in g) for g in groups]; tot = sum(n); t = a
        for g, k in zip(groups, n):
            e = t + (b - a) * k / tot
            out.append((t, e, g)); t = e
    return out


def check():
    bad = 0
    for nm, (cues, discs) in sorted(movie_cues().items()):
        p = src_of(nm, discs)
        fr = tm1.avi_frames(p)
        h0 = tm1.header(next(b for _, b in fr if len(b) >= 2 and tm1.COMP[tm1.header(b)['compression']][0]))
        w = h0['xsize']
        try:
            sc = split_cues(cues, w)
        except AssertionError as e:
            print('⛔', nm, e); bad += 1; continue
        dur = len(fr) / 15.0
        late = [c for c in cues if c[1] > dur + 0.5]
        if late:
            print('⛔', nm, '영상 길이 %.1fs 넘는 자막' % dur, [c[3] for c in late]); bad += 1
        print('%-9s %s 폭 %d 줄 %d 조각 %d' % (nm, ','.join(discs), w, len(cues), len(sc)))
    print('검사 오류', bad)
    return bad


def rate_budget(d, dt):
    """영상 프레임 k 마다 «앞으로 늘려도 되는 바이트» — min_{j≥k}(D − (누적(j) − R·j·dt)) (VIRUS movsub2)"""
    mv = tm1.movi_pos(d); lst = mv - 8
    end = lst + 8 + struct.unpack_from('<I', d, lst + 4)[0]
    i = mv + 4; cum = 0; v = []
    while i + 8 <= end:
        tag = d[i:i + 4]; n = struct.unpack_from('<I', d, i + 4)[0]
        if tag == b'LIST':
            cum += 12; i += 12; continue
        cum += 8 + n + (n & 1)
        if tag[2:] in (b'dc', b'db'):
            v.append(cum - RATE * len(v) * dt)
        i += 8 + n + (n & 1)
    D = max(v)
    ms = [0.0] * (len(v) + 1); ms[len(v)] = 1e18
    for k in range(len(v) - 1, -1, -1):
        ms[k] = min(D - v[k], ms[k + 1])
    return ms


def render(img, disp, hgt, lines, w):
    if not lines:
        return img
    px, line, band = STYLE[w]
    F = ImageFont.truetype(FONT, px); d = ImageDraw.Draw(img)
    y = hgt - band // 2 - (len(lines) - 1) * line // 2
    for ln in lines:
        d.text((disp / 2, y), ln, font=F, anchor='mm', fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0)); y += line
    return img


def make_inter(template, comp):
    """NOP·빈 덩어리 자리에 넣을 인터 프레임(위쪽 블록 전부 «그대로») — 카오스 시드 moviesub.make_inter"""
    h = tm1.header(template)
    fr = tm1enc.Frame(); fr.h = dict(h); fr.nop = False
    alg, bw, bh, bt = tm1.COMP[comp]
    fr.b16 = alg in (1, 2); ws = 0 if fr.b16 else 1
    fr.w, fr.hgt = h['xsize'] >> ws, h['ysize']; fr.nw = fr.w >> 1 if fr.b16 else fr.w
    fr.rowsize = ((fr.w >> (2 - ws)) + 7) >> 3; fr.key = 0; fr.bw, fr.bt = bw, bt
    nblk = fr.nw >> 1
    full = bytes([0xFF] * (nblk >> 3)) + (bytes([(1 << (nblk & 7)) - 1]) if nblk & 7 else b'')
    full = full + bytes(fr.rowsize - len(full))
    fr.cbits = [full] * (fr.hgt >> 2)
    fr.rows = [[] for _ in range(fr.hgt)]
    hs = h['size']; hb = bytearray(template[i] ^ template[i + 1] for i in range(1, hs))
    hb[0] = comp; hb[11] = (hb[11] | tm1.FLAG_INTERFRAME) & ~tm1.FLAG_KEYFRAME & 0xFF
    b = tm1enc.enc_header(bytes(hb), hs, 0)
    fr.buf = bytes([template[0]] + b[1:hs]) + bytes([0])
    return fr


def is_real(b):
    return len(b) >= 2 and tm1.COMP[tm1.header(b)['compression']][0]


def burn(src, cues, last=None, log=print):
    d = open(src, 'rb').read()
    fr_all = tm1.avi_frames(src)
    template = next(b for _, b in fr_all if is_real(b))
    h0 = tm1.header(template); comp = h0['compression']
    assert tm1.COMP[comp][0] == 3, '24비트만'
    disp, hgt = h0['xsize'], h0['ysize']; band = STYLE[disp][2]
    ai = d.find(b'avih') + 8
    dt = struct.unpack_from('<I', d, ai)[0] / 1e6
    buf = max(struct.unpack_from('<I', d, ai + 28)[0], max(len(b) for _, b in fr_all))
    ms = rate_budget(d, dt)
    sc = split_cues(cues, disp)
    A, B = tm1.GDecoder(), tm1.GDecoder()           # ★24비트 = 게임 모델(좌우 화소)
    out = []; extra = 0; t0 = time.time(); prev_lines = None; nre = dropped = over = oob = 0
    n = len(fr_all) if last is None else min(last, len(fr_all))
    for k in range(n):
        off, b = fr_all[k]
        t = k * dt
        c = next((c for c in sc if c[0] <= t < c[1]), None)
        lines = c[2] if c else None
        if is_real(b):
            if lines is None and A.frame is not None and B.frame is not None:
                same = B.frame == A.frame and B.dframe == A.dframe
                if same or tm1.header(b)['kflags'] & tm1.FLAG_KEYFRAME:
                    A.decode(b); B.decode(b); out.append(b); prev_lines = None
                    continue
            prevB = copy.deepcopy(B.frame) if B.frame else None
            prevBd = copy.deepcopy(B.dframe) if B.frame else None
            fr = tm1enc.trace(A, b)
        else:
            if lines == prev_lines or A.frame is None:
                out.append(b)
                if len(b) >= 2:
                    A.decode(b); B.decode(b)
                continue
            prevB = copy.deepcopy(B.frame); prevBd = copy.deepcopy(B.dframe)
            fr = make_inter(template, comp)
        nw = len(A.frame[0]); y0 = hgt - band
        cur = [list(r) for r in A.frame]; curd = [list(r) for r in A.dframe]
        if prevB is None:
            prevB = [[0] * nw for _ in range(hgt)]; prevBd = [[0] * nw for _ in range(hgt)]
        limit = int(min(buf, len(b) + ms[k] + MARGIN - extra))
        tol = None; coarse = 0; use = lines
        while True:
            img = render(Image.frombytes('RGB', (disp, hgt), tm1.game_rgb(A.frame, A.dframe)), disp, hgt, use, disp)
            px = img.load()
            tg = [[(px[2 * x, y], px[2 * x + 1, y]) for x in range(nw)] for y in range(hgt)]
            E = tm1band.BandEnc24G(A.tab, A.key[0], False, fr.bw, fr.bt, y0, tol, coarse)
            bops, bcb = E.encode_game([list(r) for r in cur], [list(r) for r in curd], prevB, prevBd, tg, fr.key)
            rows = fr.rows[:y0] + bops
            cbits = [] if fr.key else fr.cbits[:y0 >> 2] + bcb
            nb = tm1enc.rebuild(fr, rows, cbits, E.cdict)
            if len(nb) <= limit:
                break
            if E.tol < 16:
                tol = E.tol * 2
            elif coarse < 8:
                coarse += 1
            elif use is not None:                 # 그래도 넘치면 이 프레임만 자막 빼고(목표 = 원본 화면) 다시
                use = None; tol = None; coarse = 0; dropped += 1
            elif len(nb) <= buf:
                over += 1; break
            else:
                raise SystemExit('⛔ %s 프레임 %d: %d B > 버퍼 %d' % (src, k, len(nb), buf))
        oob += getattr(E, 'oob', 0)
        B.decode(nb)
        assert all((B.frame[y][x] ^ A.frame[y][x]) & 0x7FFFFFFF == 0 and B.dframe[y][x] == A.dframe[y][x]
                   for y in range(y0) for x in range(nw)), (src, k, '위쪽 불일치')
        extra += len(nb) - len(b); nre += 1
        out.append(nb); prev_lines = use
        if k % 300 == 0:
            log('  %s %d/%d %.0fs' % (os.path.basename(src), k, n, time.time() - t0))
    out += [b for _, b in fr_all[n:]]
    return out, dict(nre=nre, dropped=dropped, over=over, oob=oob)


def write_avi(src, frames_new, dst):
    """영상 덩어리만 바꿔 쓰기 — LIST 'rec ' 보존 · idx1·iddx 항목을 새 자리·크기로 · avih/strh 권장 버퍼 갱신(VIRUS movsub2.write_avi)"""
    d = open(src, 'rb').read()
    mv = tm1.movi_pos(d); lst = mv - 8
    end_movi = lst + 8 + struct.unpack_from('<I', d, lst + 4)[0]
    fi = iter(frames_new)
    remap = {}; body = bytearray()

    def walk(i, end):
        while i + 8 <= end:
            tag = d[i:i + 4]; n = struct.unpack_from('<I', d, i + 4)[0]
            o_old = i - mv
            if tag == b'LIST':
                at = len(body); body.extend(d[i:i + 12])
                walk(i + 12, i + 8 + n)
                sz = len(body) - at - 8
                struct.pack_into('<I', body, at + 4, sz)
                remap[o_old] = (at + 4, sz)
                i += 8 + n + (n & 1); continue
            data = d[i + 8:i + 8 + n]
            if tag[2:] in (b'dc', b'db'):
                data = next(fi)
            at = len(body)
            body.extend(tag + struct.pack('<I', len(data)) + data + (b'\0' if len(data) & 1 else b''))
            remap[o_old] = (at + 4, len(data))
            i += 8 + n + (n & 1)

    walk(mv + 4, end_movi)
    assert next(fi, None) is None, '새 덩어리가 남음'
    head = bytearray(d[:lst])
    movi = b'LIST' + struct.pack('<I', len(body) + 4) + b'movi' + bytes(body)

    def fix_index(buf, p, n):
        for q in range(p, p + n, 16):
            off = struct.unpack_from('<I', buf, q + 8)[0]
            no, ns = remap[off]
            struct.pack_into('<II', buf, q + 8, no, ns)

    tail = b''
    oi = d.find(b'idx1', end_movi)
    if oi >= 0:
        on = struct.unpack_from('<I', d, oi + 4)[0]
        ib = bytearray(d[oi + 8:oi + 8 + on]); fix_index(ib, 0, on)
        tail = b'idx1' + struct.pack('<I', on) + bytes(ib) + d[oi + 8 + on:]
    xi = head.find(b'iddx')
    if xi >= 0:
        fix_index(head, xi + 8, struct.unpack_from('<I', head, xi + 4)[0])
    vmax = max(len(f) for f in frames_new)
    ai = head.find(b'avih') + 8
    struct.pack_into('<I', head, ai + 28, max(vmax, struct.unpack_from('<I', head, ai + 28)[0]))
    si = head.find(b'strh') + 8
    if head[si:si + 4] == b'vids':
        struct.pack_into('<I', head, si + 36, max(vmax, struct.unpack_from('<I', head, si + 36)[0]))
    out = head + movi + tail
    struct.pack_into('<I', out, 4, len(out) - 8)
    o = bytes(out); mv2 = tm1.movi_pos(o)
    for p in (o.find(b'iddx', 0, mv2), o.find(b'idx1', mv2 + len(body))):
        if p < 0:
            continue
        n = struct.unpack_from('<I', o, p + 4)[0]
        for q in range(p + 8, p + 8 + n, 16):
            tag = o[q:q + 4]; off, sz = struct.unpack_from('<II', o, q + 8)
            h = mv2 + off
            got = o[h + 8:h + 12] if o[h:h + 4] == b'LIST' else o[h:h + 4]
            assert got == tag and struct.unpack_from('<I', o, h + 4)[0] == sz, ('색인 불일치', q)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(out)
    return len(d), len(out)


def one(job):
    nm, cues, discs, last = job
    try:
        src = src_of(nm, discs); t0 = time.time()
        fs, st = burn(src, cues, last, log=lambda *a: None)
        dst = os.path.join(OUT, nm + '.AVI')
        a, b = write_avi(src, fs, dst)
        return '%-9s 다시 짠 %d · 자막 뺀 %d · 버퍼 넘김 %d · 범위 밖 %d · %d → %d B (%+.1f%%) · %.0fs' % (
            nm, st['nre'], st['dropped'], st['over'], st['oob'], a, b, (b / a - 1) * 100, time.time() - t0)
    except BaseException as e:
        import traceback
        return '⛔%s %s %s' % (nm, type(e).__name__, traceback.format_exc()[-600:])


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    arg = sys.argv[1]
    if arg == 'check':
        sys.exit(1 if check() else 0)
    mc = movie_cues()
    if arg == 'all':
        names = [a for a in sys.argv[2:] if not a.startswith('--')] or sorted(mc)
        jobs = [(nm, mc[nm][0], mc[nm][1], None) for nm in names]
        jobs.sort(key=lambda j: -os.path.getsize(src_of(j[0], j[2])))
        import multiprocessing as mp
        nproc = int(next((a.split('=')[1] for a in sys.argv if a.startswith('--j=')), '6'))
        with mp.Pool(nproc) as pool:
            for r in pool.imap_unordered(one, jobs):
                print(r, flush=True)
        return
    last = int(sys.argv[2]) if len(sys.argv) > 2 else None
    print(one((arg, mc[arg][0], mc[arg][1], last)))
    os.makedirs(os.path.join(OUT, 'mp4'), exist_ok=True)
    tm1.to_mp4(os.path.join(OUT, arg + '.AVI'), os.path.join(OUT, 'mp4', arg + '.mp4'))


if __name__ == '__main__':
    main()
