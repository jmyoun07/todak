# -*- coding: utf-8 -*-
"""
토닥 AI 상담 색인(kb-index.js) 생성기

화면 원본(UI 결과물/screens/*.html)과 환자용으로 이미 검토된 앱 자료
(www/js/druginfo.js 의 약 16군, www/js/more2.js 의 SUPP 건강기능식품 12종)에서
검색용 색인을 뽑아 C:/Users/rudtn/todak-app/www/js/kb-index.js (window.TODAK_KB) 로 쓴다.

- 화면을 고치면 _build_app.py 가 끝에 이 스크립트를 불러 색인도 같이 갱신된다.
- 연구 문서(*.md 기준표 등)는 감수 전 항목이 섞여 있어 쓰지 않는다.
- 동의·약관·로그인·설정 같은 화면은 색인에서 뺀다. 앱 사용 안내 화면은 kind='app' 으로만 둔다.
- 검색은 chat.js(클라이언트)가 한다. 여기서는 화면별 {id, 제목, 섹션 제목·발췌, 키워드}만 만든다.
  위험 안내 섹션이 길어 여러 조각이 되면 조각마다 묶음 번호 g·순번 i 를 단다(split_risk 설명 참고).
- 시안의 예시 데이터(가짜 병원·번호·기록 수치·날짜·예시 약)는 색인에 넣지 않는다 (DEMO_RE·APP_DEMO_RE).
- 끝에 두 가지 동기화를 검사해 알린다: 건강기능식품 SUPP(more2.js ↔ chat/index.ts),
  위험신호 판정 red 구간(chat.js ↔ chat/index.ts).

단독 실행: python _build_kb.py
"""
import io, os, re, json, glob, sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 유방암 — 스크립트는 8_개발도구 안(2026-10-01 폴더 정리)
SRC = os.path.join(ROOT, 'UI 결과물', 'screens')
APP = os.path.join('C:', os.sep, 'Users', 'rudtn', 'todak-app')
JS = os.path.join(APP, 'www', 'js')
OUT = os.path.join(JS, 'kb-index.js')
CHAT_FN = os.path.join(APP, 'supabase', 'functions', 'chat', 'index.ts')

# ── 색인에서 빼는 화면: 시작·동의·약관·로그인·계정·설정·대화 자체·예시 전용·위기(배너가 따로 연결) ──
#    27(진료 준비 메모)·85(근처 병원 찾기)는 화면 전체가 시안 예시(다른 사람 이름·가짜 병원·가짜 번호)라 뺀다
#    — 병원 찾기 질문은 91(어디로 가야 할까요)이 받는다 (2026-09-18 점검 #34·#53)
EXCLUDE = {
    '01-splash', '02-consent', '03-profile-type', '04-treatment', '05-home', '07-chat',
    '11-crisis', '13-settings', '14-concerns', '19-tutorial', '20-notifications',
    '21-chat-history', '22-search', '24-privacy-data', '25-terms', '27-share', '28-note-archive',
    '96-email-signup', '97-email-login', '54-med-confirm', '59-med-scan-fail', '72-no-info',
    '74-med-effect-detail', '75-med-effect-none', '81-account-recovery', '82-account-exit',
    '85-nearby-clinic', '87-error-retry', '88-empty-states', '90-report-answer', '92-nearby-list', '93-nearby-fallback',
    # 99 환자 확인 서류(가입 단계 · 진단서 사진 올리기) — 의학 정보가 아니고, AI 상담이 이 화면을 카드로 띄울 일도 없다 (2026-09-28)
    '99-patient-verify',
}

# ── 앱 사용 안내 화면 (의학 정보가 아니라 '어디서 무엇을 하나' 안내) ──
#    이 화면들의 숫자·날짜·약 이름·횟수 줄은 거의 다 시안 예시라 색인에 넣지 않는다 (APP_DEMO_RE)
APP_USE = {
    '06-sideeffects', '10-consult-questions', '12-sources', '16-checkin', '17-selfcare-library',
    '23-notif-settings', '26-help', '53-med-scan', '55-med-today', '56-med-schedule',
    '57-med-missed', '58-med-manual', '70-med-effects', '71-my-drug-cautions', '73-cycle-setup',
    '77-visit-report', '84-care-contacts', '91-nearby-gate', '98-checkin-month',
}
EMERGENCY = {'08-redflag', '48-emergency'}

# ── 카드에 보일 화면 이름 (제목 태그가 너무 일반적인 화면만) ──
#    08 은 '열이 날 때 응급 안내'(발열 전용)로 바뀌어 제목 태그를 그대로 쓴다. 일반 응급 신호는 48(응급 안내)
TITLE = {
    '15-sideeffect-detail': '말초신경병증(손발 저림)',
    '09-food-supplement': '음식·건강기능식품',
    '69-supplement-check': '이거 먹어도 되나요? (건강기능식품 확인)',
}

