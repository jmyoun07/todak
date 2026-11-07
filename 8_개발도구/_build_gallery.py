# -*- coding: utf-8 -*-
"""
토닥 화면 시안 — 클릭해서 들어갈 수 있는 단일 HTML 빌더

만드는 것
  UI 결과물/overview_YYMMDD.html — 화면 전부를 담은 단일 HTML
  (이 파일 하나만 전달하면 다른 파일 없이 열립니다)

핵심
  - 화면 HTML 전부(screens/*.html, 2026-09-18 기준 88개)와 app.css 를 각각 "한 번만" 담는다
    (예전 빌드는 CSS 를 화면마다 중복해 1.73MB 낭비)
  - 머리말의 날짜는 빌드한 날로 자동으로 찍힌다
  - 갤러리 썸네일은 IntersectionObserver 로 지연 렌더
  - 카드를 누르면 폰 프레임 뷰어가 열리고, 화면 안의 링크를 누르면 그 화면으로 이동한다
  - iframe 안 클릭은 (a) 부모의 contentDocument 위임 리스너, (b) 주입 스크립트의 postMessage 두 경로로 가로챈다
"""
import io, os, re, json, glob, html, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 유방암 — 스크립트는 8_개발도구 안(2026-10-01 폴더 정리)
SRC = os.path.join(ROOT, 'UI 결과물')
SCREENS_DIR = os.path.join(SRC, 'screens')

# 연구 앱 밖의 시안 묶음(예: UI 결과물/_출시안_1103)을 같은 틀로 만들 때 쓰는 설정 —
# _build_gallery_launch.py 가 TODAK_GALLERY_CONF(JSON)로 넘긴다. 없으면 아래 기본값 그대로(연구 앱 갤러리).
CONF = json.loads(os.environ.get('TODAK_GALLERY_CONF') or '{}')
MAIN_CSS = os.path.join(SCREENS_DIR, 'app.css')      # 공용 app.css 는 언제나 연구 앱 원본을 쓴다
if CONF.get('src'):
    SRC = CONF['src']
    SCREENS_DIR = os.path.join(SRC, 'screens')


def rd(p):
    return io.open(p, encoding='utf-8').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)


# ───────────────────────── 1. 원본 수집 ─────────────────────────
CSS = rd(MAIN_CSS)
EXTRA_CSS = CONF.get('extra_css')                    # 시안 묶음 전용 CSS 파일 이름(screens 안) — app.css 뒤에 붙인다
if EXTRA_CSS:
    CSS += '\n' + rd(os.path.join(SCREENS_DIR, EXTRA_CSS))
OVERVIEW = rd(os.path.join(SRC, 'overview.html'))

screens = {}
for p in sorted(glob.glob(os.path.join(SCREENS_DIR, '*.html'))):
    sid = os.path.basename(p)[:-5]          # '44-detail-bone'
    s = rd(p)
    # <head> 안의 app.css 링크는 런타임에 인라인 <style> 로 갈아끼운다
    s = s.replace('<link rel="stylesheet" href="app.css">', '<!--CSS-->')
    if EXTRA_CSS:
        s = s.replace('<link rel="stylesheet" href="%s">' % EXTRA_CSS, '')
    screens[sid] = s

SCREEN_IDS = list(screens.keys())

# ─────────────────── 2. 갤러리 카드 메타 추출 ───────────────────
# overview.html 의 카드에서 파일명·번호·제목·부제를 그대로 가져온다
def parse_cards(chunk):
    """카드 단위로 먼저 자른 뒤 각각을 읽는다 — 한 카드에 요소가 빠져도 옆 카드를 삼키지 않도록."""
    out = []
    parts = chunk.split('<a class="card" href="screens/')
    for p in parts[1:]:
        sid = p.split('.html"', 1)[0]
        body = p.split('</a>', 1)[0]
        # class 뒤에 style 등 다른 속성이 붙어도 읽도록 [^>]* 를 둔다 (예: 48-emergency)
        num = re.search(r'<span class="num([^"]*)"[^>]*>([^<]*)</span>', body)
        title = re.search(r'<div class="title">(.*?)</div>', body, re.S)
        sub = re.search(r'<div class="subtitle">(.*?)</div>', body, re.S)
        out.append({
            'id': sid,
            'num': (num.group(2) if num else '').strip(),
            'numcls': (num.group(1) if num else '').strip(),
            'title': title.group(1).strip() if title else sid,
            'sub': sub.group(1).strip() if sub else '',
        })
    return out
