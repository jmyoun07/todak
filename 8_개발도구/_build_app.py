# -*- coding: utf-8 -*-
"""
토닥 앱 빌드 — 시안 화면(390×844 고정)을 실기기용(유동 크기)으로 변환

출력: 앱빌드/www/   ← 나중에 Capacitor 의 webDir 로 그대로 쓰는 폴더
  - 화면 전부 — UI 결과물/screens/*.html (2026-09-18 기준 88개)
    (가짜 상태바 제거 · viewport-fit 추가 · 기기 오버라이드 CSS 연결)
  - app.css (원본 그대로) + app-device.css (실기기 오버라이드)
  - index.html (시작 화면 = 01-splash 복사본)

시안 갤러리(overview_260830.html)는 건드리지 않는다 — 둘은 같은 원본의 다른 빌드.
"""
import io, os, re, glob, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 유방암 — 스크립트는 8_개발도구 안(2026-10-01 폴더 정리)
SRC = os.path.join(ROOT, 'UI 결과물', 'screens')
# 안드로이드 빌드가 한글 경로를 거부해서 앱 프로젝트는 영문 경로에 산다
OUT = os.path.join('C:', os.sep, 'Users', 'rudtn', 'todak-app', 'www')

DEVICE_CSS = """/* ═══ 실기기 오버라이드 — app.css 다음에 로드 ═══
   시안은 390×844 고정 프레임이지만 실제 폰은 360~430px 폭에 높이도 제각각이다.
   여기서 프레임을 화면 전체로 늘리고, 노치·펀치홀 안전영역을 처리한다. */

html, body { height: 100%; }

/* 손가락으로 벌려 확대(핀치 줌)되지 않게 — 앱(APK)처럼 화면 틀을 고정한다 (교수님 2026-09-29).
   안드로이드 크롬은 위 viewport 의 user-scalable=no 로 막히고, 아이폰 사파리는 그것을 무시하므로
   여기서 손가락 두 개 동작을 받지 않게 한다. 세로·가로로 미는 것(스크롤)은 그대로 된다.
   글자를 키우시는 분은 휴대폰 '글자 크기' 설정으로 키우실 수 있다(웹앱도 그 설정을 따른다). */
html { touch-action: pan-x pan-y; }

body {
  display: block;               /* 시안의 '가운데 폰 프레임' 정렬 해제 */
  background: var(--surface);
}

.screen {
  width: 100%;
  max-width: none;
  height: 100vh;                /* 구형 웹뷰 폴백 */
  height: 100dvh;               /* 주소창 유무에 따라 변하는 실제 높이 */
  box-shadow: none;
  padding-top: env(safe-area-inset-top);      /* 노치·펀치홀 */
}

/* 가짜 상태바(9:41)는 빌드에서 제거되지만, 혹시 남아도 숨긴다 */
.statusbar { display: none; }

/* 아주 작거나 특이한 비율의 화면에서 내용이 프레임보다 길어지면
   화면 전체를 세로 스크롤시킨다. (일반 화면은 .content 가 안에서 스크롤하므로
   바깥은 넘치지 않아 이 규칙이 발동하지 않는다 — 스플래시처럼 .content 없는
   화면의 안전망) */
.screen { overflow-y: auto; }

/* 다만 .content 가 있는 화면에서는 스크롤 상자를 하나로 둔다.
   위 줄 때문에 모든 화면이 '안에도 밖에도' 스크롤 상자를 갖고 있었다. 바깥 상자는 내릴 게
   없는데도 상자라서, 아이폰이 손가락을 그쪽에 붙이면 아무것도 안 움직이는 일이 생긴다
   (56 복약 시간 설정에서 '스크롤이 안 된다'는 말씀을 들었다).
   :has() 를 아는 브라우저(사파리 15.4+ · 크롬 105+)에서만 걸고, 모르는 옛 웹뷰는 이 묶음을
   통째로 무시해 예전과 같게 움직인다(더 나빠지지 않는다). */
@supports selector(:has(*)) {
  .screen:has(> .content) { overflow: hidden; }
}

/* ── 시안 예시 내용 가리기 (표식 설명은 app.css 쪽 주석 참고) ──
   이 파일은 앱·웹앱 빌드에만 실린다. 그래서 갤러리는 건드리지 않고 여기서만 가린다.
   · data-demo 는 '가리기'다 — 자리는 남겨 두어 배선이 값을 채울 때 칸이 튀지 않는다.
   · data-demo-box(감싸개)·data-demo-off(요소째)는 '없애기'다 — 예시 대화만큼 빈 여백을 남기면 그게 더 이상하다.
   · 배선이 끝내 못 칠한 data-demo 는 features.js 가 내용을 비운다(거짓 숫자가 드러나지 않게). */
[data-demo]     { visibility: hidden; }
[data-demo-box] { display: none; }
[data-demo-off] { display: none; }
[data-app-only] { display: block; }

/* 하단 제스처 바 안전영역 */
.bottomnav {
  height: auto;
  min-height: 76px;
  padding-bottom: calc(14px + env(safe-area-inset-bottom));
}
.footer-actions { padding-bottom: calc(14px + env(safe-area-inset-bottom)); }
.chat-input     { padding-bottom: calc(16px + env(safe-area-inset-bottom)); }

/* ── 넓은 화면(폴드 펼침·태블릿) 대응 ──
   글줄이 무한정 길어지면 읽기 어렵다. 본문·하단 버튼·입력창·내비를
   모두 480px 기둥으로 모아 가운데 정렬한다. 좁은 폰에서는 발동하지 않는다. */
@media (min-width: 480px) {
  .content { max-width: 480px; margin: 0 auto; width: 100%; }
  .footer-actions, .chat-input {
    left: 0; right: 0; margin: 0 auto; max-width: 480px;
  }
  .bottomnav {
    left: 50%; right: auto; transform: translateX(-50%);
    width: 100%; max-width: 480px;
    border-left: 1px solid var(--outline); border-right: 1px solid var(--outline);
    border-radius: 18px 18px 0 0;
  }
  .callpop { align-items: center; }
  .callpop-card { max-width: 420px; margin: 0 auto; }
}
"""