# ── 환자가 실제로 쓰는 말 → 화면 (검색 키워드). 화면 제목·섹션 제목은 자동으로 들어간다 ──
#    띄어쓰기 없이 적는다(검색이 띄어쓰기를 지우고 비교). 표기 규칙(chat.js 가 해석):
#    '=술'  한 글자 낱말 — 낱말 그 자체(또는 조사만 붙은 꼴)일 때만 ('수술'의 '술' 오인 방지)
#    '~음식' 약한 키워드 — 여러 화면을 아우르는 허브 화면용 (점수 1/3)
#    '머리가*빠' 사이 띄움 — 앞말 뒤 여섯 글자 안에 뒷말('머리가 억수로 빠지는데'·'입맛이 하나도 없어요'). 2026-10-01 검증
KW = {
    '15-sideeffect-detail': ['손발저림', '손발이저', '저려', '저림', '저리', '찌릿', '말초신경', '신경병증', '감각이둔', '감각이없', '손끝', '발끝', '단추', '손발이*저', '손이*저', '발이*저'],
    '31-detail-nausea': ['메스꺼', '울렁', '구토', '토할', '토해', '구역', '오심', '속이안좋', '속이불편', '속이*울렁', '속이*안좋', '속이*메스'],
    '32-detail-hairloss': ['탈모', '머리카락', '머리가빠', '머리털', '머리빠', '가발', '두피', '눈썹', '털이빠', '머리가많이빠', '머리가자꾸빠', '머리가한움큼', '머리가*빠', '머리카락이*빠', '머리털이*빠'],
    '33-detail-fatigue': ['피로', '피곤', '기운이없', '무기력', '지쳐', '나른', '기력', '힘이없', '기운도없', '기운이하나도', '기운이너무없', '기운이전혀', '기운이*없', '힘이*없'],
    '34-detail-arthralgia': ['관절', '관절통', '근육통', '뻣뻣', '마디', '무릎', '쑤셔', '쑤시', '뼈마디', '손가락이아', '관절이*아', '무릎이*아', '손가락이*아'],
    '35-detail-hotflash': ['안면홍조', '홍조', '열감', '화끈', '얼굴이달아', '식은땀', '땀이', '열이확'],
    '36-detail-mucositis': ['구내염', '입안', '입이헐', '헐었', '입병', '혓바늘', '입안통증', '궤양', '가글', '입이아', '입안이*헐', '입이*헐'],
    '37-detail-myelo': ['백혈구', '호중구', '면역', '감염', '발열', '열이나', '열이', '체온', '38도', '37.5', '혈소판', '골수억제', '열나'],
    '38-detail-diarrhea': ['설사', '묽은변', '물똥', '배탈', '장염', '변이묽'],
    '39-detail-skinrad': ['방사선', '방사선피부', '피부가붉', '피부화상', '피부가벗겨'],
    '40-detail-lymphedema': ['림프부종', '팔이붓', '팔부기', '팔이부', '팔이무거', '붓기', '부종', '팔이퉁퉁', '팔이땡땡', '팔이많이부', '수술한쪽팔', '팔이*부', '팔이*붓'],
    '41-detail-cardio': ['심장', '두근', '숨이차', '가슴이두근', '허셉틴', '심장기능', '부정맥'],
    '42-detail-skintgt': ['발진', '여드름', '뾰루지', '피부트러블', '표적치료피부'],
    '43-detail-dryness': ['질건조', '성관계', '부부관계', '성생활', '질분비물', '질이건조'],
    '44-detail-bone': ['골밀도', '골다공증', '뼈가약', '골절', '뼈건강'],
    '45-detail-constipation': ['변비', '변이안나', '변을못', '배변', '대변이딱딱', '변을며칠', '대변을며칠', '대변을못', '화장실을못가', '변이딱딱', '변을*못', '변이*안나'],
    '46-detail-sleep': ['잠이안', '잠을못', '못자', '불면', '수면', '잠들기', '새벽에깨', '자다가깨', '수면제', '잠이', '잠이*안', '잠을*못'],
    '47-detail-anxiety': ['불안', '재발', '걱정', '두려', '무서', '우울', '초조', '마음이힘'],
    '49-detail-cognitive': ['기억력', '깜빡', '건망', '집중이안', '항암브레인', '머리가멍', '케모브레인'],
    '50-detail-taste': ['미각', '쓴맛', '금속맛', '쇠맛', '맛이이상', '맛이변', '냄새', '후각', '맛을못'],
    '51-detail-handfoot': ['수족증후군', '손발이붉', '손바닥', '발바닥', '손발톱', '손톱', '발톱', '손발이벗겨'],
    '52-detail-weight': ['체중', '몸무게', '살이빠', '살이쪄', '살찌', '체중감소', '살이쪘', '살쪘', '살이많이쪘', '살이많이쪄', '살이자꾸쪄', '살이계속쪄', '살이너무쪄', '살이늘', '살이많이빠', '살이너무빠', '살이쭉빠', '살이*쪘', '살이*쪄', '살이*찌', '살이*빠'],
    '60-food-nausea': ['메스꺼', '울렁', '구토', '메스꺼울때음식', '울렁거릴때', '구토할때먹', '메스꺼운데뭐먹', '속이*울렁', '속이*메스'],
    '61-food-appetite': ['식욕부진', '입맛이없', '식욕', '밥맛', '못먹겠', '먹기싫', '입맛없', '=입맛', '입맛도없', '밥이안넘어', '안넘어가', '입맛이떨어', '입맛이*없', '밥맛이*없', '식욕이*없'],
    '62-food-mucositis': ['구내염', '입안', '헐었', '입병', '매운', '자극적', '신음식', '뜨거운음식', '구내염음식', '입안이헐었을때', '김치', '짠음식', '맵고', '매워', '입안이*헐'],
    '63-food-diarrhea': ['설사', '설사할때음식', '설사할때먹', '설사하는데먹'],
    '64-food-constipation': ['변비', '변비음식', '섬유질', '푸룬', '변비에좋'],
    '65-food-taste': ['미각', '맛이이상', '쓴맛', '금속맛', '맛이이상할때', '맛이없어서', '쓴맛이나'],
    '66-food-immune': ['백혈구', '면역', '과일', '생과일', '딸기', '사과', '포도', '수박', '참외', '=귤', '블루베리', '토마토', '바나나', '생채소', '채소', '샐러드', '=회', '초밥', '날것', '날달걀', '반숙', '육회', '위생', '익혀', '배달', '외식', '우유', '치즈', '생굴'],
    '67-food-bone': ['골밀도', '골다공증', '칼슘', '뼈건강', '멸치', '비타민d'],
    '68-food-weight': ['살이쪄', '체중증가', '다이어트', '살빼', '살찌', '살이쪘', '살쪘', '살이많이쪘', '살이많이쪄', '살이자꾸쪄', '살이계속쪄', '살이너무쪄', '살이늘', '살이*쪘', '살이*쪄', '살이*찌'],
    '94-food-soy': ['=콩', '두부', '두유', '된장', '청국장', '이소플라본'],
    '95-food-alcohol': ['=술', '음주', '맥주', '와인', '소주', '막걸리'],
    '09-food-supplement': ['~음식', '~먹어도', '한약', '민간요법', '해독주스', '디톡스', '~고기', '설탕', '자몽', '세인트존스'],
    '69-supplement-check': ['건강기능식품', '건기식', '영양제', '보충제', '홍삼', '인삼', '오메가', '비타민', '유산균', '프로바이오', '밀크씨슬', '커큐민', '강황', '버섯', '흑염소', '녹용', '즙', '멜라토닌'],
    '08-redflag': ['열이나', '열나', '발열', '고열', '미열', '38도', '37.5', '체온', '해열제', '오한'],
    '48-emergency': ['응급', '위험신호', '119', '가슴이아', '숨이차', '의식', '출혈', '피가안멎', '응급실', '병원연락', '병원에연락', '어디로연락', '응급안내'],
    '06-sideeffects': ['부작용목록', '부작용정보', '부작용종류'],
    '10-consult-questions': ['진료질문', '물어볼질문', '질문만들', '질문정리', '뭘물어'],
    '12-sources': ['출처', '근거자료', '자료출처'],
    '16-checkin': ['증상기록', '기록하', '오늘기록', '체크인'],
    '17-selfcare-library': ['자가관리', '관리가이드', '관리방법'],
    '23-notif-settings': ['알림설정', '알림끄', '알림시간', '알림이안'],
    # (2026-10-01 새벽 검증) '상담한 내용이 병원에 자동으로 보내져요?'에 26 을 못 찾아 AI 가 '휴대폰 안에 저장돼요'를 지어냈다
    '26-help': ['도움말', '비밀번호', '사용법', '대화저장', '앱사용', '상담내용', '상담한내용', '대화내용', '누가보나', '누가볼수', '누가봐요',
                '개인정보', '내정보는', '안전한가', '저장되나', '저장돼요', '저장되요', '보내져', '보내지나', '자동으로보내', '자동으로전송',
                '병원에*보내', '병원에*전달', '병원으로*보내', '내용이*보내', '내용이*저장', '내용은*저장', '기록은*누가', '기록을*누가', '내용을*누가'],
    '53-med-scan': ['약봉투', '약사진', '약등록', '처방전사진', '약을등록'],
    # (2026-10-26) 지난 날 체크 고치기·약 순서·드시는 시간(아침·점심) — 사용 의견으로 생긴 기능
    '55-med-today': ['오늘복약', '오늘약', '약먹었', '복약체크', '어제체크', '지난날체크', '체크를못', '못눌렀', '약순서'],
    '56-med-schedule': ['복약시간', '약시간', '약알림', '먹는시간', '약먹는시간', '드시는시간', '복용시간', '복약설정', '아침점심'],
    '57-med-missed': ['약먹기힘', '약드시기힘', '약을깜빡', '약을잊', '약을못먹', '약챙기기'],
    '58-med-manual': ['약직접입력', '약이름입력'],
    '70-med-effects': ['내약부작용', '약부작용', '먹는약부작용', '부작용이뭐', '무슨부작용', '어떤부작용', '부작용알려'],
    '71-my-drug-cautions': ['내약주의', '약주의사항', '같이먹으면안'],
    '73-cycle-setup': ['치료일정', '항암일정', '항암주기', '주사일정', '진료일', '진료날짜', '다음진료', '진료일정', '진료예약', '외래일정', '진료*넣'],
    '77-visit-report': ['진료전리포트', '리포트', '진료준비메모', '보여드릴'],
    '84-care-contacts': ['병원연락처', '담당병원번호', '연락처저장', '병원전화번호', '병원번호', '전화번호저장', '응급실번호'],
    '91-nearby-gate': ['어느과', '무슨과', '어디로가야', '근처병원', '가까운병원', '주변병원', '약국찾', '병원찾'],
    '98-checkin-month': ['한달기록', '기록보기', '지난기록'],
}