HEAD_RE = re.compile(
    r'<div class="section-header"[^>]*>'
    r'(?:\s*<span class="step-badge">(.*?)</span>)?'
    r'\s*<h2>(.*?)</h2>'
    r'\s*<span class="tag">(.*?)</span>\s*</div>'
    r'\s*<p class="section-desc">(.*?)</p>', re.S)

# 섹션 머리말 위치로 잘라, 다음 머리말 전까지를 그 섹션의 카드 영역으로 본다
heads = list(HEAD_RE.finditer(OVERVIEW))
sections = []
for i, m in enumerate(heads):
    badge, title, tag, desc = m.groups()
    chunk = OVERVIEW[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(OVERVIEW)]
    sections.append({'badge': (badge or '').strip(), 'title': title, 'tag': tag,
                     'desc': desc, 'cards': parse_cards(chunk)})

card_total = sum(len(s['cards']) for s in sections)
assert card_total == len(SCREEN_IDS), \
    '카드 %d개 ≠ 화면 %d개 — overview.html 파싱 실패' % (card_total, len(SCREEN_IDS))
for s in sections:
    for c in s['cards']:
        assert c['id'] in screens, '카드가 없는 화면을 가리킴: %s' % c['id']

# 갤러리 순서 = 화면 순회(이전/다음)의 순서
ORDER = [c['id'] for s in sections for c in s['cards']]

# ─────────────── 3. 각 화면에 링크 중계 스크립트 주입 ───────────────
# 부모의 contentDocument 접근이 막히는 환경을 대비한 폴백 경로.
BRIDGE = (
    '<script>(function(){'
    'document.addEventListener("click",function(e){'
    'var a=e.target&&e.target.closest?e.target.closest("a"):null;if(!a)return;'
    'var h=a.getAttribute("href");if(h===null)return;'
    'e.preventDefault();'
    'try{parent.postMessage({__todak:1,href:h},"*")}catch(_){}'
    '},true);'
    'document.addEventListener("submit",function(e){e.preventDefault()},true);'
    '})()</script>'
)
for sid in screens:
    s = screens[sid]
    if '</body>' in s:
        screens[sid] = s.replace('</body>', BRIDGE + '</body>', 1)
    else:
        screens[sid] = s + BRIDGE