def rd(p):
    return io.open(p, encoding='utf-8').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)


def build():
    # www 를 통째로 지우지 않는다 — 나중에 추가되는 자산(수파베이스 JS, 폰트,
    # 아이콘, 서비스워커 등)을 보존하고, 이 스크립트가 만든 것만 갱신한다.
    os.makedirs(OUT, exist_ok=True)
    for old in glob.glob(os.path.join(OUT, '*.html')):
        os.remove(old)
    for name in ('app.css', 'app-device.css'):
        q = os.path.join(OUT, name)
        if os.path.exists(q):
            os.remove(q)

    shutil.copy(os.path.join(SRC, 'app.css'), os.path.join(OUT, 'app.css'))
    wr(os.path.join(OUT, 'app-device.css'), DEVICE_CSS)

    # 상태바 안에는 span 만 있고 div 가 없으므로 "첫 </div>" 까지만 지운다.
    # (09·39·94·95 처럼 파일이 한 줄로 붙어 있으면 \n 까지 요구할 때 화면 절반이 삼켜진다)
    stat_re = re.compile(r'[ \t]*<div class="statusbar[^"]*">.*?</div>[ \t]*\n?', re.S)
    n = 0
    for p in sorted(glob.glob(os.path.join(SRC, '*.html'))):
        s = rd(p)
        # 1) 가짜 상태바 제거 (모든 화면에서 한 줄짜리)
        s, cnt = stat_re.subn('', s, count=1)
        # 2) 안전영역(env)이 iOS 에서 동작하려면 viewport-fit=cover 필요
        s = s.replace('content="width=device-width, initial-scale=1"',
                      'content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover"')
        s = s.replace('</title>', '</title>' + '\n' + '<meta name="color-scheme" content="light">', 1)
        # 3) 기기 오버라이드 CSS 연결
        s = s.replace('<link rel="stylesheet" href="app.css">',
                      '<link rel="stylesheet" href="fonts/noto.css">' + '\n' + '<link rel="stylesheet" href="app.css">' + '\n' + '<link rel="stylesheet" href="app-device.css">')
        # 3.5) PWA 메타 — 아이폰 사파리 '홈 화면에 추가' 시 앱처럼 열리게 (안드로이드 앱에는 무해)
        PWA = ('<link rel="manifest" href="manifest.webmanifest">'
               '<meta name="apple-mobile-web-app-capable" content="yes">'
               '<meta name="mobile-web-app-capable" content="yes">'
               '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
               '<meta name="apple-mobile-web-app-title" content="토닥">'
               '<link rel="apple-touch-icon" href="icon-180.png">'
               '<meta name="theme-color" content="#C43E6B">')
        if '</head>' in s and 'apple-mobile-web-app-capable' not in s:
            s = s.replace('</head>', PWA + '</head>', 1)
        # 3.6) 링크 미리보기 — 카카오톡·문자에 주소를 보내면 뜨는 카드의 제목·설명·그림 (안드로이드 앱에는 무해)
        #      이게 없으면 카카오톡이 화면 속 그림 하나(네이버 로그인 로고)를 집어 가고 설명 자리에 기본 문구를 쓴다.
        #      그림은 절대 주소여야 한다 — 배포 주소가 바뀌면 여기도 바꾼다. 그림은 _make_og_image.py 가 www/og-image.png 로 만든다.
        #      설명은 시작 화면(01) 문구와 같게 둔다.
        OG = ('<meta property="og:type" content="website">'
              '<meta property="og:title" content="토닥">'
              '<meta property="og:description" content="유방암 치료, 곁에서 함께 돌봐요">'
              '<meta property="og:image" content="https://todak-app.netlify.app/og-image.png">'
              '<meta property="og:image:width" content="1200">'
              '<meta property="og:image:height" content="630">')
        if '</head>' in s and 'og:image' not in s:
            s = s.replace('</head>', OG + '</head>', 1)

        # 4) 배선 스크립트 — 시안에는 없고 앱에만 들어간다 (www/js/ 는 이 스크립트가 지우지 않는 보존 자산)
        s = s.replace('</body>',
                      '<script src="js/config.js"></script>' + '\n'
                      '<script src="js/vendor/supabase.js"></script>' + '\n'
                      '<script src="js/app.js"></script>' + '\n'
                      '<script src="js/native.js"></script>' + '\n'
                      '<script src="js/timepick.js"></script>' + '\n'
                      '<script src="js/druginfo.js"></script>' + '\n'
                      '<script src="js/features.js"></script>' + '\n'
                      '<script src="js/more.js"></script>' + '\n'
                      '<script src="js/more2.js"></script>' + '\n'
                      '<script src="js/nearby.js"></script>' + '\n'
                      # AI 상담 색인(_build_kb.py 생성물)은 상담 화면에만 싣는다 — chat.js 보다 먼저
                      + ('<script src="js/kb-index.js"></script>' + '\n' if os.path.basename(p) == '07-chat.html' else '')
                      + '<script src="js/chat.js"></script>' + '\n' + '</body>', 1)
        wr(os.path.join(OUT, os.path.basename(p)), s)
        n += 1

    # Capacitor 진입점
    shutil.copy(os.path.join(OUT, '01-splash.html'), os.path.join(OUT, 'index.html'))

    print('■ 앱 빌드 완료 → 앱빌드/www/')
    print('   화면 %d개 · app.css + app-device.css · index.html' % n)
    left = sum('class="statusbar' in rd(f) for f in glob.glob(os.path.join(OUT, '*.html')))
    print('   상태바 잔여 %d건 (0이어야 정상)' % left)


if __name__ == '__main__':
    build()
    # AI 상담 색인(www/js/kb-index.js)도 화면 원본에서 다시 만든다
    import subprocess, sys
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '_build_kb.py')], check=False)
    # 화면 원본이 바뀌면 시안 갤러리(overview_YYMMDD.html)도 항상 같이 다시 만든다
    import subprocess, sys
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '_build_gallery.py')], check=False)
