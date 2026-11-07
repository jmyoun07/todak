# -*- coding: utf-8 -*-
"""아이폰용 웹앱 배포 묶음: todak-app/www 를 그대로 zip 으로 (Netlify Drop / Vercel 에 끌어다 놓기)
   사용: python 8_개발도구/_build_web.py  → 유방암/1_배포파일/토닥_웹배포.zip
   배포 주소: https://todak-app.netlify.app (2026-10-01 부터 새 넷리파이 계정) — 새 zip 은 그 계정 todak-app 프로젝트의
   'Already built it?' 상자(또는 Deploys 점선 네모)에 놓기. 올린 뒤 확인: python todak-app/_qa/verify/t_netlify_site.py todak-app.netlify.app

   화면 캐시(2026-09-28): 웹앱 화면 전환이 0.5~1초 걸리던 것(APK 는 바로) — Netlify 가 모든 파일을 max-age=0 으로 보내
   화면마다 파일 15개 남짓을 서버에 다시 묻기 때문. www/sw.js(틀)의 자리표에 이번 판 번호(VERSION)와
   파일 목록·지문(sha256 앞 16자)을 채워 zip 의 sw.js 로 넣는다. www/sw.js 자체는 틀 그대로 둔다(APK 는 등록하지 않음).
     - 미리 담는 파일: www 의 .html .css .js .webmanifest .png .svg 전부 (sw.js 제외)
     - 글꼴 조각(fonts/*.woff2 124개)은 미리 담지 않는다 — 화면이 쓰는 조각만 그때그때 'todak-fonts' 캐시에 담는다
     - 판 번호는 틀 + 목록의 지문 + _headers·_redirects 지문(HDR)에서 나온다 → 파일이 하나라도 바뀌면 판이 바뀌고,
       아무것도 안 바뀌면 판도 그대로. 머리(보안 헤더 등)만 바꿔도 판이 바뀌고, 그때는 옛 캐시를 옮겨 담지 않고 새로 받는다
     - 지문을 낸 바로 그 바이트를 zip 에 넣는다(파일을 한 번만 읽음) — 묶는 사이 파일이 바뀌어도 지문과 zip 이 어긋나지 않게
     - sw.js 는 배포에서 절대 빼지 않는다: 빠지면 이미 설치된 휴대폰은 새 판도 비상 스위치도 받지 못한다
       (www 폴더를 그대로 올리면 틀 sw.js 가 들어가 캐시가 꺼진다 — 안전하지만 다시 느려진다. 늘 이 zip 을 올린다)
   새 판이 휴대폰에 보이는 때: 올린 뒤 앱을 처음 연 화면은 아직 옛 판 → 뒤에서 바뀐 파일만 받고(보통 몇 초)
   → 그다음 화면 이동부터 새 판. (자세한 규칙은 www/sw.js 머리말)
   검수용: python _build_web.py <www 폴더> <zip 경로>  — 다른 폴더로 시험 묶음을 만든다(평소에는 인자 없이)"""
import os, re, sys, zipfile, json, hashlib
WWW = os.path.join('C:', os.sep, 'Users', 'rudtn', 'todak-app', 'www')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '1_배포파일', '토닥_웹배포.zip')   # 2026-10-01 폴더 정리
if len(sys.argv) > 2:
    WWW, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
vercel = {"cleanUrls": False, "trailingSlash": False,
          "headers": [{"source": "/(.*)", "headers": [{"key": "X-Frame-Options", "value": "DENY"}, {"key": "X-Content-Type-Options", "value": "nosniff"}]},
                      {"source": "/sw.js", "headers": [{"key": "Cache-Control", "value": "no-cache"}]}],
          "rewrites": [{"source": "/", "destination": "/01-splash.html"}],
          "redirects": [{"source": s, "destination": d, "permanent": True} for s, d in [
              ("/29-signup", "/01-splash.html"), ("/29-signup.html", "/01-splash.html"),
              ("/30-login", "/97-email-login.html"), ("/30-login.html", "/97-email-login.html")]]}
# Netlify: 매니페스트 MIME · 서비스워커는 늘 새로 확인(no-cache) · 기본 보안 헤더 · 루트 → 시작 화면
HEADERS = ("/manifest.webmanifest\n  Content-Type: application/manifest+json\n"
           "/sw.js\n  Cache-Control: no-cache\n"
           "/*\n  X-Frame-Options: DENY\n  X-Content-Type-Options: nosniff\n")
# 옛 주소(지금은 없는 29 가입·30 로그인 화면)로 들어오거나 옛 판 화면이 남아 있는 휴대폰은 새 화면으로 보낸다.
# (시작=가입 한 화면인 01, 이메일 로그인 97) — 파일이 없는 주소라 Netlify 가 이 규칙을 그대로 쓴다.
REDIRECTS = ("/  /01-splash.html  200\n"
             "/29-signup  /01-splash.html  301\n"
             "/29-signup.html  /01-splash.html  301\n"
             "/30-login  /97-email-login.html  301\n"
             "/30-login.html  /97-email-login.html  301\n")