# ───────────────────────── 4. 셸 CSS ─────────────────────────
SHELL_CSS = r"""
:root{
  --g-bg:#FBF7F8; --g-surface:#FFFFFF; --g-ink:#2B2126; --g-ink-2:#6E5D65;
  --g-line:#EADFE4; --g-brand:#C43E6B; --g-brand-dk:#9E2E54; --g-brand-tint:#FCEEF3;
  --g-shadow:0 1px 2px rgba(43,33,38,.05),0 8px 24px rgba(43,33,38,.07);
  --g-shadow-lg:0 24px 64px rgba(43,33,38,.28);
  --g-radius:16px;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--g-bg); color:var(--g-ink);
  font-family:'Noto Sans KR','Malgun Gothic','맑은 고딕',system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 96px}

/* ── 머리말 ── */
.masthead{padding:52px 0 30px;border-bottom:1px solid var(--g-line);margin-bottom:34px}
.masthead h1{margin:0;font-size:34px;font-weight:800;letter-spacing:-.02em;text-wrap:balance}
.masthead .lede{margin:12px 0 0;font-size:16px;line-height:1.65;color:var(--g-ink-2);max-width:62ch}
.masthead .meta{margin-top:18px;font-size:13px;color:var(--g-ink-2);display:flex;flex-wrap:wrap;gap:8px 16px}
.masthead .meta b{color:var(--g-brand-dk);font-weight:700}
.howto{
  margin-top:22px;padding:14px 16px;border:1px solid var(--g-line);border-radius:12px;
  background:var(--g-brand-tint);font-size:14px;line-height:1.7;color:var(--g-ink);
}
.howto b{color:var(--g-brand-dk)}
.howto kbd{
  display:inline-block;padding:1px 6px;border:1px solid var(--g-line);border-bottom-width:2px;
  border-radius:5px;background:#fff;font:600 12px/1.6 ui-monospace,monospace;color:var(--g-ink-2)
}

/* ── 섹션 ── */
.section-header{display:flex;align-items:baseline;gap:12px;margin:44px 0 6px;flex-wrap:wrap}
.section-header h2{margin:0;font-size:21px;font-weight:750;letter-spacing:-.01em}
.section-header .tag{
  font-size:12px;font-weight:600;color:var(--g-brand-dk);background:var(--g-brand-tint);
  padding:4px 10px;border-radius:999px
}
.section-desc{margin:0 0 18px;font-size:14px;line-height:1.7;color:var(--g-ink-2);max-width:74ch}
.step-badge{
  flex:0 0 auto;display:inline-grid;place-items:center;width:27px;height:27px;border-radius:50%;
  background:var(--g-brand);color:#fff;font-size:14px;font-weight:700;align-self:center
}
.flow-hint{
  display:inline-block;margin-right:6px;padding:2px 8px;border-radius:6px;
  background:var(--g-surface);border:1px solid var(--g-line);
  font-size:12.5px;font-weight:600;color:var(--g-brand-dk);white-space:nowrap
}

/* ── 카드 그리드 ── */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(196px,1fr));gap:20px}
.card{
  display:block;text-align:left;width:100%;padding:0;border:1px solid var(--g-line);
  border-radius:var(--g-radius);background:var(--g-surface);box-shadow:var(--g-shadow);
  overflow:hidden;cursor:pointer;font:inherit;color:inherit;
  transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease;
}
.card:hover{transform:translateY(-3px);box-shadow:0 10px 30px rgba(43,33,38,.13);border-color:var(--g-brand)}
.card:focus-visible{outline:3px solid var(--g-brand);outline-offset:3px}
.thumb-wrap{background:#F2EAEE;border-bottom:1px solid var(--g-line)}
.thumb{position:relative;width:100%;aspect-ratio:390/844;overflow:hidden}
.thumb iframe{
  position:absolute;top:0;left:0;width:390px;height:844px;border:0;
  transform-origin:0 0;pointer-events:none;background:#fff
}
.thumb .ph{position:absolute;inset:0;display:grid;place-items:center;color:#C3AEB7;font-size:26px}
.info{padding:12px 13px 14px}
.num{
  display:inline-block;font:700 11px/1.6 ui-monospace,monospace;color:var(--g-brand-dk);
  background:var(--g-brand-tint);padding:1px 7px;border-radius:5px;margin-bottom:6px
}
.num.new{background:#E3F3EC;color:#1E6B4A}
.title{font-size:14.5px;font-weight:700;line-height:1.4}
.subtitle{margin-top:3px;font-size:12.5px;line-height:1.5;color:var(--g-ink-2)}

/* ── 뷰어 ── */
.viewer{
  position:fixed;inset:0;z-index:100;display:none;
  background:rgba(35,26,30,.72);backdrop-filter:blur(6px);
}
.viewer[data-open]{display:grid;grid-template-rows:auto 1fr auto}
.v-top{
  display:flex;align-items:center;gap:12px;padding:12px 18px;color:#fff;
  background:rgba(24,18,21,.5)
}
.v-name{font-size:15px;font-weight:700;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.v-id{font:600 12px/1.6 ui-monospace,monospace;opacity:.72;flex:0 0 auto}
.v-spacer{flex:1 1 auto}
.v-btn{
  flex:0 0 auto;min-width:40px;height:40px;padding:0 13px;border:1px solid rgba(255,255,255,.28);
  border-radius:10px;background:rgba(255,255,255,.1);color:#fff;font:600 13.5px/1 inherit;
  cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px
}
.v-btn:hover{background:rgba(255,255,255,.2)}
.v-btn:focus-visible{outline:3px solid #fff;outline-offset:2px}
.v-btn[disabled]{opacity:.35;cursor:not-allowed}
.v-stage{display:grid;place-items:center;overflow:auto;padding:10px}
/* 사이저가 실제 레이아웃 상자를 갖고, 안의 iframe 만 축소한다.
   transform 만 쓰면 축소해도 상자는 844px 그대로라 스크롤 영역이 어긋난다. */
.v-holder{
  position:relative;flex:0 0 auto;border-radius:26px;overflow:hidden;background:#fff;
  box-shadow:var(--g-shadow-lg)
}
.v-frame{
  position:absolute;top:0;left:0;width:390px;height:844px;border:0;background:#fff;
  transform-origin:0 0
}
.v-bottom{
  padding:11px 18px 16px;color:rgba(255,255,255,.82);font-size:12.5px;line-height:1.6;text-align:center
}
/* 세로가 짧거나 폭이 좁으면 힌트 줄을 접어 화면에 자리를 돌려준다.
   좁은 화면에서는 어차피 키보드 조작 안내가 쓸모없다. */
@media (max-height:560px), (max-width:640px){ .v-bottom{display:none} .v-stage{padding:5px} }
.v-bottom b{color:#fff}

/* ── 토스트 ── */
.toast{
  position:fixed;left:50%;bottom:32px;transform:translateX(-50%) translateY(12px);
  z-index:120;max-width:min(520px,calc(100vw - 40px));
  padding:13px 18px;border-radius:12px;background:#2B2126;color:#fff;
  font-size:14px;line-height:1.6;box-shadow:var(--g-shadow-lg);
  opacity:0;pointer-events:none;transition:opacity .2s ease,transform .2s ease
}
.toast[data-on]{opacity:1;transform:translateX(-50%) translateY(0)}
.toast b{color:#FFC9DC}

@media (max-width:640px){
  .masthead{padding:34px 0 22px}
  .masthead h1{font-size:26px}
  .grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px}
  .wrap{padding:0 14px 72px}
  .v-top{padding:10px 12px;gap:8px}
  .v-name{font-size:14px}
}
@media (prefers-reduced-motion:reduce){
  *{transition:none!important;animation:none!important}
  .card:hover{transform:none}
}
"""

