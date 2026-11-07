# -*- coding: utf-8 -*-
"""N1(입체_기본) 아이콘을 앱 전체에 적용 — 안드로이드 런처 + 웹앱(아이폰 홈화면).

만드는 것
  1) 안드로이드 legacy 아이콘  mipmap-*/ic_launcher.png, ic_launcher_round.png
  2) 안드로이드 적응형 아이콘  mipmap-*/ic_launcher_foreground.png (새싹만, 투명 배경)
                              drawable/ic_launcher_bg.xml (연분홍 그라데이션 바탕)
  3) 웹앱 아이콘               www/icon-180.png, icon-192.png, icon-512.png

적응형 아이콘은 바깥 1/4 이 런처 모양(원·둥근사각)에 따라 잘려나가므로,
새싹은 안전영역(108dp 중 가운데 66dp) 안에 들어가게 작게 배치한다.
"""
import os, sys, shutil, tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from PIL import Image, ImageDraw
from _svg2png import render
from _iconfit import fit
import _make_icon_final as M

SRC_SVG = os.path.join(os.path.dirname(ROOT), "5_디자인", "로고", "후보N1_입체_기본.svg")   # 2026-10-01 폴더 정리
RES = os.path.join("C:", os.sep, "Users", "rudtn", "todak-app", "android", "app", "src", "main", "res")
WWW = os.path.join("C:", os.sep, "Users", "rudtn", "todak-app", "www")
TMP = tempfile.mkdtemp(prefix="icon_")

# 밀도별 배수 — legacy 는 48dp, 적응형 前景은 108dp 기준
DENS = [("mdpi", 1), ("hdpi", 1.5), ("xhdpi", 2), ("xxhdpi", 3), ("xxxhdpi", 4)]


def save(im, path, size):
    im.resize((size, size), Image.LANCZOS).save(path)


def circle_crop(im):
    """원형 런처용 — 둥근사각 타일을 원으로 잘라낸다(모서리 흰 삼각형 방지)."""
    n = im.size[0]
    mask = Image.new("L", (n * 4, n * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, n * 4 - 1, n * 4 - 1), fill=255)
    out = im.copy().convert("RGBA")
    out.putalpha(mask.resize((n, n), Image.LANCZOS))
    return out


# ── 1. 원본 타일 1024 렌더 ────────────────────────────────
tile_png = os.path.join(TMP, "tile.png")
render(SRC_SVG, tile_png, 1024)
tile = Image.open(tile_png).convert("RGBA")
print("타일 렌더 ok")

# ── 2. 새싹만(투명 배경) — 안전영역에 맞춰 축소 ───────────
fg_png = os.path.join(TMP, "fg.png")
fit(M.HEAD + M.DEFS, "", M.make_body(1.0), M.BG_HI, fg_png, target=0.55, by="max", scratch=TMP)
fg = Image.open(fg_png).convert("RGBA")
print("전경 렌더 ok")

# ── 3. 안드로이드 mipmap ──────────────────────────────────
for name, k in DENS:
    d = os.path.join(RES, "mipmap-" + name)
    os.makedirs(d, exist_ok=True)
    save(tile, os.path.join(d, "ic_launcher.png"), int(48 * k))
    save(circle_crop(tile), os.path.join(d, "ic_launcher_round.png"), int(48 * k))
    save(fg, os.path.join(d, "ic_launcher_foreground.png"), int(108 * k))
print("mipmap 5종 ok")

# ── 4. 적응형 바탕 = 연분홍 그라데이션 ────────────────────
bg_xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
          '<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">\n'
          '    <gradient android:type="linear" android:angle="315"\n'
          '        android:startColor="%s" android:endColor="%s"/>\n'
          '</shape>\n' % (M.BG_HI, M.BG_LO))
open(os.path.join(RES, "drawable", "ic_launcher_bg.xml"), "w", encoding="utf-8").write(bg_xml)

adaptive = ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@drawable/ic_launcher_bg"/>\n'
            '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>\n'
            '</adaptive-icon>\n')
for f in ("ic_launcher.xml", "ic_launcher_round.xml"):
    open(os.path.join(RES, "mipmap-anydpi-v26", f), "w", encoding="utf-8").write(adaptive)

# 옛 색 상수도 바탕색에 맞춰 둔다(다른 곳에서 참조할 때 대비)
open(os.path.join(RES, "values", "ic_launcher_background.xml"), "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
    '    <color name="ic_launcher_background">%s</color>\n</resources>\n' % M.BG_LO)
print("적응형 아이콘 ok")

# ── 5. 웹앱(아이폰 홈화면) 아이콘 ─────────────────────────
for size in (180, 192, 512):
    save(tile, os.path.join(WWW, "icon-%d.png" % size), size)
print("웹 아이콘 3종 ok")

# ── 6. 로고 폴더에도 최종본 보관 ──────────────────────────
LOGO = os.path.join(os.path.dirname(ROOT), "5_디자인", "로고")
for size in (1024, 512, 256):
    save(tile, os.path.join(LOGO, "todak_icon_%d.png" % size), size)
print("로고 폴더 보관 ok")
shutil.rmtree(TMP, ignore_errors=True)
