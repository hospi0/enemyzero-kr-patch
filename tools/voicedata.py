# -*- coding: utf-8 -*-
r"""음성 자막 자료 읽기(2026-10-25) — 원문 data/번역할것/음성자막_*.tsv + 번역 data/번역/voice_ko.tsv + 시각 data/번역/voice_time.tsv
  load() → {소리 키: [dict(id, kind, discs, a, b, jp, ko)]} (#제외 줄 뺌, 시각 순)
  squeeze(): 문장부호 뒤 공백 지움(전프로젝트 규칙 — 빌더에서)"""
import glob, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
PUNCT = ',.!?:;)]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥'
BAD = re.compile(r'[ぁ-んァ-ヶ一-龯]')


def squeeze(s):
    return re.sub('([' + re.escape(PUNCT) + ']) +', r'\1', s).strip()


def load():
    src = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', '번역할것', '음성자막_*.tsv'))):
        for l in open(p, encoding='utf-8-sig').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) > 6:
                src[c[0]] = dict(id=c[0], key=c[1], kind=c[2], discs=c[3].split(','), a=float(c[4]), b=float(c[5]), jp=c[6])
    ko = {}
    for l in open(os.path.join(ROOT, 'data', '번역', 'voice_ko.tsv'), encoding='utf-8-sig').read().split('\n')[1:]:
        c = l.split('\t')
        if len(c) > 1 and c[0]:
            ko[c[0]] = c[1]
    tm = {}
    p = os.path.join(ROOT, 'data', '번역', 'voice_time.tsv')
    if os.path.exists(p):
        for l in open(p, encoding='utf-8').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) > 2:
                tm[c[0]] = (float(c[1]), float(c[2]))
    miss = [i for i in src if i not in ko]
    assert not miss, ('번역 없는 줄', miss[:10])
    out = {}
    for i, r in src.items():
        t = ko[i].strip()
        if not t or t.startswith('#'):
            continue
        assert '\\n' not in t and not BAD.search(t), ('번역 줄 이상', i, t)
        r = dict(r); r['ko'] = squeeze(t)
        if i in tm:
            r['a'], r['b'] = tm[i]
        out.setdefault(r['key'], []).append(r)
    for v in out.values():
        v.sort(key=lambda r: (r['a'], r['id']))
    return out


def wrap(text, width, maxw):
    """줄 접기 — 공백과 «문장부호 뒤»에서만 끊는다(부호 뒤 공백은 squeeze 가 지웠으므로). 낱말 하나가 넘치면 실패."""
    toks = []                                   # (앞 구분, 조각)
    for i, w in enumerate(text.split(' ')):
        parts = re.findall('[^' + re.escape(PUNCT) + ']*[' + re.escape(PUNCT) + ']+|[^' + re.escape(PUNCT) + ']+$', w) or [w]
        for j, p in enumerate(parts):
            toks.append((' ' if i and not j else '', p))
    lines = []; cur = ''
    for sep, p in toks:
        cand = (cur + sep + p) if cur else p
        if width(cand) <= maxw:
            cur = cand; continue
        assert width(p) <= maxw, ('낱말이 줄 폭을 넘음', p)
        if cur: lines.append(cur)
        cur = p
    if cur: lines.append(cur)
    return lines
