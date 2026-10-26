# -*- coding: utf-8 -*-
r"""자막 시각 다시 잡기 (2026-10-25, VIRUS tools/retime.py 방식) — 1차 받아쓰기 시각은 «구간» 시작이라 30초 경계(30.00·60.00…)·앞 무음이 묶임.
  낱말 시각 = work/asr_words(VAD 끔) · work/asr_vad(VAD 켬) — 줄(원문)을 글자 유사도로 낱말 열에 짝짓기(원래 시각 ±40초 안, 순서 유지)
  시작 = 첫 낱말, 끝 = max(마지막 낱말 + 0.4, 시작 + max(1.2, 0.12초×한글 글자)) 이고 다음 줄 시작 − 0.05 를 넘지 않게.
  유사도 < 0.45 면 원래 시각 그대로 + 보고. → data/번역/voice_time.tsv (번호·시작·끝·유사도·출처)
  python tools/retime.py"""
import difflib, glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
norm = lambda s: re.sub(r'[\s　、。！？!?…‥・「」『』（）()，．,.~〜ー\-]', '', s)


def rows():
    src = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', '번역할것', '음성자막_*.tsv'))):
        for l in open(p, encoding='utf-8-sig').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) > 6:
                src[c[0]] = dict(id=c[0], key=c[1], kind=c[2], a=float(c[4]), b=float(c[5]), jp=c[6])
    ko = {}
    for l in open(os.path.join(ROOT, 'data', '번역', 'voice_ko.tsv'), encoding='utf-8-sig').read().split('\n')[1:]:
        c = l.split('\t')
        if len(c) > 1 and c[0]:
            ko[c[0]] = (c[1], c[2] if len(c) > 2 else '')
    return src, ko


def chars_of(key):
    """[(글자, 시작, 끝)] 두 벌(VAD 끔·켬)"""
    out = []
    for d in ('asr_words', 'asr_vad'):
        p = os.path.join(ROOT, 'work', d, key + '.json')
        if not os.path.exists(p):
            out.append([]); continue
        cs = []
        for s in json.load(open(p, encoding='utf-8'))['segs']:
            for w in (s[3] if len(s) > 3 else []):
                for ch in norm(w[2]):
                    cs.append((ch, w[0], w[1]))
        out.append(cs)
    return out


def best(cs, jp, lo, hi, a0):
    """(유사도, (시작, 끝)) — 고를 땐 원래 시각에서 먼 곳을 깎는다(짧은 이름 «ローラ» 가 뒤 줄 속 같은 낱말에 붙지 않게)"""
    t = norm(jp); n = len(t)
    if not n or not cs:
        return 0, None, -9
    sm = difflib.SequenceMatcher(None, '', t, autojunk=False)
    bst = (0, None, -9)
    idx = [i for i, c in enumerate(cs) if lo <= c[1] <= hi]
    for i in idx:
        for L in sorted({max(1, int(n * f)) for f in (0.7, 0.85, 1.0, 1.15, 1.3)}):
            if i + L > len(cs):
                continue
            sm.set_seq1(''.join(c[0] for c in cs[i:i + L]))
            r = sm.ratio()
            q = r - 0.006 * abs(cs[i][1] - a0)
            if q > bst[2]:
                bst = (r, (cs[i][1], cs[i + L - 1][2]), q)
    return bst


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src, ko = rows()
    by = {}
    for r in src.values():
        by.setdefault(r['key'], []).append(r)
    out = ['번호\t시작\t끝\t유사도\t출처']; miss = 0
    for key, rs in by.items():
        rs.sort(key=lambda r: (r['a'], r['id']))     # 보충 줄(번호 뒤)도 원래 시각 순으로
        cw = chars_of(key)
        res = []
        floor = 0.0
        for r in rs:
            if ko.get(r['id'], ('#제외',))[0].startswith('#'):
                continue
            cand = []
            for nm, cs in zip(('끔', '켬'), cw):
                sc, ab, q = best(cs, r['jp'], max(floor - 0.5, r['a'] - 40), r['b'] + 40, r['a'])
                if ab and ab[0] >= floor - 0.5:
                    cand.append((q, sc, ab, nm))
            q, sc, ab, nm = max(cand, default=(-9, 0, None, '-'))
            if sc < 0.45:
                ab = (r['a'], r['b']); nm = '원래'; miss += 1
                print('  짝 없음 %s %s %.2f %s' % (r['id'], key, sc, r['jp'][:30]))
            res.append([r, ab[0], ab[1], sc, nm])
            floor = ab[0]
        for i, (r, a, b, sc, nm) in enumerate(res):
            nko = len(re.sub(r'[^가-힣]', '', ko[r['id']][0]))
            e = max(b + 0.4, a + max(1.2, 0.12 * nko))
            if i + 1 < len(res):
                e = min(e, res[i + 1][1] - 0.05)
            e = max(e, a + 0.5)
            out.append('%s\t%.2f\t%.2f\t%.2f\t%s' % (r['id'], a, e, sc, nm))
    out = [out[0]] + sorted(out[1:])
    open(os.path.join(ROOT, 'data', '번역', 'voice_time.tsv'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('줄 %d · 짝 없음 %d' % (len(out) - 1, miss))


if __name__ == '__main__':
    main()