# ───────────────────────── 5. 셸 JS ─────────────────────────
SHELL_JS = r"""
(function(){
  'use strict';
  var CSS   = window.__TODAK_CSS;
  var HTML  = window.__TODAK_SCREENS;
  var ORDER = window.__TODAK_ORDER;
  var META  = window.__TODAK_META;

  // 화면 HTML 을 완성한다 (CSS 자리표시자를 실제 스타일로 치환)
  var cache = {};
  function build(id){
    if(cache[id]) return cache[id];
    var h = HTML[id];
    if(h === undefined) return null;
    cache[id] = h.replace('<!--CSS-->', '<style>' + CSS + '</style>');
    return cache[id];
  }

  /* ── 썸네일 지연 렌더 ──
     빠른 길은 IntersectionObserver. 다만 배경 탭에서 열면 문서가 hidden 이라
     관찰자가 깨어나지 않는다. 그래서 남은 것을 천천히 채우는 청소부를 함께 둔다. */
  var io = ('IntersectionObserver' in window) ? new IntersectionObserver(function(es){
    es.forEach(function(e){
      if(!e.isIntersecting) return;
      io.unobserve(e.target);
      paint(e.target);
    });
  }, {rootMargin:'600px 0px'}) : null;

  function paint(thumb){
    if(thumb.getAttribute('data-painted')) return;
    thumb.setAttribute('data-painted','1');
    var id = thumb.getAttribute('data-screen');
    var doc = build(id);
    if(doc === null) return;
    var f = document.createElement('iframe');
    f.setAttribute('title', (META[id] ? META[id].title : id) + ' 미리보기');
    f.setAttribute('tabindex','-1');
    f.setAttribute('aria-hidden','true');
    f.setAttribute('loading','lazy');
    f.srcdoc = doc;
    thumb.appendChild(f);
    var ph = thumb.querySelector('.ph');
    if(ph) ph.remove();
    fit(thumb, f);
  }
  function fit(thumb, f){
    var w = thumb.clientWidth || 196;
    f.style.transform = 'scale(' + (w/390) + ')';
  }
  function refit(){
    [].forEach.call(document.querySelectorAll('.thumb'), function(t){
      var f = t.querySelector('iframe');
      if(f) fit(t, f);
    });
  }

  var thumbs = [].slice.call(document.querySelectorAll('.thumb'));
  thumbs.forEach(function(t){ if(io) io.observe(t); });

  // 청소부 — 화면에 가까운 것부터 조금씩. 관찰자가 이미 그린 것은 건너뛴다.
  var sweepT = null;
  function sweep(){
    var left = thumbs.filter(function(t){ return !t.getAttribute('data-painted'); });
    if(!left.length) return;
    var vh = window.innerHeight || 800;
    left.sort(function(a, b){
      return Math.abs(a.getBoundingClientRect().top - vh / 2)
           - Math.abs(b.getBoundingClientRect().top - vh / 2);
    });
    left.slice(0, 4).forEach(paint);
    sweepT = setTimeout(sweep, 120);
  }
  function kickSweep(delay){ clearTimeout(sweepT); sweepT = setTimeout(sweep, delay); }
  kickSweep(1500);
  document.addEventListener('visibilitychange', function(){
    if(!document.hidden) kickSweep(200);
  });

  /* ── 뷰어 ── */
  var viewer = document.getElementById('viewer');
  var stage  = document.getElementById('v-stage');
  var frame  = document.getElementById('v-frame');
  var holder = document.getElementById('v-holder');
  var elName = document.getElementById('v-name');
  var elId   = document.getElementById('v-id');
  var btnBack= document.getElementById('v-back');
  var btnPrev= document.getElementById('v-prev');
  var btnNext= document.getElementById('v-next');
  var elHint = document.getElementById('v-hint');
  var wrap   = document.querySelector('.wrap');

  var stack = [];          // 뷰어 안에서 밟아온 화면들
  var current = null;
  var lastCard = null;     // 갤러리로 돌아갈 때 포커스를 되돌릴 카드

  // 세로가 모자랄 때 무한정 줄이면 글자를 못 읽는다. 이 아래로는 줄이지 않고
  // 무대를 세로로 스크롤시킨다.
  var MIN_SCALE = 0.55;

  function scaleFrame(){
    if(!current) return;
    var pad = 20;
    var availW = stage.clientWidth  - pad;
    var availH = stage.clientHeight - pad;
    var byW = Math.min(availW/390, 1);              // 가로는 반드시 들어가야 한다
    var byH = availH/844;
    var s = Math.min(byW, Math.max(byH, MIN_SCALE));
    if(!isFinite(s) || s <= 0) s = 1;
    frame.style.transform = 'scale(' + s + ')';
    holder.style.width  = Math.round(390*s) + 'px';
    holder.style.height = Math.round(844*s) + 'px';
    // 세로로 넘칠 때만 위쪽 정렬 — 가운데 정렬이면 윗부분이 잘려 못 본다
    stage.style.alignItems = (844*s > availH) ? 'start' : 'center';
  }

  function open(id, push){
    var doc = build(id);
    if(doc === null){ toast('시안에 없는 화면이에요 — <b>' + esc(id) + '</b>'); return; }
    if(push && current && current !== id) stack.push(current);
    current = id;
    frame.srcdoc = doc;
    var m = META[id] || {};
    elName.textContent = m.title || id;
    elId.textContent = id;
    viewer.setAttribute('data-open','');
    document.body.style.overflow = 'hidden';
    if(wrap) wrap.inert = true;      // 뒤 갤러리로 탭이 새지 않도록
    sync();
    scaleFrame();
    try{ location.hash = '#/' + id; }catch(_){}
    btnBack.focus();
  }

  function close(){
    viewer.removeAttribute('data-open');
    frame.srcdoc = '';
    document.body.style.overflow = '';
    if(wrap) wrap.inert = false;     // 포커스를 되돌리기 전에 먼저 푼다
    current = null; stack = [];
    try{ location.hash = ''; }catch(_){}
    if(lastCard) lastCard.focus();
  }

  function back(){
    if(stack.length) open(stack.pop(), false);
    else close();
  }

  function step(d){
    if(!current) return;
    var i = ORDER.indexOf(current);
    if(i < 0) return;
    var j = i + d;
    if(j < 0 || j >= ORDER.length) return;
    stack = [];
    open(ORDER[j], false);
  }

  function sync(){
    var i = ORDER.indexOf(current);
    btnPrev.disabled = (i <= 0);
    btnNext.disabled = (i < 0 || i >= ORDER.length - 1);
    btnBack.innerHTML = stack.length ? '‹ 뒤로' : '✕ 목록';
    elHint.innerHTML = stack.length
      ? '화면 안의 버튼을 눌러 계속 이동하실 수 있어요 · <b>' + stack.length + '단계</b> 들어와 계세요'
      : '화면 안의 버튼을 눌러보세요 · <kbd>Esc</kbd> 목록으로 · <kbd>←</kbd><kbd>→</kbd> 이전·다음';
  }

  /* ── 링크 가로채기 ── */
  var TEL = {'119':'119 구급', '109':'자살예방 상담전화 109', '1577-0199':'정신건강 상담전화 1577-0199'};

  function route(href){
    if(href === null || href === undefined) return;
    var h = String(href).trim();
    if(!h || h === '#' || h === 'app.css') return;
    if(/^javascript:/i.test(h)){
      toast('이 버튼은 <b>화면 시안에서는 동작하지 않아요</b> — 실제 앱에서 이어집니다');
      return;
    }
    if(/^tel:/i.test(h)){
      var num = h.slice(4);
      toast('실제 앱에서는 <b>' + esc(TEL[num] || num) + '</b>(으)로 전화가 걸려요 — 시안이라 걸지 않았어요');
      return;
    }
    if(/^mailto:/i.test(h)){
      toast('실제 앱에서는 메일 앱이 열려요 — <b>' + esc(h.slice(7)) + '</b>');
      return;
    }
    if(/^https?:/i.test(h)){
      toast('바깥 사이트로 연결되는 링크예요 — <b>' + esc(h) + '</b>');
      return;
    }
    var frag = '';
    var hp = h.indexOf('#');
    if(hp >= 0){ frag = h.slice(hp + 1); h = h.slice(0, hp); }
    // 앱에서 쓰는 '?' 뒤 값(72-no-info.html?q=… · 25-terms.html?tab=… · 02-consent.html?review=1)은 시안에서 쓰지 않는다 — 떼고 화면을 찾는다
    var qp = h.indexOf('?');
    if(qp >= 0) h = h.slice(0, qp);
    if(h.slice(-5) === '.html') h = h.slice(0, -5);
    if(HTML[h] === undefined){
      toast('시안에 없는 화면이에요 — <b>' + esc(h) + '</b>');
      return;
    }
    open(h, true);
    if(frag) setTimeout(function(){ scrollTo(frag); }, 120);
  }

  function scrollTo(frag){
    try{
      var d = frame.contentDocument;
      var t = d && (d.getElementById(frag) || d.querySelector('[name="' + frag + '"]'));
      if(t && t.scrollIntoView) t.scrollIntoView({block:'start'});
    }catch(_){}
  }

  // (a) 부모에서 직접 위임 — same-origin srcdoc
  frame.addEventListener('load', function(){
    scaleFrame();
    try{
      var d = frame.contentDocument;
      if(!d) return;
      d.addEventListener('click', function(e){
        var a = e.target && e.target.closest ? e.target.closest('a') : null;
        if(!a) return;
        e.preventDefault();
        route(a.getAttribute('href'));
      }, true);
      d.addEventListener('keydown', function(e){
        if(e.key === 'Escape'){ e.preventDefault(); back(); }
      });
    }catch(_){ /* (b) postMessage 경로가 받는다 */ }
  });

  // (b) 주입 스크립트의 postMessage — contentDocument 접근이 막힌 환경 대비
  window.addEventListener('message', function(e){
    var d = e.data;
    if(d && d.__todak === 1) route(d.href);
  });

  /* ── 갤러리 카드 ── */
  [].forEach.call(document.querySelectorAll('.card'), function(btn){
    btn.addEventListener('click', function(){
      lastCard = btn;
      stack = [];
      open(btn.getAttribute('data-screen'), false);
    });
  });

  btnBack.addEventListener('click', back);
  btnPrev.addEventListener('click', function(){ step(-1); });
  btnNext.addEventListener('click', function(){ step(1); });
  viewer.addEventListener('mousedown', function(e){ if(e.target === viewer) close(); });

  document.addEventListener('keydown', function(e){
    if(!viewer.hasAttribute('data-open')) return;
    if(e.key === 'Escape'){ e.preventDefault(); back(); }
    else if(e.key === 'ArrowLeft'){ e.preventDefault(); step(-1); }
    else if(e.key === 'ArrowRight'){ e.preventDefault(); step(1); }
  });

  window.addEventListener('resize', function(){ scaleFrame(); refit(); });

  /* ── 딥링크 ── */
  function fromHash(){
    var h = (location.hash || '').replace(/^#\/?/, '');
    if(h && HTML[h] !== undefined){ stack = []; open(h, false); }
  }
  window.addEventListener('hashchange', function(){
    var h = (location.hash || '').replace(/^#\/?/, '');
    if(!h){ if(viewer.hasAttribute('data-open')) close(); }
    else if(h !== current && HTML[h] !== undefined){ stack = []; open(h, false); }
  });
  fromHash();

  /* ── 토스트 ── */
  var toastEl = document.getElementById('toast'), toastT = null;
  function toast(msgHtml){
    toastEl.innerHTML = msgHtml;
    toastEl.setAttribute('data-on','');
    clearTimeout(toastT);
    toastT = setTimeout(function(){ toastEl.removeAttribute('data-on'); }, 3200);
  }
  function esc(s){
    return String(s).replace(/[&<>"]/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];
    });
  }
})();
"""