# 여러 화면에 똑같이 들어간 줄(열 기준·응급 안내·근거 표기)은 응급 화면에만 남긴다.
DUP_KEEP = {'08-redflag', '48-emergency', '37-detail-myelo'}
DUP_MIN = 4
SEC_MAX = 520        # 섹션 발췌 최대 글자
SCREEN_MAX = 3200    # 화면 하나당 발췌 합계 최대 글자
APP_SCREEN_MAX = 900
# 위험 안내(응급·연락 기준)가 든 섹션은 SEC_MAX 로 자르지 않고 RISK_CHUNK 이하 조각 여러 개로 나눠 모두 싣는다.
#   화면 상한(SCREEN_MAX)에도 걸리지 않는다 — 앞 섹션이 길어져도 맨 끝 '이럴 땐 병원에'가 잘리지 않게.
#   조각 크기는 chat.js 가 발췌 하나를 보낼 때 자르는 길이(SEC_CHARS 420)보다 작게 둔다 — 조각이 통째로 서버에 간다.
#   애매하면 넣는다(빠뜨리는 쪽이 더 나쁘다). 2026-09-19: 42 '이럴 땐 병원에'가 SEC_MAX 에 걸려 끝이 잘렸고,
#   같은 방식으로 08·37·48 의 119·연락 기준 목록이 절반 넘게 잘려 있었다.
#   2026-09-19 3차: chat.js 는 조각을 하나하나 따로 골라 화면마다 1~2개만 보낸다. 가벼운 증상 질문에 🟢 '다음 진료 때' 조각만
#   가고 🔴·🟠 기준이 빠지는 일이 생겨서, 🔴·🟠·🟢 단계가 있는 섹션은 split_risk 로 나눈다(단계 머리말을 첫 줄과 묶고,
#   조각마다 빠진 🔴·🟠 기준 한 줄을 붙인다). 조각에는 묶음 번호 g·순번 i 를 단다.
#   글자 수는 파이썬 기준이다. 조각마다 이모지가 몇 개 들어 JS 길이는 몇 자 더 길다 — 400 이면 420 안에 든다.
RISK_CHUNK = 400
RISK_RE = re.compile(r'🔴|🟠|119|응급|즉시|연락하세요|연락해\s*주세요|병원에\s*연락|병원으로\s*연락|바로\s*병원|바로\s*알리|알리세요|열이\s*나면|발열')
#   RISK_STRONG_RE: 이 표시가 하나도 없이 약한 낱말('바로 알리'·'알리세요'·'즉시'·'열이 나면'·'발열')로만 RISK_RE 에 걸린
#   단계 없는 섹션은 스스로 연락 기준을 싣지 않는다 — 그 조각에는 화면의 🔴·🟠 기준 한 줄을 붙인다 (split_risk ③, 4차)
RISK_STRONG_RE = re.compile(r'🔴|🟠|🟢|119|응급|연락')
# split_risk 가 쓰는 표시들
#   STAGE_RE: 단계 머리말 줄 — 꾸밈으로 쓴 🟠 소제목('🟠 병원 말고도 이어질 곳이 있어요')은 빼려고 행동 낱말이 든 것만 본다
STAGE_RE = re.compile(r'^(🔴|🟠|🟢)(?=.*(119|109|연락|말씀하세요|아니에요|문제예요))')
LEAD_HEAD = '※ 연락 기준 — '
LEAD_MIN, LEAD_MAX = 150, 220     # 조각에 붙이는 기준 한 줄의 글자 수 (둘째 조각부터는 LEAD_MIN 자리를 늘 비워 둔다)
LEAD_SKIP_RE = re.compile(r'^(이럴 땐 전화 말고|📞|🏥|🚑|가벼울 땐|담당 병원이 먼저|이 증상은 담당 병원)|^.{0,30}(›|안내)\s*$')
FEVER_LINE_RE = re.compile(r'^(귀\s*\(고막\)|겨드랑이|입\s*\(구강\))\s*\d')
LEAD_INTRO_RE = re.compile(r'^이때|이런 모습|이렇게 달라|아래 중 하나|아래 두 가지|세 단계로|두 층으로|응급으로 안내되는|응급 경로가')
SUBHEAD_RE = re.compile(r'^(가벼울 땐|이 증상은 담당 병원|이럴 땐 전화 말고)')   # 다음 줄과 떼지 않는 작은 제목 줄

