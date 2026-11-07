# -*- coding: utf-8 -*-
"""아이폰 설치 안내 한 장(카드뉴스) — 왼쪽 칸 위→아래, 다음 오른쪽 칸 위→아래로 읽는 6단계 판.
   사용: python 8_개발도구/_make_ios_guide.py
   재료: 맨 위 폴더의 '토닥 앱 설치 방법(아이폰).png'(교수님 캔바 1차본, 1584×2246)
           → 제목·테두리·캐릭터와 STEP 2~6 아이폰 캡처를 그대로 잘라 쓰고, 단계 글만 새로 쓴다.
         3_안내문서/아이폰_설치_캡처/ — 교수님이 10-22 보낸 화면에서 잘라 둔 것(STEP 1 카톡 링크, STEP 2 주소 입력, 공유 버튼)
   결과: 3_안내문서/토닥 앱 설치 방법(아이폰)_1022.png (같은 1584×2246)
   캡처 크기는 칸 높이에 맞춰 자동으로 줄인다(왼쪽 칸은 아래 테두리, 오른쪽 칸은 캐릭터 위까지).
"""
import os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _svg2png import CHROME
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 유방암
SRC = os.path.join(ROOT, '토닥 앱 설치 방법(아이폰).png')
CAP = os.path.join(ROOT, '3_안내문서', '아이폰_설치_캡처')
OUT = os.path.join(ROOT, '3_안내문서', '토닥 앱 설치 방법(아이폰)_1022.png')
FONT = os.path.join('C:', os.sep, 'Users', 'rudtn', 'todak-app', 'www', 'fonts', 'noto.css')
W, H = 1584, 2246
CREAM = (251, 251, 248, 255)

# 1차본에서 잘라 올 것 (원본 픽셀 좌표)
CROP = {
    'safari': (99, 600, 391, 788),
    'menu':   (548, 767, 898, 1197),      # 뒤에 토닥 시작 화면이 보이게 넓게
    'share':  (1083, 923, 1462, 1193),
    'list':   (115, 1646, 492, 1903),
    'dialog': (625, 1493, 1014, 1796),
    'char':   (1016, 1521, 1538, 2178),     # 오른쪽 끝은 테두리 그림자가 묻어 있어 4px 덜 자른다
}
# 아이폰_설치_캡처 폴더의 그림
FILES = {'kakao': 'STEP1_카톡링크.png', 'addr': 'STEP2_주소입력.png', 'toolbar': 'STEP3_공유버튼_바로보임.png'}


def url(p):
    return 'file:///' + os.path.abspath(p).replace('\\', '/').replace(' ', '%20')


def shot(name, scale, rings=(), plain=False):
    """캡처 한 장 + 누를 곳 분홍 테두리. rings: (x, y, w, h, 둥글기) — 잘라 온 그림의 픽셀 좌표.
       크기는 data-w/h 로 넘기고 실제 크기는 아래 JS 가 칸 높이에 맞춰 정한다(테두리는 % 라 같이 따라간다)."""
    w, h = SIZE[name]
    rs = ''.join('<i class="ring" style="left:%.2f%%;top:%.2f%%;width:%.2f%%;height:%.2f%%;border-radius:%s"></i>'
                 % (x / w * 100, y / h * 100, rw / w * 100, rh / h * 100, r) for x, y, rw, rh, r in rings)
    return ('<div class="shot" data-w="%.0f" data-h="%.0f"><div class="clip%s"><img src="%s.png"></div>%s</div>'
            % (w * scale, h * scale, ' plain' if plain else '', name, rs))


def step(n, cap, *parts):
    return '<section><div class="pill">STEP %d.</div><p class="cap">%s</p>%s</section>' % (n, cap, ''.join(parts))


def tip(text, *parts):
    return '<div class="tip"><p>%s</p>%s</div>' % (text, ''.join(parts))


