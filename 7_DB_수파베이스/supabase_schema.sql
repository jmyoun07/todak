-- ═══════════════════════════════════════════════════════════
-- 토닥 DB 스키마 v1  (수파베이스 대시보드 > SQL Editor 에 통째로 붙여넣고 Run)
-- 설계 원칙
--  · 위치정보 테이블 없음 — 위치는 서버로 오지 않는다
--  · chat_messages 는 회원 계정 데이터(연구 자료 아님) — 계획서: "질문 내용과 AI 답변 원문은
--    연구용 앱 사용기록으로 수집하지 않으며"
--  · app_events 는 계획서 5) 의 비식별 사용기록(접속·질문 수 등)만 담는다
--  · 모든 표에 RLS: 본인 행만 읽고 쓸 수 있다
-- 2026-09-18: 운영 DB 에 따로 실행했던 변경을 이 파일에 합쳤다 — 빈 DB 를 이 파일 하나로 만들어도 운영 DB 와 같게
--  · profiles 정책 (토닥_DB_보안수정_260914.sql 1번)
--  · 11. answer_reports (9/7 운영 DB 에 실행한 정의 그대로)  · 12. push_sent (토닥_DB_보안수정_260914.sql 2번)
-- ═══════════════════════════════════════════════════════════

-- 1. 프로필 (가입 시 자동 생성)
create table public.profiles (
  id            uuid primary key references auth.users(id) on delete cascade,
  name          text,
  birth_date    date,
  research_code text unique,          -- 연구등록번호 (연구팀 발급)
  stage         text,                 -- 치료 단계 (치료 중 / 치료 후 등)
  subtype       text,                 -- 아형 (호르몬수용체+ 등, 선택)
  stage_told    text,                 -- 병기 — 의료진에게 들은 값 그대로
  comorbidities text[] default '{}',  -- 동반질환
  concerns      text[] default '{}',  -- 걱정되는 부작용 (14-concerns)
  treatment     jsonb default '{}',   -- 치료 시작일·주기·다음 진료 (73-cycle-setup)
  notif_prefs   jsonb default '{}',   -- 알림 설정 (23-notif-settings)
  login_provider text,                -- kakao | naver | google | email (가입 시 자동 기록)
  email          text,                -- 가입 시점의 계정 이메일 사본 (원본은 auth.users)
  created_at    timestamptz not null default now()
);

-- 2. 증상 기록 (하루 1건)
create table public.checkins (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  date       date not null,
  mood       smallint check (mood between 1 and 5),  -- 1 아주 힘듦 ~ 5 아주 좋음
  symptoms   text[] default '{}',
  intensity  jsonb default '{}',      -- {"손발 저림":"보통", ...}
  memo       text,
  created_at timestamptz not null default now(),
  unique (user_id, date)
);

-- 3. 복용 약
create table public.medications (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  name       text not null,
  dose       text,
  schedule   jsonb default '{}',      -- {"아침":"08:00", ...}
  source     text not null default 'manual' check (source in ('ocr','manual')),
  active     boolean not null default true,
  created_at timestamptz not null default now(),
  unique (id, user_id)                -- med_logs 복합 FK용
);

-- 4. 복약 체크 기록
create table public.med_logs (
  id            bigint generated always as identity primary key,
  user_id       uuid not null references auth.users(id) on delete cascade,
  medication_id bigint not null,
  date          date not null,
  slot          text not null,        -- 아침/점심/저녁/자기전
  taken         boolean not null,
  created_at    timestamptz not null default now(),
  unique (user_id, medication_id, date, slot),
  -- 남의 약에 내 복용기록을 붙이는 것을 DB 차원에서 차단
  foreign key (medication_id, user_id) references public.medications(id, user_id) on delete cascade
);

-- 5. AI 상담 대화 (회원 계정 보관 · 연구 자료 아님)
create table public.chat_messages (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  role       text not null check (role in ('user','assistant')),
  content    text not null,
  created_at timestamptz not null default now()
);

-- 6. 앱 사용기록 (연구용 · 비식별 집계 원천)
--    이벤트명만 저장 — 내용·본문·위치는 어떤 경우에도 넣지 않는다
create table public.app_events (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  event      text not null check (event in
    ('app_open','chat_question','checkin_save','med_check','content_view','nearby_search')),
  created_at timestamptz not null default now()
);

-- 7. 동의 이력 (연구 동의 입증용 · 철회 시각 기록)
create table public.consent_records (
  id            bigint generated always as identity primary key,
  user_id       uuid not null references auth.users(id) on delete cascade,
  doc_version   text not null,        -- 동의문 버전 (예: 'v1 2026-09')
  terms         boolean not null,
  privacy       boolean not null,
  health_info   boolean not null,
  location      boolean not null default false,
  notifications boolean not null default false,
  consented_at  timestamptz not null default now(),
  withdrawn_at  timestamptz
);

-- 8. 푸시 구독 (기기별 · FCM 토큰/웹푸시)
create table public.push_subscriptions (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  platform   text not null check (platform in ('android','ios_web')),
  token      jsonb not null,          -- FCM 토큰 또는 웹푸시 구독 객체
  created_at timestamptz not null default now(),
  unique (user_id, platform)
);