# ───────────────────────── 6. 본문 조립 ─────────────────────────
def build_body():
    out = []
    out.append('<div class="wrap">')
    out.append('''
  <header class="masthead">
    <h1>토닥 · 화면 시안</h1>
    <p class="lede">유방암 치료 중 겪는 부작용을 스스로 살피고, 필요할 때 제때 병원에 연락하도록 돕는 앱입니다.
      아래 화면을 누르시면 실제 앱처럼 <b>안에서 계속 눌러 이동</b>하실 수 있어요.</p>
    <div class="meta">
      <span><b>%d개</b> 화면</span>
      <span>연구용 클릭 시안 · 실제 앱 아님</span>
      <span>무료 · 비영리 · 광고 없음</span>
      <span>%s</span>
    </div>
    <p class="howto">화면을 누르면 크게 열려요. 그 안의 <b>버튼과 목록을 계속 눌러</b> 돌아다녀 보세요.
      <kbd>Esc</kbd> 로 한 단계 뒤로, <kbd>←</kbd> <kbd>→</kbd> 로 이전·다음 화면.
      전화 걸기처럼 <b>시안에서 실행되면 안 되는 동작</b>은 눌러도 안내만 뜨고 실제로 실행되지 않아요.</p>
  </header>''' % (len(SCREEN_IDS), datetime.date.today().isoformat()))

    for sec in sections:
        badge = ('<span class="step-badge">%s</span>' % sec['badge']) if sec['badge'] else ''
        out.append('  <div class="section-header">%s<h2>%s</h2><span class="tag">%s</span></div>'
                   % (badge, sec['title'], sec['tag']))
        out.append('  <p class="section-desc">%s</p>' % sec['desc'])
        out.append('  <div class="grid">')
        for c in sec['cards']:
            num_cls = 'num new' if ('new' in c['numcls'].lower() or c['num'] in ('★', '★★', 'NEW')) else 'num'
            out.append(
                '    <button class="card" type="button" data-screen="%s" '
                'aria-label="%s 화면 열기">'
                '<div class="thumb-wrap"><div class="thumb" data-screen="%s"><div class="ph">🎀</div></div></div>'
                '<div class="info"><span class="%s">%s</span>'
                '<div class="title">%s</div><div class="subtitle">%s</div></div></button>'
                % (c['id'], re.sub(r'<[^>]+>', '', c['title']), c['id'],
                   num_cls, c['num'], c['title'], c['sub']))
        out.append('  </div>')

    out.append('''
  <p style="margin-top:46px;padding-top:22px;border-top:1px solid var(--g-line);
     font-size:12.5px;line-height:1.75;color:var(--g-ink-2);max-width:74ch">
    본 화면은 연구용 시안입니다. 표시된 내용은 교육·자가관리 정보이며 진단이나 처방을 대신하지 않습니다.
    본 제품은 의료기기가 아니므로 질병 유무를 판단할 수 없으며, 질병 유무 판단을 위해서는 의사의 검진이 필요합니다.
  </p>''')
    out.append('</div>')

    # 뷰어
    out.append('''
<div class="viewer" id="viewer" role="dialog" aria-modal="true" aria-label="화면 미리보기">
  <div class="v-top">
    <button class="v-btn" id="v-back" type="button">✕ 목록</button>
    <div style="min-width:0">
      <div class="v-name" id="v-name"></div>
    </div>
    <span class="v-id" id="v-id"></span>
    <span class="v-spacer"></span>
    <button class="v-btn" id="v-prev" type="button" aria-label="이전 화면">‹</button>
    <button class="v-btn" id="v-next" type="button" aria-label="다음 화면">›</button>
  </div>
  <div class="v-stage" id="v-stage">
    <div class="v-holder" id="v-holder">
      <iframe class="v-frame" id="v-frame" title="화면 미리보기"></iframe>
    </div>
  </div>
  <div class="v-bottom" id="v-hint"></div>
</div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>''')
    return '\n'.join(out)


