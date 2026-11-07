# -*- coding: utf-8 -*-
"""확정 아이콘(N1)을 배포에 필요한 모든 규격으로 내보낸다.

만드는 것
  로고/배포/  … 네이버 검수·문서용 (둥근 모서리 PNG, 정사각 PNG, 흰 배경 JPG)
  안드로이드  … mipmap 5개 밀도 x (ic_launcher, ic_launcher_round, foreground, background)
  아이폰      … AppIcon-512@2x.png (1024, 알파 없음)
  웹앱(PWA)   … icon-180 / icon-192 / icon-512

적응형 아이콘(Android 8+) 규격
  전체 캔버스 108dp 중 실제로 보이는 영역은 가운데 72dp.
  그래서 1024 디자인을 72/108 비율로 보고, 캔버스를 1536 으로 잡아 가운데 둔다.
"""
import os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from _svg2png import render
from _iconfit import fit
from _make_icon_final import HEAD, DEFS, make_body, BG_HI, BG_LO

BASE = r"C:\Users\rudtn\Desktop\claude code\유방암"
OUT = os.path.join(BASE, "5_디자인", "로고", "배포")   # 2026-10-01 폴더 정리
TMP = (r"C:\Users\rudtn\AppData\Local\Temp\claude"
       r"\C--Users-rudtn-Desktop-claude-code----\2012c286-f98a-4c68-9239-1f67d34a9ea1\scratchpad")
APP = r"C:\Users\rudtn\todak-app"
RES = os.path.join(APP, "android", "app", "src", "main", "res")
os.makedirs(OUT, exist_ok=True)

BODY = make_body(1.0)
NL = "\n"

# ── 확정본과 똑같은 배치를 쓰기 위해 맞춤 변환을 한 번 구한다 ──
_, (TX, TY, SC) = fit(HEAD + DEFS,
                      '<rect width="1024" height="1024" rx="230" fill="url(#bg)"/>' + NL,
                      '<g clip-path="url(#icon)">' + NL + BODY + '</g>' + NL,
                      BG_HI, os.path.join(TMP, "_n1_base.png"), target=0.70, by="max", scratch=TMP)
MARK = '<g transform="translate(%.3f,%.3f) scale(%.5f)">%s</g>' % (TX, TY, SC, BODY)


def svg_round():
    return (HEAD + DEFS + '<rect width="1024" height="1024" rx="230" fill="url(#bg)"/>' + NL
            + '<g clip-path="url(#icon)">' + MARK + '</g>' + NL + '</svg>' + NL)


def svg_square():
    """모서리를 깎지 않은 정사각 — 스토어·검수·아이폰용 (마스킹은 OS 가 한다)"""
    return (HEAD + DEFS + '<rect width="1024" height="1024" fill="url(#bg)"/>' + NL
            + MARK + NL + '</svg>' + NL)


BIG = ('<svg xmlns="http://www.w3.org/2000/svg" width="1536" height="1536" '
       'viewBox="-256 -256 1536 1536">' + NL)


def svg_adaptive_bg():
    return (BIG + DEFS + '<rect x="-256" y="-256" width="1536" height="1536" fill="url(#bg)"/>' + NL
            + '</svg>' + NL)


def svg_adaptive_fg():
    return BIG + DEFS + MARK + NL + '</svg>' + NL


def make(name, svg, size):
    p = os.path.join(TMP, name + ".svg")
    open(p, "w", encoding="utf-8").write(svg)
    png = os.path.join(TMP, name + ".png")
    render(p, png, size)
    return Image.open(png).convert("RGBA")


def save(im, path, size, opaque=False, circle=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = im.resize((size, size), Image.LANCZOS)
    if circle:
        from PIL import ImageDraw
        m = Image.new("L", (size * 4, size * 4), 0)
        ImageDraw.Draw(m).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
        out.putalpha(m.resize((size, size), Image.LANCZOS))
    if opaque:
        bg = Image.new("RGBA", (size, size), (255, 255, 255, 255))
        out = Image.alpha_composite(bg, out).convert("RGB")
    out.save(path)


print("렌더 중…")
ROUND = make("n1_round", svg_round(), 1024)
SQUARE = make("n1_square", svg_square(), 1024)
ADP_BG = make("n1_adp_bg", svg_adaptive_bg(), 1536)
ADP_FG = make("n1_adp_fg", svg_adaptive_fg(), 1536)

# ── 1. 검수·문서용 ────────────────────────────────────────
save(ROUND, os.path.join(OUT, "토닥_로고_1024.png"), 1024)
save(SQUARE, os.path.join(OUT, "토닥_로고_1024_정사각.png"), 1024)
save(SQUARE, os.path.join(OUT, "토닥_로고_512.png"), 512)
save(SQUARE, os.path.join(OUT, "토닥_로고_1024_흰배경.jpg"), 1024, opaque=True)
print("검수용 4개 저장")

# ── 2. 안드로이드 mipmap ─────────────────────────────────
DENS = [("mdpi", 1), ("hdpi", 1.5), ("xhdpi", 2), ("xxhdpi", 3), ("xxxhdpi", 4)]
for d, k in DENS:
    folder = os.path.join(RES, "mipmap-" + d)
    save(ROUND, os.path.join(folder, "ic_launcher.png"), int(48 * k))
    save(SQUARE, os.path.join(folder, "ic_launcher_round.png"), int(48 * k), circle=True)
    save(ADP_FG, os.path.join(folder, "ic_launcher_foreground.png"), int(108 * k))
    save(ADP_BG, os.path.join(folder, "ic_launcher_background.png"), int(108 * k))
print("안드로이드 mipmap 5개 밀도 저장")

# 적응형 아이콘이 배경 그라데이션을 쓰도록 XML 교체
ADAPTIVE = ('<?xml version="1.0" encoding="utf-8"?>' + NL
            + '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">' + NL
            + '    <background android:drawable="@mipmap/ic_launcher_background"/>' + NL
            + '    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>' + NL
            + '</adaptive-icon>' + NL)
for f in ("ic_launcher.xml", "ic_launcher_round.xml"):
    p = os.path.join(RES, "mipmap-anydpi-v26", f)
    if os.path.exists(p):
        open(p, "w", encoding="utf-8").write(ADAPTIVE)
print("적응형 아이콘 XML 갱신")

# ── 3. 아이폰 ────────────────────────────────────────────
IOS = os.path.join(APP, "ios", "App", "App", "Assets.xcassets", "AppIcon.appiconset", "AppIcon-512@2x.png")
if os.path.isdir(os.path.dirname(IOS)):
    save(SQUARE, IOS, 1024, opaque=True)      # iOS 는 알파 채널을 허용하지 않는다
    Image.open(IOS).convert("RGB").save(IOS)
    print("아이폰 AppIcon 저장")

# ── 4. 웹앱(PWA) ────────────────────────────────────────
WWW = os.path.join(APP, "www")
for n, sz in (("icon-180.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)):
    save(SQUARE, os.path.join(WWW, n), sz)
print("웹앱 아이콘 3개 저장")

print("완료")
