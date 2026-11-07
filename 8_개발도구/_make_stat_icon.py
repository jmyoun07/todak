# -*- coding: utf-8 -*-
"""알림 상태표시줄 작은 아이콘 만들기 — 앱 아이콘(N1)의 새싹만 딴 흰 실루엣.

왜 흰 실루엣인가
  안드로이드는 상태표시줄에 뜨는 작은 아이콘의 '색'을 모두 버리고 '모양(알파)'만 읽는다.
  그래서 연분홍 바탕 새싹을 그대로 넣으면 바탕까지 칠해져 네모 덩어리가 된다.
  바탕을 빼고 새싹 모양만 남긴 24dp VectorDrawable 을 만든다.

내보내는 곳
  C:\\Users\\rudtn\\todak-app\\android\\app\\src\\main\\res\\drawable\\ic_stat_todak.xml

줄기 굵기
  24dp 안에서 원래 줄기(58)는 머리카락처럼 가늘어진다. 줄기만 88/66 으로 굵혀
  작게 보일 때도 잎 두 장 + 줄기로 읽히게 했다. 더 굵히면(118/92) 잎 사이 틈이 막혀
  덩어리로 보인다 — 미리보기로 세 벌을 견줘 고른 값이다.

쓰는 법
  python _make_stat_icon.py            내보내기
  python _make_stat_icon.py --preview  후보 미리보기 PNG 도 함께 (헤드리스 크롬 필요)
"""
import io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _icon_shape import stroke, leaf_width          # noqa: E402

RES = r"C:\Users\rudtn\todak-app\android\app\src\main\res\drawable\ic_stat_todak.xml"

N = 120          # 중심선 표본 수 (앱 아이콘은 460 — 24dp 에는 이 정도면 남는다)
VIEW = 24.0      # VectorDrawable 뷰포트 (dp)
PAD = 1.0        # 가장자리 여백 (dp)
STEM_MAIN = 88   # 줄기+오른쪽 잎 획의 줄기 굵기 (앱 아이콘은 58)
STEM_LEFT = 66   # 왼쪽 잎 획의 밑동 굵기 (앱 아이콘은 38)


def pts_of(d):
    """stroke() 가 낸 'M x y L x y … Z' 를 점 목록으로 되돌린다"""
    nums = [float(v) for v in d.replace("M", " ").replace("L", " ").replace("Z", " ").split()]
    return list(zip(nums[0::2], nums[1::2]))


def shapes(stem_main=STEM_MAIN, stem_left=STEM_LEFT):
    """앱 아이콘(_make_icon_final.py)과 똑같은 중심선 — 굵기만 바꾼다"""
    m, _ = stroke([(512, 838), (506, 706), (598, 552), (714, 316)],
                  leaf_width(stem_main, 226, stem_end=0.30, peak=0.66), round_start=True, n=N)
    l, _ = stroke([(508, 744), (386, 630), (300, 398)],
                  leaf_width(stem_left, 188, stem_end=0.04, peak=0.56), round_start=True, n=N)
    return [pts_of(m), pts_of(l)]


def rdp(P, eps):
    """Douglas-Peucker — 거의 일직선인 점을 걷어내 파일을 줄인다"""
    if len(P) < 3:
        return P[:]
    ax, ay = P[0]
    bx, by = P[-1]
    dx, dy = bx - ax, by - ay
    n2 = dx * dx + dy * dy
    worst, wi = -1.0, 0
    for i in range(1, len(P) - 1):
        px, py = P[i]
        if n2 == 0:
            dist = ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        else:
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / n2))
            qx, qy = ax + t * dx, ay + t * dy
            dist = ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5
        if dist > worst:
            worst, wi = dist, i
    if worst <= eps:
        return [P[0], P[-1]]
    return rdp(P[:wi + 1], eps)[:-1] + rdp(P[wi:], eps)


def fit(polys):
    """두 모양을 한꺼번에 24dp 안에 넣는다 (비율 유지·가운데)"""
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    s = (VIEW - 2 * PAD) / max(w, h)
    ox = PAD + ((VIEW - 2 * PAD) - w * s) / 2 - min(xs) * s
    oy = PAD + ((VIEW - 2 * PAD) - h * s) / 2 - min(ys) * s
    return [[(p[0] * s + ox, p[1] * s + oy) for p in poly] for poly in polys]


def d_of(poly):
    return ("M%.3f,%.3f " % poly[0]) + " ".join("L%.3f,%.3f" % p for p in poly[1:]) + " Z"


def build(stem_main=STEM_MAIN, stem_left=STEM_LEFT, eps=0.012):
    return [rdp(poly, eps) for poly in fit(shapes(stem_main, stem_left))]


HEAD = (u'<?xml version="1.0" encoding="utf-8"?>\n'
        u'<!-- 토닥 알림 상태표시줄 아이콘 — 앱 아이콘(연분홍 새싹)의 새싹만 딴 흰 실루엣.\n'
        u'     안드로이드는 이 아이콘의 색을 버리고 모양(알파)만 읽는다. 바탕을 넣으면 네모가 된다.\n'
        u'     _make_stat_icon.py 가 만든다 — 손으로 고치지 말 것. -->\n'
        u'<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
        u'    android:width="24dp"\n'
        u'    android:height="24dp"\n'
        u'    android:viewportWidth="24"\n'
        u'    android:viewportHeight="24">\n')
PATH = u'    <path android:fillColor="#FFFFFFFF" android:pathData="%s"/>\n'


def vector_xml(polys):
    return HEAD + u"".join(PATH % d_of(p) for p in polys) + u'</vector>\n'


def preview_svg(polys, px):
    """상태표시줄 흉내 — 어두운 띠 위에 흰 실루엣을 실제 크기로"""
    body = "".join('<path fill="#fff" d="%s"/>' % d_of(p) for p in polys)
    cell = px + 16
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
            '<rect width="%d" height="%d" fill="#101014"/>'
            '<g transform="translate(8,8) scale(%.5f)">%s</g></svg>'
            % (cell, cell, cell, cell, cell, cell, px / VIEW, body))


if __name__ == "__main__":
    polys = build()
    xml = vector_xml(polys)
    os.makedirs(os.path.dirname(RES), exist_ok=True)
    io.open(RES, "w", encoding="utf-8").write(xml)
    print("ic_stat_todak.xml saved - %d points, %d bytes"
          % (sum(len(p) for p in polys), len(xml.encode("utf-8"))))
    print(RES)
    if "--preview" in sys.argv:
        from _svg2png import render
        out = os.path.join(os.path.dirname(BASE), "5_디자인", "로고", "알림아이콘_미리보기")   # 2026-10-01 폴더 정리
        os.makedirs(out, exist_ok=True)
        for tag, sm, sl in ((u"A_원래굵기", 58, 38), (u"B_쓰는값", STEM_MAIN, STEM_LEFT), (u"C_더굵게", 118, 92)):
            pp = build(sm, sl)
            for px in (24, 36, 48, 72):
                p = os.path.join(out, "%s_%dpx.svg" % (tag, px))
                io.open(p, "w", encoding="utf-8").write(preview_svg(pp, px))
                render(p, p[:-4] + ".png", px + 16)
        print("preview ->", out)