META = {}
for sec in sections:
    for c in sec['cards']:
        META[c['id']] = {'title': re.sub(r'<[^>]+>', '', c['title']),
                         'sub': re.sub(r'<[^>]+>', '', c['sub'])}

def js(obj):
    """JS 리터럴로 안전하게 직렬화.

    화면 HTML 안에는 </script> 와 <!-- 가 들어 있다. 그대로 두면 HTML 파서가
    데이터 <script> 블록을 그 자리에서 끊어버려 페이지가 통째로 망가진다.
    JSON 문자열 안에서는 </ 를 이스케이프해도 값이 같으므로 이렇게 막는다.
    U+2028/2029 는 구형 JS 파서가 줄바꿈으로 읽으므로 함께 이스케이프한다.
    """
    return (json.dumps(obj, ensure_ascii=False)
            .replace("</", r"<\/")
            .replace("<!--", r"<\!--")
            .replace(" ", "\u2028")
            .replace(" ", "\u2029"))


DATA_JS = (
    'window.__TODAK_CSS=' + js(CSS) + ';\n'
    'window.__TODAK_SCREENS=' + js(screens) + ';\n'
    'window.__TODAK_ORDER=' + js(ORDER) + ';\n'
    'window.__TODAK_META=' + js(META) + ';\n'
)

