# -*- coding: utf-8 -*-
"""토닥 수파베이스 백업 — 무료 요금제는 자동 백업이 없어서 만든 것 (2026-10-01)
   실행: 7_DB_수파베이스/DB백업하기.bat 을 두 번 누르기  (또는 유방암 폴더에서 python 8_개발도구/_backup_db.py)
   결과: 7_DB_수파베이스/백업/토닥_DB백업_YYYYMMDD_HHMM.zip
     · 표/<표이름>.json  — 그대로 되살릴 때 쓰는 원본 (모든 칸)
     · 표/<표이름>.csv   — 엑셀에서 바로 열기용 (한글이 깨지지 않게 BOM)
     · 가입자_auth_users.json — 계정 번호·이메일·가입 방법·가입/마지막 로그인 시각 (비밀번호는 수파베이스도 내주지 않는다)
     · 보관함_목록.json  — 보관함(Storage) 파일 이름·크기·올린 시각
     · 보관함/…          — 사진 파일 자체는 --photos 를 붙일 때만 담는다 (환자 확인 서류는 진단서 사진이라 민감)
     · 백업정보.json     — 언제·무엇을·몇 줄
   키: 유방암/_키모음.env 의 SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY 를 읽는다 (화면에 찍지 않는다)
   ⚠ 백업 파일에는 참여자 개인정보가 들어 있다 — 연구 자료 보관 규정에 맞는 곳(암호화 USB 등)에 옮겨 두고,
     메일·메신저로 보내지 않는다. 오래된 백업은 직접 지운다(이 도구는 아무것도 지우지 않는다).
   되살리기가 필요하면 Claude 에게 이 zip 을 주면 된다(표 JSON 을 그대로 다시 넣는다).
   시험: python _backup_db.py --url http://127.0.0.1:포트 --key 가짜키 --out 폴더 [--photos]"""
import sys, os, re, io, csv, json, time, zipfile, datetime, urllib.request, urllib.parse, urllib.error
sys.stdout.reconfigure(encoding='utf-8')

HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # 유방암
ENVF = os.path.join(HOME, '_키모음.env')
OUTD = os.path.join(HOME, '7_DB_수파베이스', '백업')
# 표 목록을 못 받아 올 때 쓰는 알려진 표(2026-10-01 기준) — 받아 온 목록과 합친다
KNOWN = ['profiles', 'medications', 'med_logs', 'checkins', 'app_events', 'chat_messages', 'answer_reports',
         'consent_records', 'patient_verifications', 'push_subscriptions', 'push_sent', 'oauth_identities', 'app_config']
PAGE = 1000


