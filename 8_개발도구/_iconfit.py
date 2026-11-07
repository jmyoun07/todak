# -*- coding: utf-8 -*-
"""아이콘 마크 자동 맞춤 — 렌더해서 잉크 영역을 재고, 목표 크기·중심에 맞춰 다시 렌더.
   사람이 좌표를 눈대중으로 맞추지 않아도 여백이 일정해진다."""
import os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _svg2png import render, preview
from PIL import Image

SIZE = 1024


def ink_bbox(png, ground_rgb, tol=24):
    """바탕색과 다른 픽셀(=마크)의 경계 상자.
       바탕색 위에 합성하면 둥근 모서리 바깥의 투명부도 바탕색이 되어 자동으로 제외된다."""
    from PIL import ImageChops
    im = Image.open(png).convert("RGBA")
    solid = Image.new("RGBA", im.size, ground_rgb + (255,))
    flat = Image.alpha_composite(solid, im).convert("RGB")
    diff = ImageChops.difference(flat, Image.new("RGB", im.size, ground_rgb)).convert("L")
    return diff.point(lambda v: 255 if v > tol else 0).getbbox()


def hex_rgb(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def fit(head, ground_svg, body, ground_hex, out_png, target=0.60,
        center=(0.5, 0.5), by="max", rounds=2, scratch=None):
    """body 를 목표 비율·중심에 맞춰 배치한 뒤 최종 렌더.
       target: 마크가 아이콘에서 차지할 비율. by='max'|'w'|'h'"""
    scratch = scratch or tempfile.gettempdir()
    tmp_svg = os.path.join(scratch, "_fit.svg")
    tmp_png = os.path.join(scratch, "_fit.png")
    tx, ty, s = 0.0, 0.0, 1.0
    for _ in range(rounds):
        svg = (head + ground_svg
               + '<g transform="translate(%.3f,%.3f) scale(%.5f)">\n%s</g>\n</svg>\n' % (tx, ty, s, body))
        open(tmp_svg, "w", encoding="utf-8").write(svg)
        render(tmp_svg, tmp_png, SIZE)
        bb = ink_bbox(tmp_png, hex_rgb(ground_hex))
        if not bb:
            break
        bw, bh = bb[2] - bb[0], bb[3] - bb[1]
        want = target * SIZE
        k = want / (max(bw, bh) if by == "max" else (bw if by == "w" else bh))
        s *= k
        cx, cy = (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0
        # 스케일은 원점(0,0) 기준이므로 중심 이동량도 함께 보정
        tx = center[0] * SIZE - (cx - tx) * k
        ty = center[1] * SIZE - (cy - ty) * k
    svg = (head + ground_svg
           + '<g transform="translate(%.3f,%.3f) scale(%.5f)">\n%s</g>\n</svg>\n' % (tx, ty, s, body))
    final_svg = os.path.splitext(out_png)[0] + ".svg"
    open(final_svg, "w", encoding="utf-8").write(svg)
    render(final_svg, out_png, SIZE)
    preview(out_png, os.path.splitext(out_png)[0] + "_64.png")
    return out_png, (tx, ty, s)
