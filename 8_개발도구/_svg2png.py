# -*- coding: utf-8 -*-
"""SVG -> PNG 렌더러 (헤드리스 크롬). 앱 아이콘 작업용.
사용:  python _svg2png.py <input.svg> <output.png> [size]
   또는 python _svg2png.py <input.svg> <output.png> 1024 --preview  (64px 확대 미리보기도 같이 저장)
"""
import os, subprocess, sys, tempfile

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def render(svg_path, png_path, size=1024):
    svg_path = os.path.abspath(svg_path); png_path = os.path.abspath(png_path)
    url = "file:///" + svg_path.replace("\\", "/")
    prof = tempfile.mkdtemp(prefix="chr_")
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1", "--default-background-color=00000000",
           "--user-data-dir=" + prof, "--screenshot=" + png_path,
           "--window-size=%d,%d" % (size, size), url]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if not os.path.exists(png_path):
        raise RuntimeError("render failed: " + (r.stderr or "")[-800:])
    return png_path


def preview(png_path, out_path, small=64, blow=320):
    """홈 화면 실제 크기(small px)로 줄였다가 확대 — 작게 보일 때 뭉개지는지 확인용"""
    from PIL import Image
    im = Image.open(png_path).convert("RGBA")
    im.resize((small, small), Image.LANCZOS).resize((blow, blow), Image.NEAREST).save(out_path)
    return out_path


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    size = int(a[2]) if len(a) > 2 else 1024
    render(a[0], a[1], size)
    if "--preview" in sys.argv:
        preview(a[1], os.path.splitext(a[1])[0] + "_64.png")
    print("ok", a[1])