def arg(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def read_env():
    env = {}
    try:
        for l in open(ENVF, encoding='utf-8-sig'):
            m = re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', l)
            if m: env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    except OSError:
        pass
    return env


env = read_env()
URL = (arg('--url') or env.get('SUPABASE_URL') or '').rstrip('/')
KEY = arg('--key') or env.get('SUPABASE_SERVICE_ROLE_KEY') or ''
OUTD = arg('--out') or OUTD
PHOTOS = '--photos' in sys.argv
if not URL or not KEY:
    print('✗ _키모음.env 에 SUPABASE_URL 과 SUPABASE_SERVICE_ROLE_KEY 가 있어야 해요.')
    print('  수파베이스 대시보드 → Project Settings → API Keys 의 service_role(secret) 키를 한 줄로 넣어 주세요.')
    sys.exit(1)
HDR = {'apikey': KEY, 'User-Agent': 'todak-backup/1.0'}
if KEY.startswith('eyJ'):                       # 예전 방식 service_role 키(JWT)만 Authorization 에도 넣는다
    HDR['Authorization'] = 'Bearer ' + KEY


def call(path, method='GET', body=None, extra=None, raw=False):
    h = dict(HDR)
    if extra: h.update(extra)
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8'); h['Content-Type'] = 'application/json'
    req = urllib.request.Request(URL + path, data=data, headers=h, method=method)
    for attempt in range(3):
        try:
            r = urllib.request.urlopen(req, timeout=60)
            b = r.read()
            return (b if raw else json.loads(b.decode('utf-8') or 'null')), {k.lower(): v for k, v in r.headers.items()}
        except urllib.error.HTTPError as e:
            if e.code in (500, 502, 503, 504) and attempt < 2:
                time.sleep(2 * (attempt + 1)); continue
            raise
        except urllib.error.URLError:
            if attempt < 2:
                time.sleep(2 * (attempt + 1)); continue
            raise


def tables():
    found, cols = [], {}
    try:
        spec, _ = call('/rest/v1/', extra={'Accept': 'application/openapi+json'})
        for name, d in (spec.get('definitions') or {}).items():
            found.append(name); cols[name] = set((d.get('properties') or {}).keys())
    except Exception as e:
        print('  (표 목록을 받지 못해 알려진 표로 합니다:', type(e).__name__ + ')')
    names = found + [t for t in KNOWN if t not in found]
    return names, cols, set(found)


def rows_of(t, has_id):
    out, start, total = [], 0, None
    base = '/rest/v1/' + urllib.parse.quote(t) + '?select=*' + ('&order=id.asc' if has_id else '')
    while True:
        try:
            b, h = call(base, extra={'Range-Unit': 'items', 'Range': '%d-%d' % (start, start + PAGE - 1), 'Prefer': 'count=exact'})
        except urllib.error.HTTPError as e:
            if e.code == 400 and has_id:                     # id 칸이 없는 표 — 정렬 없이 다시
                return rows_of(t, False)
            raise
        out.extend(b or [])
        cr = h.get('content-range', '')
        m = re.match(r'\s*(\d+)-(\d+)/(\d+|\*)', cr)
        if m and m.group(3) != '*': total = int(m.group(3))
        if not b or len(b) < PAGE or (total is not None and len(out) >= total): break
        start += PAGE
    return out


def to_csv(rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    s = io.StringIO()
    w = csv.writer(s)
    w.writerow(keys)
    for r in rows:
        w.writerow(['' if r.get(k) is None else (json.dumps(r[k], ensure_ascii=False) if isinstance(r.get(k), (dict, list)) else r[k]) for k in keys])
    return '﻿' + s.getvalue()


def auth_users():
    out, page = [], 1
    while True:
        b, _ = call('/auth/v1/admin/users?page=%d&per_page=500' % page)
        us = (b or {}).get('users') if isinstance(b, dict) else b
        us = us or []
        out.extend(us)
        if len(us) < 500: break
        page += 1
    return out


def storage_list():
    files = []
    try:
        buckets, _ = call('/storage/v1/bucket')
    except Exception as e:
        print('  (보관함 목록을 받지 못함:', type(e).__name__ + ')'); return [], []

    def walk(bucket, prefix):
        off = 0
        while True:
            items, _ = call('/storage/v1/object/list/' + urllib.parse.quote(bucket), 'POST',
                            {'prefix': prefix, 'limit': 1000, 'offset': off, 'sortBy': {'column': 'name', 'order': 'asc'}})
            items = items or []
            for it in items:
                name = it.get('name') or ''
                if name == '.emptyFolderPlaceholder': continue
                path = (prefix + '/' + name) if prefix else name
                if it.get('id') is None:                    # 폴더
                    walk(bucket, path)
                else:
                    md = it.get('metadata') or {}
                    files.append({'bucket': bucket, 'path': path, 'size': md.get('size'), 'mimetype': md.get('mimetype'),
                                  'created_at': it.get('created_at'), 'updated_at': it.get('updated_at')})
            if len(items) < 1000: break
            off += 1000
    for bk in buckets or []:
        try:
            walk(bk.get('id') or bk.get('name'), '')
        except urllib.error.HTTPError as e:
            if e.code in (401, 403): raise
            print('  (보관함 %s 목록 일부를 받지 못함: %s)' % (bk.get('id'), e.code))
    return buckets or [], files


def main():
    t0 = time.time()
    now = datetime.datetime.now()
    os.makedirs(OUTD, exist_ok=True)
    zpath = os.path.join(OUTD, '토닥_DB백업_%s.zip' % now.strftime('%Y%m%d_%H%M'))
    print('토닥 DB 백업 시작 —', now.strftime('%Y-%m-%d %H:%M'))
    info = {'만든 시각': now.isoformat(timespec='seconds'), '수파베이스 주소': URL, '표': {}, '사진 포함': PHOTOS, '도구': '8_개발도구/_backup_db.py'}
    names, cols, found = tables()
    part = zpath + '.part'          # 다 받은 뒤에만 .zip 이름을 붙인다 — 중간에 끊기면 반쪽짜리가 백업처럼 남지 않게
    try:
        _write(part, names, cols, found, info, t0)
    except BaseException:
        try: os.remove(part)        # 이 도구가 방금 만든 미완성 파일만 치운다
        except OSError: pass
        raise
    os.replace(part, zpath)
    print('\n✓ 끝 — %s (%.1f MB, %.0f초)' % (zpath, os.path.getsize(zpath) / 1e6, time.time() - t0))
    print('⚠ 이 파일에는 참여자 개인정보가 들어 있어요. 연구 자료 보관 규정에 맞는 곳에 옮겨 두시고, 메일·메신저로 보내지 마세요.')
    return zpath


def _write(zpath, names, cols, found, info, t0):
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for t in names:
            try:
                rows = rows_of(t, 'id' in cols.get(t, {'id'}))
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    raise                                    # 키가 틀림 — 표마다 실패를 늘어놓지 않고 바로 안내
                if t not in found and e.code in (404, 400):
                    continue                                 # 알려진 표인데 이제 없음 — 건너뜀
                print('  ✗ %-24s 받지 못함 (%s)' % (t, e.code)); info['표'][t] = '실패 %s' % e.code; continue
            z.writestr('표/%s.json' % t, json.dumps(rows, ensure_ascii=False, indent=1))
            z.writestr('표/%s.csv' % t, to_csv(rows))
            info['표'][t] = len(rows)
            print('  ✓ %-24s %6d줄' % (t, len(rows)))
        us = auth_users()
        z.writestr('가입자_auth_users.json', json.dumps(us, ensure_ascii=False, indent=1))
        info['가입자(auth)'] = len(us)
        print('  ✓ %-24s %6d명' % ('가입자(auth)', len(us)))
        buckets, files = storage_list()
        z.writestr('보관함_목록.json', json.dumps({'buckets': buckets, 'files': files}, ensure_ascii=False, indent=1))
        info['보관함 파일'] = len(files)
        print('  ✓ %-24s %6d개%s' % ('보관함 파일 목록', len(files), ' (사진도 담음)' if PHOTOS else ' (사진은 안 담음 — --photos 로 담기)'))
        if PHOTOS:
            n = 0
            for f in files:
                b, _ = call('/storage/v1/object/%s/%s' % (urllib.parse.quote(f['bucket']), urllib.parse.quote(f['path'])), raw=True)
                z.writestr('보관함/%s/%s' % (f['bucket'], f['path']), b); n += 1
            info['담은 사진'] = n
        info['걸린 초'] = round(time.time() - t0, 1)
        z.writestr('백업정보.json', json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    try:
        main()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print('\n✗ 수파베이스가 거절했어요 (%s). service_role 키가 맞는지 _키모음.env 를 확인해 주세요.' % e.code)
        else:
            print('\n✗ 수파베이스 쪽 오류예요 (%s). 잠시 뒤 다시 실행해 주세요 — 만들던 백업 파일은 남기지 않았어요.' % e.code)
        sys.exit(1)
    except urllib.error.URLError as e:
        print('\n✗ 수파베이스에 닿지 못했어요 — 인터넷 연결을 확인해 주세요.', getattr(e, 'reason', '')); sys.exit(1)
