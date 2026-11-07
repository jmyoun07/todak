# -*- coding: utf-8 -*-
"""링크 미리보기 그림(og:image) — 카카오톡·문자에 주소를 보냈을 때 뜨는 카드의 그림.
   사용: python 8_개발도구/_make_og_image.py
   만드는 것: 5_디자인/로고/배포/토닥_링크미리보기_1200x630.png  +  todak-app/www/og-image.png (웹 배포에 실림)

   - 1200×630: 카카오톡은 가운데를 2:1 로 잘라 보여 주고, 정사각으로 자르는 곳도 있어 로고·이름을 가운데에 세로로 둔다.
   - 그림에는 로고와 이름만 넣는다(설명 문구는 _build_app.py 의 og:description 이 따로 싣는다).
   - 아이콘과 같은 방식(HTML → 헤드리스 크롬)으로 그린다. 글꼴은 앱이 쓰는 www/fonts 의 Noto Sans KR.
"""
import os, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _svg2png import CHROME

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 유방암
WWW = os.path.join('C:', os.sep, 'Users', 'rudtn', 'todak-app', 'www')
LOGO = os.path.join(ROOT, '5_디자인', '로고', '배포', '토닥_로고_1024.png')
OUT = os.path.join(ROOT, '5_디자인', '로고', '배포', '토닥_링크미리보기_1200x630.png')
W, H = 1200, 630


def url(p):
    return 'file:///' + os.path.abspath(p).replace('\\', '/').replace(' ', '%20')


HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<link rel="stylesheet" href="%(font)s">
<style>
html, body { margin: 0; width: %(w)dpx; height: %(h)dpx; overflow: hidden; }
body { display: flex; flex-direction: column; align-items: center; justify-content: center;
       background: linear-gradient(160deg, #FFF7FB 0%%, #FBE1EB 100%%);
       font-family: 'Noto Sans KR', sans-serif; }
img { width: 236px; height: 236px; border-radius: 54px; box-shadow: 0 14px 40px rgba(158, 46, 84, .20); }
div { margin-top: 26px; font-size: 104px; font-weight: 700; letter-spacing: -3px; line-height: 1.1; color: #9E2E54; }
</style></head><body><img src="%(logo)s" alt=""><div>토닥</div></body></html>
"""


def main():
    tmp = tempfile.mkdtemp(prefix='og_')
    page = os.path.join(tmp, 'og.html')
    with open(page, 'w', encoding='utf-8') as f:
        f.write(HTML % {'font': url(os.path.join(WWW, 'fonts', 'noto.css')), 'logo': url(LOGO), 'w': W, 'h': H})
    cmd = [CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
           '--virtual-time-budget=4000',                       # 글꼴(woff2)이 실린 뒤에 찍는다
           '--user-data-dir=' + tempfile.mkdtemp(prefix='chr_'), '--screenshot=' + OUT,
           '--window-size=%d,%d' % (W, H), url(page)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    if not os.path.exists(OUT):
        raise SystemExit('그리지 못했다: ' + (r.stderr or '')[-800:])
    from PIL import Image
    im = Image.open(OUT).convert('RGB')                         # 알파 없이 — 미리보기 카드에는 투명이 필요 없다
    if im.size != (W, H):
        raise SystemExit('크기가 다르다: %s' % (im.size,))
    im.save(OUT, optimize=True)
    shutil.copy(OUT, os.path.join(WWW, 'og-image.png'))
    print('ok', OUT, '→ www/og-image.png', '%d KB' % (os.path.getsize(OUT) // 1024))


if __name__ == '__main__':
    main()