PRE_EXT = ('.html', '.css', '.js', '.webmanifest', '.png', '.svg', '.jpg')
# 틀(www/sw.js)의 자리표 — 비워 둔 값 그대로도 올바른 JS 라 틀만 올려도 돈다(= 캐시 끄기)
PH_VERSION, PH_PRECACHE, PH_FONTS, PH_HDR = "/*__VERSION__*/''", '/*__PRECACHE__*/{}', '/*__FONTS__*/{}', "/*__HDR__*/''"


def fp(data):
    return hashlib.sha256(data).hexdigest()[:16]


def all_files():
    out = []
    for root, dirs, files in os.walk(WWW):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(root, f)
            out.append((p, os.path.relpath(p, WWW).replace(os.sep, '/')))
    return out


def build_sw(files, blobs):
    if 'sw.js' not in blobs:
        raise SystemExit('www/sw.js 틀이 없다 — zip 을 만들지 않았다 (sw.js 는 배포에서 절대 빼지 않는다)')
    tpl = blobs['sw.js'].decode('utf-8')
    for ph in (PH_VERSION, PH_PRECACHE, PH_FONTS, PH_HDR):
        if tpl.count(ph) != 1:
            raise SystemExit('www/sw.js 틀에 자리표 %s 가 한 번 있어야 한다 (지금 %d번) — zip 을 만들지 않았다' % (ph, tpl.count(ph)))
    pre, fonts, other, size = {}, {}, [], 0
    for p, rel in files:
        if rel == 'sw.js':
            continue
        low = rel.lower()
        data = blobs[rel]
        if low.startswith('fonts/') and low.endswith('.woff2'):
            fonts[rel] = fp(data)
        elif low.endswith(PRE_EXT):
            pre[rel] = fp(data); size += len(data)
        else:
            other.append(rel)
    js = lambda o: json.dumps(o, sort_keys=True, separators=(',', ':'))
    hdr = fp((HEADERS + REDIRECTS + js(vercel)).encode('utf-8'))
    version = fp((tpl + js(pre) + js(fonts) + hdr).encode('utf-8'))[:10]
    sw = (tpl.replace(PH_VERSION, "'" + version + "'").replace(PH_PRECACHE, js(pre)).replace(PH_FONTS, js(fonts))
          .replace(PH_HDR, "'" + hdr + "'"))
    # 화면이 부르는 우리 파일 중 목록에 없는 것(새 그림 종류 등) — 그 파일만 캐시 없이 서버에서 받는다. 알려만 준다
    miss = set()
    for rel in pre:
        if not rel.endswith('.html'):
            continue
        for ref in re.findall(r'(?:src|href)="([^"]+)"', blobs[rel].decode('utf-8', 'replace')):
            if re.match(r'^(?:[a-zA-Z][a-zA-Z0-9+.\-]*:|//|#)', ref):
                continue
            t = re.split(r'[?#]', ref)[0].lstrip('./')
            if t and t not in pre and t not in fonts and t != 'sw.js':
                miss.add(t)
    return sw, version, pre, fonts, other, size, sorted(miss)


files = all_files()
blobs = dict((rel, open(p, 'rb').read()) for p, rel in files)     # 한 번만 읽는다 — 지문과 zip 이 같은 바이트
sw, version, pre, fonts, other, size, miss = build_sw(files, blobs)
n = 0
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    for p, rel in files:
        if rel == 'sw.js':
            continue
        zi = zipfile.ZipInfo.from_file(p, rel)                  # 날짜·권한만 파일에서, 내용은 읽어 둔 바이트로
        zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, blobs[rel]); n += 1
    z.writestr('sw.js', sw.encode('utf-8')); n += 1           # 틀이 아닌 채운 sw.js
    z.writestr('vercel.json', json.dumps(vercel, ensure_ascii=False, indent=1))
    z.writestr('_headers', HEADERS)
    z.writestr('_redirects', REDIRECTS)
print('웹 배포 묶음 → %s (%d개 파일 + 설정 3)' % (OUT, n))
print('화면 캐시 판(VERSION) %s · 미리 담는 파일 %d개 (%.1f MB) · 글꼴 조각 %d개(쓰는 것만 따로 담음)'
      % (version, len(pre), size / 1048576.0, len(fonts)))
if other:
    print('  캐시하지 않는 파일(서버에서 받음): ' + ', '.join(other[:10]) + (' …' if len(other) > 10 else ''))
if miss:
    print('  ! 화면이 부르지만 www 에 없는 파일: ' + ', '.join(miss[:10]) + (' …' if len(miss) > 10 else ''))
print('  새 판은: 올린 뒤 앱을 처음 연 화면은 아직 옛 판 → 뒤에서 바뀐 파일만 받고 → 다음 화면 이동부터 새 판')
print('  늘 이 zip 을 올린다(www 폴더를 그대로 올리면 캐시가 꺼진다) · sw.js 는 배포에서 절대 빼지 않는다')
