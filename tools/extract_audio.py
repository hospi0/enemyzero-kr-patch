# -*- coding: utf-8 -*-
r"""받아쓰기용 소리 뽑기(2026-10-25): 4장의 AVI(Duck DK4 ADPCM 22,050 Hz) 소리 트랙 + AIF → work/audio/d<장>_<이름>.wav (16 kHz 모노)
  장끼리 바이트가 같은 파일은 처음 나온 것만(work/audio/_index.tsv 에 장·이름·길이·같은 파일 목록).
  ffmpeg = C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe
  python tools/extract_audio.py"""
import hashlib, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import disc
FF = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe'
OUT = os.path.join(ROOT, 'work', 'audio')


def main():
    os.makedirs(OUT, exist_ok=True); seen = {}; rows = []
    tmp = os.path.join(tempfile.gettempdir(), 'ez_audio_tmp')
    for n in range(4):
        p = disc.bin_path(n); f = open(p, 'rb')
        for nm, l, s in disc.files(p):
            ext = nm.rsplit('.', 1)[-1].upper()
            if ext not in ('AVI', 'AIF'): continue
            head = disc.sec(f, l, 1)
            if ext == 'AVI' and b'auds' not in head: continue
            d = disc.sec(f, l, (s + 2047) // 2048)[:s]; h = hashlib.md5(d).hexdigest()
            name = nm.strip('/')
            if h in seen: seen[h][1].append('d%d' % n); continue
            key = 'd%d_%s' % (n, name.replace('/', '_').rsplit('.', 1)[0])
            src = tmp + '.' + ext.lower(); dst = os.path.join(OUT, key + '.wav')
            if os.path.exists(dst) and os.path.getsize(dst) > 44:           # 이어 돌리기
                seen[h] = (key, ['d%d' % n]); rows.append([key, ext, '%.2f' % ((os.path.getsize(dst) - 44) / 32000), h]); continue
            open(src, 'wb').write(d)
            r = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-vn', '-ac', '1', '-ar', '16000', dst])
            if r.returncode or not os.path.exists(dst): print('실패', key); continue
            sec = (os.path.getsize(dst) - 44) / 32000
            seen[h] = (key, ['d%d' % n]); rows.append([key, ext, '%.2f' % sec, h])
        print('장', n, '누적', len(rows), flush=True)
    with open(os.path.join(OUT, '_index.tsv'), 'w', encoding='utf-8') as w:
        w.write('키\t종류\t초\tmd5\t나오는 장\n')
        for k, e, sec, h in rows: w.write('%s\t%s\t%s\t%s\t%s\n' % (k, e, sec, h, ','.join(seen[h][1])))
    print('소리 %d개 %.0f분' % (len(rows), sum(float(r[2]) for r in rows) / 60))


if __name__ == '__main__':
    main()