FONT = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" '
        'href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800&display=swap">')

BODY = build_body()
# 시안 묶음은 머리말·꼬리말 문장만 갈아 끼운다(설정의 replace: [[원래 문장, 새 문장], …]) — 화면 자료(DATA_JS)는 건드리지 않는다
for _old, _new in CONF.get('replace', []):
    assert _old in BODY, '갤러리 머리말에 없는 문장: %s' % _old
    BODY = BODY.replace(_old, _new)

# ── 배포용: 완전한 문서 (이 파일 하나만 주면 됨) ──
standalone = (
    '<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    '<title>' + CONF.get('title', '토닥 화면 시안') + '</title>\n'
    + FONT + '\n<style>\n' + SHELL_CSS + '\n</style>\n</head>\n<body>\n'
    + BODY + '\n'
    + '<script>\n' + DATA_JS + '</script>\n'
    + '<script>\n' + SHELL_JS + '\n</script>\n</body>\n</html>\n'
)

STAMP = datetime.date.today().strftime('%y%m%d')
OUT_PREFIX = CONF.get('out_prefix', 'overview_')
OUT_NAME = '%s%s.html' % (OUT_PREFIX, STAMP)
OUT_PATH = os.path.join(SRC, OUT_NAME)

# 이 스크립트가 전에 만든 날짜본만 정리한다 (원본 overview.html 은 건드리지 않음)
for old in glob.glob(os.path.join(SRC, OUT_PREFIX + '??????.html')):
    if os.path.basename(old) != OUT_NAME:
        os.remove(old)
        print('   이전본 삭제  %s' % os.path.basename(old))

wr(OUT_PATH, standalone)

print('■ 빌드 완료')
print('   화면 %d개 · 섹션 %d개 · 순회 순서 %d개' % (len(SCREEN_IDS), len(sections), len(ORDER)))
print('   %-32s %.2f MB   ← 이 파일 하나만 주면 됩니다'
      % (os.path.relpath(OUT_PATH, ROOT), os.path.getsize(OUT_PATH) / 1048576))

