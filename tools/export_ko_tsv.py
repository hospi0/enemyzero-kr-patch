# -*- coding: utf-8 -*-
r"""번역 확인용 TSV(2026-10-25) — data/번역할것/음성자막_*.tsv 꼴 그대로 «번역» 열을 data/번역/voice_ko.tsv 로, 시작·끝은 voice_time.tsv 로 채워
  data/번역/음성자막_*.tsv 로 씀(제외 줄은 번역 «#제외» + 메모). 빌드는 voice_ko.tsv 를 읽음 — 이 파일은 보기용.
  python tools/export_ko_tsv.py"""
import glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ko = {}
for l in open(os.path.join(ROOT, 'data', '번역', 'voice_ko.tsv'), encoding='utf-8-sig').read().split('\n')[1:]:
    c = l.split('\t')
    if len(c) > 1: ko[c[0]] = (c[1], c[2] if len(c) > 2 else '')
tm = {}
for l in open(os.path.join(ROOT, 'data', '번역', 'voice_time.tsv'), encoding='utf-8').read().split('\n')[1:]:
    c = l.split('\t')
    if len(c) > 2: tm[c[0]] = (c[1], c[2])
for p in sorted(glob.glob(os.path.join(ROOT, 'data', '번역할것', '음성자막_*.tsv'))):
    L = open(p, encoding='utf-8-sig').read().rstrip('\n').split('\n'); out = [L[0]]
    for l in L[1:]:
        c = l.split('\t')
        t, memo = ko[c[0]]
        if c[0] in tm: c[4], c[5] = tm[c[0]]
        c[7] = t; c[8] = '; '.join(x for x in (c[8], memo) if x)
        out.append('\t'.join(c))
    q = os.path.join(ROOT, 'data', '번역', os.path.basename(p)); open(q, 'w', encoding='utf-8-sig').write('\n'.join(out) + '\n')
    print(q, len(out) - 1)
