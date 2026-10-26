# -*- coding: utf-8 -*-
r"""대사 있는 동영상 AVI 꺼내기(2026-10-25) — data/번역할것/음성자막_*.tsv 의 «동영상» 소리 → 나오는 장마다 work/movie/d<N>/<이름>.AVI
  python tools/get_movies.py"""
import glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc


def wanted():
    w = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', '번역할것', '음성자막_*.tsv'))):
        for l in open(p, encoding='utf-8-sig').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) > 3 and c[2] == '동영상':
                w[c[1].split('_', 1)[1]] = c[3].split(',')
    return w


if __name__ == '__main__':
    w = wanted(); k = 0
    for n in range(4):
        p = disc.bin_path(n); f = open(p, 'rb')
        for nm, l, s in disc.files(p):
            b = nm.strip('/').split('/')[-1]
            if b.upper().endswith('.AVI') and b[:-4] in w:
                q = os.path.join(ROOT, 'work', 'movie', 'd%d' % n, b)
                if os.path.exists(q) and os.path.getsize(q) == s: continue
                os.makedirs(os.path.dirname(q), exist_ok=True)
                open(q, 'wb').write(disc.sec(f, l, (s + 2047) // 2048)[:s]); k += 1
    print(k, '개', sorted(w))
