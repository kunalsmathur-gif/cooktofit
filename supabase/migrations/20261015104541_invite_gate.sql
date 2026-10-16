-- Invite gate runtime support (ARCHITECTURE §9.1): richer gate decisions,
-- reply-once tracking, a manual pause switch, and per-user daily usage counters.

alter type public.gate_decision add value if not exists 'activated';
alter type public.gate_decision add value if not exists 'expired';
alter type public.gate_decision add value if not exists 'capacity_full';
alter type public.gate_decision add value if not exists 'capped';
alter type public.gate_decision add value if not exists 'paused';
alter type public.gate_decision add value if not exists 'ignored';
alter type public.gate_decision add value if not exists 'waitlist_removed';

-- Whether a reply was sent for this event; drives "one static reply per number per 30 days".
alter table public.gate_events add column replied boolean not null default false;
create index gate_events_phone_hash_at_idx on public.gate_events (phone_hash, at desc);

-- Manual kill switch; the automatic spend-based one arrives with the cost ledger.
alter table public.app_settings add column paused boolean not null default false;

-- Invites lock after this many wrong codes; the admin must reissue.
alter table public.app_settings
  add column invite_max_failed_attempts integer not null default 5
  check (invite_max_failed_attempts > 0);

create index access_list_invite_code_hash_idx on public.access_list (invite_code_hash)
  where invite_code_hash is not null;

create table public.usage_counters (
  user_id  uuid not null references public.users (id) on delete cascade,
  day      date not null,
  kind     text not null check (kind in ('message', 'photo', 'url_fetch')),
  count    integer not null default 0 check (count >= 0),
  primary key (user_id, day, kind)
);

alter table public.usage_counters enable row level security;

create policy "users read own usage" on public.usage_counters
  for select to authenticated
  using (user_id = public.current_user_id() or public.is_admin());
