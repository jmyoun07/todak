-- ═══════════════════════════════════════════════════════════
-- 토닥 DB 보안 수정 (2026-09-14) — 정밀 검토에서 나온 확정 결함
-- 수파베이스 대시보드 > SQL Editor 에 통째로 붙여넣고 Run
-- ═══════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────
-- 1. profiles 를 참여자가 지우거나 새로 넣지 못하게 막는다
--
--    지금은 "own profile" 정책이 for all 이고 INSERT·DELETE 권한이 남아 있어서,
--    참여자가 자기 행을 지운 뒤 research_code·login_provider·email 을 직접 써넣은
--    새 행을 만들 수 있다. 칼럼 단위 update 제한이 이 경로로 우회된다.
--    (앱 코드는 profiles 에 insert·delete 를 한 번도 하지 않는다 — 행 생성은 트리거가 한다)
-- ─────────────────────────────────────────────────────────
revoke insert, delete on public.profiles from authenticated, anon;

drop policy if exists "own profile" on public.profiles;
create policy "read own profile"   on public.profiles for select
  using (auth.uid() = id);
create policy "update own profile" on public.profiles for update
  using (auth.uid() = id) with check (auth.uid() = id);

-- ─────────────────────────────────────────────────────────
-- 2. push_sent 표를 스키마에 정식으로 넣는다
--
--    push-send 함수는 알림 한 건마다 이 표에 먼저 INSERT 해서 중복 발송을 막는다.
--    표가 없으면 매번 오류가 나고 함수는 '이미 보냈다'로 보고 건너뛴다 →
--    복약·진료 알림이 한 건도 안 나가는데 함수는 정상 응답(sent:0)을 돌려준다.
--    정책 없이 RLS 만 켜면 서버 함수(service role) 전용이 된다 — oauth_identities 와 같은 방식.
-- ─────────────────────────────────────────────────────────
create table if not exists public.push_sent (
  user_id    uuid not null references auth.users(id) on delete cascade,
  key        text not null,
  sent_on    date not null,
  created_at timestamptz not null default now(),
  primary key (user_id, key, sent_on)
);
alter table public.push_sent enable row level security;
revoke all on public.push_sent from authenticated, anon;

-- ─────────────────────────────────────────────────────────
-- 3. 이미 저장된 '자기 전'(공백) 슬롯을 앱 표준인 '자기전'으로 맞춘다
--
--    공백이 있으면 '오늘의 복약' 화면에 그 복용분이 아예 안 나타나 체크할 수 없다.
-- ─────────────────────────────────────────────────────────
update public.medications
   set schedule = replace(schedule::text, '자기 전', '자기전')::jsonb
 where schedule::text like '%자기 전%';

-- ─────────────────────────────────────────────────────────
-- 4. 확인
-- ─────────────────────────────────────────────────────────
select 'profiles 정책' as 항목, policyname as 값 from pg_policies
 where schemaname='public' and tablename='profiles'
union all
select 'push_sent 존재', case when to_regclass('public.push_sent') is null then '없음' else '있음' end
union all
select '자기 전 남은 행', count(*)::text from public.medications where schedule::text like '%자기 전%';