def page():
    left = [
        step(1, "카카오톡으로 받은 링크를 꾹 눌러<br>‘복사’를 눌러주세요",
             tip('링크를 바로 누르면 카카오톡 안에서 열려서<br>홈 화면에 추가할 수 없어요'),
             shot('kakao', .56)),
        step(2, "Safari 앱을 열고 주소창에 링크를 붙여넣은 뒤<br>파란 ‘이동’ 키를 눌러주세요",
             shot('safari', .5, plain=True),
             shot('addr', .66, [(748, 148, 160, 116, '28px')])),
        step(3, "토닥 화면이 나오면 아래쪽 ‘···’(점 세 개)를<br>누르고 ‘공유’를 눌러주세요",
             shot('menu', 1.0, [(110, 104, 96, 44, '22px')]),
             tip('아래에 공유 버튼이 바로 보이면 그 버튼을 눌러도 돼요',
                 shot('toolbar', .5, [(344, 8, 114, 114, '50%')]))),
    ]
    right = [
        step(4, "‘더 보기’를 눌러주세요", shot('share', 1.1, [(272, 128, 102, 108, '26px')])),
        step(5, "‘홈 화면에 추가’를 눌러주세요", shot('list', 1.1, [(8, 207, 166, 48, '24px')])),
        step(6, "‘웹 앱으로 열기’를 켜고 ‘추가’를 눌러<br>설치를 마쳐주세요",
             shot('dialog', 1.1, [(314, -14, 78, 76, '50%'), (310, 216, 84, 46, '24px')])),
    ]
    return ''.join(left), ''.join(right)


HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<link rel="stylesheet" href="%(font)s">
<style>
html, body { margin: 0; width: %(w)dpx; height: %(h)dpx; overflow: hidden; }
body { position: relative; background: url(base.png) no-repeat 0 0 / %(w)dpx %(h)dpx;
       font-family: 'Noto Sans KR', sans-serif; color: #222; word-break: keep-all; }
.col { position: absolute; top: 326px; width: 672px; }
.col.l { left: 82px; } .col.r { left: 830px; }
.vline { position: absolute; left: 790px; top: 346px; width: 3px; height: 1800px; background: #E4BCC2; }
section + section { margin-top: 28px; padding-top: 28px; border-top: 2px solid #E4BCC2; }
.pill { display: inline-block; height: 50px; line-height: 50px; padding: 0 20px; border-radius: 25px;
        background: #FC768F; color: #fff; font-weight: 700; font-size: 31px; letter-spacing: -.5px; }
.cap { margin: 14px 0 0; font-size: 34px; font-weight: 700; line-height: 1.4; letter-spacing: -1px; }
.tip { margin: 14px 0 0; padding: 14px 22px; border-radius: 18px; background: #FDEDF0; }
.tip p { margin: 0; font-size: 27px; font-weight: 500; line-height: 1.45; color: #5E4A52; letter-spacing: -.6px; }
.tip .shot { margin-top: 12px; }
.shot { position: relative; margin: 20px auto 0; }
.clip { width: 100%%; height: 100%%; overflow: hidden; border-radius: 18px;
        box-shadow: 0 0 0 2px #EFE3E6, 0 8px 22px rgba(158, 46, 84, .10); }
.clip.plain { box-shadow: none; border-radius: 0; }
.clip img { display: block; width: 100%%; height: 100%%; }
.ring { position: absolute; border: 6px solid #F04C78; box-sizing: border-box;
        box-shadow: 0 0 0 3px rgba(255, 255, 255, .85); }
.char { position: absolute; left: 1258px; top: 1872px; height: 334px; }
</style></head><body>
<div class="vline"></div>
<div class="col l" data-limit="2170">%(left)s</div>
<div class="col r" data-limit="1850">%(right)s</div>
<img class="char" src="char.png">
<script>
// 칸마다 캡처를 같은 비율로 줄여 아래 한계(data-limit)를 넘지 않게 한다 — 키우지는 않는다.
// 글꼴이 실린 뒤에 잰다(먼저 재면 대체 글꼴 높이로 재서 너무 줄어든다)
function fit() { document.querySelectorAll('.col').forEach(function (col) {
  var shots = col.querySelectorAll('.shot'), limit = +col.dataset.limit, m = 1;
  for (var i = 0; i < 6; i++) {
    shots.forEach(function (s) { s.style.width = s.dataset.w * m + 'px'; s.style.height = s.dataset.h * m + 'px'; });
    var bottom = col.getBoundingClientRect().bottom, over = bottom - limit;
    if (over <= 0) break;
    var sum = 0; shots.forEach(function (s) { sum += s.dataset.h * m; });
    m = m * (1 - over / sum) - 0.002;
  }
  document.title = (document.title ? document.title + ' ' : '') + col.className + '=' + m.toFixed(3);
}); }
document.fonts.ready.then(function () { window.addEventListener('load', fit); if (document.readyState === 'complete') fit(); });
</script>
</body></html>
"""


def cut_bg(im):
    """캐릭터 둘레의 크림색 바탕만 투명하게 — 가장자리와 이어진 바탕만 지워서 흰 옷·로봇 몸은 남긴다"""
    import numpy as np
    from scipy import ndimage
    a = np.array(im.convert('RGBA')).astype(int)
    near = np.abs(a[..., :3] - np.array(CREAM[:3])).max(-1) < 14
    lab, _ = ndimage.label(near)
    edge_ids = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(edge_ids))
    a[..., 3] = np.where(bg, 0, 255)
    return Image.fromarray(a.astype('uint8'), 'RGBA')


SIZE = {}


def main():
    src = Image.open(SRC).convert('RGBA')
    if src.size != (W, H):
        raise SystemExit('1차본 크기가 다르다: %s' % (src.size,))
    tmp = tempfile.mkdtemp(prefix='iosguide_')
    for k, b in CROP.items():
        c = src.crop(b)
        if k == 'char':
            c = cut_bg(c)
        c.save(os.path.join(tmp, k + '.png')); SIZE[k] = c.size
    for k, f in FILES.items():
        c = Image.open(os.path.join(CAP, f)).convert('RGB')
        c.save(os.path.join(tmp, k + '.png')); SIZE[k] = c.size
    # 바탕: 제목·고리·테두리는 그대로, 안쪽은 크림색으로 비운다 (아래 둥근 모서리는 건드리지 않게 두 번에 나눠)
    base = src.copy()
    d = ImageDraw.Draw(base)
    d.rectangle((34, 300, 1542, 2150), fill=CREAM)
    d.rectangle((90, 2150, 1490, 2204), fill=CREAM)
    # 1차본 로봇의 하트가 오른쪽 테두리에 걸쳐 있었다 — 그 줄만 깨끗한 줄(1200)의 테두리로 덮는다
    edge = src.crop((1540, 1200, W, 1201))
    for y in range(1660, 1760):
        base.paste(edge, (1540, y))
    base.save(os.path.join(tmp, 'base.png'))
    left, right = page()
    pg = os.path.join(tmp, 'guide.html')
    with open(pg, 'w', encoding='utf-8') as f:
        f.write(HTML % {'font': url(FONT), 'w': W, 'h': H, 'left': left, 'right': right})
    png = os.path.join(tmp, 'out.png')
    cmd = [CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
           '--virtual-time-budget=5000', '--user-data-dir=' + tempfile.mkdtemp(prefix='chr_'),
           '--screenshot=' + png, '--window-size=%d,%d' % (W, H), url(pg)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    if not os.path.exists(png):
        raise SystemExit('그리지 못했다: ' + (r.stderr or '')[-800:])
    im = Image.open(png).convert('RGB')
    if im.size != (W, H):
        raise SystemExit('크기가 다르다: %s' % (im.size,))
    im.save(OUT, optimize=True)
    print('ok', OUT, '(작업 폴더 %s)' % tmp)


if __name__ == '__main__':
    main()