SKIP_CLASSES = {'statusbar', 'bottomnav', 'footer-actions', 'tx-badge', 'appbar', 'chat-input', 'callpop', 'bubble', 'nav-item'}
# 시안의 예시 개인화 문장(특정 회원 상황을 가정한 줄)은 색인에서 뺀다
PERSONAL_RE = re.compile(r'드시고 계시죠|받고 계시죠|입력하셨어요|많이 놀라셨죠|지영|김토닥|드실\s*약은|등록하신\s*약')
# 시안의 예시 데이터 — 모든 화면에서 뺀다: 가짜 병원(○○대학교병원·○○정형외과)·가짜 전화번호(02-0000-0000)·시안 상태 표시(상태 ⓐ)
#   AI 가 '토닥 자료'로 받아 회원 본인 정보나 실제 번호처럼 말하지 않게 (2026-09-18 점검 #34)
DEMO_RE = re.compile(r'○○\s*(대학교|병원|의원|정형|내과|외과|약국|치과|한의원|종합)|\d{2,4}-\d{3,4}-\d{4}|상태\s*[ⓐ-ⓩ]|[ⓐ-ⓩ]\s*·')
# 앱 사용 화면(APP_USE)의 숫자 줄은 거의 다 예시 기록이다 — 날짜·횟수·비율·진행·시각·예시 약 용량·증상별 날수·숫자만 있는 칸.
#   화면이 무엇을 하는지 설명하는 문장만 남긴다 (점검 #54: '관절통 — 13일 중 9일'·'7월 27일(월)'·'저녁에 드실 약은 없어요')
APP_DEMO_RE = re.compile(
    r'\d+\s*월\s*\d+\s*일|\d{4}\s*[.년]\s*\d|\d+\s*/\s*\d+'
    r'|\d+\s*일\s*중\s*\d+|\d+\s*%|\d+\s*회\s*중|\d+\s*회차|\d+\s*주기|\d+\s*일차|D-\d+|\d+\s*일\s*남'
    r'|\d{1,2}:\d{2}'
    r'|\d+\s*(mg|mcg|밀리그램)'
    r'|[가-힣]\d+\s*일'
    r'|^\d+([.,]\d+)?\s*(일|회|분|번|개|시간|주|달)?$'
)
HEAD_CLASSES = {'section-label', 'card-title', 'faq-q'}
BLOCK_TAGS = {'div', 'p', 'li', 'ul', 'ol', 'a', 'section', 'h1', 'h2', 'h3', 'h4', 'br', 'tr', 'label', 'button'}
VOID = {'img', 'br', 'input', 'meta', 'link', 'hr', 'source', 'wbr', 'path', 'circle', 'rect'}


def rd(p):
    return io.open(p, encoding='utf-8').read()


