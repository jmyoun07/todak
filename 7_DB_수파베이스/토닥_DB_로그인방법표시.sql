-- ═══════════════════════════════════════════════════════════
-- 토닥 — profiles 에 '로그인 방법'과 '이메일' 보이게 하기 (2026-09-14)
-- 수파베이스 대시보드 > SQL Editor 에 통째로 붙여넣고 Run
--
-- 왜 필요한가: 로그인 방법(kakao/naver/google/email)과 이메일은 auth.users 에만
--   있어서 profiles 표에서는 보이지 않는다. 가입할 때 profiles 에도 함께 적어 둔다.
-- ═══════════════════════════════════════════════════════════

-- 1) 칸 두 개 추가
alter table public.profiles
  add column if not exists login_provider text,   -- kakao | naver | google | email
  add column if not exists email          text;   -- 가입 시점의 계정 이메일 (사본)

-- 참여자가 스스로 고치지 못하게 — 쓰기 권한 목록에 넣지 않는다(기존 목록 그대로 유지)

-- 2) 앞으로 가입하는 계정은 자동으로 채워지게 (트리거 교체)
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, login_provider)
  values (
    new.id,
    new.email,
    -- 카카오·네이버는 서버 함수가 계정을 만들면서 user_metadata 에 남긴 값을 쓰고,
    -- 구글·이메일은 수파베이스가 남긴 app_metadata 의 provider 를 쓴다.
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

-- 3) 계정은 있는데 profiles 행이 없는 경우 되살리기
--    (profiles 를 지워도 auth.users 의 계정은 남는다 — 이 상태면 앱이 프로필을 못 찾는다)
insert into public.profiles (id)
select u.id
from auth.users u
left join public.profiles p on p.id = u.id
where p.id is null;

-- 4) 이미 있는 행들 채우기
update public.profiles p
set email          = coalesce(p.email, u.email),
    login_provider = coalesce(
      p.login_provider,
      u.raw_user_meta_data ->> 'oauth_provider',
      u.raw_app_meta_data  ->> 'provider',
      'email'
    )
from auth.users u
where u.id = p.id
  and (p.email is null or p.login_provider is null);

-- 5) 확인용 — 누가 어떤 방법으로 들어왔는지 한눈에
select p.id, p.login_provider, p.email, p.name, p.birth_date, p.stage, p.created_at
from public.profiles p
order by p.created_at desc;