-- ─── RLS: 전 표 본인 행만 ───
alter table public.profiles      enable row level security;
alter table public.checkins      enable row level security;
alter table public.medications   enable row level security;
alter table public.med_logs      enable row level security;
alter table public.chat_messages enable row level security;
alter table public.app_events    enable row level security;
alter table public.consent_records    enable row level security;
alter table public.push_subscriptions enable row level security;

-- 프로필은 본인 행 읽기·고치기만 (2026-09-14 보안 수정: 예전 "own profile" for all 을 둘로 쪼갬).
-- 행은 가입 트리거(handle_new_user)가 만든다 — 참여자가 자기 행을 지우고 research_code 등을 써넣어 다시 만드는 길을 막는다.
create policy "read own profile"   on public.profiles for select using (auth.uid() = id);
create policy "update own profile" on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);
create policy "own checkins" on public.checkins      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own meds"     on public.medications   for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own medlogs"  on public.med_logs      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own chats"    on public.chat_messages for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
-- 사용기록·동의는 남기기만 하고 고치거나 지울 수 없다 (연구 로그 무결성)
create policy "insert own events"   on public.app_events for insert with check (auth.uid() = user_id);
create policy "read own events"     on public.app_events for select using (auth.uid() = user_id);  -- 주간 사용 현황 표시용 (수정·삭제는 계속 불가)
create policy "insert own consent"  on public.consent_records for insert with check (auth.uid() = user_id);
create policy "read own consent"    on public.consent_records for select using (auth.uid() = user_id);
create policy "own push"            on public.push_subscriptions for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- 연구등록번호는 연구팀(service role)만 기록·수정한다
revoke insert, delete on public.profiles from authenticated, anon;   -- 2026-09-14 보안 수정 (앱은 profiles 에 insert·delete 를 하지 않는다)
revoke update on public.profiles from authenticated;
grant  update (name, birth_date, stage, subtype, stage_told, comorbidities, concerns, treatment, notif_prefs)
  on public.profiles to authenticated;

-- ─── 가입하면 프로필 자동 생성 ───
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, login_provider)
  values (
    new.id,
    new.email,
    -- 카카오·네이버는 서버 함수가 user_metadata 에 남긴 값, 구글·이메일은 수파베이스의 provider
    coalesce(
      new.raw_user_meta_data ->> 'oauth_provider',
      new.raw_app_meta_data  ->> 'provider',
      'email'
    )
  )
  on conflict (id) do update
    set email          = coalesce(public.profiles.email, excluded.email),
        login_provider = coalesce(public.profiles.login_provider, excluded.login_provider);
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 9. 앱 설정 (업데이트 배너 등 · 연구팀이 SQL로만 수정)
create table if not exists public.app_config (
  key   text primary key,
  value jsonb not null
);
alter table public.app_config enable row level security;
create policy "read config" on public.app_config for select using (true);
revoke insert, update, delete on public.app_config from authenticated, anon;
-- 새 버전 배포 시(앱 config.js appVersion 과 같게): update public.app_config set value = '{"latest":"0.9.1","note":"","url":""}' where key='version';

-- 10. 간편 로그인 신원 매핑 (서버 함수 전용 · 이메일 문자열만 믿는 계정 연결 금지)
create table if not exists public.oauth_identities (
  provider   text not null check (provider in ('kakao','naver')),
  oauth_id   text not null,
  user_id    uuid not null references auth.users(id) on delete cascade,
  email      text not null,
  created_at timestamptz not null default now(),
  primary key (provider, oauth_id)
);
alter table public.oauth_identities enable row level security;
revoke all on public.oauth_identities from authenticated, anon;

-- 11. 답변 신고 (90 화면 · more2.js page90 이 insert) — 본인 insert/select 만
--     2026-09-07 운영 DB 에 실행한 정의 그대로 옮김 (그때 유방암 폴더 사본에만 덧붙였고, 지금은 두 파일 어디에도 없었다)
create table if not exists public.answer_reports (
  id bigserial primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  message_id bigint,
  reason text not null,
  note text,
  created_at timestamptz not null default now()
);
alter table public.answer_reports enable row level security;
create policy "insert own report" on public.answer_reports for insert with check (auth.uid() = user_id);
create policy "read own report" on public.answer_reports for select using (auth.uid() = user_id);

-- 12. 알림 보낸 기록 (push-send 함수가 한 건마다 먼저 insert 해서 중복 발송을 막는다)
--     표가 없으면 insert 오류를 '이미 보냈다'로 보고 건너뛰어 알림이 한 건도 안 나간다.
--     정책 없이 RLS 만 켜서 서버 함수(service role) 전용 — oauth_identities 와 같은 방식. (토닥_DB_보안수정_260914.sql 2번)
--     참고: 운영 DB 의 이 표는 2026-09-09 에 user_id 외래키 없이 먼저 만들어졌다(9/14 문은 if not exists 라 그대로 둠).
--     push-send 는 pg_cron·pg_net 확장의 'todak-push' 일정(5분마다)으로 불린다 — 비밀 키가 들어가서 이 파일에는 적지 않는다.
create table if not exists public.push_sent (
  user_id    uuid not null references auth.users(id) on delete cascade,
  key        text not null,
  sent_on    date not null,
  created_at timestamptz not null default now(),
  primary key (user_id, key, sent_on)
);
alter table public.push_sent enable row level security;
revoke all on public.push_sent from authenticated, anon;
