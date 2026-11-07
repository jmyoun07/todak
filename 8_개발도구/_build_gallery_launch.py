# -*- coding: utf-8 -*-
"""
출시안 갤러리 빌드 — UI 결과물/_출시안_1103 (연구 앱에 들어가지 않는 '출시 방향' 시안)

  python 8_개발도구/_build_gallery_launch.py
  → UI 결과물/_출시안_1103/overview_출시안_YYMMDD.html (이 파일 하나만 주면 열림)

_build_gallery.py 를 같은 틀로 다시 돌린다 — 설정(TODAK_GALLERY_CONF)만 넘긴다.
  · 화면은 _출시안_1103/screens/*.html, 카드 순서·제목은 _출시안_1103/overview.html
  · 공용 app.css 는 연구 앱 원본을 쓰고, 이 묶음 전용 launch.css 를 뒤에 붙인다
  · 화면 파일을 바로 열어 볼 때를 위해 app.css 사본을 screens 안에 맞춰 둔다(원본이 바뀌면 다시 복사)
_build_app.py 는 UI 결과물/screens 만 읽으므로 이 묶음은 연구 앱(www)에 들어가지 않는다.
"""
import os, sys, json, shutil, runpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAUNCH = os.path.join(ROOT, 'UI 결과물', '_출시안_1103')
MAIN_CSS = os.path.join(ROOT, 'UI 결과물', 'screens', 'app.css')

shutil.copyfile(MAIN_CSS, os.path.join(LAUNCH, 'screens', 'app.css'))

conf = {
    'src': LAUNCH,
    'extra_css': 'launch.css',
    'out_prefix': 'overview_출시안_',
    'title': '토닥 출시안 화면 시안',
    'replace': [
        ['<h1>토닥 · 화면 시안</h1>', '<h1>토닥 · 출시안 화면 시안</h1>'],
        ['유방암 치료 중 겪는 부작용을 스스로 살피고, 필요할 때 제때 병원에 연락하도록 돕는 앱입니다.',
         '연구 앱을 실제 유방암 환자용 앱으로 넓힐 때의 방향(2026-11-03)을 화면으로 옮긴 시안입니다. '
         '<b>연구 앱에는 들어가지 않아요.</b> 자가 점검을 컨디션·복약과 섞기, 스트레칭과 AI 코칭, '
         '관리해 주는 병원 찾기, 관리 제품 제휴 네 가지를 담았어요. '
         '화면 안 ‹ 뒤로는 시안이라 한 곳으로 고정했고, 앱에서는 들어온 화면으로 돌아가요.'],
        ['<span>연구용 클릭 시안 · 실제 앱 아님</span>', '<span>출시 방향 시안 · 연구 앱과 별개</span>'],
        ['<span>무료 · 비영리 · 광고 없음</span>', '<span>예시 자료 · 감수 전</span>'],
        ['본 화면은 연구용 시안입니다.', '본 화면은 출시 방향을 보여 주는 시안이며, 동작·문구는 의료진 감수 전입니다.'],
    ],
}
os.environ['TODAK_GALLERY_CONF'] = json.dumps(conf, ensure_ascii=False)
sys.argv = [os.path.join(ROOT, '8_개발도구', '_build_gallery.py')]
runpy.run_path(sys.argv[0], run_name='__main__')
