# -*- coding: utf-8 -*-
r"""받아쓰기(2026-10-25, 마리카 tools/asr_prompt.py 를 옮김) — work/audio/*.wav(tools/extract_audio.py) → work/asr/<키>.json
  faster_whisper large-v3 · 일본어 · VAD 켬 + 낱말 시각(2차, 환청 대조·시각 맞춤용) · 등장인물·용어 초기 프롬프트. 이어 돌리기 가능.
  C:\claude\utils\whisper-venv\Scripts\python.exe tools/asr.py"""
import json, os, sys, time, wave
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work', 'audio'); OUT = os.path.join(ROOT, 'work', 'asr_vad')
PROMPT = ('キンバリー、ローラ、マーカス、パーカー、デヴィッド、ジョージ、ロニー、エネミー、ヴィークル・ジ・アキ、AKI、X-GIL、'
          'VEXX、ウィンタータワー、サマータワー、ガン・チャージャー、カード・キィ、ボイスレコーダー、VPS、コールドスリープ。')


def load(p):
    w = wave.open(p, 'rb'); a = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    return a


def main():
    from faster_whisper import WhisperModel
    m = WhisperModel('large-v3', device='cuda', compute_type='float16')
    os.makedirs(OUT, exist_ok=True)
    files = sorted(f for f in os.listdir(SRC) if f.endswith('.wav'))
    t0 = time.time(); done = 0
    for k, f in enumerate(files):
        dst = os.path.join(OUT, f[:-4] + '.json')
        if os.path.exists(dst): continue
        a = load(os.path.join(SRC, f))
        segs, _ = m.transcribe(a, language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=True, initial_prompt=PROMPT, word_timestamps=True)
        segs = [[round(s.start, 2), round(s.end, 2), s.text.strip(), [[round(w.start,2), round(w.end,2), w.word] for w in (s.words or [])]] for s in segs]
        json.dump({'file': f, 'sec': round(len(a) / 16000, 2), 'segs': segs}, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
        done += 1
        if done % 20 == 0: print('%d/%d %.0fs' % (k + 1, len(files), time.time() - t0), flush=True)
    print('끝 %d개 %.0fs' % (done, time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
