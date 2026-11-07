# -*- coding: utf-8 -*-
"""가변 굵기 획 만들기 (2차·3차 베지어 중심선).
   중심선 점 목록도 함께 돌려주므로 잎맥·음영을 중심선에 맞춰 그릴 수 있다."""
import math


def smooth(t): return t * t * (3 - 2 * t)


def _bez(P):
    """점 2개=직선, 3개=2차, 4개=3차"""
    n = len(P)
    if n == 3:
        def C(t):
            m = 1 - t
            return (m * m * P[0][0] + 2 * m * t * P[1][0] + t * t * P[2][0],
                    m * m * P[0][1] + 2 * m * t * P[1][1] + t * t * P[2][1])
    elif n == 4:
        def C(t):
            m = 1 - t
            return (m**3 * P[0][0] + 3 * m * m * t * P[1][0] + 3 * m * t * t * P[2][0] + t**3 * P[3][0],
                    m**3 * P[0][1] + 3 * m * m * t * P[1][1] + 3 * m * t * t * P[2][1] + t**3 * P[3][1])
    else:
        def C(t):
            return (P[0][0] + (P[-1][0] - P[0][0]) * t, P[0][1] + (P[-1][1] - P[0][1]) * t)
    return C


def stroke(P, W, round_start=True, round_end=False, n=460):
    """중심선 P(점 목록)를 따라 굵기 함수 W(t) 로 그린 형태.
       round_end=False 면 끝이 한 점으로 모인다(잎 끝).
       반환: (path_d, 중심선 점 목록)"""
    C = _bez(P)

    def frame(t):
        x, y = C(t)
        x2, y2 = C(min(1.0, t + 4e-4)); x1, y1 = C(max(0.0, t - 4e-4))
        dx, dy = x2 - x1, y2 - y1
        m = math.hypot(dx, dy) or 1.0
        return (x, y, dx / m, dy / m, -dy / m, dx / m)

    up, dn, mid = [], [], []
    for i in range(n + 1):
        t = i / n
        x, y, tx, ty, nx, ny = frame(t); h = W(t) / 2
        up.append((x + nx * h, y + ny * h)); dn.append((x - nx * h, y - ny * h)); mid.append((x, y))

    def cap(t, sign):
        x, y, tx, ty, nx, ny = frame(t); r = W(t) / 2
        return [(x + (nx * math.cos(th) + tx * math.sin(th) * sign) * r,
                 y + (ny * math.cos(th) + ty * math.sin(th) * sign) * r)
                for th in [math.pi * k / 40 for k in range(1, 40)]]

    pts = list(up)
    pts += cap(1.0, 1) if round_end else []
    pts += list(reversed(dn))
    pts += list(reversed(cap(0.0, -1))) if round_start else []
    d = "M %.2f %.2f " % pts[0] + " ".join("L %.2f %.2f" % p for p in pts[1:]) + " Z"
    return d, mid


def leaf_width(w_stem, w_max, stem_end=0.30, peak=0.62):
    """줄기 굵기로 시작해 가운데에서 가장 넓어졌다가 끝에서 한 점으로 모이는 굵기 함수.
       구간 경계에서 기울기를 0 으로 맞춰 이음새에 각이 생기지 않는다."""
    def W(t):
        if t <= stem_end:
            return w_stem
        if t <= peak:
            return w_stem + (w_max - w_stem) * smooth((t - stem_end) / (peak - stem_end))
        u = (t - peak) / (1 - peak)
        return w_max * (1 - u * u) ** 0.70
    return W


def taper_width(w0, w1):
    return lambda t: w0 + (w1 - w0) * smooth(t)


def bbox(d):
    xs, ys = [], []
    for tok in d.replace("M", " ").replace("L", " ").replace("Z", " ").split():
        pass
    nums = [float(v) for v in d.replace("M", " ").replace("L", " ").replace("Z", " ").split()]
    xs = nums[0::2]; ys = nums[1::2]
    return (min(xs), min(ys), max(xs), max(ys))


def polyline(pts):
    return "M %.2f %.2f " % pts[0] + " ".join("L %.2f %.2f" % p for p in pts[1:])