class ScreenParser(HTMLParser):
    """화면 HTML → [('h'|'t', 글)] 흐름 + appbar 제목·부제."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, skip, head, appbar_title, appbar_sub)
        self.items = []
        self.buf = []
        self.head_buf = []
        self.app_title = ''
        self.app_sub = ''
        self.title_tag = ''
        self.in_title = False

    def _flags(self):
        skip = any(s[1] for s in self.stack)
        head = any(s[2] for s in self.stack)
        at = any(s[3] for s in self.stack)
        asub = any(s[4] for s in self.stack)
        return skip, head, at, asub

    def _flush(self):
        t = re.sub(r'[ \t\r\f\v]+', ' ', ''.join(self.buf))
        t = re.sub(r' *\n[\n ]*', '\n', t).strip()   # 블록 경계(줄바꿈)는 살린다
        if t:
            self.items.append(('t', t))
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.in_title = True
        a = dict(attrs)
        cls = set((a.get('class') or '').split())
        style = (a.get('style') or '').replace(' ', '')
        if tag in VOID:
            if tag == 'br':
                self.buf.append(' ')
            return
        hidden = ('hidden' in a or 'display:none' in style) and 'faq-a' not in cls   # 도움말 답은 눌러야 펼쳐질 뿐 내용이다
        # 시안 예시(data-demo·data-demo-box·data-demo-off — 앱에서는 가려지거나 실제 값으로 바뀐다)와 앱이 지우는 칸(data-kb-skip)은 뺀다.
        #   2026-10-01 검증: 56 시안의 예시 약(혈압약·60일분)과 앱에선 지워지는 '다시 알림 — 30분 뒤 한 번 더'가 색인에 들어가
        #   AI 가 없는 기능을 있다고 답했다. 색인에만 넣을 설명은 data-kb-only(앱·갤러리에서는 안 보임)
        demo = any(k in a for k in ('data-demo-box', 'data-demo-off', 'data-kb-skip'))   # data-demo 는 넣는다 — '보통' 기분처럼 실제 선택지에 시안 모양만 붙은 칸이 있다
        skip = bool(cls & SKIP_CLASSES) or tag in ('script', 'style', 'svg') or hidden or demo
        head = bool(cls & HEAD_CLASSES)
        if tag in BLOCK_TAGS:
            if head:
                self._flush()
            else:
                self.buf.append('\n')
        self.stack.append((tag, skip, head, 'appbar-title' in cls, 'appbar-sub' in cls))

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag in VOID:
            return
        # 가장 가까운 같은 태그까지 닫는다 (느슨한 마크업 대비)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                popped = self.stack[i:]
                del self.stack[i:]
                if any(p[2] for p in popped) and not any(s[2] for s in self.stack):
                    h = re.sub(r'\s+', ' ', ''.join(self.head_buf)).strip()
                    if h:
                        self.items.append(('h', h))
                    self.head_buf = []
                break
        if tag in BLOCK_TAGS:
            self.buf.append('\n')

    def handle_data(self, data):
        if self.in_title:
            self.title_tag += data
            return
        skip, head, at, asub = self._flags()
        if at:
            self.app_title += data
        if asub:
            self.app_sub += data
        if skip:
            return
        if head:
            self.head_buf.append(data)
        else:
            self.buf.append(data)

    def close(self):
        super().close()
        self._flush()


def lines_of(text):
    out = []
    for ln in text.split('\n'):
        ln = re.sub(r'\s+', ' ', ln).strip()
        if ln and not re.fullmatch(r'[›‹＋✓●·\-–—]+', ln):
            out.append(ln)
    return out


def norm_line(s):
    return re.sub(r'[^0-9a-z가-힣.]', '', s.lower())


def parse_screen(path):
    p = ScreenParser()
    p.feed(rd(path))
    p.close()
    # 'h'/'t' 흐름을 섹션으로 묶는다. 't' 조각은 줄 단위로 쪼갠다.
    secs = []
    cur = {'h': '', 'lines': []}
    for kind, val in p.items:
        if kind == 'h':
            if cur['lines'] or cur['h']:
                if not cur['lines'] and cur['h']:
                    cur['h'] = cur['h'] + ' · ' + val     # 제목만 연달아 나오면 합친다
                    continue
                secs.append(cur)
            cur = {'h': val, 'lines': []}
        else:
            for ln in val.split('\n'):
                ln = re.sub(r'\s+', ' ', ln).strip()
                if ln:
                    cur['lines'].append(ln)
    if cur['lines'] or cur['h']:
        secs.append(cur)
    # 줄 정리: 이모지·기호만 있는 줄 제거
    for s in secs:
        s['lines'] = [l for l in s['lines'] if re.search(r'[0-9A-Za-z가-힣]', l)]
    title_tag = re.sub(r'^토닥\s*·\s*', '', p.title_tag.strip())
    return {
        'title_tag': title_tag,
        'app_title': re.sub(r'\s+', ' ', p.app_title).strip(),
        'app_sub': re.sub(r'\s+', ' ', p.app_sub).strip(),
        'secs': secs,
    }


def depersonalize(s):
    s = s.replace('지영님이', '회원님이').replace('지영님의', '회원님의').replace('지영님', '회원님')
    return s


def line_pieces(lines, n):
    """줄 목록을 n 자 이하 토막으로. 한 줄이 n 자를 넘으면 문장 끝·목록 사이(' · ')·띄어쓰기 순으로 끊는다.
    '다 ' 는 낱말에 붙은 것만 문장 끝으로 본다 — '국물은 다 마시지 않기'의 '다'(모두)에서 끊으면 '국물은 다'만 남아 뜻이 뒤집힌다."""
    pieces = []
    for l in lines:
        while len(l) > n:
            da = [mm.start() for mm in re.finditer(r'(?<=\S)다 ', l[:n])]
            cut = max(l.rfind('. ', 0, n), l.rfind('요 ', 0, n), da[-1] if da else -1)
            if cut < n // 2:
                cut = l.rfind(' · ', 0, n)
            if cut < n // 2:
                cut = l.rfind(' ', 0, n)
            if cut < n // 2:
                cut = n - 1
            pieces.append(l[:cut + 1].rstrip())
            l = l[cut + 1:].lstrip()
        if l:
            pieces.append(l)
    return pieces


def split_sec(lines, n):
    """줄 목록을 ' / ' 로 이어 n 자 이하 조각들로 나눈다(줄 경계 우선). 한 줄이 n 자를 넘으면 문장 끝·띄어쓰기에서 끊는다."""
    out, cur = [], ''
    for p in line_pieces(lines, n):
        if cur and len(cur) + 3 + len(p) > n:
            out.append(cur)
            cur = p
        else:
            cur = cur + ' / ' + p if cur else p
    if cur:
        out.append(cur)
    return out


def lead_items(lines):
    """🔴·🟠 단계 줄에서 올림 기준만 원문 그대로 뽑는다 → [(보일 글, [이미 들었는지 볼 글…])].
    한 줄에서는 첫 문장의 ' — ' 앞만 쓴다(앞이 '젤로다(카페시타빈)' 같은 짧은 이름표면 첫 문장 전체).
    기준으로 보는 것: '…때'로 끝나거나 '때는'·119·109·응급실이 든 문장, '…도 같은 단계예요'(앞부분만),
    '…면 … 연락·119·알리·신호' 꼴, 끝맺음 없는 목록 줄('처음 겪는 경련'). 설명·버튼·링크 줄과 '이런 모습이면 …' 같은 이끄는 줄은 뺀다.
    열 기준 줄(귀·겨드랑이·입)은 한 항목으로 묶어 둘째 자리에 둔다(자리가 모자라면 뒤 항목부터 덜기 때문).
    (4차 보완) 첫 문장 뒤에 119·109 가 든 문장이 있으면 그 문장도 항목으로 넣는다 — 첫 항목 바로 뒤, 열 기준 앞(덜 때 나중에 빠지게).
      앞의 '…연락하시고,' 마디는 단계 머리말과 겹쳐 뗀다. 52 🟠 줄의 '가슴이 아프거나 가만히 있어도 숨이 찰 때는 119예요'가
      첫 문장만 옮기던 3·4차 기준 한 줄에서 빠져, 부종 질문에 '이럴 땐 병원에' 조각이 못 가면 119 기준이 통째로 빠졌다.
      지금 화면들에서 이 꼴은 52 한 줄뿐이다(DUP 로 빠진 52 🔴 항목은 그대로 — advisor)."""
    items, fever, urgent = [], [], []
    for l in lines:
        if STAGE_RE.match(l) or LEAD_SKIP_RE.search(l):
            continue
        if FEVER_LINE_RE.match(l):
            fever.append(l)
            continue
        first = re.split(r'(?<=[.])\s', l)[0].rstrip('. ')
        s = re.split(r'\s[—–]\s', first)[0]
        label = s != first and len(s) <= 30 and not re.search(r'때$|[요다죠]$', re.sub(r'\s*\([^()]*\)$', '', s))
        if label:
            s = first
        same = s.endswith('도 같은 단계예요')
        s = re.sub(r'도 같은 단계예요$', '', s)
        if LEAD_INTRO_RE.search(s):
            continue
        base = re.sub(r'\s*\([^()]*\)$', '', s)        # 끝의 괄호 덧말은 떼고 본다 ('…날 때 (열이 함께 나면 위 🔴 단계예요)')
        if (label or same or re.search(r'때(예요)?$|때는|119|109|응급실', base)
                or re.search(r'면,?\s.*(연락|119|알리|신호)[^.]{0,8}$', base) or not re.search(r'[요다죠]$', base)):
            items.append((s, [s]))
        for e in re.split(r'(?<=[.])\s', l)[1:]:
            e = e.rstrip('. ')
            if re.search(r'119|109', e) and not LEAD_SKIP_RE.search(e) and not LEAD_INTRO_RE.search(e):
                e = re.sub(r'^[^,]*(연락하시고|알리시고),\s*', '', e)
                urgent.append((e, [e]))
    items = items[:1] + urgent + items[1:]
    if fever:
        items.insert(1 + len(urgent) if items else 0, ('열 ' + '·'.join(fever), fever))
    return items


def make_lead(blocks, have='', limit=None):
    """🔴·🟠 단계의 기준을 한 줄(LEAD)로. have(그 조각에 이미 든 글)에 있는 항목은 뺀다.
    기준 줄이 하나도 없는 단계(여러 화면에 같은 줄이라 DUP 로 빠진 '🔴 지금 바로 119')는 머리말만 둔다 — 화면과 같게.
    limit 을 넘으면 항목이 가장 많은 단계의 끝 항목부터 덜고 '등'을 붙인다. 단계마다 하나씩만 남아도 넘으면
    머리말만 있는 단계부터, 그다음 뒤 단계부터 뺀다. 그래도 넘으면 빈 줄.
    (4차 보완) 덜 차례가 119·109 항목이고, 같은 번호를 단 머리말만 있는 단계('🔴 지금 바로 119')를 빼면 한 줄이 들어가면
    그 머리말을 먼저 뺀다 — 번호는 항목이 전하고, 머리말만으로는 언제 거는지가 없다 (52 도세탁셀 조각)."""
    limit = LEAD_MAX if limit is None else min(limit, LEAD_MAX)
    parts = []
    for mark, bl in blocks:
        if mark in ('🔴', '🟠'):
            items = lead_items(bl[1:])
            its = [t for t, keys in items if not all(k in have for k in keys)]
            if its or (not items and bl[0] not in have):
                parts.append([bl[0], its, False])

    def render(ps):
        return LEAD_HEAD + ' / '.join(h + (': ' + ' · '.join(its) + (' 등' if cut else '') if its else '')
                                      for h, its, cut in ps)
    s = render(parts) if parts else ''
    while parts and len(s) > limit:
        big = max(parts, key=lambda p: len(p[1]))
        bare = [p for p in parts if not p[1]]
        num = re.search(r'119|109', big[1][-1]) if len(big[1]) > 1 else None
        same = [p for p in bare if num and num.group() in p[0]]
        rest = [p for p in parts if p is not same[-1]] if same else []
        if same and len(render(rest)) <= limit:
            parts = rest
        elif len(big[1]) > 1:
            big[1].pop()
            big[2] = True
        elif len(parts) > 1:
            parts.remove(bare[-1] if bare else parts[-1])
        else:
            return ''
        s = render(parts)
    return s


def stage_blocks(lines):
    """줄 목록 → [[단계 표시, [줄…]], …]. 단계 표시(STAGE_RE)가 없는 앞머리는 ''."""
    blocks = []
    for l in lines:
        m = STAGE_RE.match(l)
        if m or not blocks:
            blocks.append([m.group(1) if m else '', [l]])
        else:
            blocks[-1][1].append(l)
    return blocks


def split_risk(lines, n, stage=None):
    """위험 안내 섹션을 n 자 이하 조각으로 나눈다 (2026-09-19 3차).
    chat.js 는 조각을 하나하나 따로 점수 매겨 화면마다 1~2개만 서버로 보낸다. 그래서 가벼운 증상 질문에는 🟢 '다음 진료 때'
    조각만 가고 🔴·🟠 기준이 빠지곤 했다(42 여드름·40 림프부종·34 관절통 등). 그래서
      ① 🔴·🟠·🟢 머리말은 그 단계의 첫 줄과 한 토막으로 묶는다 — 머리말만 앞 조각 끝에 홀로 붙지 않게.
         한 단계가 다음 조각으로 넘어가면 그 조각은 '머리말 (이어서)'로 시작한다.
      ② 조각에 없는 🔴·🟠 기준을 한 줄(LEAD_HEAD …)로 붙인다 — 둘째 조각부터는 맨 앞에, 첫 조각은 자리가 남으면 맨 끝에.
         어느 조각이 뽑혀도 올림 기준이 함께 간다. 문구는 화면에 있는 기준 줄을 그대로 옮긴다(새 문구를 만들지 않음).
         둘째 조각부터는 이 한 줄이 들어갈 자리를 비워 두고 나눈다.
    단계 표시가 없는 섹션은 예전처럼 줄 경계로만 나눈다(split_sec).
      ③ (4차) 그런데 약한 낱말로만 걸린 단계 없는 섹션(RISK_STRONG_RE 없음)은 스스로 연락 기준을 싣지 않으면서 조각 여럿이
         화면 자리(1~2개)를 다 차지해 🔴·🟠 기준을 밀어낸다(52 '부었을 때는 소금부터 줄여요'의 '바로 알리' 3조각이
         '다리가 퉁퉁 부었어요'에서 '이럴 땐 병원에' 🟠 조각을 밀어냄). 부르는 쪽이 그런 섹션에만 stage(같은 화면 단계 섹션
         '이럴 땐 병원에'의 줄)를 넘기고, 그러면 조각마다 그 화면의 🔴·🟠 기준 한 줄을 끝에 붙인다.
         조각을 한 덩어리로 되돌리면 SEC_MAX·chat.js 420자 자르기에 뒤쪽 기준(52 주당 2.3kg)이 다시 잘리므로 나누기는 그대로 둔다.
         강한 표시가 있는 섹션(40 '응급실', 47·51 등)까지 붙이면 관리 문장과 기준 한 줄이 한 조각에 섞여 검색 점수가 바뀐다
         ('가슴이 꽉 조이는 것처럼 아파요'에 40 림프부종이 후보로 새로 뜸) — 그래서 약한 낱말 섹션만.
         (4차 보완) 이 조각들은 build_screens 가 단계 섹션 뒤로 옮겨 싣고 'lw' 표시를 단다. 기준 한 줄에는 🟠 줄 뒤의 119 문장도 든다(lead_items)."""
    if len(' / '.join(lines)) <= n:
        return [' / '.join(lines)]
    blocks = stage_blocks(lines)        # [단계 표시, [줄…]] — 단계 표시가 없는 앞머리는 ''
    if not any(b[0] for b in blocks):
        sb = stage_blocks(stage) if stage else []
        lead = make_lead(sb) if sb else ''
        if not lead:
            return split_sec(lines, n)
        res = []
        for c in split_sec(lines, n - min(len(lead), LEAD_MIN) - 3):
            ld = make_lead(sb, c, n - len(c) - 3)
            res.append(c + ' / ' + ld if ld else c)
        return res
    full = make_lead(blocks)
    room = n - (min(len(full), LEAD_MIN) + 3 if full else 0)   # 둘째 조각부터의 본문 자리 (기준 한 줄은 LEAD_MIN 자 이상 남긴다)
    pieces = []                                     # (단계 번호, 단계 안 순번, 토막)
    for bi, (mark, bl) in enumerate(blocks):
        head = bl[0] if mark else ''
        body = []                                   # 떼면 뜻이 끊기는 줄은 한 토막으로 묶는다
        for l in (bl[1:] if mark else bl):
            particle = re.match(r'^(을|를|으로|로|에서|에|와|과)\s', l)          # 링크 글자가 빠져 조사로 시작하는 줄
            if body and ((SUBHEAD_RE.match(body[-1]) and '/' not in body[-1])     # '가벼울 땐 근처 병원 찾기' + 다음 줄
                         or (FEVER_LINE_RE.match(l) and FEVER_LINE_RE.match(body[-1]))   # 귀·겨드랑이·입 열 기준
                         or particle):
                body[-1] += ' / ' + l
                if particle and len(body) > 1 and len(body[-1].split(' / ')[0]) <= 15:
                    last = body.pop()
                    body[-1] += ' / ' + last        # '…두지 말고 / 심장 관련 안내 / 를 먼저 보세요.'
            else:
                body.append(l)
        top = room - (len(head) + len(' (이어서)') + 3 if head else 0)   # 이어지는 조각에 머리말과 함께 들어갈 크기
        ps = line_pieces(body[:1], top - (len(head) + 3 if head else 0)) + line_pieces(body[1:], top)
        if head:
            ps = [head + ' / ' + ps[0]] + ps[1:] if ps else [head]
        pieces += [(bi, k, p) for k, p in enumerate(ps)]

    def pack(first):
        out, cur = [], ''
        for bi, k, p in pieces:
            lim = first if not out else room
            if cur and len(cur) + 3 + len(p) <= lim:
                cur += ' / ' + p
            else:
                if cur:
                    out.append(cur)
                cur = (blocks[bi][1][0] + ' (이어서) / ' + p) if (k and blocks[bi][0]) else p
        if cur:
            out.append(cur)
        return out
    out = pack(n)
    miss = [bl[0] for mark, bl in blocks if mark in ('🔴', '🟠') and len(out) > 1 and bl[0] not in out[0]]
    if miss and not make_lead(blocks, out[0], n - len(out[0]) - 3):
        out = pack(room)    # 첫 조각에 통째로 빠진 🔴·🟠 단계가 있는데 기준 한 줄을 붙일 자리가 없으면 첫 조각도 자리를 비워 두고 다시 나눈다
    res = []
    for i, c in enumerate(out):
        ld = make_lead(blocks, c, n - len(c) - 3)
        res.append(c if not ld else (c + ' / ' + ld if i == 0 else ld + ' / ' + c))
    return res


def build_screens():
    parsed = {}
    for path in sorted(glob.glob(os.path.join(SRC, '*.html'))):
        sid = os.path.splitext(os.path.basename(path))[0]
        if sid in EXCLUDE:
            continue
        parsed[sid] = parse_screen(path)

    # 여러 화면에 반복되는 줄 세기
    count = {}
    for sid, d in parsed.items():
        seen = set()
        for s in d['secs']:
            for l in s['lines']:
                k = norm_line(l)
                if len(k) >= 12 and k not in seen:
                    seen.add(k)
                    count[k] = count.get(k, 0) + 1

    screens = []
    for sid, d in parsed.items():
        kind = 'emergency' if sid in EMERGENCY else ('app' if sid in APP_USE else ('food' if re.match(r'^(6[0-9]|9[45]|09)-', sid) else 'info'))
        title = TITLE.get(sid) or d['title_tag'] or d['app_title']
        limit = APP_SCREEN_MAX if kind == 'app' else SCREEN_MAX
        total = 0
        full = False         # 화면 상한이 찼으면 위험 안내 섹션만 더 받는다
        grp = 0              # 조각으로 나뉜 섹션의 묶음 번호 (화면 안에서)
        secs = []
        rows = []            # (섹션 제목, 남길 줄) — 먼저 다 거른 뒤 아래에서 싣는다
        for s in d['secs']:
            keep = []
            for l in s['lines']:
                k = norm_line(l)
                if sid not in DUP_KEEP and len(k) >= 12 and count.get(k, 0) >= DUP_MIN:
                    continue
                if l.startswith('근거:') or '의료기기가 아니므로' in l or PERSONAL_RE.search(l) or DEMO_RE.search(l):
                    continue
                if kind == 'app' and APP_DEMO_RE.search(l):
                    continue
                keep.append(depersonalize(l))
            h = re.sub(r'[\s＋›]+$', '', depersonalize(s['h']))
            # 섹션 제목도 예시 데이터면 버린다 ('항암 3주기 · 5일차'·'2026년 7월')
            if PERSONAL_RE.search(h) or DEMO_RE.search(h) or (kind == 'app' and APP_DEMO_RE.search(h)):
                h = ''
            rows.append((h, keep))
        # 이 화면의 🔴·🟠 단계 섹션('이럴 땐 병원에')의 줄 — 약한 낱말로만 걸린 단계 없는 섹션의 조각에 그 기준 한 줄을 붙인다 (split_risk ③)
        stage = next((k for _, k in rows if any(STAGE_RE.match(l) for l in k)), None)
        # (4차 보완) 기준 한 줄을 붙여 나누는 약한 섹션(weak)은 그 단계 섹션 뒤로 옮겨 싣는다.
        #   기준 한 줄이 단계 문구를 그대로 옮겨 적어서, 약한 조각과 '이럴 땐 병원에' 조각이 같은 질문 바이그램을 가져가 점수가 같아지곤 한다.
        #   chat.js 는 점수가 같으면 앞 섹션을 먼저 고르므로(안정 정렬), 앞에 있던 52 소금·36 관리 조각이 단계 조각을 밀어냈다
        #   ('살이 빠져요'에 🟢 '줄 때' 기준 대신 소금 조각 둘, '혀에 백태가 꼈어요'에 칸디다 설명 대신 신맛 사탕 조각).
        #   나누지 않는 짧은 약한 섹션(RISK_CHUNK 이하 — 기준 한 줄이 붙지 않음)과 강한 표시가 있는 섹션은 자리를 옮기지 않는다.
        order, later, seen = [], [], stage is None
        for h, keep in rows:
            x = ' / '.join(keep)
            weak = bool(stage is not None and keep is not stage and len(x) > RISK_CHUNK
                        and RISK_RE.search(h + ' ' + x) and not RISK_STRONG_RE.search(h + ' ' + x))
            if weak and not seen:
                later.append((h, keep, weak))
                continue
            order.append((h, keep, weak))
            if keep is stage:
                seen = True
                order += later
                later = []
        for h, keep, weak in order + later:
            if not keep and not h:
                continue
            x = ' / '.join(keep)
            if x and RISK_RE.search(h + ' ' + x) and (kind != 'app' or (not full and total + len(x) <= limit)):
                # 위험 안내 — 자르지 않고 조각으로 나눠 모두 싣는다 (RISK_RE 설명 참고).
                #   앱 사용 화면은 화면 상한 안에 통째로 들어갈 때만 — 상한 밖은 시안 예시(예시 약 목록 등)라 예전처럼 뺀다
                parts = split_risk(keep, RISK_CHUNK, None if RISK_STRONG_RE.search(h + ' ' + x) else stage)
                for pi, part in enumerate(parts):
                    total += len(part)
                    sec = {'h': h, 'x': part}
                    if len(parts) > 1:
                        sec['g'], sec['i'] = grp, pi     # 같은 섹션 조각의 묶음 번호·순번 (chat.js 가 앞 조각을 함께 보낼 때 쓸 수 있게)
                    if weak and LEAD_HEAD in part:
                        sec['lw'] = 1     # 본문에는 단계가 없고 다른 섹션의 기준 한 줄만 붙은 조각 — chat.js 가 '단계 조각' 자리를 따질 때 빼고 볼 수 있게
                    secs.append(sec)
                grp += 1 if len(parts) > 1 else 0
                continue
            if full:
                continue
            if len(x) > SEC_MAX:
                x = x[:SEC_MAX].rstrip() + '…'
            if not x:
                # 제목만 남은 섹션은 제목만 키워드 역할로 둔다
                secs.append({'h': h, 'x': ''})
                continue
            if total + len(x) > limit:
                room = limit - total
                if room < 80:
                    full = True          # 예전의 break — 뒤에 오는 위험 안내 섹션은 계속 받는다
                    continue
                x = x[:room].rstrip() + '…'
            total += len(x)
            secs.append({'h': h, 'x': x})
        kw = list(KW.get(sid, []))
        screens.append({
            'id': sid, 't': title, 'sub': '' if sid == '08-redflag' else d['app_sub'], 'k': kind, 'kw': kw, 's': secs,
        })
    return screens


STR = r"'((?:[^'\\]|\\.)*)'"


def js_unq(s):
    return s.replace("\\'", "'").replace('\\\\', '\\')


def parse_drugs():
    src = rd(os.path.join(JS, 'druginfo.js'))
    m = re.search(r'var DRUGS = \[(.*?)\n  \];', src, re.S)
    if not m:
        raise SystemExit('druginfo.js 에서 DRUGS 를 찾지 못했어요')
    body = m.group(1)
    chunks = re.split(r'\n    \{\s*\n', '\n' + body)
    drugs = []
    for ch in chunks:
        pm = re.search(r'pat:\s*(/.+/[a-z]*),\s*\n', ch)
        if not pm:
            continue
        cm = re.search(r"cat:\s*" + STR + r",\s*name:\s*" + STR, ch)
        wm = re.search(r"warn:\s*" + STR, ch)
        effects = []
        for em in re.finditer(r"\{\s*n:\s*" + STR + r",\s*d:\s*" + STR + r"(?:,\s*link:\s*" + STR + r")?\s*\}", ch):
            e = {'n': js_unq(em.group(1)), 'd': js_unq(em.group(2))}
            if em.group(3):
                e['link'] = re.sub(r'\.html$', '', js_unq(em.group(3)))
            effects.append(e)
        drugs.append({
            'pat': pm.group(1), 'cat': js_unq(cm.group(1)), 'name': js_unq(cm.group(2)),
            'effects': effects, 'warn': js_unq(wm.group(1)) if wm else '',
        })
    return drugs


def parse_supp(src, label):
    m = re.search(r'(?:var|const) SUPP[^=]*= \[(.*?)\n\s*\];', src, re.S)
    if not m:
        raise SystemExit(label + ' 에서 SUPP 를 찾지 못했어요')
    out = []
    for line in m.group(1).split('\n'):
        pm = re.search(r'pat:\s*(/.+?/[a-z]*),\s*name:\s*' + STR, line)
        if not pm:
            continue
        km = re.search(r'known:\s*' + STR, line)
        lm = re.search(r'lv:\s*' + STR, line)
        out.append({'pat': pm.group(1), 'name': js_unq(pm.group(2)),
                    'lv': js_unq(lm.group(1)) if lm else '', 'known': js_unq(km.group(1)) if km else ''})
    return out


# 위험신호 판정(red:start ~ red:end)은 서버 chat/index.ts 와 앱 chat.js 에 같은 글이 한 벌씩 있다.
# 서버 쪽에만 붙는 타입 표기(: string · : RedRule[] · : Record<string, string> …)와 들여쓰기를 지우고 비교한다.
RED_TYPE_RE = re.compile(r':\s*(string|boolean|number|RegExp|RegExpExecArray|RedRule|RedWhy)(\[\])?(\s*\|\s*null)?(?=\s*[,)={;])')


def red_block(src):
    a = src.find('/* ── red:start ──')
    b = src.find('/* ── red:end ── */')
    if a < 0 or b < 0:
        return None
    blk = RED_TYPE_RE.sub('', src[a:b])
    blk = re.sub(r':\s*Record<string,\s*string>', '', blk)
    return '\n'.join(l.strip() for l in blk.splitlines() if l.strip())


def js_dump(obj, regex_keys=('pat',)):
    """JSON 으로 쓰되 pat 값은 JS 정규식 리터럴로 넣는다."""
    lits = []

    def walk(o):
        if isinstance(o, dict):
            r = {}
            for k, v in o.items():
                if k in regex_keys and isinstance(v, str) and v.startswith('/'):
                    lits.append(v)
                    r[k] = '__RE%d__' % (len(lits) - 1)
                else:
                    r[k] = walk(v)
            return r
        if isinstance(o, list):
            return [walk(x) for x in o]
        return o

    s = json.dumps(walk(obj), ensure_ascii=False, separators=(',', ':'))
    for i, lit in enumerate(lits):
        s = s.replace('"__RE%d__"' % i, lit)
    return s


def main():
    screens = build_screens()
    drugs = parse_drugs()
    supps = parse_supp(rd(os.path.join(JS, 'more2.js')), 'more2.js')
    ids = set(s['id'] for s in screens)
    # 약 자료의 화면 링크가 색인 밖이면 링크를 뗀다 (없는 화면 카드 방지)
    for d in drugs:
        for e in d['effects']:
            if e.get('link') and e['link'] not in ids:
                del e['link']

    data = {'v': 1, 'screens': screens, 'drugs': drugs, 'supps': supps}
    js = ('/* 자동 생성 파일 — _build_kb.py 가 화면 원본·druginfo.js·more2.js(SUPP)에서 만든다. 직접 고치지 마세요.\n'
          '   AI 상담(07-chat)의 검색 색인. 연구 문서(*.md)는 포함하지 않는다. */\n'
          'window.TODAK_KB = ' + js_dump(data) + ';\n')
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(js)

    chars = sum(len(x['x']) for s in screens for x in s['s'])
    print('■ AI 상담 색인 → www/js/kb-index.js')
    print('   화면 %d개 (앱 사용 %d) · 발췌 %d자 · 약 %d군 · 건강기능식품 %d종 · 파일 %dKB' % (
        len(screens), sum(1 for s in screens if s['k'] == 'app'), chars, len(drugs), len(supps),
        len(js.encode('utf-8')) // 1024))

    # 서버 함수(chat/index.ts)는 교수님이 파일째 붙여넣어 배포하므로 SUPP 를 따로 품고 있다.
    # more2.js 와 어긋나면 알린다 (고정 안전 문구가 앱 화면과 달라지지 않게).
    if os.path.exists(CHAT_FN):
        try:
            fn = parse_supp(rd(CHAT_FN), 'chat/index.ts')
            a = [(x['pat'], x['name'], x['known']) for x in supps]
            b = [(x['pat'], x['name'], x['known']) for x in fn]
            if a != b:
                print('   ⚠ chat/index.ts 의 SUPP 가 more2.js 와 달라요 — 서버 함수의 SUPP 를 맞춘 뒤 다시 배포하세요')
            else:
                print('   chat/index.ts SUPP 동기화 확인 (%d종 일치)' % len(fn))
        except SystemExit as e:
            print('   ⚠', e)
        # 앱은 서버가 답하지 못해도 위기(109)·119·오늘 연락 안내를 띄우려고 같은 위험신호 판정을 갖는다 — 어긋나면 알린다
        ra, rb = red_block(rd(CHAT_FN)), red_block(rd(os.path.join(JS, 'chat.js')))
        if ra is None or rb is None:
            print('   ⚠ 위험신호 판정(red:start~red:end) 표시를 chat/index.ts 또는 chat.js 에서 찾지 못했어요')
        elif ra != rb:
            print('   ⚠ chat.js 와 chat/index.ts 의 위험신호 판정(red 구간)이 달라요 — 두 파일을 똑같이 맞춘 뒤 서버를 다시 배포하세요')
        else:
            print('   위험신호 판정 동기화 확인 (앱 chat.js = 서버 chat/index.ts)')
    missing = [k for k in KW if k not in ids]
    if missing:
        print('   ⚠ 키워드만 있고 색인에 없는 화면:', ', '.join(missing))


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
