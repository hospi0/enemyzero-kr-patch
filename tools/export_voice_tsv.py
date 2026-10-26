# -*- coding: utf-8 -*-
"""음성 자막 번역 TSV(2026-10-25): work/asr/*.json → data/번역할것/음성자막_NN.tsv (20KB 단위, 자투리 합침)
  열: 번호 · 소리(장_파일) · 종류(AVI 동영상/AIF 게임 안) · 나오는 장 · 시작 · 끝 · 받아쓰기 · 번역 · 메모
  환청(«ご視聴…», 프롬프트 읊기 등)은 뺌."""
import glob, json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAD = re.compile(r'ご視聴|ありがとうございました|チャンネル登録|サマータワー、ガン|ウィンタータワー、サマー|キンバリー、ローラ|字幕|おやすみなさい$|^車内の音声$|^エンディング$')
HEAD = '번호\t소리\t종류\t나오는 장\t시작\t끝\t받아쓰기\t번역\t메모\n'


def main():
    idx = {}
    for l in open(os.path.join(ROOT, 'work', 'audio', '_index.tsv'), encoding='utf-8').read().split('\n')[1:]:
        if l: c = l.split('\t'); idx[c[0]] = c
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'asr', '*.json'))):
        k = os.path.basename(f)[:-5]; j = json.load(open(f, encoding='utf-8'))
        for a, b, t in j['segs']:
            if t and not BAD.search(t): rows.append([k, '동영상' if idx[k][1] == 'AVI' else '게임 안', idx[k][4], '%.2f' % a, '%.2f' % b, t, '', ''])
    out = os.path.join(ROOT, 'data', '번역할것'); files = []; cur = []; size = 0
    for n, r in enumerate(rows, 1):
        line = '%05d\t' % n + '\t'.join(r) + '\n'
        if cur and size + len(line.encode('utf-8')) > 20000: files.append(cur); cur = []; size = 0
        cur.append(line); size += len(line.encode('utf-8'))
    if cur:
        if files and size < 5000: files[-1] += cur
        else: files.append(cur)
    for k, ls in enumerate(files, 1):
        open(os.path.join(out, '음성자막_%02d.tsv' % k), 'w', encoding='utf-8-sig', newline='\n').write(HEAD + ''.join(ls))
    print('음성 자막 %d줄 → %d파일' % (len(rows), len(files)))


if __name__ == '__main__':
    main()
