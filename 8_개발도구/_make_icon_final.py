# -*- coding: utf-8 -*-
"""토닥 아이콘 최종 — 연분홍 바탕 + 새싹 (L2 계열), 하나로 이어진 형태 + 입체감.

고친 점
  1. 줄기와 오른쪽 잎을 '한 획'으로 그린다. 줄기 따로 잎 따로 붙인 이음새가 사라진다.
  2. 왼쪽 잎은 줄기 안쪽에서 시작해 뒤로 지나간다. 밑동이 줄기에 가려져 자연스럽게 갈라져 보인다.
  3. 입체감: 면의 결(그라데이션) + 가장자리 그늘 + 또렷한 잎맥 + 앞 잎 그림자 + 바닥 그림자 + 빛 반사.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _iconfit import fit
from _icon_shape import stroke, leaf_width, bbox, polyline

OUT = r"C:\Users\rudtn\Desktop\claude code\유방암\5_디자인\로고"   # 2026-10-01 폴더 정리
TMP = (r"C:\Users\rudtn\AppData\Local\Temp\claude"
       r"\C--Users-rudtn-Desktop-claude-code----\2012c286-f98a-4c68-9239-1f67d34a9ea1\scratchpad")

# ── 팔레트 ──────────────────────────────────────────────
BG_HI, BG_LO = "#FFF7FB", "#FCE2EE"      # 연분홍 바탕 (위가 밝다)
R_HI, R_LO = "#FB689B", "#AB2156"        # 앞 잎·줄기 로즈 (빛 / 그늘)
P_HI, P_LO = "#FFBDD7", "#E85D8D"        # 뒤 잎 핑크 (빛 / 그늘)
SHADE = "#B81E5E"                        # 그늘·그림자 색 (채도를 살려 탁해지지 않게)

# ── 형태 ────────────────────────────────────────────────
MAIN, MAIN_MID = stroke([(512, 838), (506, 706), (598, 552), (714, 316)],
                        leaf_width(58, 226, stem_end=0.30, peak=0.66), round_start=True)
LEFT, LEFT_MID = stroke([(508, 744), (386, 630), (300, 398)],
                        leaf_width(38, 188, stem_end=0.04, peak=0.56), round_start=True)

NL = "\n"


def grad(gid, d, c_hi, c_lo):
    """면의 결. 빛은 왼쪽 위에서 온다."""
    x0, y0, x1, y1 = bbox(d)
    return ('<linearGradient id="%s" gradientUnits="userSpaceOnUse" '
            'x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f">'
            '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/>'
            '</linearGradient>' + NL) % (gid, x0, y0, x1, y1, c_hi, c_lo)


def rim(path_d, width, opacity):
    """잎 안쪽 가장자리에 지는 그늘 — 면이 둥글게 말려 보이게 한다."""
    return ('<path fill="none" stroke="%s" stroke-width="%d" opacity="%.2f" '
            'filter="url(#rim)" d="%s"/>' + NL) % (SHADE, width, opacity, path_d)


def band(mid, width, opacity, dx, dy, flt):
    """중심선을 따라가는 그늘. flt='soft' 면 넓은 결, 'crease' 면 또렷한 잎맥."""
    return ('<g opacity="%.2f" filter="url(#%s)" transform="translate(%d,%d)">'
            '<path fill="none" stroke="%s" stroke-width="%d" stroke-linecap="round" d="%s"/>'
            '</g>' + NL) % (opacity, flt, dx, dy, SHADE, width, polyline(mid[16:-36]))


def spec(cx, cy, rx, ry, rot, opacity):
    """빛 반사 — 잎 윗면이 부풀어 보이게 한다."""
    return ('<ellipse cx="%d" cy="%d" rx="%d" ry="%d" fill="#FFFFFF" opacity="%.2f" '
            'filter="url(#glow)" transform="rotate(%d %d %d)"/>' + NL) % (
        cx, cy, rx, ry, opacity, rot, cx, cy)


DEFS = ('<defs>' + NL
        + '<clipPath id="icon"><rect width="1024" height="1024" rx="230"/></clipPath>' + NL
        + '<clipPath id="cLeft"><path d="%s"/></clipPath>' % LEFT + NL
        + '<clipPath id="cMain"><path d="%s"/></clipPath>' % MAIN + NL
        + '<filter id="soft" x="-60%" y="-60%" width="220%" height="220%">'
          '<feGaussianBlur stdDeviation="22"/></filter>' + NL
        + '<filter id="crease" x="-60%" y="-60%" width="220%" height="220%">'
          '<feGaussianBlur stdDeviation="7"/></filter>' + NL
        + '<filter id="rim" x="-60%" y="-60%" width="220%" height="220%">'
          '<feGaussianBlur stdDeviation="26"/></filter>' + NL
        + '<filter id="mid" x="-60%" y="-60%" width="220%" height="220%">'
          '<feGaussianBlur stdDeviation="14"/></filter>' + NL
        + '<filter id="drop" x="-60%" y="-60%" width="220%" height="220%">'
          '<feGaussianBlur stdDeviation="12"/></filter>' + NL
        + '<filter id="glow" x="-60%" y="-60%" width="220%" height="220%">'
          '<feGaussianBlur stdDeviation="44"/></filter>' + NL
        + '<linearGradient id="bg" gradientUnits="userSpaceOnUse" x1="120" y1="60" x2="900" y2="1000">'
          '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
          % (BG_HI, BG_LO) + NL
        + grad("gL", LEFT, P_HI, P_LO) + grad("gM", MAIN, R_HI, R_LO)
        + '</defs>' + NL)

def make_body(k=1.0):
    """k 는 음영의 세기. 1.0 이 기본, 값을 키우면 더 깊게 파인다."""
    def o(v):
        return min(0.95, v * k)
    return (
        # 바닥 그림자
        '<g opacity="%.2f" filter="url(#drop)" transform="translate(-4,14)">'
        '<path fill="%s" d="%s"/><path fill="%s" d="%s"/></g>'
        % (o(0.16), SHADE, LEFT, SHADE, MAIN) + NL
        # ── 뒤 잎 ──
        + '<path fill="url(#gL)" d="%s"/>' % LEFT + NL
        + '<g clip-path="url(#cLeft)">'
        + rim(LEFT, 78, o(0.20))
        + band(LEFT_MID, 52, o(0.15), 16, 14, "soft")
        + band(LEFT_MID, 14, o(0.40), 5, 5, "crease")
        + spec(348, 452, 86, 138, -32, 0.26)
        + '</g>' + NL
        # 앞(줄기+오른쪽 잎)이 뒤 잎에 드리우는 그림자
        + '<g clip-path="url(#cLeft)"><g opacity="%.2f" filter="url(#mid)" transform="translate(-18,22)">'
          '<path fill="%s" d="%s"/></g></g>' % (o(0.55), SHADE, MAIN) + NL
        # ── 앞 잎 + 줄기 (한 획) ──
        + '<path fill="url(#gM)" d="%s"/>' % MAIN + NL
        + '<g clip-path="url(#cMain)">'
        + rim(MAIN, 88, o(0.18))
        + band(MAIN_MID, 60, o(0.14), 18, 16, "soft")
        + band(MAIN_MID, 16, o(0.38), 6, 6, "crease")
        + spec(626, 376, 112, 182, 24, 0.30)
        + '</g>' + NL
    )


BODY = make_body(1.0)

HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">' + NL
GROUND = '<rect width="1024" height="1024" rx="230" fill="url(#bg)"/>' + NL


def build(tag, name, body, target=0.70):
    png = os.path.join(OUT, "후보%s_%s.png" % (tag, name))
    fit(HEAD + DEFS, GROUND, '<g clip-path="url(#icon)">' + NL + body + '</g>' + NL,
        BG_HI, png, target=target, by="max", scratch=TMP)
    print(tag, "ok")


if __name__ == "__main__":
    build("N1", "입체_기본", make_body(1.0))
    build("N2", "입체_깊게", make_body(1.55))
