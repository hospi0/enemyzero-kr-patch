# -*- coding: utf-8 -*-
r"""0.BIN 에 게임 안 음성 자막 훅 넣기(2026-10-25) → work/build/0.BIN (4장 공통 — 원본 4장 md5 같음)
  tools/subdata.py(자막 자료) + tools/subhook.py(훅) · 넣기 전 tools/test_sub.py 검산 통과해야 함.
  python tools/build_0bin.py"""
import hashlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import subdata as D, subhook as H, test_sub

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if not test_sub.main():
        sys.exit('⛔ 훅 검산 실패 — 0.BIN 안 만듦')
    idx, bits, advs, lists, pages_all, npage = D.build()
    b0 = open(os.path.join(ROOT, 'work', 'disc1', '0.BIN'), 'rb').read()
    s, lab, lay = H.patch_bin(b0, bits, advs, lists)
    os.makedirs(os.path.join(ROOT, 'work', 'build'), exist_ok=True)
    p = os.path.join(ROOT, 'work', 'build', '0.BIN'); open(p, 'wb').write(s)
    print('0.BIN %d → %d B · 블록 0x%08X~0x%08X · md5 %s' % (len(b0), len(s), H.BLOCK, lay['END'], hashlib.md5(s).hexdigest()))
