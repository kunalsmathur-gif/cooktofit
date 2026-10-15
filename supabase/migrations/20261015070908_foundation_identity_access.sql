-- Phase 0 foundation: identity, households, invite-only access and app settings.
-- See docs/ARCHITECTURE.md §4 and §9.1. Every table has RLS enabled; anything not
-- covered by an explicit policy is reachable only by the service role (the Brain).

create extension if not exists pg_trgm with schema extensions;
create extension if not exists vector with schema extensions;

-- ---------------------------------------------------------------- households / users
create table public.households (
  id          uuid primary key default gen_random_uuid(),
  name        text not null check (length(trim(name)) > 0),
  created_at  timestamptz not null default now()
);

create type public.persona as enum ('beginner', 'intermediate', 'advanced');

-- A user exists from invite activation (WhatsApp-first), before any web sign-in,
-- so auth.users is linked optionally.
create table public.users (
  id            uuid primary key default gen_random_uuid(),
  household_id  uuid references public.households (id) on delete set null,
  auth_user_id  uuid unique references auth.users (id) on delete set null,
  display_name  text not null check (length(trim(display_name)) > 0),
  persona       public.persona,
  timezone      text not null default 'Asia/Kolkata',
  created_at    timestamptz not null default now()
);
create index users_household_id_idx on public.users (household_id);

create type public.channel as enum ('whatsapp', 'web', 'email');

create table public.channel_identities (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.users (id) on delete cascade,
  channel      public.channel not null,
  external_id  text not null,           -- E.164 phone for whatsapp, email for web/email
  verified_at  timestamptz,
  created_at   timestamptz not null default now(),
  unique (channel, external_id)
);
create index channel_identities_user_id_idx on public.channel_identities (user_id);

-- ---------------------------------------------------------------- invite-only access
create type public.member_role as enum ('admin', 'member');
create type public.access_status as enum ('invited', 'active', 'revoked');

create table public.access_list (
  phone_e164         text primary key check (phone_e164 ~ '^\+[1-9][0-9]{7,14}$'),
  email              text check (email is null or email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
  user_id            uuid unique references public.users (id) on delete set null,
  household_id       uuid references public.households (id) on delete set null,
  display_name       text not null,
  role               public.member_role not null default 'member',
  status             public.access_status not null default 'invited',
  invited_by         uuid references public.users (id) on delete set null,
  invite_code_hash   text,
  invite_expires_at  timestamptz,
  failed_attempts    integer not null default 0 check (failed_attempts >= 0),
  activated_at       timestamptz,
  revoked_at         timestamptz,
  created_at         timestamptz not null default now(),
  check (status <> 'active' or (user_id is not null and activated_at is not null)),
  check (status <> 'revoked' or revoked_at is not null)
);
create unique index access_list_email_key on public.access_list (lower(email)) where email is not null;

create type public.gate_decision as enum ('allow', 'deny', 'waitlist', 'code_mismatch');

-- No message content is ever stored here; phone numbers are hashed.
create table public.gate_events (
  id          bigint generated always as identity primary key,
  phone_hash  text not null,
  decision    public.gate_decision not null,
  at          timestamptz not null default now()
);
create index gate_events_at_idx on public.gate_events (at);

create table public.waitlist (
  phone_e164     text primary key check (phone_e164 ~ '^\+[1-9][0-9]{7,14}$'),
  consent_at     timestamptz not null,
  source         text not null default 'whatsapp',
  first_seen_at  timestamptz not null default now(),
  attempts       integer not null default 1 check (attempts >= 1)
);

-- ---------------------------------------------------------------- app settings (singleton)
create type public.gate_mode as enum ('invite_only', 'open');
create type public.non_member_reply as enum ('silent', 'static_once_30d');

create table public.app_settings (
  id                            smallint primary key default 1 check (id = 1),
  gate_mode                     public.gate_mode not null default 'invite_only',
  non_member_reply              public.non_member_reply not null default 'silent',
  max_active_users              integer not null default 10 check (max_active_users > 0),
  invites_per_member            integer not null default 0 check (invites_per_member >= 0),
  global_monthly_budget_inr     integer not null default 1000 check (global_monthly_budget_inr >= 0),
  per_user_monthly_budget_inr   integer not null default 400 check (per_user_monthly_budget_inr >= 0),
  daily_message_cap             integer not null default 200 check (daily_message_cap > 0),
  daily_photo_cap               integer not null default 30 check (daily_photo_cap > 0),
  daily_url_fetch_cap           integer not null default 20 check (daily_url_fetch_cap > 0),
  updated_at                    timestamptz not null default now()
);

-- ---------------------------------------------------------------- helpers
create function public.current_user_id() returns uuid
language sql stable security definer set search_path = '' as $$
  select u.id from public.users u where u.auth_user_id = auth.uid()
$$;

create function public.is_admin() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.access_list a
    where a.user_id = public.current_user_id() and a.role = 'admin' and a.status = 'active'
  )
$$;

revoke execute on function public.current_user_id() from public, anon;
revoke execute on function public.is_admin() from public, anon;
grant execute on function public.current_user_id() to authenticated;
grant execute on function public.is_admin() to authenticated;

-- ---------------------------------------------------------------- row level security
alter table public.households          enable row level security;
alter table public.users               enable row level security;
alter table public.channel_identities  enable row level security;
alter table public.access_list         enable row level security;
alter table public.gate_events         enable row level security;
alter table public.waitlist            enable row level security;
alter table public.app_settings        enable row level security;

create policy "users read self and household" on public.users
  for select to authenticated
  using (
    id = public.current_user_id()
    or household_id = (select u.household_id from public.users u where u.id = public.current_user_id())
  );

create policy "members read own household" on public.households
  for select to authenticated
  using (id = (select u.household_id from public.users u where u.id = public.current_user_id()));

create policy "users read own identities" on public.channel_identities
  for select to authenticated
  using (user_id = public.current_user_id());

create policy "admins read access list" on public.access_list
  for select to authenticated using (public.is_admin());

create policy "admins read gate events" on public.gate_events
  for select to authenticated using (public.is_admin());

create policy "admins read waitlist" on public.waitlist
  for select to authenticated using (public.is_admin());

create policy "admins read settings" on public.app_settings
  for select to authenticated using (public.is_admin());
